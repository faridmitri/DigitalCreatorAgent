"""Reusable ADK agent callbacks for the trend_agent pipeline."""
import asyncio
import logging

from google.adk.agents.callback_context import CallbackContext
from google.genai import types as genai_types

logger = logging.getLogger(__name__)


def make_quota_cooldown(agent_name: str, seconds: int = 10):
    """Return a before_agent_callback that sleeps to spread Vertex AI RPM.

    Returning None from the callback tells ADK to proceed with normal
    agent execution. asyncio.sleep yields to the event loop instead of
    blocking it.
    """
    async def _cooldown(
        callback_context: CallbackContext,
    ) -> genai_types.Content | None:
        logger.info("%s: waiting %ds before LLM call …", agent_name, seconds)
        await asyncio.sleep(seconds)
        return None

    _cooldown.__name__ = f"quota_cooldown_{agent_name}"
    return _cooldown
