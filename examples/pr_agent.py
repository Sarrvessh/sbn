#!/usr/bin/env python3
"""Generate structured PR descriptions from a git diff - every step traced via SBN-ARMS.

Usage:
    git diff HEAD~1 | python examples/pr_agent.py
    python examples/pr_agent.py --diff-file examples/sample.diff
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI

from sbn_sdk.integrations.base import IntegrationTracer

BACKEND_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("SBN_API_KEY", "ingest-local-dev-key")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.getenv("DEFAULT_AGENT_MODEL", "openai/gpt-4o-mini")


class PRAgent:
    """Reads a diff and produces a structured PR description using traced LLM calls."""

    def __init__(self, project_name: str = "pr-agent") -> None:
        if not OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to your .env file or set it as an environment variable."
            )
        self.project_name = project_name
        self.tracer = IntegrationTracer(
            backend_url=BACKEND_URL,
            api_key=API_KEY,
            project_name=project_name,
            model_name=MODEL,
        )
        self._llm = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "SBN-ARMS PR Agent",
            },
        )

    def _call_llm(self, system: str, prompt: str) -> tuple[str, int, int, float]:
        start = time.perf_counter()
        resp = self._llm.responses.create(
            model=MODEL,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_output_tokens=1024,
            temperature=0.3,
        )
        usage = getattr(resp, "usage", None)
        inp = int(getattr(usage, "input_tokens", 0) or 0)
        out = int(getattr(usage, "output_tokens", 0) or 0)
        cost = round((inp / 1_000_000) * 0.15 + (out / 1_000_000) * 0.60, 8)
        text = getattr(resp, "output_text", "") or ""
        return text, inp, out, cost

    def _span_step(self, name: str, span_type: str, input_text: str, fn):
        """Helper: create a span, run fn, attach telemetry, return result."""
        span = self.tracer.create_span(name=name, span_type=span_type, input_text=input_text[:500])
        try:
            result, inp, out, cost = fn()
            if span:
                span._input_tokens = inp
                span._output_tokens = out
                span._total_tokens = inp + out
                span._cost = cost
            return result
        except Exception as exc:
            if span:
                span.end_error(str(exc))
            raise
        finally:
            if span:
                span.end()

    # ── Pipeline steps ───────────────────────────────────────────

    def analyze_diff(self, diff: str) -> str:
        """Classify each changed file (added, removed, modified; language; purpose)."""
        return self._span_step("analyze_diff", "llm", diff[:300], lambda: self._call_llm(
            system="You are a code reviewer. Summarise what each file in this diff does.",
            prompt=f"Analyze this diff and output a one-line summary per file changed:\n\n{diff[:4000]}",
        ))

    def generate_title(self, diff: str, analysis: str) -> str:
        """Generate a conventional-commit title (feat|fix|refactor|chore|docs|test)."""
        return self._span_step("generate_title", "llm", analysis[:200], lambda: self._call_llm(
            system="Output ONLY one line: <type>: <short description>",
            prompt=f"Based on this diff and analysis, write a conventional commit title:\n\nDiff:\n{diff[:2000]}\n\nAnalysis:\n{analysis}",
        ))

    def write_description(self, diff: str, analysis: str, title: str) -> str:
        """Write the full PR body: what changed, why, testing notes."""
        return self._span_step("write_description", "llm", title, lambda: self._call_llm(
            system="Write a PR description in markdown with: ## Summary, ## Changes, ## Why, ## Testing",
            prompt=f"Title: {title}\n\nAnalysis: {analysis}\n\nDiff:\n{diff[:3000]}",
        ))

    def suggest_labels(self, diff: str, title: str) -> str:
        """Suggest GitHub labels and a changelog category."""
        return self._span_step("suggest_labels", "llm", title, lambda: self._call_llm(
            system="Output a comma-separated list of labels and the changelog category on separate lines.",
            prompt=f"Suggest labels for this PR:\nTitle: {title}\n\nDiff:\n{diff[:1500]}",
        ))

    def run(self, diff: str) -> dict[str, str]:
        """Full pipeline: analyse → title → description → labels."""
        span = self.tracer.create_span(name="pr_agent", span_type="chain", input_text=diff[:200])
        try:
            print(f"  [{datetime.now(timezone.utc):%H:%M:%S}] Analyzing changes...")
            analysis = self.analyze_diff(diff)
            print(f"  [{datetime.now(timezone.utc):%H:%M:%S}] Generating title...")
            title = self.generate_title(diff, analysis)
            print(f"  [{datetime.now(timezone.utc):%H:%M:%S}] Writing description...")
            description = self.write_description(diff, analysis, title)
            print(f"  [{datetime.now(timezone.utc):%H:%M:%S}] Suggesting labels...")
            labels = self.suggest_labels(diff, title)
            return {"title": title, "description": description, "labels": labels}
        except Exception as exc:
            if span:
                span.end_error(str(exc))
            raise
        finally:
            if span:
                span.end()


def main() -> None:
    parser = argparse.ArgumentParser(description="PR Description Generator - traced with SBN-ARMS")
    parser.add_argument("--diff-file", help="Read diff from file instead of stdin")
    parser.add_argument("--project", default="pr-agent", help="SBN project name")
    args = parser.parse_args()

    if args.diff_file:
        with open(args.diff_file) as f:
            diff = f.read()
    else:
        diff = sys.stdin.read()

    if not diff.strip():
        print("No diff input. Pipe a git diff or use --diff-file.")
        sys.exit(1)

    agent = PRAgent(project_name=args.project)
    print(f"SBN - ARMS PR Agent")
    print(f"  Backend:  {BACKEND_URL}")
    print(f"  Project:  {args.project}")
    print(f"  Model:    {MODEL}")
    print(f"  Trace ID: {agent.tracer.trace_request_id}")
    print(f"  Diff:     {len(diff)} bytes")
    print()

    result = agent.run(diff)

    print()
    print("=" * 60)
    print("PR DESCRIPTION")
    print("=" * 60)
    print("Title:")
    print(result["title"])
    print()
    print("Description:")
    print(result["description"])
    print()
    print("Labels / Changelog:")
    print(result["labels"])
    print("=" * 60)

    print(f"\nTrace: {BACKEND_URL}/traces/{agent.tracer.trace_request_id}")


if __name__ == "__main__":
    main()
