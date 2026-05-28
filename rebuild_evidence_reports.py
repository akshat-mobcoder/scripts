#!/usr/bin/env python3
"""Rebuild manager-readable evidence Markdown files from saved evidence JSON."""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict

from ai.report_generator import ReportGenerator
from config import OUTPUT_EVIDENCE_DIR, OUTPUT_JSON_DIR


def slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "_", value.lower()).strip("_")


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def profile_from_evidence(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Build enough profile data to render evidence even if profile JSON is missing."""
    final_data = evidence.get("final_extracted_data", {})
    basis = evidence.get("analysis_basis", {})
    return {
        "business_name": evidence.get("business_name", "Business"),
        "website_url": evidence.get("website_url", "N/A"),
        "emails": final_data.get("emails", []),
        "phone_numbers": final_data.get("phone_numbers", []),
        "addresses": final_data.get("addresses", []),
        "business_hours": final_data.get("business_hours", []),
        "social_links": final_data.get("social_links", {}),
        "tech_stack": final_data.get("tech_stack", []),
        "seo": basis.get("seo", {}),
        "performance": basis.get("performance", {}),
        "cro": basis.get("cro", {}),
        "hiring": basis.get("hiring", {}),
        "social": basis.get("social", {}),
        "reviews": basis.get("reviews", {}),
        "scores": basis.get("scores", {}),
        "outreach": {},
        "outreach_email": "",
    }


def find_profile(evidence: Dict[str, Any], evidence_path: Path) -> Dict[str, Any]:
    business_name = evidence.get("business_name") or evidence_path.stem.replace("_evidence", "")
    candidates = [
        Path(OUTPUT_JSON_DIR) / f"{slugify(business_name)}.json",
        Path(OUTPUT_JSON_DIR) / f"{evidence_path.stem.replace('_evidence', '')}.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return load_json(candidate)
    return profile_from_evidence(evidence)


def rebuild_one(evidence_path: Path) -> Path:
    evidence = load_json(evidence_path)
    profile = find_profile(evidence, evidence_path)
    markdown = ReportGenerator.generate_evidence_markdown(profile, evidence)
    output_path = evidence_path.with_suffix(".md")
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def main() -> int:
    evidence_dir = Path(OUTPUT_EVIDENCE_DIR)
    evidence_files = sorted(evidence_dir.glob("*_evidence.json"))
    if not evidence_files:
        print("[INFO] No evidence JSON files found.")
        return 0

    for evidence_path in evidence_files:
        try:
            output_path = rebuild_one(evidence_path)
            print(f"[OK] Rebuilt {output_path}")
        except Exception as exc:
            print(f"[ERROR] Failed to rebuild {evidence_path}: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
