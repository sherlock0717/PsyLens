from pathlib import Path
import pandas as pd
import re
import argparse

def clean_text(s: str) -> str:
    if pd.isna(s):
        return ""
    t = str(s)

    # 去掉论坛 reply 头
    t = re.sub(r"^Reply to .*?\)\s*", "", t, flags=re.IGNORECASE)

    # 去掉图片路径
    t = re.sub(r"\./mon_\d{6}/\d{2}/-[^\s]+?\.(jpg|png|jpeg|gif)", " ", t, flags=re.IGNORECASE)

    # 去掉多余空白
    t = re.sub(r"\s+", " ", t).strip()

    return t

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.input, encoding="utf-8-sig")
    df["raw_text"] = df["raw_text"].apply(clean_text)

    # 去掉空文本
    df = df[df["raw_text"].astype(str).str.strip() != ""].copy()

    df.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Saved cleaned file to {args.output}, rows={len(df)}")

if __name__ == "__main__":
    main()