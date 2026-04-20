"""
tests_e2e/conftest.py — Playwright fixtures for the Job Fit Agent UI tests.

LEARNING NOTE: conftest.py is a special pytest file. Fixtures defined here
are automatically available to all tests in the same directory and subdirectories
without needing to import them.

This file sets up:
1. The Flask server as a background thread (so tests have something to talk to)
2. The Playwright browser and page fixtures
3. The AnalyzerPage page object

Run all E2E tests with:
    pytest tests_e2e/ -v

Run with visible browser (useful for debugging):
    pytest tests_e2e/ -v --headed

LEARNING NOTE: Playwright for Python uses async/await OR sync API.
We're using the SYNC API here (from playwright.sync_api) because it's
simpler to learn and doesn't require async test functions. The sync API
is perfectly fine for test suites — the async API is for production apps.
"""

import pytest
import threading
import time
import sys
import os

def pytest_configure(config):
    config.addinivalue_line("markers", "api: marks tests that call the Anthropic API")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext


# ── Server fixture ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def live_server():
    """
    Start the Flask server in a background thread for the test session.

    LEARNING NOTE: scope="session" means this fixture starts once and
    stays running for all tests. When the session ends, the server stops.

    We use threading.Thread because Flask's development server is blocking —
    it needs its own thread so pytest can continue running tests.
    """
    # Import here to avoid issues with path setup
    from web.app import app

    app.config["TESTING"] = True

    server_thread = threading.Thread(
        target=lambda: app.run(port=5001, debug=False, use_reloader=False),
        daemon=True  # daemon=True means thread dies when main process dies
    )
    server_thread.start()

    # Wait for server to be ready
    # LEARNING NOTE: This is a simple polling approach. In production
    # you'd use a more robust readiness check.
    import urllib.request
    for _ in range(20):
        try:
            urllib.request.urlopen("http://localhost:5001/health")
            break
        except Exception:
            time.sleep(0.3)

    yield "http://localhost:5001"
    # Server stops automatically because daemon=True


# ── Playwright fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def browser_instance():
    """
    Launch a single browser instance for the entire test session.

    LEARNING NOTE: Playwright supports chromium, firefox, and webkit.
    We use chromium (Chrome) by default. You can parametrize this to
    run tests across all three browsers — that's a Phase 4 enhancement.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Change to False to watch tests run
        )
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def page(browser_instance, live_server):
    """
    Create a fresh browser page (tab) for each test.

    LEARNING NOTE: scope="function" means each test gets a clean page.
    This prevents test pollution — one test's state doesn't bleed into the next.

    The page fixture is the main thing you use in Playwright tests.
    page.goto(), page.fill(), page.click(), page.locator() — all through page.
    """
    context = browser_instance.new_context()
    page = context.new_page()

    # Navigate to the app before each test
    page.goto(live_server)

    yield page

    # Cleanup after each test
    context.close()


# ── Sample data fixtures ───────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def sample_resume():
    """Load resume from data file — reused across all tests."""
    resume_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "resume.txt"
    )
    with open(resume_path, "r") as f:
        return f.read().strip()


@pytest.fixture(scope="session")
def sample_jd_gravie():
    """Load Gravie JD — known strong fit for testing positive flows."""
    jd_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "sample_jds", "gravie.txt"
    )
    with open(jd_path, "r") as f:
        return f.read().strip()


@pytest.fixture(scope="session")
def sample_jd_e2optics():
    """Load E2 Optics JD — known not-fit for testing negative flows."""
    jd_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "sample_jds", "e2optics.txt"
    )
    with open(jd_path, "r") as f:
        return f.read().strip()
