# -*- coding: utf-8 -*-
"""showcase 数据驱动校验：计数与状态从源文件计算，源变化则输出随之变化（无硬编码）。"""
import csv
import importlib.util
import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V2_DIR = REPO_ROOT / "data" / "v2"
REGISTER = REPO_ROOT / "data" / "decisions" / "decision_register.json"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


showcase_mod = _load("build_showcase_data")
evaluator = _load("evaluate_v2")


def _copy_v2(tmp_path):
    dst = tmp_path / "v2"
    shutil.copytree(V2_DIR, dst)
    return dst


def _drop_last_row(path):
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    with path.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(rows[:-1])


def test_counts_are_computed_not_hardcoded(tmp_path):
    s = showcase_mod.build(tmp_path / "s.json", input_dir=V2_DIR)
    _, samples = evaluator.audit.read_csv_rows(V2_DIR / "samples_v2.csv")
    assert s["counts"]["samples"] == len(samples)
    assert s["hero_summary"]["platform_count"] == len({r["platform_source"] for r in samples})


def test_sample_count_changes_when_sample_removed(tmp_path):
    base = showcase_mod.build(tmp_path / "b.json", input_dir=V2_DIR)
    dst = _copy_v2(tmp_path)
    _drop_last_row(dst / "samples_v2.csv")
    changed = showcase_mod.build(tmp_path / "c.json", input_dir=dst)
    assert changed["counts"]["samples"] == base["counts"]["samples"] - 1


def test_migrated_evidence_changes_when_evidence_removed(tmp_path):
    base = showcase_mod.build(tmp_path / "b.json", input_dir=V2_DIR)
    dst = _copy_v2(tmp_path)
    _drop_last_row(dst / "evidence_v2.csv")
    changed = showcase_mod.build(tmp_path / "c.json", input_dir=dst)
    assert changed["counts"]["migrated_evidence"] == base["counts"]["migrated_evidence"] - 1


def test_label_status_changes_with_human_log(tmp_path):
    dst = _copy_v2(tmp_path)
    log = dst / "human_review_log.csv"
    with log.open("r", encoding="utf-8", newline="") as f:
        header = next(csv.reader(f))
    row = {c: "" for c in header}
    row.update({"review_event_id": "RE_T", "entity_type": "evidence", "entity_id": "NGA_0001_U01",
                "reviewer_type": "human", "review_status": "human_reviewed"})
    with log.open("a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow([row[c] for c in header])
    # 重新评测（写回 tmp），再构建 showcase
    evaluator.evaluate(input_dir=dst, output_dir=dst)
    s = showcase_mod.build(tmp_path / "s.json", input_dir=dst)
    assert s["status"]["label_review_status"] == "IN_PROGRESS"


def test_open_decisions_change_with_register(tmp_path):
    base = showcase_mod.build(tmp_path / "b.json", input_dir=V2_DIR, decisions_path=REGISTER)
    reg = json.loads(REGISTER.read_text(encoding="utf-8"))
    reg["decisions"] = reg["decisions"][:-1]  # 去掉一条
    p = tmp_path / "reg.json"
    p.write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    changed = showcase_mod.build(tmp_path / "c.json", input_dir=V2_DIR, decisions_path=p)
    assert len(changed["open_decisions"]) == len(base["open_decisions"]) - 1


def test_repo_ref_switches_links(tmp_path):
    main_s = showcase_mod.build(tmp_path / "m.json", input_dir=V2_DIR, repo_ref="main")
    for url in main_s["doc_links"].values():
        assert "/main/" in url or url.endswith("/main")
    assert main_s["repo_ref"] == "main"


def test_no_hardcoded_status_string(tmp_path):
    s = showcase_mod.build(tmp_path / "s.json", input_dir=V2_DIR)
    # 状态来自评测报告（PASS/NOT_STARTED），hero_status 用自然语言
    labels = {x["label"]: x["value"] for x in s["hero_status"]}
    assert labels["结构校验"] == "已通过"
    assert labels["当前编码"] == "规则基线"


def test_per_platform_value_when_equal(tmp_path):
    """各平台数量完全相等时才输出 per_platform，且等于分布公共值（非整数除法推定）。"""
    s = showcase_mod.build(tmp_path / "s.json", input_dir=V2_DIR)
    assert s["counts"]["all_platforms_equal"] is True
    assert isinstance(s["counts"]["per_platform"], int)
    dist_values = set(s["counts"]["platform_distribution"].values())
    assert dist_values == {s["counts"]["per_platform"]}
    assert "各" in s["hero_summary"]["per_platform_text"]


def test_per_platform_none_when_unequal(tmp_path):
    """各平台数量不等时 per_platform 为 None，不推定；分布仍完整给出。"""
    dst = _copy_v2(tmp_path)
    sp = dst / "samples_v2.csv"
    with sp.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header, body = rows[0], rows[1:]
    with sp.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([header] + body[:-5])  # 去掉 5 行，破坏平台间相等
    s = showcase_mod.build(tmp_path / "s.json", input_dir=dst)
    assert s["counts"]["all_platforms_equal"] is False
    assert s["counts"]["per_platform"] is None
    dist = s["counts"]["platform_distribution"]
    assert len(set(dist.values())) > 1
    assert "不等" in s["hero_summary"]["per_platform_text"]


def test_case_name_is_dynamic(tmp_path):
    """案例名由数据计算（含实际平台数），不写死。"""
    s = showcase_mod.build(tmp_path / "s.json", input_dir=V2_DIR)
    assert str(s["hero_summary"]["platform_count"]) in s["hero_summary"]["case"]


def test_evidence_example_prefers_public_dataset(tmp_path):
    """默认优先使用已脱敏的公开证据 data/public/evidence_public.csv。"""
    s = showcase_mod.build(tmp_path / "s.json", input_dir=V2_DIR)
    ex = s["evidence_example"]
    assert ex["source"] == "public_dataset"
    assert "http://" not in ex["sample_excerpt"] and "https://" not in ex["sample_excerpt"]


def test_evidence_example_fallback_is_sanitized(tmp_path):
    """回退到 provisional 时用与 public dataset 相同的脱敏函数处理。"""
    dst = _copy_v2(tmp_path)
    pp = dst / "evidence_provisional_v2.csv"
    with pp.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    for r in rows:
        if r.get("label_source") == "legacy_ai":
            r["unit_text"] = "泄露 http://evil.example.com/leak " + r["unit_text"]
            break
    with pp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    empty_pub = tmp_path / "empty_public"
    empty_pub.mkdir()
    s = showcase_mod.build(tmp_path / "s.json", input_dir=dst, public_dir=empty_pub)
    ex = s["evidence_example"]
    assert ex["source"] == "provisional_sanitized"
    assert "http://" not in ex["sample_excerpt"]
    assert "[链接已移除]" in ex["sample_excerpt"]
