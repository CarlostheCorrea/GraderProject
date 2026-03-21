from __future__ import annotations

import re
from pathlib import Path


RUBRIC_EXAMPLE_DIR_MAP = {
    "college_cross_disciplinary_other_v1": "AcademicSkills",
    "essay_quality_v2": "EssayQualityExample",
    "college_humanities_social_sciences_meta_v2": "Humanities&SocialSciences",
    "phd_unified_meta_v3": "PhDAcademicPaper",
}

_GRADE_PRIORITY = {
    "A+": 8,
    "A": 7,
    "A-": 6,
    "B+": 5,
    "B": 4,
    "B-": 3,
    "C": 2,
    "Needs Major Revision": 1,
}


def _normalize_grade(raw_grade: str) -> str:
    cleaned = raw_grade.strip().replace("NeedsMajorRevision", "Needs Major Revision")
    return cleaned


def _parse_grade_from_filename(filename: str) -> str | None:
    match = re.match(r"^([A-C](?:[+-])?|NeedsMajorRevision|Needs\ Major\ Revision)[_ -].*", filename, flags=re.IGNORECASE)
    if not match:
        return None
    token = match.group(1)
    normalized = _normalize_grade(token)
    if normalized in _GRADE_PRIORITY:
        return normalized
    return None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def _compact_excerpt(text: str, max_chars: int = 700) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars].rstrip() + "..."


def load_calibration_examples(base_dir: Path) -> dict[str, list[dict]]:
    bank: dict[str, list[dict]] = {}
    for rubric_id, folder_name in RUBRIC_EXAMPLE_DIR_MAP.items():
        folder = base_dir / folder_name
        if not folder.exists() or not folder.is_dir():
            bank[rubric_id] = []
            continue

        examples: list[dict] = []
        for path in sorted(folder.glob("*.txt")):
            grade = _parse_grade_from_filename(path.name)
            if not grade:
                continue
            text = _read_text(path)
            if not text:
                continue
            examples.append(
                {
                    "grade": grade,
                    "filename": path.name,
                    "excerpt": _compact_excerpt(text),
                }
            )

        examples.sort(key=lambda row: _GRADE_PRIORITY.get(row["grade"], 0), reverse=True)
        bank[rubric_id] = examples
    return bank


def pick_calibration_anchors(examples: list[dict], max_examples: int = 3) -> list[dict]:
    if not examples:
        return []

    high = [row for row in examples if row["grade"] in {"A+", "A", "A-"}]
    mid = [row for row in examples if row["grade"] in {"B+", "B", "B-"}]
    low = [row for row in examples if row["grade"] in {"C", "Needs Major Revision"}]

    picked: list[dict] = []
    for bucket in (high, mid, low):
        if bucket:
            picked.append(bucket[0])

    if len(picked) < max_examples:
        seen = {row["filename"] for row in picked}
        for row in examples:
            if row["filename"] in seen:
                continue
            picked.append(row)
            seen.add(row["filename"])
            if len(picked) >= max_examples:
                break

    return picked[:max_examples]
