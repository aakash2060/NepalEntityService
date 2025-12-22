"""
Project matching utilities for deduplication across data sources.

This module provides matching logic to identify duplicate projects when
importing from multiple sources (DFMIS, World Bank, ADB, JICA, etc.).

Matching Strategy (conservative - prefer false negatives over false positives):
- Level 4 (HIGH):   Donor project ID found in existing donor_extensions
- Level 3 (HIGH):   Exact normalized name match
- Level 2 (MEDIUM): Fuzzy name (>85%) + amount within 15%
- Level 1 (LOW):    Fuzzy name (>80%) only - likely different phase/additional financing

Usage:
    from project_matcher import WorldBankMatcher, ADBMatcher, MatchLevel

    # Source-specific matchers
    wb_matcher = WorldBankMatcher(existing_projects)
    result = wb_matcher.find_match(new_wb_project)

    # Or use base class with source parameter
    matcher = ProjectMatcher(existing_projects)
    result = matcher.find_match(new_project, source="WB")

    if result.should_skip():
        # Skip - likely duplicate
    else:
        # Safe to import as new
"""

import re
from abc import ABC
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import IntEnum
from typing import Any, Dict, List, Optional


class MatchLevel(IntEnum):
    """Match confidence levels - higher = more confident it's a duplicate."""

    NONE = 0  # No match found
    LOW = 1  # Fuzzy name only (>80%) - may be different phase
    MEDIUM = 2  # Fuzzy name (>85%) + similar amount
    HIGH_NAME = 3  # Exact normalized name match
    HIGH_ID = 4  # Donor project ID match


@dataclass
class MatchResult:
    """Result of a project match attempt."""

    level: MatchLevel
    matched_project: Optional[Dict[str, Any]] = None
    similarity: float = 0.0
    match_reason: str = ""
    new_project_name: str = ""
    existing_project_name: str = ""

    def should_skip(self) -> bool:
        """Conservative: skip if any match found (Level 1+)."""
        return self.level >= MatchLevel.LOW

    def is_high_confidence(self) -> bool:
        """High confidence duplicate (Level 3-4)."""
        return self.level >= MatchLevel.HIGH_NAME

    def is_definite_duplicate(self) -> bool:
        """Definite duplicate - same project ID."""
        return self.level == MatchLevel.HIGH_ID


class ProjectMatcher(ABC):
    """Base class for project matching across sources.

    Conservative matching strategy - prefers false negatives (missing a duplicate)
    over false positives (incorrectly marking as duplicate).

    Subclass this for source-specific matching logic.
    """

    # Source identifier (override in subclasses)
    SOURCE: str = ""

    # Donor name variations to match in existing data
    DONOR_NAMES: List[str] = []

    # Thresholds (conservative)
    FUZZY_THRESHOLD_HIGH = 0.85  # For Level 2 (with amount check)
    FUZZY_THRESHOLD_LOW = 0.80  # For Level 1 (name only)
    AMOUNT_TOLERANCE = 0.15  # 15% tolerance for amount comparison

    def __init__(self, existing_projects: List[Dict[str, Any]]):
        """Initialize matcher with existing projects.

        Args:
            existing_projects: List of project dicts from database
        """
        self.existing_projects = existing_projects
        self._name_index: Dict[str, Dict] = {}
        self._donor_id_index: Dict[str, Dict] = {}
        self._build_indexes()

    def _build_indexes(self) -> None:
        """Build lookup indexes for efficient matching."""
        for project in self.existing_projects:
            # Index by normalized name
            name = self._get_project_name(project)
            norm_name = self._normalize_name(name)
            if norm_name:
                self._name_index[norm_name] = project

            # Index by donor project IDs (source-specific)
            for donor_id in self._extract_existing_donor_ids(project):
                self._donor_id_index[donor_id.upper()] = project

    def _extract_existing_donor_ids(self, project: Dict) -> List[str]:
        """Extract donor project IDs from existing project that match this source.

        Override in subclasses for source-specific ID extraction.
        """
        ids = []
        extensions = project.get("donor_extensions", []) or []
        for ext in extensions:
            donor = (ext.get("donor") or "").lower()
            # Check if this extension is from our source
            if self._is_matching_donor(donor):
                if ext.get("donor_project_id"):
                    ids.append(str(ext["donor_project_id"]))
            # Also check raw_payload
            raw = ext.get("raw_payload", {}) or {}
            for key in ["project_id", "proj_id", "id"]:
                if raw.get(key):
                    val = str(raw[key])
                    if self._is_valid_project_id(val):
                        ids.append(val)
        return ids

    def _is_matching_donor(self, donor_name: str) -> bool:
        """Check if donor name matches this source."""
        donor_lower = donor_name.lower()
        for name in self.DONOR_NAMES:
            if name.lower() in donor_lower:
                return True
        return False

    def _is_valid_project_id(self, project_id: str) -> bool:
        """Check if project ID is valid for this source. Override in subclasses."""
        return bool(project_id)

    def _extract_new_project_id(self, project: Dict) -> Optional[str]:
        """Extract project ID from new project. Override in subclasses."""
        # Check _migration_metadata
        meta = project.get("_migration_metadata", {})
        id_key = f"{self.SOURCE.lower()}_project_id"
        if meta.get(id_key):
            return meta[id_key]

        # Check donor_extensions
        extensions = project.get("donor_extensions", []) or []
        for ext in extensions:
            if ext.get("donor_project_id"):
                return ext["donor_project_id"]

        # Check slug
        slug = project.get("slug", "")
        prefix = f"{self.SOURCE.lower()}-"
        if slug.startswith(prefix):
            return slug[len(prefix) :]

        return None

    def find_match(self, project: Dict[str, Any]) -> MatchResult:
        """Find if project matches any existing project.

        Args:
            project: New project to check

        Returns:
            MatchResult with level and matched project if found
        """
        project_name = self._get_project_name(project)
        project_name_norm = self._normalize_name(project_name)
        project_amount = self._get_total_amount(project)

        # Level 4: Check donor project ID
        donor_id = self._extract_new_project_id(project)
        if donor_id and donor_id.upper() in self._donor_id_index:
            matched = self._donor_id_index[donor_id.upper()]
            return MatchResult(
                level=MatchLevel.HIGH_ID,
                matched_project=matched,
                similarity=1.0,
                match_reason=f"Donor ID match: {donor_id}",
                new_project_name=project_name,
                existing_project_name=self._get_project_name(matched),
            )

        # Level 3: Exact normalized name match
        if project_name_norm and project_name_norm in self._name_index:
            matched = self._name_index[project_name_norm]
            return MatchResult(
                level=MatchLevel.HIGH_NAME,
                matched_project=matched,
                similarity=1.0,
                match_reason="Exact name match",
                new_project_name=project_name,
                existing_project_name=self._get_project_name(matched),
            )

        # Level 2 & 1: Fuzzy name matching
        best_match = None
        best_score = 0.0

        for existing_name, existing_project in self._name_index.items():
            score = self._similarity_score(project_name_norm, existing_name)
            if score > best_score:
                best_score = score
                best_match = existing_project

        if best_match and best_score >= self.FUZZY_THRESHOLD_HIGH:
            existing_amount = self._get_total_amount(best_match)
            if self._amounts_similar(project_amount, existing_amount):
                return MatchResult(
                    level=MatchLevel.MEDIUM,
                    matched_project=best_match,
                    similarity=best_score,
                    match_reason=f"Fuzzy name ({best_score:.1%}) + similar amount",
                    new_project_name=project_name,
                    existing_project_name=self._get_project_name(best_match),
                )

        if best_match and best_score >= self.FUZZY_THRESHOLD_LOW:
            return MatchResult(
                level=MatchLevel.LOW,
                matched_project=best_match,
                similarity=best_score,
                match_reason=f"Fuzzy name only ({best_score:.1%})",
                new_project_name=project_name,
                existing_project_name=self._get_project_name(best_match),
            )

        return MatchResult(
            level=MatchLevel.NONE,
            matched_project=None,
            similarity=best_score,
            match_reason="No match found",
            new_project_name=project_name,
            existing_project_name="",
        )

    def _normalize_name(self, name: str) -> str:
        """Normalize project name for comparison."""
        if not name:
            return ""
        # Lowercase, remove extra whitespace
        name = name.lower().strip()
        name = re.sub(r"\s+", " ", name)
        # Remove common prefixes
        prefixes = [
            "nepal:",
            "nepal -",
            "nepal-",
            "np:",
            "np -",
            "np-",
            "nepal ",
        ]
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix) :].strip()
        # Remove special characters for comparison
        name = re.sub(r"[^\w\s]", "", name)
        return name

    def _get_project_name(self, project: Dict) -> str:
        """Extract project name from project data."""
        # Try names array first (Entity format)
        names = project.get("names", [])
        if names:
            for name in names:
                if name.get("en", {}).get("full"):
                    return name["en"]["full"]
        # Fallback to name field
        return project.get("name", "")

    def _get_total_amount(self, project: Dict) -> float:
        """Extract total commitment amount from project."""
        # Try total_commitment first
        if project.get("total_commitment"):
            try:
                return float(project["total_commitment"])
            except (ValueError, TypeError):
                pass
        # Sum financing amounts
        financing = project.get("financing", []) or []
        total = 0.0
        for f in financing:
            if f.get("amount"):
                try:
                    total += float(f["amount"])
                except (ValueError, TypeError):
                    pass
        return total

    def _similarity_score(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings."""
        if not s1 or not s2:
            return 0.0
        return SequenceMatcher(None, s1, s2).ratio()

    def _amounts_similar(self, amt1: float, amt2: float) -> bool:
        """Check if two amounts are within tolerance."""
        if amt1 == 0 and amt2 == 0:
            return True
        if amt1 == 0 or amt2 == 0:
            return False
        ratio = min(amt1, amt2) / max(amt1, amt2)
        return ratio >= (1 - self.AMOUNT_TOLERANCE)


# =============================================================================
# SOURCE-SPECIFIC MATCHERS
# =============================================================================


class WorldBankMatcher(ProjectMatcher):
    """Matcher for World Bank projects."""

    SOURCE = "WB"
    DONOR_NAMES = ["world bank", "ibrd", "ida", "wb"]

    def _is_valid_project_id(self, project_id: str) -> bool:
        """WB project IDs start with P followed by digits (e.g., P123456)."""
        if not project_id:
            return False
        pid = project_id.upper()
        return pid.startswith("P") and len(pid) >= 6 and pid[1:].isdigit()

    def _extract_new_project_id(self, project: Dict) -> Optional[str]:
        """Extract WB project ID from new project."""
        # Check _migration_metadata
        meta = project.get("_migration_metadata", {})
        if meta.get("wb_project_id"):
            return meta["wb_project_id"]

        # Check donor_extensions
        extensions = project.get("donor_extensions", []) or []
        for ext in extensions:
            if ext.get("donor_project_id"):
                pid = ext["donor_project_id"]
                if self._is_valid_project_id(pid):
                    return pid

        # Check slug (wb-P123456)
        slug = project.get("slug", "")
        if slug.startswith("wb-"):
            return slug[3:]

        return None


class ADBMatcher(ProjectMatcher):
    """Matcher for Asian Development Bank projects."""

    SOURCE = "ADB"
    DONOR_NAMES = ["asian development bank", "adb"]

    def _is_valid_project_id(self, project_id: str) -> bool:
        """ADB project IDs are typically numeric or IATI identifiers."""
        if not project_id:
            return False
        # ADB uses numeric IDs or IATI format (XM-DAC-46004-...)
        return project_id.isdigit() or project_id.startswith("XM-DAC")

    def _extract_new_project_id(self, project: Dict) -> Optional[str]:
        """Extract ADB project ID from new project."""
        meta = project.get("_migration_metadata", {})
        if meta.get("adb_project_id"):
            return meta["adb_project_id"]

        extensions = project.get("donor_extensions", []) or []
        for ext in extensions:
            donor = (ext.get("donor") or "").lower()
            if "adb" in donor or "asian development" in donor:
                if ext.get("donor_project_id"):
                    return ext["donor_project_id"]

        slug = project.get("slug", "")
        if slug.startswith("adb-"):
            return slug[4:]

        return None


class JICAMatcher(ProjectMatcher):
    """Matcher for JICA projects.

    JICA doesn't have standardized project IDs like WB (P-numbers) or ADB (IATI).
    We generate IDs from project name + approval date, so matching relies more
    heavily on name matching than ID matching.
    """

    SOURCE = "JICA"
    DONOR_NAMES = ["jica", "japan international cooperation", "japan"]

    def _is_valid_project_id(self, project_id: str) -> bool:
        """JICA project IDs are generated from name+date, format: JICA-YYYYMMDD-name."""
        if not project_id:
            return False
        return project_id.upper().startswith("JICA-") and len(project_id) >= 10

    def _extract_new_project_id(self, project: Dict) -> Optional[str]:
        """Extract JICA project ID from new project."""
        # Check _migration_metadata
        meta = project.get("_migration_metadata", {})
        if meta.get("jica_project_id"):
            return meta["jica_project_id"]

        # Check donor_extensions
        extensions = project.get("donor_extensions", []) or []
        for ext in extensions:
            donor = (ext.get("donor") or "").lower()
            if "jica" in donor or "japan" in donor:
                if ext.get("donor_project_id"):
                    return ext["donor_project_id"]

        # Check slug (jica-...)
        slug = project.get("slug", "")
        if slug.startswith("jica-"):
            return slug

        return None


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def get_matcher_for_source(
    source: str, existing_projects: List[Dict[str, Any]]
) -> ProjectMatcher:
    """Factory function to get appropriate matcher for a source.

    Args:
        source: Source identifier (WB, ADB, JICA)
        existing_projects: List of existing projects

    Returns:
        Appropriate ProjectMatcher subclass instance
    """
    matchers = {
        "WB": WorldBankMatcher,
        "WORLD_BANK": WorldBankMatcher,
        "ADB": ADBMatcher,
        "JICA": JICAMatcher,
    }
    matcher_class = matchers.get(source.upper(), WorldBankMatcher)
    return matcher_class(existing_projects)


def get_match_stats(projects: List[Dict], matcher: ProjectMatcher) -> Dict[str, Any]:
    """Get matching statistics for a list of projects.

    Args:
        projects: List of projects to check
        matcher: ProjectMatcher instance

    Returns:
        Dict with counts by match level and lists of matches
    """
    stats = {
        "total": len(projects),
        "high_id": 0,
        "high_name": 0,
        "medium": 0,
        "low": 0,
        "none": 0,
        "to_skip": 0,
        "to_import": 0,
        "skipped_projects": [],
        "import_projects": [],
    }

    for project in projects:
        result = matcher.find_match(project)
        if result.level == MatchLevel.HIGH_ID:
            stats["high_id"] += 1
        elif result.level == MatchLevel.HIGH_NAME:
            stats["high_name"] += 1
        elif result.level == MatchLevel.MEDIUM:
            stats["medium"] += 1
        elif result.level == MatchLevel.LOW:
            stats["low"] += 1
        else:
            stats["none"] += 1

        if result.should_skip():
            stats["to_skip"] += 1
            stats["skipped_projects"].append(
                {
                    "project": project,
                    "match_result": result,
                }
            )
        else:
            stats["to_import"] += 1
            stats["import_projects"].append(project)

    return stats
