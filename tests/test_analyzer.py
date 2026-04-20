"""
tests/test_analyzer.py — Basic unit tests for Phase 1.

LEARNING NOTE: pytest is the standard Python testing framework.
Run with: pytest tests/ -v

These tests don't call the API — they test the parsing and validation logic.
That's intentional: API calls are expensive and slow. Test the logic separately
from the API calls. This is the same philosophy you apply in QE.

Phase 2 will add eval tests that DO call the API and measure output quality.
"""

import pytest
from src.models import FitAnalysis, FitLevel, SkillGap
from src.analyzer import JobFitAnalyzer


# ─── Model Tests ──────────────────────────────────────────────────────────────

class TestFitAnalysis:
    """Tests for the FitAnalysis dataclass."""

    def test_strong_fit_is_worth_applying(self):
        analysis = FitAnalysis(
            fit_level=FitLevel.STRONG,
            fit_score=85,
            headline="Strong match across all requirements",
        )
        assert analysis.is_worth_applying() is True

    def test_not_fit_is_not_worth_applying(self):
        analysis = FitAnalysis(
            fit_level=FitLevel.NOT_FIT,
            fit_score=20,
            headline="Significant domain mismatch",
        )
        assert analysis.is_worth_applying() is False

    def test_partial_fit_above_threshold_is_worth_applying(self):
        analysis = FitAnalysis(
            fit_level=FitLevel.PARTIAL,
            fit_score=75,
            headline="Good fit with one notable gap",
        )
        assert analysis.is_worth_applying() is True

    def test_partial_fit_below_threshold_is_not_worth_applying(self):
        analysis = FitAnalysis(
            fit_level=FitLevel.PARTIAL,
            fit_score=45,
            headline="Some overlap but significant gaps",
        )
        assert analysis.is_worth_applying() is False

    def test_blocking_gaps_filter(self):
        analysis = FitAnalysis(
            fit_level=FitLevel.PARTIAL,
            fit_score=65,
            headline="Test",
            gaps=[
                SkillGap(skill="Python", severity="blocking", bridge="Learn Python"),
                SkillGap(skill="Jest", severity="notable", bridge="Transferable from Mocha"),
                SkillGap(skill="AWS", severity="minor", bridge="Familiarity sufficient"),
            ]
        )
        blocking = analysis.blocking_gaps()
        assert len(blocking) == 1
        assert blocking[0].skill == "Python"

    def test_no_blocking_gaps(self):
        analysis = FitAnalysis(
            fit_level=FitLevel.STRONG,
            fit_score=90,
            headline="Test",
            gaps=[
                SkillGap(skill="Jest", severity="minor", bridge="Transferable"),
            ]
        )
        assert len(analysis.blocking_gaps()) == 0


# ─── Parser Tests ─────────────────────────────────────────────────────────────

class TestResponseParser:
    """Tests for the JSON response parsing logic in JobFitAnalyzer."""

    def setup_method(self):
        """
        LEARNING NOTE: setup_method runs before each test.
        We create the analyzer without calling the API — just testing parsing.
        """
        self.analyzer = JobFitAnalyzer()

    def test_parses_valid_response(self):
        data = {
            "job_title": "Senior QA Engineer",
            "company_name": "Gravie",
            "fit_level": "Strong Fit",
            "fit_score": 88,
            "headline": "Daily Claude Code user with Cypress expertise — strong match",
            "reasoning": "Candidate's AI tooling depth is a genuine differentiator.",
            "strong_matches": ["Cypress framework expertise", "Claude Code daily use"],
            "gaps": [
                {
                    "skill": "Playwright",
                    "severity": "notable",
                    "bridge": "Architecture transfers from Cypress; learnable quickly"
                }
            ],
            "differentiators": ["Only candidate who uses Claude Code in production"],
            "cover_letter_angles": ["Lead with the AI-driven test generation workflow"],
            "likely_interview_questions": ["Walk me through your Cypress framework design"],
            "things_to_address_proactively": ["Playwright gap — have a clear answer ready"],
        }
        result = self.analyzer._parse_response(data)

        assert result.fit_level == FitLevel.STRONG
        assert result.fit_score == 88
        assert result.job_title == "Senior QA Engineer"
        assert result.company_name == "Gravie"
        assert len(result.strong_matches) == 2
        assert len(result.gaps) == 1
        assert result.gaps[0].skill == "Playwright"
        assert result.gaps[0].severity == "notable"

    def test_handles_unknown_fit_level_gracefully(self):
        """
        LEARNING NOTE: This tests defensive programming — what happens when
        Claude returns something unexpected. Good AI QE always tests the
        unexpected path.
        """
        data = {
            "fit_level": "Completely Made Up Level",
            "fit_score": 60,
            "headline": "Test",
        }
        result = self.analyzer._parse_response(data)
        # Should default to PARTIAL, not crash
        assert result.fit_level == FitLevel.PARTIAL

    def test_handles_missing_fields_gracefully(self):
        """Minimal valid response — only required fields."""
        data = {
            "fit_level": "Partial Fit",
            "fit_score": 65,
            "headline": "Good technical fit with one gap",
        }
        result = self.analyzer._parse_response(data)
        assert result.fit_level == FitLevel.PARTIAL
        assert result.strong_matches == []
        assert result.gaps == []

    def test_fit_score_converts_to_int(self):
        """Claude sometimes returns scores as strings."""
        data = {
            "fit_level": "Strong Fit",
            "fit_score": "82",      # String, not int
            "headline": "Test",
        }
        result = self.analyzer._parse_response(data)
        assert isinstance(result.fit_score, int)
        assert result.fit_score == 82


# ─── File Loading Tests ───────────────────────────────────────────────────────

class TestFileLoading:

    def setup_method(self):
        self.analyzer = JobFitAnalyzer()

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            self.analyzer.load_text("data/nonexistent_file.txt")

    def test_loads_existing_file(self, tmp_path):
        """
        LEARNING NOTE: tmp_path is a pytest fixture that gives you a temporary
        directory that's cleaned up after each test. Use it instead of creating
        real files in your project directory.
        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("Senior QA Engineer position requiring Cypress experience")

        content = self.analyzer.load_text(str(test_file))
        assert "Cypress" in content
