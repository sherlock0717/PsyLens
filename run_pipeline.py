import os, json, argparse, csv, pathlib, random
from typing import Dict, Any, List
import pandas as pd
import yaml
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

ROOT = pathlib.Path(__file__).resolve().parents[1]

def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def make_client(provider: str):
    load_dotenv()
    if provider == "deepseek":
        return OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        ), os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    elif provider == "openai":
        return OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        ), os.getenv("OPENAI_REVIEW_MODEL", "")
    raise ValueError("Unknown provider")

def call_json(client, model: str, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    resp = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role":"system","content":system_prompt},
            {"role":"user","content":user_prompt}
        ],
        temperature=0.1,
        max_tokens=1200,
    )
    content = resp.choices[0].message.content or "{}"
    return json.loads(content)

def stage_clean(df, client, model):
    system = read_text(ROOT / "prompts" / "01_clean_extract_system.txt")
    outputs = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="stage01_clean"):
        user = f"""Return json.
INPUT ID: {row['id']}
RAW TEXT:
{row['raw_text']}

Required JSON shape:
{{
  "id": "{row['id']}",
  "is_valid_feedback": true,
  "split_units": [
    {{
      "unit_text": "text",
      "main_subject": "short phrase",
      "tone": "neutral|negative|positive|mixed"
    }}
  ]
}}"""
        try:
            out = call_json(client, model, system, user)
        except Exception as e:
            out = {"id": str(row['id']), "is_valid_feedback": False, "split_units": [], "error": str(e)}
        outputs.append(out)
    return outputs

def stage_surface(units, client, model, mode):
    system = read_text(ROOT / "prompts" / "02_surface_code_system.txt")
    if mode == "game":
        allowed = ["rewards","matchmaking","progression","balance","new_player_onboarding","community_conflict","communication_transparency","event_design","other_uncertain"]
    else:
        allowed = ["onboarding","search","navigation","trust","content_quality","interaction_friction","retention_trigger","other_uncertain"]
    outputs = []
    for item in tqdm(units, desc="stage02_surface"):
        user = f"""Return json.
Allowed labels: {allowed}
Feedback ID: {item['id']}
Feedback text: {item['unit_text']}

Required JSON:
{{
  "id": "{item['id']}",
  "surface_topic": "one allowed label",
  "reason_short": "one short sentence"
}}"""
        try:
            out = call_json(client, model, system, user)
        except Exception as e:
            out = {"id": item["id"], "surface_topic": "other_uncertain", "reason_short": f"error:{e}"}
        outputs.append(out)
    return outputs

def stage_psych(units, client, model, mode):
    system_name = "03_psych_code_game_system.txt" if mode == "game" else "03_psych_code_ux_system.txt"
    system = read_text(ROOT / "prompts" / system_name)
    outputs = []
    for item in tqdm(units, desc="stage03_psych"):
        user = f"""Return json.
Feedback ID: {item['id']}
Feedback text: {item['unit_text']}

Required JSON:
{{
  "id": "{item['id']}",
  "mechanism_label": "allowed label or uncertain",
  "confidence": "high|medium|low",
  "evidence_phrase": "short exact phrase from the feedback"
}}"""
        try:
            out = call_json(client, model, system, user)
        except Exception as e:
            out = {"id": item["id"], "mechanism_label": "uncertain", "confidence": "low", "evidence_phrase": f"error:{e}"}
        outputs.append(out)
    return outputs

def stage_validate(merged_df, client, model):
    system = read_text(ROOT / "prompts" / "04_validate_system.txt")
    # simple grouped insight candidates
    candidates = []
    for (topic, mech), sub in merged_df.groupby(["surface_topic","mechanism_label"]):
        ids = sub["id"].astype(str).tolist()[:8]
        if topic == "other_uncertain":
            continue
        insight = f"Feedback around [{topic}] frequently co-occurs with [{mech}] signals."
        candidates.append({"insight": insight, "ids": ids, "n": len(sub)})
    outputs = []
    for c in tqdm(candidates, desc="stage04_validate"):
        freq_type = "high_frequency" if c["n"] >= 5 else "high_intensity_or_low_frequency"
        user = f"""Return json.
Candidate insight: {c['insight']}
Supporting ids: {c['ids']}
Observed count: {c['n']}
Frequency type hint: {freq_type}

Required JSON:
{{
  "insight": "same or revised insight",
  "supporting_ids": ["id1","id2"],
  "frequency_type": "high_frequency|high_intensity_or_low_frequency",
  "confidence": "high|medium|low",
  "needs_human_review": false
}}"""
        try:
            out = call_json(client, model, system, user)
        except Exception as e:
            out = {"insight": c["insight"], "supporting_ids": c["ids"], "frequency_type": freq_type, "confidence": "low", "needs_human_review": True, "error": str(e)}
        outputs.append(out)
    return outputs

def stage_actions(validated, client, model, case_cfg):
    system = read_text(ROOT / "prompts" / "05_compose_insights_system.txt")
    kept = [x for x in validated if not x.get("needs_human_review", True)]
    top = kept[:6] if kept else validated[:6]
    user = f"""Return json.
Case name: {case_cfg['case_name']}
Business question: {case_cfg['business_question']}
Validated insights:
{json.dumps(top, ensure_ascii=False)}

Required JSON:
{{
  "safe": ["action 1", "action 2"],
  "balanced": ["action 1", "action 2"],
  "bold": ["action 1", "action 2"]
}}"""
    try:
        out = call_json(client, model, system, user)
    except Exception as e:
        out = {"safe":[f"error:{e}"],"balanced":[],"bold":[]}
    return out

def maybe_review_with_gpt(merged_df, sample_n, mode, review_provider, review_model):
    if not review_provider or sample_n <= 0:
        return None
    client, default_model = make_client(review_provider)
    model = review_model or default_model
    sample = merged_df.sample(min(sample_n, len(merged_df)), random_state=42)
    system = "You are reviewing a psychology-informed coding table. Flag likely over-interpretation, weak evidence, or inconsistent labeling. Return concise JSON."
    user = f"""Return json.
Mode: {mode}
Sample rows:
{sample[['id','raw_text','surface_topic','mechanism_label','confidence']].to_dict(orient='records')}

Required JSON:
{{
  "review_summary": "short paragraph",
  "flagged_ids": ["id1","id2"],
  "recommendations": ["rec1","rec2"]
}}"""
    return call_json(client, model, system, user)

def save_jsonl(items, path):
    with open(path, "w", encoding="utf-8") as f:
        for x in items:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--mode", choices=["game","ux"], required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--review_provider", default="")
    parser.add_argument("--review_model", default="")
    parser.add_argument("--review_sample", type=int, default=0)
    args = parser.parse_args()

    case_cfg = load_yaml(args.case)
    out_dir = ROOT / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input)
    required = {"id","raw_text"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Input CSV missing required columns: {missing}")

    client, model = make_client("deepseek")

    # stage 1
    clean = stage_clean(df, client, model)
    save_jsonl(clean, out_dir / "01_clean_extract.jsonl")

    units = []
    for item in clean:
        for i, unit in enumerate(item.get("split_units", [])):
            uid = f"{item.get('id')}_u{i+1}"
            units.append({"id": uid, "parent_id": item.get("id"), "unit_text": unit.get("unit_text","")})

    # stage 2
    surface = stage_surface(units, client, model, args.mode)
    save_jsonl(surface, out_dir / "02_surface_code.jsonl")

    # stage 3
    psych = stage_psych(units, client, model, args.mode)
    save_jsonl(psych, out_dir / "03_psych_code.jsonl")

    # merge
    units_df = pd.DataFrame(units)
    surface_df = pd.DataFrame(surface)
    psych_df = pd.DataFrame(psych)
    merged = units_df.merge(surface_df, on="id", how="left").merge(psych_df, on="id", how="left")
    # add parent raw text
    parent_map = df.set_index("id")["raw_text"].to_dict()
    merged["raw_text"] = merged["parent_id"].map(parent_map)
    merged.to_csv(out_dir / "final_evidence_table.csv", index=False, encoding="utf-8-sig")

    # optional review
    review = maybe_review_with_gpt(merged, args.review_sample, args.mode, args.review_provider, args.review_model)
    if review:
        with open(out_dir / "gpt_review.json", "w", encoding="utf-8") as f:
            json.dump(review, f, ensure_ascii=False, indent=2)

    # stage 4
    validated = stage_validate(merged, client, model)
    save_jsonl(validated, out_dir / "04_validated_insights.jsonl")

    # stage 5
    action_matrix = stage_actions(validated, client, model, case_cfg)
    with open(out_dir / "05_action_matrix.json", "w", encoding="utf-8") as f:
        json.dump(action_matrix, f, ensure_ascii=False, indent=2)

    print("Pipeline complete. Outputs written to", out_dir)

if __name__ == "__main__":
    main()
