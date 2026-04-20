"""
web/app.py — Flask web server for the Job Fit Agent UI.

This is your Phase 3 backend. It:
1. Serves the HTML UI at GET /
2. Accepts POST /analyze with resume + JD text
3. Calls the existing JobFitAnalyzer
4. Returns structured JSON to the frontend

LEARNING NOTE: Flask is Python's most popular lightweight web framework.
- @app.route() decorates a function to handle a URL
- request.json reads the JSON body from a POST request
- jsonify() converts a Python dict to a JSON response
- render_template() serves an HTML file from the templates/ folder

Run with:
    cd web && python app.py
    # Then open http://localhost:5000 in your browser

Or from the project root:
    python web/app.py
"""

import sys
import os
from dotenv import load_dotenv
load_dotenv()

# LEARNING NOTE: This adds the project root to Python's import path
# so we can import from src/ even though we're running from web/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, render_template
from src.analyzer import JobFitAnalyzer
from src.models import FitLevel

app = Flask(__name__, template_folder="templates", static_folder="static")

# Initialize analyzer once at startup — not on every request
analyzer = JobFitAnalyzer(max_tokens=4000)


@app.route("/")
def index():
    """Serve the main UI page."""
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Accept resume + JD text, return fit analysis as JSON.

    Expected request body:
    {
        "resume": "full resume text...",
        "job_description": "full JD text..."
    }

    Returns:
    {
        "success": true,
        "data": { ...fit analysis fields... }
    }

    LEARNING NOTE: Always validate inputs before processing.
    Return consistent error shapes so the frontend can handle them predictably.
    This is the same defensive programming principle from Phase 1.
    """
    data = request.get_json()

    # Input validation
    if not data:
        return jsonify({"success": False, "error": "No JSON body provided"}), 400

    resume = data.get("resume", "").strip()
    job_description = data.get("job_description", "").strip()

    if not resume:
        return jsonify({"success": False, "error": "Resume text is required"}), 400

    if not job_description:
        return jsonify({"success": False, "error": "Job description is required"}), 400

    if len(resume) < 100:
        return jsonify({"success": False, "error": "Resume text seems too short — please paste your full resume"}), 400

    if len(job_description) < 50:
        return jsonify({"success": False, "error": "Job description seems too short"}), 400

    # Run analysis
    try:
        analysis = analyzer.analyze(resume, job_description)
    except RuntimeError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    except ValueError as e:
        return jsonify({"success": False, "error": f"Analysis parsing error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": "Unexpected error during analysis"}), 500

    # Serialize the FitAnalysis dataclass to a dict
    # LEARNING NOTE: Dataclasses don't auto-serialize to JSON.
    # We manually build the dict here. In Phase 5 (LangChain refactor)
    # we'd use Pydantic models which handle this automatically.
    result = {
        "fit_level": analysis.fit_level.value,
        "fit_score": analysis.fit_score,
        "headline": analysis.headline,
        "reasoning": analysis.reasoning,
        "job_title": analysis.job_title,
        "company_name": analysis.company_name,
        "strong_matches": analysis.strong_matches,
        "gaps": [
            {
                "skill": g.skill,
                "severity": g.severity,
                "bridge": g.bridge,
            }
            for g in analysis.gaps
        ],
        "differentiators": analysis.differentiators,
        "cover_letter_angles": analysis.cover_letter_angles,
        "likely_interview_questions": analysis.likely_interview_questions,
        "things_to_address_proactively": analysis.things_to_address_proactively,
        "is_worth_applying": analysis.is_worth_applying(),
        "blocking_gaps": [g.skill for g in analysis.blocking_gaps()],
    }

    return jsonify({"success": True, "data": result})


@app.route("/health")
def health():
    """
    Health check endpoint.

    LEARNING NOTE: Every web app should have a /health endpoint.
    Playwright tests use this to verify the server is running before
    starting the test suite. CI/CD pipelines use it the same way.
    """
    return jsonify({"status": "ok", "service": "job-fit-agent"})


if __name__ == "__main__":
    # LEARNING NOTE: debug=True enables auto-reload on file changes
    # and shows detailed error pages. Never use debug=True in production.
    app.run(debug=True, port=5000)
