# Job Fit Agent

An AI-powered job fit analyzer built with Python + Anthropic API + LangChain.

## Project Structure
```
job_fit_agent/
├── src/
│   ├── agent.py         # Phase 5: LangChain multi-tool agent
│   ├── analyzer.py      # Core fit analysis logic
│   ├── models.py        # Data models / typed outputs
│   └── prompts.py       # Prompt templates
├── evals/
│   └── eval_suite.py    # Phase 2: AI output evaluation framework
├── tests/
│   └── test_analyzer.py # Unit tests (no API calls)
├── tests_e2e/           # Phase 3: Playwright E2E tests
├── web/
│   └── app.py           # Phase 3: Flask web server
├── data/
│   ├── resume.txt       # Your resume in plain text
│   └── sample_jds/      # Sample job descriptions for testing
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

# Run CLI analysis
python main.py --jd data/sample_jds/example.txt

# Run LangChain agent (Phase 5)
python -c "
from pathlib import Path
from src.agent import run_analysis
resume = Path('data/resume.txt').read_text().strip()
jd = Path('data/sample_jds/gravie.txt').read_text().strip()
print(run_analysis(resume, jd))
"

# Run Eval Suite
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

#
# Phase 5 - LANGCHAIN MULTI-TOOL AGENT
## What I built:
- A LangChain agent (`src/agent.py`) with three tools: `analyze_fit`, `identify_gaps`, `generate_recommendations`
- Module-level context pattern so tools take no parameters and the agent can't drop them between calls
- A caching layer (`_get_analysis`) so all three tools share one underlying Anthropic API call
- The agent synthesizes all three tool results into a structured narrative report

## What I learned:
- How agentic systems differ from single-shot LLM calls: the `{agent_scratchpad}` is what makes it agentic — the model reasons, calls a tool, reads the result, reasons again
- The `@tool` decorator + docstring is the API contract between the agent and the tool — the docstring tells Claude when and why to call it
- Debugged a real agentic failure mode: the agent dropped required parameters on subsequent tool calls after treating earlier inputs as "known context." Fix: move shared state to module-level context
- Output normalization matters — agent output can be `str` or `list[dict]` depending on model/version
- What I can now say in an interview:
"I refactored a single-call LLM app into a LangChain multi-tool agent. I hit a real parameter-dropping bug where the agent stopped passing inputs to later tool calls — diagnosed it, understood why it happens in agentic loops, and fixed it with a module-level context pattern. I also built caching so three tools share one API call."