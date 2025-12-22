#!/usr/bin/env python3
"""
Check for overlap between JICA and DFMIS project data.

This script uses the JICAMatcher class to identify duplicates.

Run: poetry run python migrations/007-source-projects/check_jica_dfmis_overlap.py
"""

import json
from pathlib import Path

from project_matcher import JICAMatcher, MatchLevel, get_match_stats


def load_jsonl(filepath: Path) -> list:
    """Load projects from JSONL file."""
    projects = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                projects.append(json.loads(line))
    return projects


def main():
    source_dir = Path(__file__).parent / "source"

    # Load data
    dfmis_file = source_dir / "dfmis_projects.jsonl"
    jica_file = source_dir / "jica_projects.jsonl"

    if not dfmis_file.exists():
        print(f"ERROR: DFMIS file not found: {dfmis_file}")
        return

    if not jica_file.exists():
        print(f"ERROR: JICA file not found: {jica_file}")
        print("Run the JICA scraper first:")
        print("  poetry run python migrations/007-source-projects/jica/scrape_jica.py")
        return

    print("Loading project data...")
    dfmis_projects = load_jsonl(dfmis_file)
    jica_projects = load_jsonl(jica_file)

    print(f"  DFMIS projects: {len(dfmis_projects)}")
    print(f"  JICA projects: {len(jica_projects)}")
    print()

    # Create JICA matcher with DFMIS as existing projects
    print("=" * 80)
    print("USING JICAMatcher CLASS")
    print("=" * 80)
    print()
    print("Matching Strategy (conservative):")
    print("  Level 4 (HIGH):   JICA project ID found in DFMIS donor_extensions")
    print("  Level 3 (HIGH):   Exact normalized name match")
    print("  Level 2 (MEDIUM): Fuzzy name (>85%) + amount within 15%")
    print("  Level 1 (LOW):    Fuzzy name (>80%) only")
    print()
    print("Note: JICA doesn't have standardized IDs, so matching relies more on names.")
    print()

    matcher = JICAMatcher(dfmis_projects)
    stats = get_match_stats(jica_projects, matcher)

    # Print detailed results
    print("=" * 80)
    print("MATCH RESULTS")
    print("=" * 80)

    # Group by level
    by_level = {
        MatchLevel.HIGH_ID: [],
        MatchLevel.HIGH_NAME: [],
        MatchLevel.MEDIUM: [],
        MatchLevel.LOW: [],
    }

    for item in stats["skipped_projects"]:
        result = item["match_result"]
        by_level[result.level].append(item)

    print(f"\n--- LEVEL 4: JICA ID MATCHES ({len(by_level[MatchLevel.HIGH_ID])}) ---")
    for item in by_level[MatchLevel.HIGH_ID][:5]:
        r = item["match_result"]
        print(f"  NEW: {r.new_project_name[:60]}")
        print(f"  EXISTING: {r.existing_project_name[:60]}")
        print(f"  Reason: {r.match_reason}")
        print()

    print(f"\n--- LEVEL 3: EXACT NAME ({len(by_level[MatchLevel.HIGH_NAME])}) ---")
    for item in by_level[MatchLevel.HIGH_NAME][:5]:
        r = item["match_result"]
        print(f"  NEW: {r.new_project_name[:60]}")
        print(f"  EXISTING: {r.existing_project_name[:60]}")
        print()

    print(f"\n--- LEVEL 2: FUZZY + AMOUNT ({len(by_level[MatchLevel.MEDIUM])}) ---")
    for item in by_level[MatchLevel.MEDIUM][:5]:
        r = item["match_result"]
        print(f"  NEW: {r.new_project_name[:55]}")
        print(f"  EXISTING: {r.existing_project_name[:55]}")
        print(f"  Similarity: {r.similarity:.1%}")
        print()

    print(f"\n--- LEVEL 1: FUZZY NAME ONLY ({len(by_level[MatchLevel.LOW])}) ---")
    print("(These may be different projects - additional financing, phases)")
    for item in by_level[MatchLevel.LOW][:10]:
        r = item["match_result"]
        print(f"  NEW: {r.new_project_name[:55]}")
        print(f"  EXISTING: {r.existing_project_name[:55]}")
        print(f"  Similarity: {r.similarity:.1%}")
        print()

    print(f"\n--- NO MATCHES ({len(stats['import_projects'])}) ---")
    print("JICA projects safe to import (first 20):")
    for p in stats["import_projects"][:20]:
        names = p.get("names", [])
        name = names[0]["en"]["full"] if names else p.get("name", "Unknown")
        amount = p.get("total_commitment") or 0
        # Format amount in millions JPY
        if amount > 0:
            amount_str = f"¥{amount / 1_000_000:,.0f}M"
        else:
            amount_str = "N/A"
        stage = p.get("stage", "unknown")
        print(f"  - {name[:55]} ({amount_str}, {stage})")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total JICA projects: {stats['total']}")
    print(f"  - Level 4 (JICA ID match):    {stats['high_id']:3d} - SKIP")
    print(f"  - Level 3 (Exact name):       {stats['high_name']:3d} - SKIP")
    print(f"  - Level 2 (Fuzzy + amount):   {stats['medium']:3d} - SKIP")
    print(f"  - Level 1 (Fuzzy name only):  {stats['low']:3d} - SKIP (conservative)")
    print(f"  - No matches:                 {stats['none']:3d} - IMPORT")
    print()
    print("MIGRATION PLAN:")
    print(f"  - Projects to SKIP:   {stats['to_skip']:3d}")
    print(f"  - Projects to IMPORT: {stats['to_import']:3d}")


if __name__ == "__main__":
    main()
