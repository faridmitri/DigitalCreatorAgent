"""Parses the writer's JSON output into individual session-state keys.

No LLM, no tools, no tokens — pure Python state manipulation. Sits
between writer_agent and image_creator_agent so downstream prompts can
inject only the fields they need (image_prompt sentence, title, etc.)
instead of the entire blog_draft blob with the full HTML body.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

logger = logging.getLogger(__name__)


class DraftSplitter(BaseAgent):
    """Reads `blog_draft` from state, parses its JSON, and writes each
    field to its own state key.
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        raw = ctx.session.state.get("blog_draft", "")
        parsed = self._extract_json(raw)

        if parsed is None:
            logger.error(
                "draft_splitter: could not extract JSON from blog_draft "
                "(first 200 chars: %r)",
                (raw[:200] if isinstance(raw, str) else raw),
            )
            parsed = {}

        # Normalize labels to a list of strings — defensive in case the
        # writer emits null or a string instead of a list.
        labels = parsed.get("labels", [])
        if not isinstance(labels, list):
            labels = []

        state_delta = {
            "blog_draft_title":            parsed.get("title", ""),
            "blog_draft_meta_description": parsed.get("meta_description", ""),
            "blog_draft_slug":             parsed.get("slug", ""),
            "blog_draft_html":             parsed.get("html", ""),
            "blog_draft_image_prompt":     parsed.get("image_prompt", ""),
            "blog_draft_labels":           labels,
        }

        logger.info(
            "draft_splitter: split blog_draft → title=%r, image_prompt=%r, "
            "html_len=%d, labels=%d",
            state_delta["blog_draft_title"][:60],
            state_delta["blog_draft_image_prompt"][:60],
            len(state_delta["blog_draft_html"]),
            len(state_delta["blog_draft_labels"]),
        )

        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(state_delta=state_delta),
        )

    @staticmethod
    def _extract_json(text):
        """Best-effort JSON extraction.

        Writer is instructed to output strict JSON on the LAST line, with a
        prose summary above it. Handles:
          - already-parsed dict (defensive)
          - pure JSON string
          - summary text + JSON on last line
          - JSON wrapped in ```json fences (in case the LLM disobeys)
        """
        if not text:
            return None
        if isinstance(text, dict):
            return text
        if not isinstance(text, str):
            return None

        text = text.strip()

        # Strip code fences if the LLM disobeyed and added them.
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]  # drop opening ```json
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]  # drop closing ```
            text = "\n".join(lines).strip()

        # Try a direct parse first — cleanest case.
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try the substring from the LAST opening brace to end. Works for
        # "Summary paragraph...\n{...}" — the most common writer output.
        last_open = text.rfind("{")
        if last_open != -1:
            try:
                return json.loads(text[last_open:])
            except json.JSONDecodeError:
                pass

        # Last resort: scan lines from the bottom.
        for line in reversed(text.split("\n")):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

        return None


draft_splitter_agent = DraftSplitter(
    name="draft_splitter",
    description=(
        "Parses the writer's JSON output into individual state keys "
        "(title, meta_description, slug, html, image_prompt, labels)."
    ),
)