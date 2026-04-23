"""
agent.py — LangChain agent version of the job fit analyzer.

Uses three tools (analyze_fit, identify_gaps, generate_recommendations) backed
by the existing JobFitAnalyzer. Resume and job description are stored in a
module-level context set by run_analysis before the agent executes, so tools
take no parameters and the agent cannot drop them on subsequent calls.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from src.analyzer import JobFitAnalyzer
from src.models import FitAnalysis

load_dotenv()

_analyzer = JobFitAnalyzer()
_cache: dict[tuple[str, str], FitAnalysis] = {}
_ctx: dict[str, str] = {}


def _get_analysis() -> FitAnalysis:
    resume = _ctx["resume"]
    job_description = _ctx["job_description"]
    key = (resume, job_description)
    if key not in _cache:
        _cache[key] = _analyzer.analyze(resume, job_description)
    return _cache[key]


@tool
def analyze_fit() -> dict[str, Any]:
    """Analyze how well the candidate's resume fits the job description.

    Returns the overall fit level (Strong/Partial/Stretch/Not a Fit), a 0-100
    score, a one-sentence headline, strong matching qualifications, candidate
    differentiators, and the reasoning behind the verdict. Call this first.
    """
    a = _get_analysis()
    return {
        "fit_level": a.fit_level.value,
        "fit_score": a.fit_score,
        "headline": a.headline,
        "strong_matches": a.strong_matches,
        "differentiators": a.differentiators,
        "reasoning": a.reasoning,
        "job_title": a.job_title,
        "company_name": a.company_name,
    }


@tool
def identify_gaps() -> dict[str, Any]:
    """Identify skill and experience gaps between the resume and job description.

    Returns each gap with its skill name, severity (blocking / notable / minor),
    and a bridge suggestion for how to address or frame the gap. Also indicates
    whether the role is worth applying to given the gap profile.
    """
    a = _get_analysis()
    return {
        "gaps": [
            {"skill": g.skill, "severity": g.severity, "bridge": g.bridge}
            for g in a.gaps
        ],
        "blocking_gap_skills": [g.skill for g in a.blocking_gaps()],
        "is_worth_applying": a.is_worth_applying(),
    }


@tool
def generate_recommendations() -> dict[str, Any]:
    """Generate actionable application recommendations for the candidate.

    Returns cover letter angles to emphasize, likely interview questions to
    prepare for, and things to address proactively in the application or
    during interviews.
    """
    a = _get_analysis()
    return {
        "cover_letter_angles": a.cover_letter_angles,
        "likely_interview_questions": a.likely_interview_questions,
        "things_to_address_proactively": a.things_to_address_proactively,
    }


_TOOLS = [analyze_fit, identify_gaps, generate_recommendations]

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a senior career advisor and technical recruiter. "
        "When given a resume and job description, use the available tools to "
        "analyze the candidate's fit, surface skill gaps, and produce actionable "
        "recommendations. Be honest, specific, and helpful.",
    ),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])


def build_agent(model: str = "claude-opus-4-6", max_tokens: int = 4000) -> AgentExecutor:
    """Return a configured LangChain AgentExecutor for job fit analysis."""
    llm = ChatAnthropic(
        model=model,
        max_tokens=max_tokens,
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )
    agent = create_tool_calling_agent(llm, _TOOLS, _PROMPT)
    return AgentExecutor(agent=agent, tools=_TOOLS, verbose=True)


def run_analysis(resume: str, job_description: str, model: str = "claude-opus-4-6") -> str:
    """Run a complete job fit analysis and return the agent's synthesized response."""
    _ctx["resume"] = resume
    _ctx["job_description"] = job_description
    executor = build_agent(model=model)
    result = executor.invoke({
        "input": (
            "Please analyze the candidate's fit for the job, identify gaps, "
            "and generate application recommendations."
        )
    })
    return result["output"]
