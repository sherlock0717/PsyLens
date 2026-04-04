#!/usr/bin/env python3
import argparse, json, os, re, time
from pathlib import Path
import pandas as pd
from openai import OpenAI

SYSTEM_PROMPT = """
You are assisting a psychology-informed game community study on League of Legends Hex ARAM.
For each feedback row, produce a cleaned version and classify whether to keep it for analysis.

Rules:
- Remove obvious forum markup, quote headers, image placeholders, uid/pid fragments.
- Keep the meaning as much as possible.
- keep_ai = 1 if the text contains interpretable player experience / community evidence.
- keep_ai = 0 for pure memes, pure insults with no experience signal, empty quote residue, too-short noise.
- theme_bucket: balance_mechanic, hero_experience, team_interaction, fairness_attribution, off_topic
- mechanism_prior: competence_frustration, fairness_threat, community_norm, uncertain
- info_score: 0-3, where 3 means high-information, 2 moderate, 1 minimal but usable, 0 noise.
- drop_reason: empty if keep_ai=1, otherwise one of noise_markup, too_short, off_topic, pure_insult, duplicate_like.
Return strict JSON only.
"""

USER_TMPL = """
platform_source: {platform_source}
window_tag: {window_tag}
thread_or_video_title: {thread_or_video_title}
reply_type: {reply_type}
raw_text: {raw_text}

Return JSON with keys:
cleaned_text, keep_ai, theme_bucket, mechanism_prior, info_score, drop_reason, rationale
"""


def get_client():
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY or OPENAI_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    return OpenAI(api_key=api_key, base_url=base_url)


def fast_strip(text: str) -> str:
    if pd.isna(text):
        return ""
    t = str(text)
    t = re.sub(r"\[/?(?:quote|img|b|i|u|url|color|size).*?\]", " ", t, flags=re.I)
    t = re.sub(r"\[/?(?:pid|uid)\]", " ", t, flags=re.I)
    t = re.sub(r"Reply to .*?:", " ", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def ask(client, model, row, retries=3):
    user = USER_TMPL.format(
        platform_source=row.get("platform_source", ""),
        window_tag=row.get("window_tag", ""),
        thread_or_video_title=str(row.get("thread_or_video_title", row.get("thread_title", "")))[:160],
        reply_type=row.get("reply_type", ""),
        raw_text=fast_strip(row.get("raw_text", ""))[:700],
    )
    for i in range(retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user},
                ],
            )
            data = json.loads(resp.choices[0].message.content)
            return {
                "cleaned_text": str(data.get("cleaned_text", ""))[:1000],
                "keep_ai": int(data.get("keep_ai", 0)),
                "theme_bucket": data.get("theme_bucket", "off_topic"),
                "mechanism_prior": data.get("mechanism_prior", "uncertain"),
                "info_score": int(data.get("info_score", 0)),
                "drop_reason": str(data.get("drop_reason", ""))[:50],
                "rationale": str(data.get("rationale", ""))[:80],
            }
        except Exception:
            if i == retries - 1:
                cleaned = fast_strip(row.get("raw_text", ""))
                keep = int(len(cleaned) >= 12)
                return {
                    "cleaned_text": cleaned,
                    "keep_ai": keep,
                    "theme_bucket": "off_topic" if not keep else "balance_mechanic",
                    "mechanism_prior": "uncertain",
                    "info_score": 1 if keep else 0,
                    "drop_reason": "api_error" if not keep else "",
                    "rationale": "fallback",
                }
            time.sleep(1.5 * (i + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--model", default=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    args = ap.parse_args()

    df = pd.read_csv(args.input)
    client = get_client()
    rows = []
    for _, row in df.iterrows():
        res = ask(client, args.model, row)
        merged = {**row.to_dict(), **res}
        rows.append(merged)
    out = pd.DataFrame(rows)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Saved {len(out)} rows to {args.output}")

if __name__ == "__main__":
    main()
