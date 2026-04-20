# Job Fit Agent — Phase 1

An AI-powered job fit analyzer built with Python + Anthropic API.

## Project Structure
```
job_fit_agent/
├── src/
│   ├── analyzer.py      # Core fit analysis logic
│   ├── models.py        # Data models / typed outputs
│   └── prompts.py       # Prompt templates (your prompt engineering playground)
├── evals/
│   └── eval_suite.py    # Phase 2: eval framework (coming next)
├── data/
│   ├── resume.txt       # Your resume (paste it here)
│   └── sample_jds/      # Sample job descriptions for testing
├── tests/
│   └── test_analyzer.py # Basic unit tests
├── main.py              # CLI entry point
├── requirements.txt
└── README.md
```

## Setup
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Add your Anthropic API key
export ANTHROPIC_API_KEY="your-key-here"

# Run it
python main.py --jd data/sample_jds/example.txt

# Run Eval Engine
pytest evals/eval_suite.py -v
```


## Learning Goals (Phase 1)
- Python fundamentals: classes, dataclasses, type hints, file I/O
- Anthropic API: client setup, messages, structured outputs
- Prompt engineering: system prompts, context injection, output formatting
- Error handling and validation in Python

## Lessons
- Phase 1 — Python + Anthropic API + structured outputs
- Phase 2 — Eval framework for measuring AI quality
- Phase 3 — Playwright UI (closes the Playwright gap)
- Phase 4 — Azure DevOps pipeline
- Phase 5 — LangChain agent refactor

#
# Phase 2 - EVAL FRAMEWORK
## What I built:
- A ground truth dataset of 4 labeled job fits
- 4 test classes covering fit accuracy, output quality, recommendations, and structural integrity
- Session-scoped caching so 52 tests run on 4 API calls
- A working eval loop — run, fail, diagnose, fix, repeat

## What I learned:
- Every single failure across 5 runs was a ground truth problem, not a Claude problem. That's the central lesson of AI evaluation work and it's not obvious until you experience it. The AI was often more accurate than the human ground truth. Knowing when to fix the eval vs. fix the AI is the judgment call that separates good AI QE from bad AI QE.
- What I can now say in an interview:
"I built an eval framework for an LLM-based system — defined ground truth, wrote property-based tests for non-deterministic outputs, and iterated through multiple rounds of ground truth refinement. The hardest part wasn't the code, it was distinguishing between AI errors and ground truth errors."