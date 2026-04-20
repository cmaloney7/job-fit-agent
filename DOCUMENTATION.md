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
| 3 | Playwright UI + E2E test suite | Playwright hands-on experience |
| 4 | Azure DevOps CI/CD pipeline | Azure DevOps modernization |
| 5 | LangChain multi-tool agent refactor | Agentic framework knowledge |

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

## Phase 3 — Playwright UI *(coming soon)*

### What You'll Build

A simple web frontend for the job fit analyzer: paste a JD, get results.
Write Playwright tests for it.

### Skills Targeted

- Playwright from scratch: page objects, fixtures, locators, assertions
- E2E testing of a real web app you built yourself
- The practical differences between Cypress and Playwright
- Testing async UI behavior and API responses

---

## Phase 4 — Azure DevOps Pipeline *(coming soon)*

### What You'll Build

A CI/CD pipeline in Azure DevOps that runs the eval suite and Playwright
tests on every commit. Includes a quality gate that fails the build if
AI output quality drops below a threshold.

### Skills Targeted

- Azure DevOps YAML pipeline configuration
- Quality gates tied to AI output metrics
- CI/CD from the configuration side (not just consuming pipelines)
- Drift detection in automated CI context

---

## Phase 5 — LangChain Agent *(coming soon)*

### What You'll Build

Refactor the analyzer into a LangChain multi-tool agent with separate tools
for reading the JD, querying the resume, and generating interview prep.

### Skills Targeted

- How agentic systems are architecturally constructed
- Tool calling, memory, and multi-step reasoning
- Why this matters for testing agentic systems
- LangChain/LangGraph hands-on experience

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
│   ├── models.py        # FitAnalysis, FitLevel, SkillGap dataclasses
│   ├── analyzer.py      # Anthropic API client and JSON parsing
│   ├── prompts.py       # System prompt and analysis prompt templates
│   └── __init__.py
├── evals/
│   ├── eval_suite.py    # Phase 2: AI output evaluation framework
│   └── __init__.py
├── tests/
│   └── test_analyzer.py # Unit tests (no API calls)
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

# Add API key (get from console.anthropic.com)
export ANTHROPIC_API_KEY="sk-ant-..."

# Add your resume
# Paste plain text resume into data/resume.txt

# Run your first analysis
python main.py --jd data/sample_jds/gravie.txt

# Run unit tests (instant, no API)
pytest tests/ -v

# Run eval suite (4 API calls, ~3 minutes)
pytest evals/eval_suite.py -v
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `anthropic` | Anthropic API client |
| `rich` | Color-coded terminal output |
| `pytest` | Test framework for both unit tests and evals |
| `python-dotenv` | Optional: load API key from `.env` file 