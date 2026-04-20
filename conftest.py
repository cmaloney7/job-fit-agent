import sys
import os

# Add project root to Python path so 'src' can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "api: marks tests that call the Anthropic API"
    )

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print a helpful summary note after eval runs."""
    skipped = len(terminalreporter.stats.get('skipped', []))
    if skipped > 0 and skipped <= 12:
        terminalreporter.write_sep(
            "-",
            f"NOTE: {skipped} skips are expected and intentional — "
            "run 'pytest evals/eval_suite.py -v --tb=short' for details, "
            "or see the Skip Reason Reference at the bottom of eval_suite.py"
        )
        