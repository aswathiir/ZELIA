#!/usr/bin/env python3
"""Create/refresh curated active schemes across all states in DB.

The goal is to keep noisy records out of top matches while preserving
state-specific coverage and a national fallback.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor


POSITIVE_KEYWORDS: Dict[str, int] = {
    "scheme": 4,
    "yojana": 5,
    "pension": 7,
    "benefit": 4,
    "subsidy": 6,
    "assistance": 6,
    "allowance": 6,
    "welfare": 5,
    "insurance": 5,
    "health": 4,
    "housing": 5,
    "livelihood": 5,
    "employment": 5,
    "training": 4,
    "skill": 4,
    "scholarship": 5,
    "farmer": 5,
    "kisan": 5,
    "disability": 6,
    "elderly": 5,
    "senior": 4,
    "widow": 6,
}

NEGATIVE_KEYWORDS: Dict[str, int] = {
    "voter list": 15,
    "vehicle list": 14,
    "census": 12,
    "election": 10,
    "tender": 10,
    "admit card": 12,
    "exam result": 12,
    "recruitment": 8,
    "weather": 8,
    "lottery": 10,
}

HARD_EXCLUDE_PATTERNS: Sequence[str] = (
    r"\bvoter\s+list\b",
    r"\bvehicle\s+list\b",
    r"\bcensus\b",
    r"\belection\b",
    r"\badmit\s+card\b",
    r"\bexam\s+result\b",
)

ALWAYS_INCLUDE_SCHEME_IDS = {
    "ka-widow-pension",
    "ka-old-age-pension",
    "ka-disability-pension",
    "ka-destitute-pension",
    "pmjay",
    "pm-kisan",
    "pm-ujjwala",
    "nsap-ignoaps",
}

DEFAULT_SCOPE_STATES = ("KA", "TN", "UP", "MH", "RJ", "ALL")


@dataclass
class ScoreResult:
    score: int
    reasons: List[str]
    hard_excluded: bool


def _text_blob(row: Dict[str, object]) -> str:
    parts = [
        str(row.get("scheme_name") or ""),
        str(row.get("description") or ""),
        str(row.get("benefits") or ""),
        str(row.get("eligibility_summary") or ""),
    ]
    return " ".join(parts).lower()


def score_scheme(row: Dict[str, object]) -> ScoreResult:
    scheme_id = str(row.get("scheme_id") or "")
    name = str(row.get("scheme_name") or "")
    text = _text_blob(row)

    score = 0
    reasons: List[str] = []

    for keyword, weight in POSITIVE_KEYWORDS.items():
        if keyword in text:
            score += weight
            reasons.append(f"+{weight}:{keyword}")

    for keyword, weight in NEGATIVE_KEYWORDS.items():
        if keyword in text:
            score -= weight
            reasons.append(f"-{weight}:{keyword}")

    if len(name) > 180:
        score -= 5
        reasons.append("-5:very_long_title")
    if "http://" in text or "https://" in text:
        score -= 2
        reasons.append("-2:raw_url_noise")
    if re.search(r"\b(19|20)\d{2}\b", name) and "scheme" not in name.lower():
        score -= 2
        reasons.append("-2:yearly_news_style")

    hard_excluded = any(re.search(pat, text) for pat in HARD_EXCLUDE_PATTERNS)
    if hard_excluded:
        reasons.append("hard_excluded_pattern")

    if scheme_id in ALWAYS_INCLUDE_SCHEME_IDS:
        score += 25
        reasons.append("+25:always_include_seeded")
        hard_excluded = False

    return ScoreResult(score=score, reasons=reasons, hard_excluded=hard_excluded)


def choose_active(
    rows: List[Dict[str, object]],
    min_per_state: int,
    max_per_state: int,
    min_score: int,
) -> Tuple[set[str], Dict[str, Dict[str, object]]]:
    scored_rows: List[Tuple[Dict[str, object], ScoreResult]] = []
    details: Dict[str, Dict[str, object]] = {}
    for row in rows:
        res = score_scheme(row)
        scored_rows.append((row, res))
        sid = str(row.get("scheme_id"))
        details[sid] = {
            "score": res.score,
            "reasons": res.reasons,
            "hard_excluded": res.hard_excluded,
        }

    scored_rows.sort(key=lambda x: x[1].score, reverse=True)
    selected: List[str] = []

    for row, res in scored_rows:
        sid = str(row.get("scheme_id"))
        if sid in selected:
            continue
        if sid in ALWAYS_INCLUDE_SCHEME_IDS:
            selected.append(sid)
            continue
        if not res.hard_excluded and res.score >= min_score:
            selected.append(sid)
        if len(selected) >= max_per_state:
            break

    if len(selected) < min_per_state:
        for row, res in scored_rows:
            sid = str(row.get("scheme_id"))
            if sid in selected:
                continue
            if res.hard_excluded:
                continue
            selected.append(sid)
            if len(selected) >= min_per_state:
                break

    return set(selected), details


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL"))
    parser.add_argument("--states", default=",".join(DEFAULT_SCOPE_STATES))
    parser.add_argument("--min-per-state", type=int, default=12)
    parser.add_argument("--max-per-state", type=int, default=40)
    parser.add_argument("--min-score", type=int, default=8)
    parser.add_argument("--manifest", default="data/ingestion/active_scheme_manifest.json")
    args = parser.parse_args()

    if not args.db_url:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL is required")

    states = [s.strip().upper() for s in args.states.split(",") if s.strip()]

    conn = psycopg2.connect(args.db_url, cursor_factory=RealDictCursor)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute(
        """
        SELECT scheme_id, scheme_name, COALESCE(state_code,'ALL') AS state_code,
               description, benefits, eligibility_summary
        FROM schemes
        WHERE COALESCE(state_code,'ALL') = ANY(%s)
        """,
        (states,),
    )
    rows = list(cur.fetchall())

    by_state: Dict[str, List[Dict[str, object]]] = {s: [] for s in states}
    for row in rows:
        by_state[str(row.get("state_code"))].append(row)

    active_ids: set[str] = set()
    state_summary: Dict[str, Dict[str, object]] = {}
    details_index: Dict[str, Dict[str, object]] = {}

    for state in states:
        state_rows = by_state.get(state, [])
        selected, details = choose_active(
            state_rows,
            min_per_state=args.min_per_state,
            max_per_state=args.max_per_state,
            min_score=args.min_score,
        )
        active_ids.update(selected)
        details_index.update(details)
        ranked = sorted(
            (
                {
                    "scheme_id": str(r.get("scheme_id")),
                    "scheme_name": str(r.get("scheme_name") or ""),
                    "score": details[str(r.get("scheme_id"))]["score"],
                }
                for r in state_rows
                if str(r.get("scheme_id")) in selected
            ),
            key=lambda x: x["score"],
            reverse=True,
        )
        state_summary[state] = {
            "total": len(state_rows),
            "active": len(selected),
            "top_active": ranked[:12],
        }

    # Upsert full scope rows: selected = active, others inactive.
    for row in rows:
        sid = str(row.get("scheme_id"))
        state = str(row.get("state_code"))
        detail = details_index.get(sid, {"score": 0, "reasons": []})
        is_active = sid in active_ids
        cur.execute(
            """
            INSERT INTO scheme_curation (
                scheme_id, state_code, is_active, curation_score, curation_reason, curated_by, curated_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (scheme_id) DO UPDATE SET
                state_code = EXCLUDED.state_code,
                is_active = EXCLUDED.is_active,
                curation_score = EXCLUDED.curation_score,
                curation_reason = EXCLUDED.curation_reason,
                curated_by = EXCLUDED.curated_by,
                curated_at = NOW(),
                updated_at = NOW()
            """,
            (
                sid,
                state,
                is_active,
                detail["score"],
                ",".join(detail["reasons"][:12]),
                "auto_curator_v1",
            ),
        )

    conn.commit()
    cur.close()
    conn.close()

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope_states": states,
        "threshold": {
            "min_per_state": args.min_per_state,
            "max_per_state": args.max_per_state,
            "min_score": args.min_score,
        },
        "totals": {
            "scanned_rows": len(rows),
            "active_rows": len(active_ids),
        },
        "states": state_summary,
    }

    out = Path(args.manifest)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"Manifest written: {out}")


if __name__ == "__main__":
    main()
