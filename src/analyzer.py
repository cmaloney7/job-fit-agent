"""
analyzer.py — Core job fit analysis logic using the Anthropic API.

LEARNING NOTE: This file teaches you:
1. Python class structure and __init__ methods
2. Working with the Anthropic SDK
3. JSON parsing and error handling
4. Type hints and Optional types
5. The difference between ValueError, JSONDecodeError, and API errors

Work through it slowly. If something is confusing, ask Claude Code to explain it.
"""

import json
import os
from pathlib import Path
from typing import Optional

import anthropic

from src.models import FitAnalysis, FitLevel, SkillGap
from src.prompts import SYSTEM_PROMPT, ANALYSIS_PROMPT_TEMPLATE


class JobFitAnalyzer:
    """
    Main analyzer class. Wraps the Anthropic API and handles:
    - Loading resume and JD text
    - Calling Claude with the right prompts
    - Parsing the JSON response into a FitAnalysis object
    - Error handling when things go wrong

    LEARNING NOTE: Python classes use 'self' where JavaScript/TypeScript use 'this'.
    __init__ is the constructor. Everything else is a regular method.
    """

    def __init__(
        self,
        model: str = "claude-opus-4-6",
        max_tokens: int = 4000,
    ):
        """
        LEARNING NOTE: The Anthropic client automatically reads ANTHROPIC_API_KEY
        from your environment. No need to pass it explicitly.
        """
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens

    def load_text(self, path: str) -> str:
        """
        Load text from a file path.

        LEARNING NOTE: pathlib.Path is the modern Python way to handle file paths.
        Path("data/resume.txt").read_text() is cleaner than open()/read()/close().
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return file_path.read_text(encoding="utf-8").strip()

    def analyze(
        self,
        resume: str,
        job_description: str,
    ) -> FitAnalysis:
        """
        Run a fit analysis and return a structured FitAnalysis object.

        This is the core method. It:
        1. Builds the prompt
        2. Calls Claude
        3. Parses the JSON response
        4. Constructs a FitAnalysis dataclass
        5. Handles errors at each step

        LEARNING NOTE: Try adding a print() call to see the raw API response
        before parsing. Understanding what Claude actually returns is key to
        debugging prompt issues.
        """
        # Build the user prompt by filling in the template
        # LEARNING NOTE: .format() substitutes {resume} and {job_description}
        user_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            resume=resume,
            job_description=job_description,
        )

        # Call the Anthropic API
        # LEARNING NOTE: This is a synchronous call. In a production system
        # you'd use async/await. For learning, sync is fine.
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
            )
        except anthropic.APIConnectionError as e:
            raise RuntimeError(f"Could not connect to Anthropic API: {e}")
        except anthropic.AuthenticationError:
            raise RuntimeError(
                "Invalid API key. Set ANTHROPIC_API_KEY environment variable."
            )
        except anthropic.RateLimitError:
            raise RuntimeError("Rate limit hit. Wait a moment and try again.")

        # Extract the text content from the response
        # LEARNING NOTE: response.content is a list of content blocks.
        # For text responses, we want the first block's text.
        raw_text = response.content[0].text

        # Strip markdown code fences if Claude wraps the JSON
        # LEARNING NOTE: This is a real-world AI QE problem — models sometimes
        # ignore output format instructions. Always sanitize before parsing.
        raw_text = raw_text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[-1]   # remove first line (```json)
            raw_text = raw_text.rsplit("```", 1)[0]  # remove trailing ```
            raw_text = raw_text.strip()

        # Parse the JSON response into a dict
        # LEARNING NOTE: This is where prompt engineering matters most.
        # If Claude doesn't return valid JSON, this will fail. Your eval
        # suite (Phase 2) will catch this.
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            # EXPERIMENT: Add debug logging here to see what Claude returned
            # print(f"DEBUG — raw response:\n{raw_text}")
            raise ValueError(f"Claude returned invalid JSON: {e}\n\nRaw response:\n{raw_text[:500]}")

        # Convert the dict into a FitAnalysis dataclass
        return self._parse_response(data)

    def analyze_from_files(
        self,
        resume_path: str,
        jd_path: str,
    ) -> FitAnalysis:
        """Convenience method — load from files and analyze."""
        resume = self.load_text(resume_path)
        job_description = self.load_text(jd_path)
        return self.analyze(resume, job_description)

    def _parse_response(self, data: dict) -> FitAnalysis:
        """
        Convert the raw JSON dict from Claude into a typed FitAnalysis object.

        LEARNING NOTE: This is defensive programming — we validate and convert
        each field rather than blindly trusting Claude's output. This is exactly
        the kind of validation you'd write when testing AI-generated structured data.

        EXPERIMENT: What happens if Claude returns a fit_level that doesn't match
        the enum? The .get() with a default handles that gracefully. Try removing
        the default and see what error you get.
        """
        # Map the string fit level to our enum
        # LEARNING NOTE: dict.get() returns None (or a default) if key is missing
        fit_level_str = data.get("fit_level", "Partial Fit")
        try:
            fit_level = FitLevel(fit_level_str)
        except ValueError:
            # If Claude returns something unexpected, default to Partial Fit
            fit_level = FitLevel.PARTIAL

        # Parse gaps into SkillGap objects
        # LEARNING NOTE: List comprehension — Python's concise way to transform lists.
        # Equivalent to JavaScript's .map()
        gaps = [
            SkillGap(
                skill=g.get("skill", "Unknown"),
                severity=g.get("severity", "notable"),
                bridge=g.get("bridge", ""),
            )
            for g in data.get("gaps", [])
        ]

        return FitAnalysis(
            fit_level=fit_level,
            fit_score=int(data.get("fit_score", 50)),
            headline=data.get("headline", ""),
            strong_matches=data.get("strong_matches", []),
            gaps=gaps,
            differentiators=data.get("differentiators", []),
            cover_letter_angles=data.get("cover_letter_angles", []),
            likely_interview_questions=data.get("likely_interview_questions", []),
            things_to_address_proactively=data.get("things_to_address_proactively", []),
            job_title=data.get("job_title"),
            company_name=data.get("company_name"),
            reasoning=data.get("reasoning"),
        )
