# Job Fit Agent — Project Documentation

A practical AI engineering project built to upskill in Python, LLM evaluation,
Playwright, Azure DevOps, and agentic frameworks — while solving a real problem
during a job search.

---

## What This Project Is

An AI-powered job fit analyzer that takes a resume and a job description and
returns a structured assessment: fit level, score, strong matches, gaps with
actionable bridges, cover letter angles, likely interview questions, and
things to address proactively.

Built incrementally across five phases, each phase targeting a specific skill gap
identified in the job market:

| Phase | What You Built | Skill Gap Closed |
|-------|---------------|-----------------|
| 1 | Core Python application + Anthropic API | Python, LLM integration |
| 2 | Eval framework for measuring AI output quality | AI QE evaluation methodology |
| 3 | Flask UI + 16 Playwright E2E tests | Playwright hands-on experience |
| 4 | GitHub Actions CI/CD pipeline + branch protection | CI/CD configuration, feature branch workflow |
| 5 | LangChain multi-tool agent refactor | Agentic framework knowledge, tool calling, context management |

---

## Phase 1 — Core Application

### What You Built

A Python CLI application that calls the Anthropic API and returns structured
job fit analysis. Three files do all the work:

**`src/models.py`** — Defines what a fit analysis looks like as a Python object
before any AI is involved. A `FitAnalysis` dataclass contains:
- `fit_level` — a `FitLevel` enum (Strong Fit, Partial Fit, Stretch, Not a Fit)
- `fit_score` — integer 0–100
- `headline` — one sentence verdict
- `strong_matches` — list of specific evidence from the resume
- `gaps` — list of `SkillGap` objects (skill, severity, bridge advice)
- `differentiators` — things that make the candidate stand out
- `cover_letter_angles` — specific angles to lead with
- `likely_interview_questions` — questions specific to this resume/JD combo
- `things_to_address_proactively` — gaps to get ahead of

**`src/prompts.py`** — All prompt templates live here. The system prompt
establishes Claude as a senior technical recruiter. The analysis prompt
injects the resume and JD and specifies the exact JSON schema Claude must return.
This is the prompt engineering playground — changing prompts here and measuring
output quality change in Phase 2 is the core iteration loop.

**`src/analyzer.py`** — The engine. Calls the Anthropic API, handles errors
(connection errors, auth errors, rate limits), strips markdown code fences
from the response (a real-world AI output sanitization problem), parses the
JSON, and converts it into a typed `FitAnalysis` object with defensive
programming throughout.

**`main.py`** — CLI entry point using `argparse`. Accepts `--jd` (file path)
or `--jd-text` (raw text), `--resume` (defaults to `data/resume.txt`), and
`--json` for raw output. Uses the `rich` library for color-coded terminal output.

### How to Run It

```bash
# Activate virtual environment
source venv/bin/activate

# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run analysis
python main.py --jd data/sample_jds/gravie.txt

# Raw JSON output
python main.py --jd data/sample_jds/gravie.txt --json

# Inline JD text
python main.py --jd-text "Senior QA Engineer, 5+ years Cypress required..."
```

### What You Learned

**Python fundamentals:**
- Dataclasses and the `@dataclass` decorator (Python's equivalent of TypeScript interfaces with auto-generated `__init__`)
- Enums: `class FitLevel(Enum)` — use `.value` to get the string
- Type hints: `list[str]`, `Optional[str]`, `dict`
- `field(default_factory=list)` — why you never use `field(default=[])` (mutable default gotcha)
- `pathlib.Path` for file handling — cleaner than `open()/read()/close()`
- `.format()` for string template substitution
- List comprehensions as Python's equivalent of JavaScript `.map()`

**Anthropic API:**
- `anthropic.Anthropic()` auto-reads `ANTHROPIC_API_KEY` from environment
- `client.messages.create()` with `model`, `max_tokens`, `system`, `messages`
- `response.content[0].text` to extract the response text
- `max_tokens` controls how much Claude can generate — too low causes truncation mid-JSON

**Real-world AI QE problems encountered:**
- Claude returned markdown code fences (` ```json `) despite being told not to — required sanitization before `json.loads()`
- Response truncation when `max_tokens` was too low — fix: increase to 4000
- Non-deterministic outputs requiring defensive JSON parsing with `.get()` defaults

**Unit tests (`tests/test_analyzer.py`):**
- Tests that don't call the API — test the parsing and validation logic only
- `pytest.fixture` with `tmp_path` for temporary test files
- Testing defensive programming: what happens when Claude returns an unknown fit level

### Key Design Decisions

**Why keep prompts in a separate file:** Same reason test fixtures belong in one place — makes them easy to iterate, version, and evaluate. When you change a prompt and re-run the eval suite, you can measure whether quality improved.

**Why use dataclasses instead of plain dicts:** Type safety catches bugs. `analysis.fit_score` is always an int. `analysis.gaps` is always a list of `SkillGap` objects. Without typing, you'd be doing `analysis["gaps"][0]["skill"]` with no guarantee any of those keys exist.

**Why parse defensively:** Claude sometimes returns unexpected values. `.get("fit_level", "Partial Fit")` returns a safe default instead of crashing. This is exactly the kind of validation you'd write when testing AI-generated structured data.

---

## Phase 2 — Eval Framework

### What You Built

A pytest-based evaluation suite (`evals/eval_suite.py`) that measures whether
Claude's job fit analyses are accurate, specific, and well-formed. Runs against
a labeled ground truth dataset of known job fits.

### The Core Problem Phase 2 Solves

You cannot test AI outputs with traditional assertions:
```python
assert result == "expected output"  # WRONG — Claude's output changes every run
```

Instead, you test **properties** — things that should always be true regardless
of exact wording:
- Did Claude assign the right fit level?
- Did it identify the gaps we know exist?
- Is the score in the right range?
- Is the output well-formed with valid fields?

### Ground Truth Dataset

Four labeled cases in the `GROUND_TRUTH` list:

| Case | Expected Fit | Score Range | Notes |
|------|-------------|-------------|-------|
| Gravie | Strong Fit | 75–100 | Daily Claude Code user, framework history |
| E2 Optics | Not a Fit | 0–35 | Physical construction QA, zero overlap |
| Anthropic | Stretch | 15–45 | Claude Code power user, no ML depth |
| Disney | Partial Fit | 55–80 | Strong QE but Python/cloud-native gaps |

Each case also defines:
- `must_mention_skills` — skills Claude should recognize from the resume
- `must_identify_gaps` — gaps Claude should flag
- `should_recommend_applying` — expected apply/skip verdict

### Test Classes

**`TestFitLevelAccuracy`** — Does Claude get the verdict right?
- `test_fit_level_matches_ground_truth` — exact fit level match
- `test_fit_score_in_expected_range` — score within defined bounds

**`TestOutputQuality`** — Is the analysis specific or generic/hallucinated?
- `test_response_is_not_empty` — headline exists and isn't trivially short
- `test_has_reasoning` — Claude explains its verdict
- `test_mentions_expected_skills` — checks full analysis text for key skill mentions
- `test_identifies_key_gaps` — verifies known gaps are surfaced
- `test_not_fit_has_low_score` — NOT_FIT cases should score ≤ 35
- `test_strong_fit_has_multiple_matches` — STRONG cases should have 3+ specific matches

**`TestApplicationRecommendation`** — Does the apply/skip recommendation match?

**`TestStructuralIntegrity`** — Is the output well-formed?
- Score in 0–100 range
- Interview questions generated (except NOT_FIT cases)
- Every gap has bridge advice
- Gap severities are valid values (blocking/notable/minor)

### Session-Scoped Caching

```python
@pytest.fixture(scope="session")
def analyses(analyzer, resume_text):
    # Runs all 4 API calls ONCE, caches results
    # All 52 tests evaluate the cached results — no extra API calls
```

Without this, 52 tests × 1 API call each = 52 API calls, ~10 minutes, significant cost.
With caching: 4 API calls, ~3 minutes, ~$0.10.

### How to Run It

```bash
# Full eval suite (4 API calls, ~3 minutes)
pytest evals/eval_suite.py -v

# Just one case
pytest evals/eval_suite.py -v -k "gravie"

# Just one test class
pytest evals/eval_suite.py -v -k "TestFitLevelAccuracy"

# Unit tests only (no API calls, instant)
pytest tests/ -v
```

### What You Learned

**The most important lesson: every failure was a ground truth problem, not a Claude problem.**

Across 5 rounds of debugging, Claude was consistently more accurate than the
human-defined ground truth:
- Scored the Anthropic role lower (22 vs. our expected 40+) because it correctly
  identified deeper gaps in ML engineering depth
- Found 3 transferable skills in E2 Optics despite clear domain mismatch —
  correctly qualified each one as superficial, still scored it 5/100
- Called Disney a Partial Fit (62) rather than Strong Fit — correctly identified
  Python gap and cloud-native experience gap at Principal level

**The central judgment call in AI evaluation:** when a test fails, is the AI
wrong or is the ground truth wrong? Learning to tell the difference is the
skill that makes a good AI QE engineer.

**Eval design principles learned:**
- Test outcomes, not mechanics (score ≤ 35 is better than match count ≤ 2)
- Keyword matching is brittle — Claude uses synonyms ("system prompt authoring"
  instead of "prompt engineering")
- Different rules apply to different case types (NOT_FIT cases don't need
  interview questions)
- Separate "generate outputs" from "evaluate outputs" — cache aggressively

---

## Phase 3 — Flask UI + Playwright E2E Tests

### What You Built

A Flask web server and a clean HTML/CSS/JS frontend — paste a resume and JD,
click Analyze Fit, see the full analysis rendered in the browser with
color-coded verdict banners, score bars, gap cards, and interview questions.

Then wrote 16 Playwright E2E tests across three layers:
- **Smoke tests** — page loads, elements exist, typing works (no API, instant)
- **Validation tests** — error handling for empty/short inputs, error state resets
- **Analysis flow tests** — full end-to-end through a live API

Key files:
- `web/app.py` — Flask server with routes: GET /, POST /analyze
- `web/templates/index.html` — single-file UI with data-testid attributes for Playwright
- `tests_e2e/pages/analyzer_page.py` — Page Object pattern wrapping all UI interactions
- `tests_e2e/conftest.py` — fixtures that start a live server once for all 16 tests
- `tests_e2e/test_ui.py` — the 16 tests themselves

### What You Learned

- Flask routing and request/response handling
- Playwright locators, assertions, and explicit timeouts
- The Page Object pattern — all UI interactions abstracted into one class
- Session-scoped fixtures that start a live server once for all tests
- Debugging "passes locally, fails in CI" — headed vs headless browser mode
- `data-testid` attributes as a testing contract between UI and test code

### Key Playwright vs Cypress Difference

Playwright timeouts are explicit per-action rather than a global setting.
`wait_for_results(timeout=60000)` is intentional — API calls take time.
In Cypress you'd set a global `defaultCommandTimeout`. In Playwright you
set it where it matters.

---

## Phase 4 — GitHub Actions CI/CD Pipeline

### What You Built

A `.github/workflows/ci.yml` pipeline that runs automatically on every
push to main and every pull request. Three jobs:

1. **Unit Tests** — runs instantly, no API calls, always runs on push/PR
2. **Playwright Smoke Tests** — browser tests, no API calls, gates behind unit tests
3. **AI Eval Suite** — calls Anthropic API, manual trigger only to control costs

Branch protection rules on main require:
- All PRs must pass Unit Tests and Smoke Tests before merging
- Direct pushes to main are blocked — all changes go through feature branches and PRs

### How to Run the Eval Suite via GitHub Actions

1. Go to github.com/cmaloney7/job-fit-agent
2. Click the **Actions** tab
3. Click **Job Fit Agent CI** in the left sidebar
4. Click **Run workflow** → set `run_evals` to `true`
5. Click the green **Run workflow** button

Takes ~3 minutes and costs ~$0.10 in API credits.

### What You Learned

- GitHub Actions YAML pipeline syntax — `on`, `jobs`, `steps`, `needs`, `if`
- How to gate jobs with `needs:` — smoke tests only run if unit tests pass
- How to store secrets with `secrets.ANTHROPIC_API_KEY` — never exposed in logs
- `workflow_dispatch` — manual trigger with input parameters
- Debugging CI environment differences vs local:
  - Missing dependencies (playwright, flask not in requirements.txt)
  - Headed browser failing on headless Linux runner (set headless=True)
- Branch protection rules — requiring status checks before merge
- Feature branch workflow: `git checkout -b feature/name` → PR → CI → merge

### Feature Branch Workflow

```bash
# Never push directly to main
git checkout -b feature/my-change
# make changes
git add .
git commit -m "Description of change"
git push origin feature/my-change
# Open PR on GitHub → CI runs → merge when green
```

---

## Phase 5 — LangChain Multi-Tool Agent

### What You Built

A LangChain agent version of the job fit analyzer (`src/agent.py`) that
replaces the single API call with an autonomous multi-tool workflow.

**Phase 1 flow:**
```
resume + JD → single Claude API call → FitAnalysis object
```

**Phase 5 flow:**
```
resume + JD → Agent reasons → calls tools → synthesizes → narrative report
```

### Architecture

**Three tools the agent can call:**

`analyze_fit()` — Returns fit level, score, headline, strong matches,
differentiators, and reasoning. The agent calls this first.

`identify_gaps()` — Returns each skill gap with severity (blocking/notable/minor)
and bridge advice. Also returns whether the role is worth applying to.

`generate_recommendations()` — Returns cover letter angles, likely interview
questions, and things to address proactively.

**The context pattern — why tools take no parameters:**

The agent controls when and how tools are called. If tools require `resume`
and `job_description` as parameters, the agent sometimes drops them on
subsequent calls (a real LangChain bug). Solution: store inputs in a
module-level context dict before the agent runs. Tools read from context
instead of receiving inputs directly.

```python
_ctx: dict[str, str] = {}

def run_analysis(resume: str, job_description: str) -> str:
    _ctx["resume"] = resume        # set context first
    _ctx["job_description"] = job_description
    executor = build_agent()
    result = executor.invoke(...)  # agent calls tools, tools read from _ctx
    return result["output"]
```

**Caching across tool calls:**

All three tools call `_get_analysis()` which caches the underlying
`FitAnalysis` object. If the agent calls all three tools on the same
inputs, only one Anthropic API call is made. The agent sees three
separate tool results but pays for one.

### How to Run It

```bash
python -c "
from pathlib import Path
from src.agent import run_analysis

resume = Path('data/resume.txt').read_text().strip()
jd = Path('data/sample_jds/gravie.txt').read_text().strip()
output = run_analysis(resume, jd)

if isinstance(output, list):
    output = output[0]['text']
print(output)
"
```

### What You Learned

**LangChain fundamentals:**
- `@tool` decorator — converts a function into a LangChain tool; the docstring
  is sent to Claude so it knows when and why to call the tool
- `ChatPromptTemplate.from_messages()` — system prompt, human input, and
  `{agent_scratchpad}` placeholder where the agent stores reasoning between calls
- `create_tool_calling_agent()` — wires the LLM, tools, and prompt together
- `AgentExecutor` — runs the agent loop; `verbose=True` shows reasoning in real time
- `ChatAnthropic` — LangChain's wrapper for the Anthropic API

**The agent scratchpad:**
The `{agent_scratchpad}` placeholder is how LangChain makes the system agentic.
Between tool calls, the agent writes its intermediate reasoning to the scratchpad.
It thinks, calls a tool, sees the result, thinks again, calls another tool. Without
the scratchpad, it would be a single-shot LLM call, not an agent.

**Real bug encountered — parameter dropping:**
The agent was calling `generate_recommendations` with an empty dict `{}`
because after calling the first two tools it treated the inputs as "known."
The fix was moving inputs to module-level context so tools don't require
parameters at all. This is a real agentic system failure mode worth knowing.

**Output normalization:**
The agent output can be either a string or a list depending on the model
and LangChain version. Always normalize:
```python
if isinstance(output, list):
    output = output[0]['text']
```

### Interview Talking Point

*"I refactored my job fit analyzer from a single LLM call into a LangChain
multi-tool agent. The agent autonomously decides which tools to call —
fit analysis, gap identification, and recommendation generation — and
synthesizes the results into a structured narrative report. I debugged a
real agentic failure where the agent was dropping required parameters on
subsequent tool calls, and solved it by moving shared state to a
module-level context. The output quality improved significantly because the
agent can reason about the combined results of all three tools before
producing its final synthesis."*

---

## Interview Talking Points

### "Tell me about a project that demonstrates your AI QE experience."

> "I built a job fit analyzer using the Anthropic API and Python. The interesting
> part wasn't the application itself — it was building the eval framework. The core
> challenge is that you can't test AI outputs with traditional assertions because
> the output changes every run. So instead of testing exact outputs, I defined
> properties that good outputs must have: correct fit level, score in the right
> range, identification of known gaps, well-formed structure. I built a pytest
> suite with session-scoped caching so all the evaluation tests run against a
> single set of cached API responses. The most important thing I learned:
> every failure was a ground truth problem, not a Claude problem. Claude was
> consistently more accurate than my manual assessments. Knowing when to fix
> the AI vs. fix your expectations is the judgment call at the heart of AI QE."

### "How do you test non-deterministic AI outputs?"

> "You test properties, not exact values. Instead of asserting the output equals
> something specific, you assert things that should always be true: the score
> is between 0 and 100, the fit level is one of the valid enum values, every
> gap has bridge advice, the reasoning isn't suspiciously short. For semantic
> content — like 'did Claude identify the right gaps' — you check whether
> expected keywords appear anywhere in the full analysis text, not in a specific
> field. And you build a labeled ground truth dataset of known correct answers
> to compare against."

### "What's the hardest part of building AI evaluation frameworks?"

> "Building good ground truth. The eval framework is only as good as the humans
> who defined what 'correct' looks like. In my project I went through five rounds
> of test failures and every single one was a ground truth problem. Claude scored
> the Anthropic Prompt Engineer role a 22 when I expected 40+. My first instinct
> was 'Claude is wrong.' But reading its reasoning — 'using AI tools as a power
> user is categorically different from owning system prompts for a frontier model'
> — I realized Claude was more accurate than I was. I updated the ground truth.
> That experience of questioning your own expectations rather than immediately
> blaming the AI is what makes a good AI QE engineer."

### "Walk me through a prompt engineering challenge you've worked on."

> "When I built the analyzer, Claude kept returning JSON wrapped in markdown code
> fences even though the prompt explicitly said not to. The response started with
> triple backticks, which caused json.loads() to fail. I had to add sanitization
> before parsing — strip the opening fence line and the closing backticks. That's
> a real-world example of why AI output validation is a discipline: models
> sometimes ignore formatting instructions, and your parsing layer has to be
> defensive. The more interesting challenge was that my prompts were generating
> responses that got truncated mid-JSON when max_tokens was too low. The fix was
> simple — increase to 4000 — but diagnosing it required understanding how token
> limits interact with response length and content complexity."

---

## Project Structure

```
job_fit_agent/
├── src/
│   ├── agent.py         # Phase 5: LangChain multi-tool agent
│   ├── analyzer.py      # Anthropic API client and JSON parsing
│   ├── models.py        # FitAnalysis, FitLevel, SkillGap dataclasses
│   ├── prompts.py       # System prompt and analysis prompt templates
│   └── __init__.py
├── evals/
│   ├── eval_suite.py    # Phase 2: AI output evaluation framework
│   └── __init__.py
├── tests/
│   └── test_analyzer.py # Unit tests (no API calls)
├── tests_e2e/
│   ├── conftest.py      # Playwright fixtures and server setup
│   ├── test_ui.py       # E2E tests (smoke, validation, analysis flow)
│   └── pages/
│       └── analyzer_page.py  # Page Object for the web UI
├── web/
│   ├── app.py           # Flask web server
│   └── templates/
│       └── index.html   # Web UI (HTML/CSS/JS)
├── data/
│   ├── resume.txt       # Your resume in plain text
│   └── sample_jds/      # Job description text files
│       ├── gravie.txt
│       ├── e2optics.txt
│       ├── anthropic.txt
│       └── disneysdet.txt
├── main.py              # CLI entry point
├── requirements.txt
└── README.md
```

---

## Setup

```bash
# Clone / unzip project
cd job_fit_agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser (one-time setup)
python -m playwright install chromium

# Set up your .env file (see section below — do this before running anything)

# Add your resume
# Paste plain text resume into data/resume.txt

# Run your first analysis
python main.py --jd data/sample_jds/gravie.txt

# Unit tests (instant, no API)
pytest tests/ -v

# Eval suite (4 API calls, ~3 minutes)
pytest evals/eval_suite.py -v
```

---

## API Key Setup — .env File

Instead of running `export ANTHROPIC_API_KEY=...` every time you open
a new Terminal window, store your key in a `.env` file and let the
app load it automatically on startup.

**Step 1 — Create the `.env` file in the project root:**
```bash
cd ~/Projects/job-fit-agent-phase-1/job_fit_agent
touch .env
```

Open `.env` in any text editor and add:
```
ANTHROPIC_API_KEY=sk-ant-...
```
No quotes, no spaces around the `=`. Replace `sk-ant-...` with your
actual key from console.anthropic.com.

**Step 2 — Add `.env` to `.gitignore`** so your API key is never committed:
```bash
echo ".env" >> .gitignore
```

**Step 3 — Verify `python-dotenv` is installed:**
```bash
pip install python-dotenv
```

**How it works:** Both `web/app.py` and `main.py` call `load_dotenv()`
on startup, which reads your `.env` file and loads the key into the
environment automatically. You never need to `export` it manually again.

**After this, your startup sequence is simply:**
```bash
source venv/bin/activate
python web/app.py
```

> **Security note:** Never commit your `.env` file to Git. The `.gitignore`
> entry above prevents this. If you ever accidentally expose your API key,
> rotate it immediately at console.anthropic.com.

---

## Starting the Web Application (Phase 3)

Every time you want to use the web UI, follow these steps in order.

**Step 1 — Open Terminal and navigate to the project:**
```bash
cd ~/Projects/job-fit-agent-phase-1/job_fit_agent
```

**Step 2 — Activate the virtual environment:**
```bash
source venv/bin/activate
```
You'll see `(venv)` appear at the start of your prompt. This is required
every time you open a new Terminal window — without it, Python commands
won't find the installed packages.

**Step 3 — Set your Anthropic API key:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```
This is also required every new Terminal session unless you've added it
to your `~/.zshrc` file permanently.

**Step 4 — Start the Flask server:**
```bash
python web/app.py
```
You'll see output like:
```
* Running on http://127.0.0.1:5000
* Debug mode: on
```

**Step 5 — Open the app in your browser:**
```
http://localhost:5000
```

Paste your resume text in the left panel, paste a job description in the
right panel, and click **Analyze Fit**.

---

**To stop the server:** Press `Ctrl+C` in the Terminal window where it's running.

**If you see "Address already in use":** A previous server is still running.
Find and stop it:
```bash
lsof -i :5000
kill -9 <PID>   # replace <PID> with the number from the output above
```

---

## Running the Playwright E2E Tests (Phase 3)

The E2E tests require the Flask server to be running. The test suite
starts its own server automatically on port 5001 — you don't need to
start the server manually for tests.

```bash
# Make sure venv is activated and API key is set, then:

# Smoke tests only — no API calls, fast (~15 seconds)
pytest tests_e2e/ -v -k "smoke"

# Validation tests — tests error handling, no API calls
pytest tests_e2e/ -v -k "validation"

# Full E2E suite — includes API calls (~5-6 minutes)
pytest tests_e2e/ -v

# Watch tests run in a visible browser window
# Open conftest.py and change headless=True to headless=False, then:
pytest tests_e2e/ -v -k "smoke"
```

**Common gotcha:** If `test_error_clears_on_new_valid_submission` fails,
it's almost always because the API key isn't set in the current terminal
session. Set it and re-run.

---

## Quick Reference — All Commands

```bash
# Activate environment (run every new Terminal session)
source venv/bin/activate

# Set API key (run every new Terminal session)
export ANTHROPIC_API_KEY="sk-ant-..."

# API key healthcheck
python -m src.health

# Start web UI
python web/app.py
# Then open: http://localhost:5000

# CLI analysis
python main.py --jd data/sample_jds/gravie.txt

# LangChain agent (Phase 5)
python -c "
from pathlib import Path
from src.agent import run_analysis
resume = Path('data/resume.txt').read_text().strip()
jd = Path('data/sample_jds/gravie.txt').read_text().strip()
print(run_analysis(resume, jd))
"

# Unit tests (instant)
pytest tests/ -v

# Eval suite (~3 minutes, costs ~$0.10)
pytest evals/eval_suite.py -v

# E2E smoke tests (fast, no API)
pytest tests_e2e/ -v -k "smoke"

# Full E2E suite (~6 minutes)
pytest tests_e2e/ -v
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `anthropic` | Anthropic API client |
| `flask` | Web server for the Phase 3 UI |
| `playwright` | Browser automation for E2E tests |
| `rich` | Color-coded terminal output |
| `pytest` | Test framework for unit tests, evals, and E2E |
| `python-dotenv` | Load API key from `.env` file |
| `langchain` | Agent framework for Phase 5 multi-tool agent |
| `langchain-anthropic` | LangChain wrapper for the Anthropic API |
