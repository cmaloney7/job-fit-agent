"""
models.py — Typed data structures for job fit analysis.

LEARNING NOTE: Python dataclasses are like TypeScript interfaces but with
built-in __init__, __repr__, and optional validation. The @dataclass decorator
generates boilerplate so you don't have to write it manually.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class FitLevel(Enum):
    """
    LEARNING NOTE: Python Enum — similar to TypeScript enum.
    Use .value to get the string, e.g. FitLevel.STRONG.value == "Strong Fit"
    """
    STRONG    = "Strong Fit"
    PARTIAL   = "Partial Fit"
    STRETCH   = "Stretch / Long Shot"
    NOT_FIT   = "Not a Fit"


@dataclass
class SkillGap:
    """Represents a single gap between job requirements and candidate background."""
    skill: str
    severity: str        # "blocking", "notable", "minor"
    bridge: str          # How to address it or frame it


@dataclass
class FitAnalysis:
    """
    The structured output of a job fit analysis.

    LEARNING NOTE: field(default_factory=list) is how you set mutable defaults
    in dataclasses. Never use field(default=[]) — that's a Python gotcha where
    all instances share the same list object.
    """
    # Core verdict
    fit_level: FitLevel
    fit_score: int                          # 0-100
    headline: str                           # One sentence summary

    # Detailed breakdown
    strong_matches: list[str] = field(default_factory=list)
    gaps: list[SkillGap] = field(default_factory=list)
    differentiators: list[str] = field(default_factory=list)   # Things that make you stand out

    # Actionable outputs
    cover_letter_angles: list[str] = field(default_factory=list)
    likely_interview_questions: list[str] = field(default_factory=list)
    things_to_address_proactively: list[str] = field(default_factory=list)

    # Metadata
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    reasoning: Optional[str] = None        # Claude's full reasoning (useful for debugging prompts)

    def blocking_gaps(self) -> list[SkillGap]:
        """Return only the gaps that could end a screening conversation."""
        return [g for g in self.gaps if g.severity == "blocking"]

    def is_worth_applying(self) -> bool:
        """Simple heuristic — override this with your own judgment."""
        return self.fit_level in (FitLevel.STRONG, FitLevel.PARTIAL) and self.fit_score >= 60

    def __str__(self) -> str:
        gaps_str = "\n".join(f"  - [{g.severity}] {g.skill}: {g.bridge}" for g in self.gaps)
        matches_str = "\n".join(f"  + {m}" for m in self.strong_matches)
        return (
            f"\n{'='*60}\n"
            f"  {self.fit_level.value} ({self.fit_score}/100)\n"
            f"  {self.headline}\n"
            f"{'='*60}\n"
            f"\nSTRONG MATCHES:\n{matches_str}\n"
            f"\nGAPS:\n{gaps_str}\n"
            f"\nWORTH APPLYING: {'Yes' if self.is_worth_applying() else 'No'}\n"
        )
