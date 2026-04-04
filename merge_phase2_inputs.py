#!/usr/bin/env python3
import argparse
from pathlib import Path
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs='+', required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--per-platform", type=int, default=120)
    args = ap.parse_args()

    frames = [pd.read_csv(p) for p in args.inputs]
    df = pd.concat(frames, ignore_index=True)
    if "keep_ai" in df.columns:
        df = df[df["keep_ai"] == 1].copy()
    if "keep_manual" in df.columns:
        df = df[(df["keep_manual"].isna()) | (df["keep_manual"] == 1)].copy()
    if "cleaned_text" in df.columns:
        df["raw_text"] = df["cleaned_text"].fillna(df.get("raw_text", ""))

    selected = []
    score_col = "info_score" if "info_score" in df.columns else None
    for platform, g in df.groupby("platform_source", dropna=False):
        if score_col:
            g = g.sort_values([score_col], ascending=False)
        selected.append(g.head(args.per_platform))
    out = pd.concat(selected, ignore_index=True)

    # standardize columns for PsyLens
    rename_map = {
        "thread_title": "thread_or_video_title",
        "title": "thread_or_video_title"
    }
    out = out.rename(columns=rename_map)

    cols = [
        "record_id", "platform_source", "window_tag", "theme_bucket",
        "thread_or_video_title", "url", "publish_time", "reply_type", "raw_text"
    ]
    for c in cols:
        if c not in out.columns:
            out[c] = ""
    final = out[cols].copy()
    final.insert(0, "id", range(1, len(final) + 1))
    final["source_type"] = final["platform_source"].astype(str)
    final["channel"] = final["platform_source"].astype(str) + "_" + final["window_tag"].astype(str)
    final["date"] = final["publish_time"]
    final["segment_guess"] = final["theme_bucket"]
    final = final[["id", "source_type", "date", "channel", "raw_text", "url", "segment_guess", "platform_source", "window_tag", "theme_bucket", "thread_or_video_title", "reply_type"]]

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Saved {len(final)} rows to {args.output}")

if __name__ == "__main__":
    main()
