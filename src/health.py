"""
src/health.py — Anthropic API health check utility.

Used by all three phases to verify the API key is valid and working
before running tests or starting the server.

Usage:
    # From command line
    python -m src.health

    # From code
    from src.health import check_api_key, require_api_key
    check_api_key()   # prints status, returns True/False
    require_api_key() # prints status, exits if not working
"""

import os
import sys


def check_api_key(verbose: bool = True) -> bool:
    """
    Verify the Anthropic API key is set and valid.

    Makes a minimal API call (1 token) to confirm authentication works.
    Returns True if healthy, False if not.
    """
    # Load .env if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    # Check 1 — key exists
    if not api_key:
        if verbose:
            print("✗ ANTHROPIC_API_KEY is not set.")
            print("  Fix: Add it to your .env file or run:")
            print("       export ANTHROPIC_API_KEY='sk-ant-...'")
        return False

    # Check 2 — key has right format
    if not api_key.startswith("sk-ant-"):
        if verbose:
            print(f"✗ ANTHROPIC_API_KEY looks wrong (starts with '{api_key[:10]}...')")
            print("  Expected format: sk-ant-...")
            print("  Get your key at: console.anthropic.com")
        return False

    # Check 3 — make a minimal live API call
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        client.messages.create(
            model="claude-haiku-4-5-20251001",  # cheapest model for health check
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        if verbose:
            masked = f"{api_key[:12]}...{api_key[-4:]}"
            print(f"✓ Anthropic API key is valid and working ({masked})")
        return True

    except anthropic.AuthenticationError:
        if verbose:
            print("✗ Anthropic API key is invalid or expired.")
            print("  Get a new key at: console.anthropic.com/settings/keys")
        return False

    except anthropic.APIConnectionError:
        if verbose:
            print("✗ Could not connect to Anthropic API.")
            print("  Check your internet connection and try again.")
        return False

    except anthropic.RateLimitError:
        if verbose:
            print("⚠ API key is valid but rate limit hit.")
            print("  Wait a moment and try again.")
        return True  # key is valid, just rate limited

    except Exception as e:
        if verbose:
            print(f"✗ Unexpected error checking API key: {e}")
        return False


def require_api_key():
    """
    Check API key and exit with a helpful message if it's not working.
    Use this at the start of scripts that require a valid key.
    """
    if not check_api_key(verbose=True):
        print()
        print("Cannot continue without a valid API key.")
        print("See DOCUMENTATION.md → API Key Setup for instructions.")
        sys.exit(1)


if __name__ == "__main__":
    """Run as: python -m src.health"""
    print("Checking Anthropic API key...\n")
    ok = check_api_key(verbose=True)
    sys.exit(0 if ok else 1)
