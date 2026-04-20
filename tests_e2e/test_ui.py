"""
tests_e2e/test_ui.py — Playwright E2E tests for the Job Fit Agent UI.

These tests open a real browser, interact with the UI like a real user,
and verify the application works end-to-end.

LEARNING NOTE: The key differences between these E2E tests and the
unit/eval tests you've already written:

Unit tests (tests/):      No browser, no API, instant, test logic only
Eval tests (evals/):      Real API calls, no browser, test AI output quality
E2E tests (tests_e2e/):  Real browser, real API, slow, test the full system

Each layer has a purpose. E2E tests catch integration bugs that unit tests
can't — like "the button doesn't trigger the right API endpoint" or
"the results don't render when the response comes back."

Run with:
    pytest tests_e2e/ -v               # headless (fast)
    pytest tests_e2e/ -v --headed      # visible browser (great for learning)
    pytest tests_e2e/ -v -k "smoke"    # just smoke tests (no API calls)
    pytest tests_e2e/ -v -k "not api"  # skip tests that call the API

PLAYWRIGHT ASSERTIONS:
    expect(locator).to_be_visible()          — element is on screen
    expect(locator).to_have_text("...")      — exact text match
    expect(locator).to_contain_text("...")   — partial text match
    expect(locator).to_be_enabled()          — not disabled
    expect(locator).to_be_disabled()         — is disabled
    expect(locator).to_have_count(n)         — n elements match

All expect() assertions automatically retry for up to 5 seconds before
failing — no explicit waits needed for most cases.
"""

import pytest
from playwright.sync_api import Page, expect
from tests_e2e.pages.analyzer_page import AnalyzerPage


# ── Smoke tests (no API calls) ─────────────────────────────────────────────────
# Fast tests that verify the UI loads and basic interactions work.
# Run these during development to check the UI without hitting the API.

class TestSmoke:
    """Basic smoke tests — verify the page loads and UI elements exist."""

    def test_page_loads(self, page: Page):
        """
        The page should load with the correct title.

        LEARNING NOTE: This is your first Playwright assertion.
        expect(page).to_have_title() checks the <title> tag.
        Playwright automatically waits and retries until it passes or times out.
        """
        expect(page).to_have_title("Job Fit Agent")

    def test_input_fields_present(self, page: Page):
        """Both textarea inputs should be visible on load."""
        ap = AnalyzerPage(page)
        expect(ap.resume_input).to_be_visible()
        expect(ap.jd_input).to_be_visible()

    def test_analyze_button_present(self, page: Page):
        """The analyze button should be visible and enabled."""
        ap = AnalyzerPage(page)
        expect(ap.analyze_button).to_be_visible()
        expect(ap.analyze_button).to_be_enabled()

    def test_results_hidden_on_load(self, page: Page):
        """Results panel should not be visible before analysis runs."""
        ap = AnalyzerPage(page)
        expect(ap.results_panel).to_be_hidden()

    def test_error_hidden_on_load(self, page: Page):
        """Error box should not be visible on initial load."""
        ap = AnalyzerPage(page)
        expect(ap.error_message).to_be_hidden()

    def test_typing_in_resume_field(self, page: Page):
        """Should be able to type in the resume field."""
        ap = AnalyzerPage(page)
        ap.fill_resume("Test resume content")
        expect(ap.resume_input).to_have_value("Test resume content")

    def test_typing_in_jd_field(self, page: Page):
        """Should be able to type in the JD field."""
        ap = AnalyzerPage(page)
        ap.fill_jd("Test job description")
        expect(ap.jd_input).to_have_value("Test job description")


# ── Validation tests (no API calls) ───────────────────────────────────────────
# Test that the server validates inputs correctly.

class TestValidation:
    """Input validation — verify error handling for bad inputs."""

    def test_empty_resume_shows_error(self, page: Page):
        """
        Submitting with empty resume should show an error.

        LEARNING NOTE: We fill the JD but leave resume empty.
        The server should return a 400 with an error message.
        """
        ap = AnalyzerPage(page)
        ap.fill_jd("Senior QA Engineer requiring 5 years Cypress experience")
        ap.click_analyze()
        ap.wait_for_error()
        expect(ap.error_message).to_be_visible()
        expect(ap.error_message).to_contain_text("Resume")

    def test_empty_jd_shows_error(self, page: Page):
        """Submitting with empty JD should show an error."""
        ap = AnalyzerPage(page)
        ap.fill_resume("Corey Molloy, 15 years QA engineering experience " * 5)
        ap.click_analyze()
        ap.wait_for_error()
        expect(ap.error_message).to_be_visible()
        expect(ap.error_message).to_contain_text("Job description")

    def test_short_resume_shows_error(self, page: Page):
        """A suspiciously short resume should show an error."""
        ap = AnalyzerPage(page)
        ap.fill_resume("I am a QA engineer.")
        ap.fill_jd("Senior QA Engineer requiring 5 years Cypress experience in financial services")
        ap.click_analyze()
        ap.wait_for_error()
        expect(ap.error_message).to_be_visible()

    def test_error_clears_on_new_valid_submission(self, page: Page, sample_resume, sample_jd_gravie):
        """
        After an error, a valid submission should clear the error and show results.

        LEARNING NOTE: This tests state management — does the UI correctly
        reset error state when a new valid request comes in?
        """
        ap = AnalyzerPage(page)

        # First trigger an error
        ap.fill_jd("Short JD")
        ap.click_analyze()
        ap.wait_for_error()
        expect(ap.error_message).to_be_visible()

        # Now submit valid data
        ap.fill_resume(sample_resume)
        ap.fill_jd(sample_jd_gravie)
        ap.click_analyze()
        ap.wait_for_results(timeout=60000)

        # Error should be gone, results should show
        expect(ap.error_message).to_be_hidden()
        expect(ap.results_panel).to_be_visible()


# ── Analysis flow tests (API calls) ───────────────────────────────────────────
# These tests call the real Anthropic API — they're slower and cost money.
# Mark them explicitly so you can skip them during rapid UI iteration.

@pytest.mark.api
class TestAnalysisFlow:
    """Full analysis flow tests — require running Anthropic API."""

    def test_strong_fit_renders_correctly(self, page: Page, sample_resume, sample_jd_gravie):
        """
        A strong fit analysis should render the verdict banner, score,
        matches, and gaps correctly.

        LEARNING NOTE: This is your most important E2E test.
        It validates the complete happy path: input → API → rendered results.
        """
        ap = AnalyzerPage(page)
        ap.analyze(sample_resume, sample_jd_gravie)
        ap.wait_for_results(timeout=60000)

        # Results panel visible
        expect(ap.results_panel).to_be_visible()

        # Fit level shown
        expect(ap.fit_level).to_be_visible()
        fit_level = ap.get_fit_level()
        assert fit_level in ["Strong Fit", "Partial Fit", "Stretch / Long Shot", "Not a Fit"]

        # Score shown and in valid range
        score = ap.get_fit_score()
        assert 0 <= score <= 100

        # Headline shown
        expect(ap.headline).to_be_visible()
        assert len(ap.get_headline()) > 10

        # Recommendation shown
        expect(ap.apply_rec).to_be_visible()

    def test_strong_fit_has_matches(self, page: Page, sample_resume, sample_jd_gravie):
        """A strong fit analysis should show multiple strong matches."""
        ap = AnalyzerPage(page)
        ap.analyze(sample_resume, sample_jd_gravie)
        ap.wait_for_results(timeout=60000)

        match_count = ap.get_match_count()
        assert match_count >= 2, f"Expected at least 2 matches, got {match_count}"

    def test_not_fit_verdict_for_wrong_domain(self, page: Page, sample_resume, sample_jd_e2optics):
        """
        E2 Optics (construction QA) should render as Not a Fit.

        LEARNING NOTE: This tests the negative path — the UI should handle
        NOT_FIT results correctly just as well as STRONG_FIT results.
        """
        ap = AnalyzerPage(page)
        ap.analyze(sample_resume, sample_jd_e2optics)
        ap.wait_for_results(timeout=60000)

        expect(ap.results_panel).to_be_visible()
        fit_level = ap.get_fit_level()
        score = ap.get_fit_score()

        assert fit_level == "Not a Fit", f"Expected 'Not a Fit', got '{fit_level}'"
        assert score <= 35, f"Expected score <= 35 for NOT_FIT, got {score}"
        assert not ap.is_worth_applying(), "Should not recommend applying for NOT_FIT"

    def test_verdict_banner_has_correct_css_class(self, page: Page, sample_resume, sample_jd_gravie):
        """
        The verdict banner should have the correct CSS class for the fit level.

        LEARNING NOTE: This tests visual logic — does the right color class
        get applied to the banner? This catches bugs where the data is correct
        but the styling logic is broken.
        """
        ap = AnalyzerPage(page)
        ap.analyze(sample_resume, sample_jd_gravie)
        ap.wait_for_results(timeout=60000)

        fit_level = ap.get_fit_level()
        banner = ap.verdict_banner

        if fit_level == "Strong Fit":
            expect(banner).to_have_class("verdict strong")
        elif fit_level == "Partial Fit":
            expect(banner).to_have_class("verdict partial")
        elif fit_level == "Stretch / Long Shot":
            expect(banner).to_have_class("verdict stretch")
        elif fit_level == "Not a Fit":
            expect(banner).to_have_class("verdict not-fit")

    def test_second_analysis_replaces_first(self, page: Page, sample_resume, sample_jd_gravie, sample_jd_e2optics):
        """
        Running a second analysis should replace the first results.

        LEARNING NOTE: This tests state reset — does the UI correctly
        clear previous results when a new analysis runs?
        This is a common UI bug: old results bleed into new ones.
        """
        ap = AnalyzerPage(page)

        # First analysis
        ap.analyze(sample_resume, sample_jd_gravie)
        ap.wait_for_results(timeout=60000)
        first_headline = ap.get_headline()

        # Second analysis with different JD
        ap.fill_jd(sample_jd_e2optics)
        ap.click_analyze()
        ap.wait_for_results(timeout=60000)
        second_headline = ap.get_headline()

        # Headlines should be different
        assert first_headline != second_headline, "Second analysis should produce different results"
