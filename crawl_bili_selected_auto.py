import argparse
import csv
import hashlib
import json
import os
import random
import re
import time
import urllib.parse
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]

RELEVANT_PATTERNS = {
    "balance_mechanic": [
        r"平衡", r"机制", r"数值", r"装备", r"海克斯", r"套路", r"玩法", r"理解", r"操作",
        r"强度", r"削弱", r"增强", r"节奏", r"随机", r"吃熟练", r"不会玩", r"会玩",
    ],
    "hero_experience": [
        r"英雄", r"角色", r"ad", r"ap", r"坦克", r"刺客", r"射手", r"法师", r"战士",
        r"拿到", r"选到", r"某个英雄", r"手感", r"熟练度",
    ],
    "team_interaction": [
        r"队友", r"开摆", r"送", r"挂机", r"配合", r"沟通", r"喷", r"心态", r"上头",
        r"阵容", r"匹配到", r"四个", r"不会玩", r"一起", r"队伍",
    ],
    "fairness_attribution": [
        r"公平", r"不公平", r"运气", r"随机", r"匹配", r"机制问题", r"规则", r"系统",
        r"恶心", r"坐牢", r"没法玩", r"不讲道理", r"偏袒",
    ],
}

NEGATIVE_PATTERNS = [
    r"哈哈哈", r"笑死", r"路过", r"打卡", r"前排", r"加油", r"UP", r"来了", r"签到",
    r"催更", r"好看", r"支持", r"牛", r"卧槽", r"纯路人", r"表情", r"doge",
]


def load_cookie_string(path: Optional[str]) -> str:
    if not path or not os.path.exists(path):
        return ""
    text = open(path, "r", encoding="utf-8").read().strip()
    if "\n" in text:
        parts = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                parts.append(f"{k.strip()}={v.strip()}")
        return "; ".join(parts)
    return text


def clean_text(text: str) -> str:
    text = str(text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_bvid(url: str) -> Optional[str]:
    if not isinstance(url, str):
        return None
    m = re.search(r"BV[0-9A-Za-z]+", url)
    return m.group(0) if m else None


def parse_desc(row: pd.Series) -> str:
    for col in ["desc", "description", "title", "summary", "snippet"]:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            return str(row[col]).strip()
    return ""


@dataclass
class VideoInfo:
    bvid: str
    aid: int
    title: str
    desc: str
    url: str


class BiliClient:
    def __init__(self, cookie_string: str = "", sleep_sec: float = 1.2):
        self.session = requests.Session()
        self.sleep_sec = sleep_sec
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://www.bilibili.com/",
            "Origin": "https://www.bilibili.com",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        if cookie_string:
            headers["Cookie"] = cookie_string
        self.session.headers.update(headers)
        self._wbi_keys: Optional[Tuple[str, str]] = None
        self._wbi_keys_ts: float = 0.0

    def _sleep(self):
        time.sleep(self.sleep_sec + random.uniform(0.1, 0.35))

    def get_json(self, url: str, params: Optional[dict] = None) -> dict:
        r = self.session.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json()

    def get_video_info(self, bvid: str) -> Optional[VideoInfo]:
        data = self.get_json("https://api.bilibili.com/x/web-interface/view", {"bvid": bvid})
        if data.get("code") != 0 or not data.get("data"):
            return None
        d = data["data"]
        return VideoInfo(
            bvid=bvid,
            aid=int(d.get("aid", 0)),
            title=clean_text(d.get("title", "")),
            desc=clean_text(d.get("desc", "")),
            url=f"https://www.bilibili.com/video/{bvid}",
        )

    def _fetch_wbi_keys(self) -> Tuple[str, str]:
        if self._wbi_keys and (time.time() - self._wbi_keys_ts) < 3600:
            return self._wbi_keys
        data = self.get_json("https://api.bilibili.com/x/web-interface/nav")
        wbi = (data.get("data") or {}).get("wbi_img") or {}
        img_url = wbi.get("img_url", "")
        sub_url = wbi.get("sub_url", "")
        if not img_url or not sub_url:
            raise RuntimeError("无法从 nav 接口获取 wbi_img 密钥")
        img_key = img_url.rsplit("/", 1)[-1].split(".")[0]
        sub_key = sub_url.rsplit("/", 1)[-1].split(".")[0]
        self._wbi_keys = (img_key, sub_key)
        self._wbi_keys_ts = time.time()
        return self._wbi_keys

    def _get_mixin_key(self, img_key: str, sub_key: str) -> str:
        raw = img_key + sub_key
        return "".join(raw[i] for i in MIXIN_KEY_ENC_TAB)[:32]

    def _sign_wbi(self, params: dict) -> dict:
        img_key, sub_key = self._fetch_wbi_keys()
        mixin_key = self._get_mixin_key(img_key, sub_key)
        signed = dict(params)
        signed["wts"] = int(time.time())
        # Filter special chars per common WBI handling
        filtered = {}
        for k, v in signed.items():
            v = str(v)
            v = re.sub(r"[!'()*]", "", v)
            filtered[k] = v
        query = urllib.parse.urlencode(sorted(filtered.items()))
        signed["w_rid"] = hashlib.md5((query + mixin_key).encode("utf-8")).hexdigest()
        return signed

    def fetch_comment_page(self, oid: int, mode: int = 3, pagination_offset: Optional[str] = None) -> dict:
        params = {
            "oid": oid,
            "type": 1,
            "mode": mode,
            "plat": 1,
            "web_location": 1315875,
        }
        if pagination_offset:
            params["pagination_str"] = json.dumps({"offset": pagination_offset}, ensure_ascii=False, separators=(",", ":"))
        else:
            params["seek_rpid"] = ""
        params = self._sign_wbi(params)
        data = self.get_json("https://api.bilibili.com/x/v2/reply/wbi/main", params=params)
        self._sleep()
        return data

    def fetch_comments(self, oid: int, recent_pages: int = 2) -> List[dict]:
        comments: List[dict] = []
        # hot page first
        try:
            hot_data = self.fetch_comment_page(oid, mode=3)
            comments.extend(self._extract_replies(hot_data, source="hot"))
        except Exception as e:
            comments.append({"_error": f"hot_fetch_failed: {e}"})

        # latest pages
        next_offset = None
        for idx in range(recent_pages):
            try:
                latest = self.fetch_comment_page(oid, mode=2, pagination_offset=next_offset)
            except Exception as e:
                comments.append({"_error": f"latest_fetch_failed_p{idx+1}: {e}"})
                break
            comments.extend(self._extract_replies(latest, source=f"latest_p{idx+1}"))
            data = latest.get("data") or {}
            cursor = data.get("cursor") or {}
            pag = cursor.get("pagination_reply") or {}
            next_offset = pag.get("next_offset")
            if cursor.get("is_end") or not next_offset:
                break
        return comments

    def _extract_replies(self, payload: dict, source: str) -> List[dict]:
        out = []
        if not isinstance(payload, dict):
            return out
        if payload.get("code") != 0:
            out.append({
                "_error": f"api_code_{payload.get('code')}",
                "_message": payload.get("message", ""),
                "_source": source,
            })
            return out
        data = payload.get("data") or {}
        for key in ["top_replies", "hots", "replies"]:
            items = data.get(key) or []
            for item in items:
                content = ((item or {}).get("content") or {}).get("message", "")
                uname = (((item or {}).get("member") or {}).get("uname") or "")
                out.append({
                    "source": source,
                    "list_key": key,
                    "rpid": str((item or {}).get("rpid", "")),
                    "uname": clean_text(uname),
                    "raw_text": clean_text(content),
                    "like": int((item or {}).get("like") or 0),
                    "rcount": int((item or {}).get("rcount") or 0),
                })
        return out


def score_comment(text: str) -> Tuple[int, List[str], str]:
    text = clean_text(text)
    if not text:
        return -999, [], ""
    score = 0
    buckets = []
    for bucket, pats in RELEVANT_PATTERNS.items():
        hit = any(re.search(p, text, flags=re.I) for p in pats)
        if hit:
            score += 2
            buckets.append(bucket)
    neg_hit = sum(1 for p in NEGATIVE_PATTERNS if re.search(p, text, flags=re.I))
    score -= neg_hit
    # length bonus for substantive comments
    if len(text) >= 12:
        score += 1
    if len(text) >= 24:
        score += 1
    primary = max(set(buckets), key=buckets.count) if buckets else ""
    return score, buckets, primary


def build_registry(selected_csv: str, output_csv: str, debug_comments_csv: str, cookie_file: Optional[str], recent_pages: int, max_comments_per_video: int):
    df = pd.read_csv(selected_csv)
    client = BiliClient(load_cookie_string(cookie_file))
    rows = []
    debug_rows = []

    for _, row in df.iterrows():
        url = str(row.get("url", "") or row.get("link", "") or "")
        bvid = extract_bvid(url)
        if not bvid:
            continue
        info = client.get_video_info(bvid)
        if not info:
            continue

        seed_title = clean_text(str(row.get("title", "") or ""))
        seed_desc = parse_desc(row)
        op_text_parts = [f"标题：{info.title or seed_title}"]
        if info.desc or seed_desc:
            op_text_parts.append(f"简介：{info.desc or seed_desc}")
        op_text = "；".join([x for x in op_text_parts if x])
        rows.append({
            "platform": "bili",
            "thread_id": bvid,
            "item_id": f"{bvid}_op",
            "source_type": "op_context",
            "raw_text": op_text,
            "url": info.url,
            "title": info.title or seed_title,
            "theme_bucket_seed": row.get("theme_bucket", ""),
            "time_window": row.get("window", row.get("time_window", "")),
        })

        comments = client.fetch_comments(info.aid, recent_pages=recent_pages)
        kept = []
        for c in comments:
            dbg = {
                "bvid": bvid,
                "aid": info.aid,
                "title": info.title,
                **c,
            }
            text = clean_text(c.get("raw_text", ""))
            score, buckets, primary = score_comment(text)
            dbg["relevance_score"] = score
            dbg["matched_buckets"] = "|".join(sorted(set(buckets)))
            debug_rows.append(dbg)
            if text and score >= 2 and not c.get("_error"):
                kept.append((score, primary or row.get("theme_bucket", ""), c))

        # dedupe by text, keep strongest
        seen = set()
        kept_sorted = sorted(kept, key=lambda x: (x[0], int((x[2] or {}).get("like", 0))), reverse=True)
        added = 0
        for score, primary, c in kept_sorted:
            text = clean_text(c.get("raw_text", ""))
            if text in seen:
                continue
            seen.add(text)
            rows.append({
                "platform": "bili",
                "thread_id": bvid,
                "item_id": f"{bvid}_{c.get('rpid') or added+1}",
                "source_type": "recent_reply",
                "raw_text": text,
                "url": info.url,
                "title": info.title,
                "theme_bucket_seed": primary,
                "time_window": row.get("window", row.get("time_window", "")),
            })
            added += 1
            if added >= max_comments_per_video:
                break

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    pd.DataFrame(rows).to_csv(output_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame(debug_rows).to_csv(debug_comments_csv, index=False, encoding="utf-8-sig")
    print(f"Saved Bilibili registry to {output_csv}, rows={len(rows)}")
    print(f"Saved debug comments to {debug_comments_csv}, rows={len(debug_rows)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selected", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--debug-comments", required=True)
    ap.add_argument("--cookie-file", default="")
    ap.add_argument("--recent-pages", type=int, default=2)
    ap.add_argument("--max-comments-per-video", type=int, default=8)
    args = ap.parse_args()
    build_registry(args.selected, args.output, args.debug_comments, args.cookie_file, args.recent_pages, args.max_comments_per_video)
