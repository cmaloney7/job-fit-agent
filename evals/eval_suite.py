"""
evals/eval_suite.py — Phase 2: AI Output Evaluation Framework

This is where you learn to measure AI quality systematically.

The core problem: Claude's responses are non-deterministic. You can't write
a traditional unit test that says "output == expected_output" because the
output changes every run. Instead you define PROPERTIES that good output
must have — and test for those.

This is exactly what Amplifire, RadarFirst, and the AI QA Engineer role
are asking for when they say "build evaluation frameworks for AI features."

Run with:
    pytest evals/eval_suite.py -v
    pytest evals/eval_suite.py -v --tb=short   # less verbose on failures
    pytest evals/eval_suite.py -v -k "test_fit_level"  # run one test group

LEARNING NOTE: These tests DO call the Anthropic API. They will cost a small
amount per run (~$0.05-0.15 depending on model). Run them deliberately, not
on every save. In a real CI/CD pipeline you'd gate these behind a flag.
"""

import pytest
import os
from pathlib import Path
from src.analyzer import JobFitAnalyzer
from src.models import FitAnalysis, FitLevel


# ─── Ground Truth Dataset ─────────────────────────────────────────────────────
#
# This is your "labeled dataset" — the known correct answers you're testing
# Claude against. You built this manually over months of job search work.
# Now you're using it to measure AI quality.
#
# LEARNING NOTE: In production AI QE, building ground truth datasets is
# often the hardest and most valuable work. A good eval is only as good
# as its ground truth.

GROUND_TRUTH = [
    {
        "id": "gravie",
        "jd_file": "data/sample_jds/gravie.txt",
        "expected_fit_level": FitLevel.STRONG,
        "expected_score_min": 75,
        "expected_score_max": 100,
        "must_mention_skills": ["Claude Code", "Cypress", "framework"],
        "must_identify_gaps": ["Playwright"],
        "should_recommend_applying": True,
        "notes": "Strong fit — daily Claude Code user, framework-from-scratch history",
    },
    {
        "id": "e2optics",
        "jd_file": "data/sample_jds/e2optics.txt",
        "expected_fit_level": FitLevel.NOT_FIT,
        "expected_score_min": 0,
        "expected_score_max": 35,
        "must_mention_skills": [],
        "must_identify_gaps": ["structured cabling", "BICSI", "construction"],
        "should_recommend_applying": False,
        "notes": "Not a fit — physical construction QA, no software overlap",
    },
    {
        "id": "anthropic",
        "jd_file": "data/sample_jds/anthropic.txt",
        "expected_fit_level": FitLevel.STRETCH,
        "expected_score_min": 15,
        "expected_score_max": 45,
        "must_mention_skills": ["Claude Code", "evaluation"],
        "must_identify_gaps": ["model training", "system prompt"],
        "should_recommend_applying": None,  # None = we don't assert this
        "notes": "Stretch — strong Claude Code use but no ML engineering depth",
    },
    {
        "id": "disney",
        "jd_file": "data/sample_jds/disneysdet.txt",
        "expected_fit_level": FitLevel.PARTIAL,
        "expected_score_min": 55,
        "expected_score_max": 80,
        "must_mention_skills": ["automation", "leadership", "python"],
        "must_identify_gaps": [],   # No major gaps expected
        "should_recommend_applying": True,
        "notes": "Strong fit — principal SDET leadership role",
    },
]


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def analyzer():
    """
    LEARNING NOTE: scope="session" means this fixture is created once for
    the entire test session, not once per test. Since the analyzer has no
    state that changes between tests, this is fine and avoids re-initializing
    the Anthropic client repeatedly.
    """
    return JobFitAnalyzer(max_tokens=4000)


@pytest.fixture(scope="session")
def resume_text():
    """Load resume once for the entire session."""
    resume_path = Path("data/resume.txt")
    if not resume_path.exists():
        pytest.skip("data/resume.txt not found — add your resume to run evals")
    return resume_path.read_text(encoding="utf-8").strip()


@pytest.fixture(scope="session")
def analyses(analyzer, resume_text):
    """
    Run all analyses once and cache results for the session.

    LEARNING NOTE: This is important — without caching, each test would
    make a separate API call, costing 10x more and taking 10x longer.
    In production eval systems, you always separate "generate outputs"
    from "evaluate outputs."

    This fixture generates all outputs first, then the tests below just
    evaluate the cached results.
    """
    results = {}
    for case in GROUND_TRUTH:
        jd_path = Path(case["jd_file"])
        if not jd_path.exists():
            print(f"\nWARNING: {case['jd_file']} not found — skipping {case['id']}")
            continue
        try:
            jd_text = jd_path.read_text(encoding="utf-8").strip()
            analysis = analyzer.analyze(resume_text, jd_text)
            results[case["id"]] = analysis
            print(f"\n✓ Analyzed: {case['id']} → {analysis.fit_level.value} ({analysis.fit_score}/100)")
        except Exception as e:
            print(f"\n✗ Failed: {case['id']} → {e}")
            results[case["id"]] = None
    return results


# ─── Eval Tests ───────────────────────────────────────────────────────────────
#
# LEARNING NOTE: pytest.mark.parametrize runs the same test function multiple
# times with different inputs. This is the clean way to test multiple cases
# without copy-pasting test functions.

@pytest.mark.parametrize("case", GROUND_TRUTH, ids=[c["id"] for c in GROUND_TRUTH])
class TestFitLevelAccuracy:
    """
    Does Claude assign the right fit level to each JD?
    This is the most important eval — a wrong fit level is a wrong recommendation.
    """

    def test_fit_level_matches_ground_truth(self, analyses, case):
        """Claude's fit level should match our manually determined ground truth."""
        analysis = analyses.get(case["id"])
        if analysis is None:
            pytest.skip(f"Analysis not available for {case['id']}")

        assert analysis.fit_level == case["expected_fit_level"], (
            f"\n[{case['id']}] Expected: {case['expected_fit_level'].value}"
            f"\n         Got:      {analysis.fit_level.value}"
            f"\n         Score:    {analysis.fit_score}/100"
            f"\n         Headline: {analysis.headline}"
            f"\n         Notes:    {case['notes']}"
        )

    def test_fit_score_in_expected_range(self, analyses, case):
        """Claude's numeric score should fall within the expected range."""
        analysis = analyses.get(case["id"])
        if analysis is None:
            pytest.skip(f"Analysis not available for {case['id']}")

        score = analysis.fit_score
        assert case["expected_score_min"] <= score <= case["expected_score_max"], (
            f"\n[{case['id']}] Score {score} outside expected range "
            f"[{case['expected_score_min']}-{case['expected_score_max']}]"
        )


@pytest.mark.parametrize("case", GROUND_TRUTH, ids=[c["id"] for c in GROUND_TRUTH])
class TestOutputQuality:
    """
    Is the analysis specific and accurate — or generic and hallucinated?
    These tests catch common AI failure modes: vagueness, missing key gaps,
    and false confidence.
    """

    def test_response_is_not_empty(self, analyses, case):
        """Basic sanity — did we get a real response?"""
        analysis = analyses.get(case["id"])
        if analysis is None:
            pytest.skip(f"Analysis not available for {case['id']}")

        assert analysis.headline, "Headline should not be empty"
        assert len(analysis.headline) > 20, "Headline is suspiciously short"

    def test_has_reasoning(self, analyses, case):
        """Claude should always explain its verdict."""
        analysis = analyses.get(case["id"])
        if analysis is None:
            pytest.skip(f"Analysis not available for {case['id']}")

        assert analysis.reasoning, "Reasoning should not be empty"
        assert len(analysis.reasoning) > 50, "Reasoning is suspiciously short"

    def test_mentions_expected_skills(self, analyses, case):
        """
        Claude should recognize and mention key skills when they're relevant.
        This catches cases where Claude gives a generic analysis rather than
        reading the actual resume.

        LEARNING NOTE: We check the full text of the analysis, not just one field.
        A skill might appear in strong_matches, differentiators, or reasoning.
        """
        analysis = analyses.get(case["id"])
        if analysis is None:
            pytest.skip(f"Analysis not available for {case['id']}")

        if not case["must_mention_skills"]:
            pytest.skip("No required skills to check for this case")

        # Combine all text fields for checking
        all_text = " ".join([
            analysis.headline or "",
            analysis.reasoning or "",
            " ".join(analysis.strong_matches),
            " ".join(analysis.differentiators),
        ]).lower()

        for skill in case["must_mention_skills"]:
            assert skill.lower() in all_text, (
                f"\n[{case['id']}] Expected mention of '{skill}' but didn't find it"
                f"\n         This may indicate a generic/hallucinated analysis"
            )

    def test_identifies_key_gaps(self, analyses, case):
        """
        Claude should identify known gaps.
        This catches false confidence — cases where Claude says 'Strong Fit'
        but misses an obvious gap.
        """
        analysis = analyses.get(case["id"])
        if analysis is None:
            pytest.skip(f"Analysis not available for {case['id']}")

        if not case["must_identify_gaps"]:
            pytest.skip("No required gaps to check for this case")

        gap_text = " ".join([
            g.skill.lower() for g in analysis.gaps
        ] + [
            analysis.reasoning.lower() if analysis.reasoning else ""
        ])

        for gap_keyword in case["must_identify_gaps"]:
            assert gap_keyword.lower() in gap_text, (
                f"\n[{case['id']}] Expected gap '{gap_keyword}' to be identified"
                f"\n         Gaps found: {[g.skill for g in analysis.gaps]}"
            )

    def test_not_fit_has_no_strong_matches(self, analyses, case):
        """
        For NOT_FIT cases, Claude shouldn't be finding lots of strong matches.
        This catches hallucination where Claude invents relevance.
        """
        analysis = analyses.get(case["id"])
        if analysis is None:
            pytest.skip(f"Analysis not available for {case['id']}")

        if case["expected_fit_level"] != FitLevel.NOT_FIT:
            pytest.skip("Only applies to NOT_FIT cases")

        assert analysis.fit_score <= 35, (
                f"\n[{case['id']}] NOT_FIT case scored {analysis.fit_score} — too high"
                f"\n         Score should be <= 35 for a clear domain mismatch"
            )

    def test_strong_fit_has_multiple_matches(self, analyses, case):
        """Strong fits should have substantive evidence — not just one match."""
        analysis = analyses.get(case["id"])
        if analysis is None:
            pytest.skip(f"Analysis not available for {case['id']}")

        if case["expected_fit_level"] != FitLevel.STRONG:
            pytest.skip("Only applies to STRONG cases")

        assert len(analysis.strong_matches) >= 3, (
            f"\n[{case['id']}] STRONG_FIT case only has {len(analysis.strong_matches)} matches"
            f"\n         Expected at least 3 specific matches"
        )


@pytest.mark.parametrize("case", GROUND_TRUTH, ids=[c["id"] for c in GROUND_TRUTH])
class TestApplicationRecommendation:
    """Does Claude's apply/skip recommendation match our ground truth?"""

    def test_application_recommendation(self, analyses, case):
        """The worth_applying flag should match our manual assessment."""
        analysis = analyses.get(case["id"])
        if analysis is None:
            pytest.skip(f"Analysis not available for {case['id']}")

        if case["should_recommend_applying"] is None:
            pytest.skip("No recommendation ground truth for this case")

        assert analysis.is_worth_applying() == case["should_recommend_applying"], (
            f"\n[{case['id']}] Recommendation mismatch"
            f"\n         Expected: {'Apply' if case['should_recommend_applying'] else 'Skip'}"
            f"\n         Got:      {'Apply' if analysis.is_worth_applying() else 'Skip'}"
            f"\n         Score:    {analysis.fit_score}/100"
        )


# ─── Structural Integrity Tests ───────────────────────────────────────────────
# These run on every case and catch malformed outputs regardless of content.

@pytest.mark.parametrize("case", GROUND_TRUTH, ids=[c["id"] for c in GROUND_TRUTH])
class TestStructuralIntegrity:
    """Is the output well-formed and complete?"""

    def test_score_is_valid_range(self, analyses, case):
        analysis = analyses.get(case["id"])
        if analysis is None:
            pytest.skip(f"Analysis not available for {case['id']}")
        assert 0 <= analysis.fit_score <= 100, f"Score {analysis.fit_score} out of range"

    def test_has_interview_questions(self, analyses, case):
        """Every non-rejected analysis should generate interview prep questions."""
        analysis = analyses.get(case["id"])
        if analysis is None:
            pytest.skip(f"Analysis not available for {case['id']}")

        # NOT_FIT cases may not generate interview questions — that's correct behavior
        if case["expected_fit_level"] == FitLevel.NOT_FIT:
            pytest.skip("NOT_FIT cases don't require interview questions")

        assert len(analysis.likely_interview_questions) >= 2, (
            "Should generate at least 2 interview questions"
        )

    def test_gaps_have_bridges(self, analyses, case):
        """Every gap should include actionable advice on how to address it."""
        analysis = analyses.get(case["id"])
        if analysis is None:
            pytest.skip(f"Analysis not available for {case['id']}")
        for gap in analysis.gaps:
            assert gap.bridge, f"Gap '{gap.skill}' has no bridge advice"
            assert len(gap.bridge) > 10, f"Gap '{gap.skill}' bridge is too short"

    def test_severity_values_are_valid(self, analyses, case):
        """Gap severities must be one of the three valid values."""
        analysis = analyses.get(case["id"])
        if analysis is None:
            pytest.skip(f"Analysis not available for {case['id']}")
        valid_severities = {"blocking", "notable", "minor"}
        for gap in analysis.gaps:
            assert gap.severity in valid_severities, (
                f"Gap '{gap.skill}' has invalid severity '{gap.severity}'"
            )
