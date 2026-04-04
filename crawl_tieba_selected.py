import argparse
import html
import json
import os
import random
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
]

SECURITY_MARKERS = [
    "安全验证",
    "BIOC_OPTIONS",
    "bfe_captcha",
    "seccaptcha.baidu.com",
    "window.BIOC_OPTIONS",
]

OUTPUT_COLUMNS = [
    "record_id",
    "platform_source",
    "window_tag",
    "theme_bucket",
    "thread_or_video_title",
    "url",
    "publish_time",
    "reply_type",
    "raw_text",
    "keep_manual",
    "thread_tid",
    "post_id",
    "post_no",
    "author_name",
    "comment_num",
]


def canonical_tid(url: str) -> Optional[str]:
    m = re.search(r"tieba\.baidu\.com/p/(\d+)", str(url))
    return m.group(1) if m else None


def build_thread_url(tid: str, pn: int = 1, only_lz: bool = False) -> str:
    base = f"https://tieba.baidu.com/p/{tid}"
    params = [f"pn={pn}"]
    if only_lz:
        params.append("see_lz=1")
    return base + "?" + "&".join(params)


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text: str) -> str:
    t = html.unescape(str(text))
    t = re.sub(r"^回复\s*\d+楼[:：]?\s*", "", t)
    t = re.sub(r"^楼中楼[:：]?\s*", "", t)
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"\[[^\]]{1,20}\]", " ", t)
    t = re.sub(r"回复\s*@?\S+", " ", t)
    return normalize_ws(t)


def load_cookie_string(cookie_string: str = "", cookie_file: str = "") -> str:
    value = (cookie_string or "").strip() or os.getenv("TIEBA_COOKIE", "").strip()
    if value:
        return value
    if cookie_file:
        path = Path(cookie_file)
        if path.exists():
            return path.read_text(encoding="utf-8", errors="ignore").strip()
    return ""


def make_session(cookie_string: Optional[str] = None) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": "https://tieba.baidu.com/",
            "Upgrade-Insecure-Requests": "1",
        }
    )
    if cookie_string:
        s.headers["Cookie"] = cookie_string
    return s


def is_security_page(text: str) -> bool:
    sample = text[:8000] if text else ""
    return any(marker in sample for marker in SECURITY_MARKERS)


def write_debug_html(debug_path: Optional[Path], text: str) -> None:
    if debug_path is None:
        return
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    debug_path.write_text(text or "", encoding="utf-8", errors="ignore")


def fetch(
    session: requests.Session,
    url: str,
    timeout: int = 20,
    debug_path: Optional[Path] = None,
    retries: int = 2,
) -> str:
    last_error = None
    for attempt in range(retries + 1):
        try:
            session.headers["User-Agent"] = random.choice(USER_AGENTS)
            r = session.get(url, timeout=timeout, allow_redirects=True)
            status = r.status_code
            r.encoding = r.apparent_encoding or r.encoding or "utf-8"
            text = r.text or ""
            if status in {403, 418, 429} or is_security_page(text):
                write_debug_html(debug_path, text)
                raise RuntimeError(f"security_block status={status} url={r.url}")
            if "帖子不存在" in text or "帖子已被删除" in text or "内容暂不可见" in text:
                write_debug_html(debug_path, text)
                raise RuntimeError(f"thread_unavailable status={status} url={r.url}")
            if len(text) < 500:
                write_debug_html(debug_path, text)
                raise RuntimeError(f"empty_or_short_html status={status} url={r.url}")
            return text
        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(1.2 + random.random() * 0.8)
            else:
                raise
    raise RuntimeError(str(last_error))


def parse_total_pages(soup: BeautifulSoup) -> int:
    candidates = []
    for a in soup.select("a[href*='?pn='], a[href*='&pn=']"):
        href = a.get("href") or ""
        m = re.search(r"[?&]pn=(\d+)", href)
        if m:
            candidates.append(int(m.group(1)))
    txt = soup.get_text(" ", strip=True)
    m2 = re.search(r"共\s*(\d+)\s*页", txt)
    if m2:
        candidates.append(int(m2.group(1)))
    return max(candidates) if candidates else 1


def safe_json_loads(raw: str) -> Dict:
    try:
        return json.loads(html.unescape(raw)) if raw else {}
    except Exception:
        return {}


def extract_post(node) -> Optional[Dict]:
    data_field = node.get("data-field") or ""
    info = safe_json_loads(data_field)
    content_info = info.get("content", {}) if isinstance(info, dict) else {}
    author_info = info.get("author", {}) if isinstance(info, dict) else {}

    content_node = (
        node.select_one("div.d_post_content.j_d_post_content")
        or node.select_one("div.d_post_content")
        or node.select_one("div[id^='post_content_']")
    )
    if not content_node:
        return None
    raw = content_node.get_text(" ", strip=True)
    cleaned = clean_text(raw)
    if not cleaned:
        return None
    return {
        "post_id": str(content_info.get("post_id", "")),
        "post_no": int(content_info.get("post_no", 0) or 0),
        "publish_time": str(content_info.get("date", "")),
        "author_name": str(author_info.get("user_name", "")),
        "comment_num": int(content_info.get("comment_num", 0) or 0),
        "raw_text": cleaned,
    }


def parse_posts_from_html(html_text: str) -> List[Dict]:
    soup = BeautifulSoup(html_text, "html.parser")
    posts: List[Dict] = []

    # Primary parser: classic Tieba structure.
    for node in soup.select("div.l_post, li.l_post, div.j_l_post, li.j_l_post"):
        post = extract_post(node)
        if post:
            posts.append(post)

    # Fallback parser: find content blocks first, then walk upwards to parent with data-field.
    if not posts:
        for content_node in soup.select("div[id^='post_content_'], div.d_post_content"):
            parent = content_node.find_parent(attrs={"data-field": True})
            if not parent:
                continue
            post = extract_post(parent)
            if post:
                posts.append(post)

    # Last-resort regex parser for old/static HTML dumps.
    if not posts:
        pattern = re.compile(
            r"data-field=([\"'])(?P<data>.*?)\1[^>]*>.*?(?:id=[\"']post_content_\d+[\"']|class=[\"'][^\"']*d_post_content[^\"']*[\"'])[^>]*>(?P<html>.*?)</div>",
            flags=re.S,
        )
        for m in pattern.finditer(html_text):
            info = safe_json_loads(m.group("data"))
            content_info = info.get("content", {}) if isinstance(info, dict) else {}
            author_info = info.get("author", {}) if isinstance(info, dict) else {}
            cleaned = clean_text(BeautifulSoup(m.group("html"), "html.parser").get_text(" ", strip=True))
            if cleaned:
                posts.append(
                    {
                        "post_id": str(content_info.get("post_id", "")),
                        "post_no": int(content_info.get("post_no", 0) or 0),
                        "publish_time": str(content_info.get("date", "")),
                        "author_name": str(author_info.get("user_name", "")),
                        "comment_num": int(content_info.get("comment_num", 0) or 0),
                        "raw_text": cleaned,
                    }
                )

    return posts


def load_selected(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    if "keep_recommended" in df.columns:
        df = df[df["keep_recommended"] == 1].copy()
    df["tid"] = df["url"].apply(canonical_tid)
    return df[df["tid"].notna()].copy()


def dedupe_records(rows: List[Dict]) -> List[Dict]:
    seen = set()
    kept = []
    for r in rows:
        key = (r.get("url", ""), r.get("post_id", ""), r.get("raw_text", ""))
        if key in seen:
            continue
        seen.add(key)
        kept.append(r)
    return kept


def find_local_html_pages(tid: str, html_dir: Path) -> List[Tuple[int, Path]]:
    candidates = []
    for p in html_dir.glob(f"{tid}*.html"):
        m = re.search(r"(?:_p|_pn|_page)(\d+)", p.stem)
        page_no = int(m.group(1)) if m else 1
        candidates.append((page_no, p))
    return sorted(candidates, key=lambda x: (x[0], x[1].name))


def load_pages_for_thread(
    session: requests.Session,
    tid: str,
    max_pages: int,
    only_lz: bool,
    sleep_sec: float,
    debug_html_dir: Optional[Path],
    local_html_dir: Optional[Path],
) -> List[str]:
    local_pages: List[Tuple[int, Path]] = []
    if local_html_dir:
        local_pages = find_local_html_pages(tid, local_html_dir)
    if local_pages:
        html_pages = []
        for page_no, path in local_pages[:max_pages]:
            html_pages.append(path.read_text(encoding="utf-8", errors="ignore"))
        return html_pages

    first_url = build_thread_url(tid, pn=1, only_lz=only_lz)
    first_debug = debug_html_dir / f"{tid}_p1.html" if debug_html_dir else None
    first_html = fetch(session, first_url, debug_path=first_debug)
    soup = BeautifulSoup(first_html, "html.parser")
    total_pages = min(parse_total_pages(soup), max_pages)

    html_pages = [first_html]
    for pn in range(2, total_pages + 1):
        time.sleep(sleep_sec + random.random() * 0.5)
        debug_path = debug_html_dir / f"{tid}_p{pn}.html" if debug_html_dir else None
        html_pages.append(fetch(session, build_thread_url(tid, pn=pn, only_lz=only_lz), debug_path=debug_path))
    return html_pages


def build_feedback_rows_for_thread(
    session: requests.Session,
    selected_row: pd.Series,
    max_pages: int,
    max_replies_per_thread: int,
    min_text_len: int,
    sleep_sec: float,
    only_lz: bool,
    debug_html_dir: Optional[Path],
    local_html_dir: Optional[Path],
) -> List[Dict]:
    tid = str(selected_row["tid"])
    html_pages = load_pages_for_thread(
        session=session,
        tid=tid,
        max_pages=max_pages,
        only_lz=only_lz,
        sleep_sec=sleep_sec,
        debug_html_dir=debug_html_dir,
        local_html_dir=local_html_dir,
    )

    collected = []
    for html_text in html_pages:
        posts = parse_posts_from_html(html_text)
        for p in posts:
            if len(p["raw_text"]) < min_text_len:
                continue
            collected.append(p)

    if not collected:
        raise RuntimeError("no_posts_parsed")

    collected = sorted(collected, key=lambda x: (x["post_no"] if x["post_no"] else 999999))
    op_rows = [p for p in collected if p["post_no"] == 1][:1]
    reply_rows = [p for p in collected if p["post_no"] != 1][:max_replies_per_thread]
    final_posts = op_rows + reply_rows

    out = []
    for idx, p in enumerate(final_posts, start=1):
        out.append(
            {
                "record_id": f"TIEBA_{tid}_{idx:03d}",
                "platform_source": "Tieba",
                "window_tag": selected_row.get("window_tag", ""),
                "theme_bucket": selected_row.get("theme_bucket", ""),
                "thread_or_video_title": selected_row.get("title", ""),
                "url": selected_row.get("url", ""),
                "publish_time": p.get("publish_time", ""),
                "reply_type": "op_context" if p.get("post_no") == 1 else "recent_reply",
                "raw_text": p.get("raw_text", ""),
                "keep_manual": 1,
                "thread_tid": tid,
                "post_id": p.get("post_id", ""),
                "post_no": p.get("post_no", ""),
                "author_name": p.get("author_name", ""),
                "comment_num": p.get("comment_num", ""),
            }
        )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selected", required=True, help="phase2_seed_registry_tieba_selected.csv")
    ap.add_argument("--output", required=True, help="feedback_registry_tieba.csv")
    ap.add_argument("--summary", default="", help="optional summary csv path")
    ap.add_argument("--cookie-string", default="")
    ap.add_argument("--cookie-file", default="", help="optional text file containing full Tieba cookie header")
    ap.add_argument("--debug-html-dir", default="", help="save blocked/raw html here for inspection")
    ap.add_argument("--local-html-dir", default="", help="read locally saved html files here before live fetching")
    ap.add_argument("--max-pages-per-thread", type=int, default=3)
    ap.add_argument("--max-replies-per-thread", type=int, default=8)
    ap.add_argument("--min-text-len", type=int, default=8)
    ap.add_argument("--sleep-sec", type=float, default=1.0)
    ap.add_argument("--only-lz", action="store_true")
    args = ap.parse_args()

    selected = load_selected(Path(args.selected))
    cookie_string = load_cookie_string(args.cookie_string, args.cookie_file)
    session = make_session(cookie_string)
    debug_html_dir = Path(args.debug_html_dir) if args.debug_html_dir else None
    local_html_dir = Path(args.local_html_dir) if args.local_html_dir else None

    all_rows = []
    summary_rows = []
    for _, row in selected.iterrows():
        tid = str(row["tid"])
        try:
            rows = build_feedback_rows_for_thread(
                session=session,
                selected_row=row,
                max_pages=args.max_pages_per_thread,
                max_replies_per_thread=args.max_replies_per_thread,
                min_text_len=args.min_text_len,
                sleep_sec=args.sleep_sec,
                only_lz=args.only_lz,
                debug_html_dir=debug_html_dir,
                local_html_dir=local_html_dir,
            )
            rows = dedupe_records(rows)
            all_rows.extend(rows)
            summary_rows.append(
                {
                    "tid": tid,
                    "title": row.get("title", ""),
                    "window_tag": row.get("window_tag", ""),
                    "theme_bucket": row.get("theme_bucket", ""),
                    "kept_rows": len(rows),
                    "kept_op": sum(1 for r in rows if r["reply_type"] == "op_context"),
                    "kept_reply": sum(1 for r in rows if r["reply_type"] != "op_context"),
                    "url": row.get("url", ""),
                    "source_mode": "local_html" if local_html_dir and find_local_html_pages(tid, local_html_dir) else "live_fetch",
                }
            )
        except Exception as e:
            summary_rows.append(
                {
                    "tid": tid,
                    "title": row.get("title", ""),
                    "window_tag": row.get("window_tag", ""),
                    "theme_bucket": row.get("theme_bucket", ""),
                    "kept_rows": 0,
                    "kept_op": 0,
                    "kept_reply": 0,
                    "url": row.get("url", ""),
                    "error": str(e),
                    "source_mode": "local_html" if local_html_dir and find_local_html_pages(tid, local_html_dir) else "live_fetch",
                }
            )
        time.sleep(args.sleep_sec + random.random() * 0.5)

    out_df = pd.DataFrame(all_rows)
    if not out_df.empty:
        out_df.to_csv(args.output, index=False, encoding="utf-8-sig")
    else:
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(args.output, index=False, encoding="utf-8-sig")

    summary_path = args.summary or str(Path(args.output).with_name("feedback_registry_tieba_summary.csv"))
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(f"Saved {len(out_df)} rows to {args.output}")
    print(f"Saved summary to {summary_path}")


if __name__ == "__main__":
    main()
