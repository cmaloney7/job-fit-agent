"""
prompts.py — All prompt templates live here.

LEARNING NOTE: Keeping prompts in one place is important for the same reason
keeping test fixtures in one place is important — it makes them easy to iterate,
version, and evaluate. This is your prompt engineering playground.

As you work through the project, experiment with:
- Different system prompt structures
- Few-shot examples (showing Claude examples of good analysis)
- Chain-of-thought prompting (asking Claude to reason step by step)
- Output format specifications (XML, JSON, markdown)
- Persona framing ("You are a senior technical recruiter...")
"""


# ─── System Prompt ────────────────────────────────────────────────────────────
# EXPERIMENT: Try changing the persona, the output format, the reasoning style.
# Run your eval suite (Phase 2) after each change to see if quality improves.

SYSTEM_PROMPT = """You are a senior technical recruiter and career advisor with deep expertise 
in software quality engineering, test automation, and AI/ML roles. You have reviewed 
thousands of QA resumes and understand exactly what hiring managers in this space look for.

Your job is to give an honest, specific, and actionable fit assessment — not a generic one. 
You point out real gaps without sugarcoating them, and you identify genuine differentiators 
that a candidate might undersell.

You always respond in valid JSON matching the schema provided. Do not include any text 
outside the JSON object. Do not use markdown code fences."""


# ─── Analysis Prompt Template ─────────────────────────────────────────────────
# EXPERIMENT: The structure of this prompt heavily influences output quality.
# Try reordering sections, adding examples, or changing how you frame the task.

ANALYSIS_PROMPT_TEMPLATE = """Analyze how well this candidate fits the job description below.

## CANDIDATE RESUME
{resume}

## JOB DESCRIPTION  
{job_description}

## YOUR TASK
Provide a detailed, honest fit assessment. Be specific — reference actual skills, 
tools, and experiences from the resume. Do not make generic statements.

Respond with a JSON object matching this exact schema:

{{
  "job_title": "string — extracted from JD",
  "company_name": "string — extracted from JD or 'Unknown'",
  "fit_level": "one of: Strong Fit | Partial Fit | Stretch / Long Shot | Not a Fit",
  "fit_score": "integer 0-100",
  "headline": "string — one sentence verdict, specific and honest",
  "reasoning": "string — 2-3 sentences of honest overall assessment",
  "strong_matches": [
    "string — specific skill/experience match with evidence from resume"
  ],
  "gaps": [
    {{
      "skill": "string — the missing skill or experience",
      "severity": "one of: blocking | notable | minor",
      "bridge": "string — how to address this gap or frame it honestly"
    }}
  ],
  "differentiators": [
    "string — things that make this candidate stand out for this specific role"
  ],
  "cover_letter_angles": [
    "string — specific angle to lead with in a cover letter"
  ],
  "likely_interview_questions": [
    "string — question the interviewer will likely ask given this resume/JD combo"
  ],
  "things_to_address_proactively": [
    "string — gaps or concerns to get ahead of rather than wait to be asked"
  ]
}}"""


# ─── Interview Prep Prompt (bonus — add this in Phase 1.5) ───────────────────

INTERVIEW_PREP_TEMPLATE = """Given this fit analysis, generate 5 behavioral interview questions 
specific to this role, and for each one, suggest how this candidate should frame their answer 
based on their actual experience.

FIT ANALYSIS SUMMARY:
{fit_summary}

Format as JSON: [{{"question": "...", "suggested_framing": "..."}}]"""
