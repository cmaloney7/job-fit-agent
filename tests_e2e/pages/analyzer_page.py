"""
tests_e2e/pages/analyzer_page.py — Page Object for the Job Fit Agent UI.

LEARNING NOTE: A Page Object (PO) is a design pattern for UI testing.
Instead of writing raw Playwright calls in every test:

    page.locator('[data-testid="resume-input"]').fill(resume_text)
    page.locator('[data-testid="analyze-button"]').click()

You create a class that wraps those interactions:

    analyzer_page.fill_resume(resume_text)
    analyzer_page.click_analyze()

Benefits:
1. Tests read like plain English — easier to understand and maintain
2. If the UI changes (e.g., a testid changes), you fix it in ONE place
3. You can add helper methods like wait_for_results() that handle timing

This is the same principle as reusable component architecture in test
automation frameworks — don't repeat yourself, abstract the details.

PLAYWRIGHT KEY CONCEPTS:
- page.locator()   — finds elements, supports CSS, XPath, text, testid
- .fill()          — types into an input or textarea
- .click()         — clicks an element
- .text_content()  — gets the visible text
- .is_visible()    — checks if element is on screen
- .wait_for()      — waits until element matches a state
- expect(locator)  — assertion with automatic retry/waiting
"""

from playwright.sync_api import Page, expect


class AnalyzerPage:
    """
    Page object for the main Job Fit Agent UI page.

    All interactions with the UI go through this class.
    Tests import this and use its methods instead of raw Playwright calls.
    """

    def __init__(self, page: Page):
        self.page = page

        # ── Locators ──────────────────────────────────────────────
        # LEARNING NOTE: We use data-testid attributes for locators.
        # This is better than CSS classes (which change for style reasons)
        # or text (which changes for copy reasons).
        # data-testid attributes exist ONLY for testing — stable contract.

        self.resume_input    = page.get_by_test_id("resume-input")
        self.jd_input        = page.get_by_test_id("jd-input")
        self.analyze_button  = page.get_by_test_id("analyze-button")
        self.results_panel   = page.get_by_test_id("results-panel")
        self.verdict_banner  = page.get_by_test_id("verdict-banner")
        self.fit_level       = page.get_by_test_id("fit-level")
        self.fit_score       = page.get_by_test_id("fit-score")
        self.apply_rec       = page.get_by_test_id("apply-recommendation")
        self.headline        = page.get_by_test_id("headline")
        self.error_message   = page.get_by_test_id("error-message")
        self.matches_list    = page.get_by_test_id("matches-list")
        self.gaps_list       = page.get_by_test_id("gaps-list")

    # ── Actions ────────────────────────────────────────────────────

    def fill_resume(self, text: str):
        """Fill the resume textarea."""
        self.resume_input.fill(text)

    def fill_jd(self, text: str):
        """Fill the job description textarea."""
        self.jd_input.fill(text)

    def click_analyze(self):
        """Click the analyze button."""
        self.analyze_button.click()

    def analyze(self, resume: str, jd: str):
        """
        Full flow: fill both fields and click analyze.
        Convenience method used by most tests.
        """
        self.fill_resume(resume)
        self.fill_jd(jd)
        self.click_analyze()

    def wait_for_results(self, timeout: int = 60000):
        """
        Wait for results panel to appear.

        LEARNING NOTE: timeout is in milliseconds. Playwright's default
        is 30 seconds but API calls can take longer — we use 60s here.
        This is the key difference from Cypress: Playwright timeouts are
        explicit per-action, Cypress has a global timeout setting.
        """
        self.results_panel.wait_for(state="visible", timeout=timeout)

    def wait_for_error(self, timeout: int = 10000):
        """Wait for error message to appear."""
        self.error_message.wait_for(state="visible", timeout=timeout)

    # ── Queries ────────────────────────────────────────────────────

    def get_fit_level(self) -> str:
        """Get the fit level text (e.g., 'Strong Fit')."""
        return self.fit_level.text_content().strip()

    def get_fit_score(self) -> int:
        """Get the numeric fit score from the score badge."""
        # Score badge text is like "82 / 100" — extract the number
        text = self.fit_score.text_content().strip()
        return int(text.split("/")[0].strip())

    def get_headline(self) -> str:
        """Get the analysis headline text."""
        return self.headline.text_content().strip()

    def get_error_text(self) -> str:
        """Get the error message text."""
        return self.error_message.text_content().strip()

    def is_worth_applying(self) -> bool:
        """Check if the recommendation is to apply."""
        text = self.apply_rec.text_content().strip()
        return "worth applying" in text.lower()

    def get_match_count(self) -> int:
        """Count how many strong matches are shown."""
        return self.matches_list.locator(".item").count()

    def get_gap_count(self) -> int:
        """Count how many gaps are shown."""
        return self.gaps_list.locator(".gap-item").count()

    def has_blocking_gaps(self) -> bool:
        """Check if any blocking severity gaps are present."""
        return self.gaps_list.locator(".severity.blocking").count() > 0

    def is_results_visible(self) -> bool:
        """Check if the results panel is visible."""
        return self.results_panel.is_visible()

    def is_error_visible(self) -> bool:
        """Check if the error box is visible."""
        return self.error_message.is_visible()
