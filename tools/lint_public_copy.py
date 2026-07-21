#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PsyLens 公开文案检查工具。

用途：扫描面向读者的展示与方法文件，标记不利于普通读者理解的表达，
并给出问题类型、优先级和改写提示。工具只做发现与提醒，不自动改写整段
文本；改写由人工或 Agent 逐项确认后完成，以免自动替换改变原意。

默认扫描：README.md、docs/**/*.md、docs/index.html、pipeline/**/*.md、
demo/**/*.md、tools/**/*.py、demo/src/**/*.py。

用法：
    python tools/lint_public_copy.py --root . --format markdown
    python tools/lint_public_copy.py --strict   # 存在 P0 问题时以非零码退出

输出字段：file_path, line_number, original_text, issue_type,
reader_impact, suggested_text, action, priority。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
DEFAULT_CONFIG = REPO_ROOT / "config" / "public_copy_rules.yaml"

DEFAULT_TARGET_GLOBS = [
    "README.md",
    "docs/**/*.md",
    "docs/index.html",
    "pipeline/**/*.md",
    "demo/**/*.md",
    "tools/**/*.py",
    "demo/src/**/*.py",
]

# 若未安装 PyYAML 或配置缺失时使用的内置默认规则。
DEFAULT_RULES = {
    "banned_phrases": ["赋能", "打通", "深度洞察", "全链路", "全方位", "值得注意的是",
                       "不难发现", "显而易见", "站得住", "普通语言"],
    "discouraged_phrases": ["质量风险", "做不了", "无法使用", "不可用", "缺失字段", "字段缺失"],
    "technical_terms": ["构念", "语义链路", "grounding", "adjudication", "标签熵",
                        "calibration", "abstain", "schema", "pipeline", "deterministic",
                        "混淆矩阵", "Kappa", "Alpha"],
    "internal_process_terms": ["BLOCKED", "发布阻断", "返修", "phase1/", "phase2/", "Issue #"],
    "repeated_status_terms": ["未人工复核", "尚未人工复核", "待人工复核", "人工复核", "不确定率"],
    "allowed_files": ["docs/CONTENT_STYLE_GUIDE.md", "config/public_copy_rules.yaml",
                      "tools/lint_public_copy.py"],
    "excluded_paths": ["data", "artifacts", "archive", ".git", "tests/fixtures", "docs/files"],
    "max_sentence_length": 60,
    "max_unexplained_terms_per_sentence": 3,
    "max_repeated_status_per_file": 3,
}

# 展示层文件（内部工程词在这些文件里判 P1）。
DISPLAY_FILES = {"README.md", "docs/index.html"}

ISSUE_META = {
    "template_phrase": ("P0", "rewrite", "模板化空话，读者得不到具体信息"),
    "negative_framing": ("P1", "rewrite", "以项目不足为主线，削弱可读性与信任"),
    "not_this_but_that": ("P0", "rewrite", "“不是……而是……”句式绕弯，读者需二次解析"),
    "internal_process_language": ("P1", "move_to_issue", "内部工程状态进入展示层，与读者决策无关"),
    "repeated_status": ("P1", "move_to_method_doc", "同一状态反复提醒，建议集中说明一次"),
    "long_sentence": ("P2", "rewrite", "句子过长，读者难以一次读懂"),
    "technical_term_overload": ("P2", "rewrite", "单句术语堆叠，首次出现缺少中文解释"),
}


def _coerce(v):
    v = v.strip().strip('"').strip("'")
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v


def parse_simple_yaml(text):
    """解析本项目使用的简单 YAML（标量、字符串列表），不依赖 PyYAML。

    仅支持：顶层 ``key: value``、``key:`` 后跟 ``  - item`` 列表、整行注释。
    值中允许出现 ``#``（如 ``Issue #``），因此不做行内注释剥离。
    """
    data = {}
    key = None
    for raw in text.splitlines():
        if raw.strip().startswith("#") or not raw.strip():
            continue
        if raw.lstrip().startswith("- "):
            item = raw.lstrip()[2:]
            if key is not None and isinstance(data.get(key), list):
                data[key].append(_coerce(item))
            continue
        if ":" in raw and not raw.startswith((" ", "\t")):
            k, _, v = raw.partition(":")
            k = k.strip()
            if v.strip() == "":
                data[k] = []
                key = k
            else:
                data[k] = _coerce(v)
                key = None
    return data


def load_rules(config_path):
    rules = dict(DEFAULT_RULES)
    p = Path(config_path)
    if not p.exists():
        return rules
    text = p.read_text(encoding="utf-8")
    loaded = None
    try:
        import yaml  # noqa: PLC0415
        loaded = yaml.safe_load(text)
    except Exception:  # noqa: BLE001
        loaded = parse_simple_yaml(text)
    if isinstance(loaded, dict):
        rules.update({k: v for k, v in loaded.items() if v is not None})
    return rules


def _rel(path):
    try:
        return Path(path).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


def _is_excluded(rel_path, excluded):
    parts = rel_path.split("/")
    for ex in excluded:
        ex = ex.strip("/")
        if rel_path == ex or rel_path.startswith(ex + "/") or ex in parts:
            return True
    return False


def collect_files(root, target_globs, excluded, extra_exclude):
    root = Path(root)
    seen = {}
    for pattern in target_globs:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            rel = _rel(path)
            if _is_excluded(rel, list(excluded) + list(extra_exclude)):
                continue
            seen[rel] = path
    return list(seen.items())


# 句子切分：按中文句末标点与换行切分。
_SENT_SPLIT = re.compile(r"[。！？；\n]")
# 从 Markdown/HTML 行中提取可读文本时移除的语法噪声。
_MD_NOISE = re.compile(r"(```.*?```|`[^`]*`|<[^>]+>|\[[^\]]*\]\([^)]*\)|https?://\S+|[#>*_|\-])")


def _clean_line(line):
    return _MD_NOISE.sub(" ", line)


def _has_explanation(sentence):
    return any(mark in sentence for mark in ("：", ":", "指", "表示", "例如", "即", "是指", "用来", "用于"))


def _iter_text_lines(path, rel):
    """返回 [(line_number, raw_line, text_for_check)]。

    .py 文件仅检查含中文的注释与字符串行（近似用户可见文案）。
    """
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out = []
    is_py = rel.endswith(".py")
    for i, raw in enumerate(lines, start=1):
        if is_py:
            stripped = raw.strip()
            has_cjk = re.search(r"[\u4e00-\u9fff]", raw)
            looks_text = stripped.startswith("#") or ('"' in raw) or ("'" in raw)
            if not (has_cjk and looks_text):
                continue
        out.append((i, raw, _clean_line(raw)))
    return out


def lint_file(path, rel, rules):
    findings = []
    exempt = rel in set(rules.get("allowed_files", []))
    banned = rules.get("banned_phrases", [])
    discouraged = rules.get("discouraged_phrases", [])
    tech = rules.get("technical_terms", [])
    internal = rules.get("internal_process_terms", [])
    status_terms = rules.get("repeated_status_terms", [])
    max_len = int(rules.get("max_sentence_length", 60))
    max_terms = int(rules.get("max_unexplained_terms_per_sentence", 3))
    max_status = int(rules.get("max_repeated_status_per_file", 3))
    is_display = rel in DISPLAY_FILES

    status_hits = 0

    for lineno, raw, text in _iter_text_lines(path, rel):
        # 内部工程语言（展示层）
        if is_display:
            for term in internal:
                if term in raw:
                    findings.append(_mk(rel, lineno, raw.strip(), "internal_process_language",
                                        f"改为读者可用信息或移入 Issue/PR：{term}"))
        if exempt:
            # 白名单文件仍统计重复状态，但不判模板/负面/术语
            status_hits += sum(text.count(t) for t in status_terms)
            continue

        # P0：不是……而是……
        if re.search(r"不是[^，。；！？]{0,40}而是", text):
            findings.append(_mk(rel, lineno, raw.strip(), "not_this_but_that",
                                "改为直接陈述结论"))
        # P0：模板空话
        for phrase in banned:
            if phrase in text:
                findings.append(_mk(rel, lineno, raw.strip(), "template_phrase",
                                    f"删除或替换为具体事实：{phrase}"))
        # P1：负面框架
        for phrase in discouraged:
            if phrase in text:
                findings.append(_mk(rel, lineno, raw.strip(), "negative_framing",
                                    f"改为能力、覆盖率或校准动作：{phrase}"))

        status_hits += sum(text.count(t) for t in status_terms)

        # 逐句检查长度与术语堆叠
        for sent in _SENT_SPLIT.split(text):
            s = sent.strip()
            if not s:
                continue
            cjk_len = len(re.sub(r"\s", "", s))
            if cjk_len > max_len:
                findings.append(_mk(rel, lineno, s[:60], "long_sentence",
                                    "拆成两三句或改用编号/表格"))
            term_count = sum(1 for t in tech if t in s)
            if term_count >= max_terms and not _has_explanation(s):
                findings.append(_mk(rel, lineno, s[:60], "technical_term_overload",
                                    "首次出现的术语补充中文解释，或拆句"))

    if not exempt and status_hits > max_status:
        findings.append(_mk(rel, 0, f"重复状态提醒出现约 {status_hits} 次", "repeated_status",
                            "适用范围与复核状态集中说明一次"))
    return findings


def _mk(file_path, line_number, original_text, issue_type, suggested_text):
    priority, action, impact = ISSUE_META[issue_type]
    return {
        "file_path": file_path,
        "line_number": line_number,
        "original_text": original_text,
        "issue_type": issue_type,
        "reader_impact": impact,
        "suggested_text": suggested_text,
        "action": action,
        "priority": priority,
    }


FIELDS = ["file_path", "line_number", "original_text", "issue_type",
          "reader_impact", "suggested_text", "action", "priority"]


def run(root, config_path, target_globs=None, extra_exclude=None, allowlist=None):
    rules = load_rules(config_path)
    if allowlist:
        rules["allowed_files"] = list(rules.get("allowed_files", [])) + list(allowlist)
    globs = target_globs or DEFAULT_TARGET_GLOBS
    files = collect_files(root, globs, rules.get("excluded_paths", []), extra_exclude or [])
    findings = []
    for rel, path in files:
        findings.append((rel, path))
    all_findings = []
    for rel, path in files:
        all_findings.extend(lint_file(path, rel, rules))
    return all_findings, [rel for rel, _ in files]


def render_markdown(findings, scanned):
    from collections import Counter
    by_type = Counter(f["issue_type"] for f in findings)
    by_file = Counter(f["file_path"] for f in findings)
    by_pri = Counter(f["priority"] for f in findings)
    lines = ["# 公开文案检查报告", ""]
    lines.append(f"- 扫描文件：{len(scanned)}")
    lines.append(f"- 发现问题：{len(findings)}")
    lines.append(f"- 优先级分布：P0={by_pri.get('P0', 0)}、P1={by_pri.get('P1', 0)}、P2={by_pri.get('P2', 0)}")
    lines.append("")
    lines.append("## 问题类型分布")
    for t, n in by_type.most_common():
        lines.append(f"- {t}：{n}")
    lines.append("")
    lines.append("## 问题最多的文件")
    for f, n in by_file.most_common(10):
        lines.append(f"- {f}：{n}")
    lines.append("")
    lines.append("## 明细")
    lines.append("")
    lines.append("| 文件 | 行 | 类型 | 优先级 | 建议 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for f in findings:
        lines.append(f"| {f['file_path']} | {f['line_number']} | {f['issue_type']} | "
                     f"{f['priority']} | {f['suggested_text']} |")
    return "\n".join(lines) + "\n"


def write_output(findings, scanned, out_path, fmt):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        payload = {
            "scanned_file_count": len(scanned),
            "finding_count": len(findings),
            "scanned_files": scanned,
            "findings": findings,
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    elif fmt == "csv":
        with out_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            w.writeheader()
            for f in findings:
                w.writerow(f)
    else:  # markdown
        out_path.write_text(render_markdown(findings, scanned), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="扫描公开展示与方法文件，标记不利于阅读的表达（发现工具，不自动改写）")
    ap.add_argument("--root", default=str(REPO_ROOT), help="扫描根目录，默认仓库根")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="规则配置，默认 config/public_copy_rules.yaml")
    ap.add_argument("--output", default=None, help="输出文件路径；不指定则打印到标准输出")
    ap.add_argument("--format", choices=["json", "markdown", "csv"], default="markdown")
    ap.add_argument("--strict", action="store_true", help="存在 P0 问题时以退出码 1 结束")
    ap.add_argument("--exclude", action="append", default=[], help="额外排除目录，可多次指定")
    ap.add_argument("--allowlist", action="append", default=[], help="额外豁免文件（相对路径），可多次指定")
    args = ap.parse_args(argv)

    findings, scanned = run(args.root, args.config, extra_exclude=args.exclude, allowlist=args.allowlist)
    p0 = [f for f in findings if f["priority"] == "P0"]

    if args.output:
        write_output(findings, scanned, args.output, args.format)
        print(f"公开文案检查完成：扫描 {len(scanned)} 个文件，发现 {len(findings)} 处问题"
              f"（P0={len(p0)}）。报告写入 {args.output}")
    else:
        if args.format == "json":
            print(json.dumps({"scanned_file_count": len(scanned), "finding_count": len(findings),
                              "findings": findings}, ensure_ascii=False, indent=2))
        elif args.format == "csv":
            w = csv.DictWriter(sys.stdout, fieldnames=FIELDS)
            w.writeheader()
            for f in findings:
                w.writerow(f)
        else:
            print(render_markdown(findings, scanned))

    if args.strict and p0:
        print(f"strict 模式：存在 {len(p0)} 处 P0 问题，需先改写。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
