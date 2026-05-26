"""Researcher: 2-stage sub-pipeline.

Stage 1 (ParallelAgent): four discoverers concurrently fetch rising posts
        from Reddit, each targeting their assigned subreddit.
Stage 2 (LlmAgent): finalizer dedups against blog history, picks the
        highest-score survivor, emits selected_trend.
"""

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent

from ..prompts import (
    TECH_TRENDS_DISCOVERER_PROMPT,
    GOOGLE_NEWS_DISCOVERER_PROMPT,
    GOOGLE_TRAINING_DISCOVERER_PROMPT,
    GOOGLE_CERT_DISCOVERER_PROMPT,
    TREND_FINALIZER_PROMPT,
)
from ..tools import (
    fetch_rising_posts,
    get_recent_blog_topics,
)

_DISCOVERER_MODEL = "gemini-2.5-flash-lite"
_FINALIZER_MODEL = "gemini-2.5-flash"


tech_trends_discoverer = LlmAgent(
    name="tech_trends_discoverer",
    model=_DISCOVERER_MODEL,
    description="Finds rising posts from r/artificial.",
    instruction=TECH_TRENDS_DISCOVERER_PROMPT,
    tools=[fetch_rising_posts],
    output_key="tech_trends_candidates",
)

google_news_discoverer = LlmAgent(
    name="google_news_discoverer",
    model=_DISCOVERER_MODEL,
    description="Finds rising posts from r/singularity.",
    instruction=GOOGLE_NEWS_DISCOVERER_PROMPT,
    tools=[fetch_rising_posts],
    output_key="google_news_candidates",
)

google_training_discoverer = LlmAgent(
    name="google_training_discoverer",
    model=_DISCOVERER_MODEL,
    description="Finds rising posts from r/learnmachinelearning.",
    instruction=GOOGLE_TRAINING_DISCOVERER_PROMPT,
    tools=[fetch_rising_posts],
    output_key="google_training_candidates",
)

google_cert_discoverer = LlmAgent(
    name="google_cert_discoverer",
    model=_DISCOVERER_MODEL,
    description="Finds rising posts from r/googlecloud.",
    instruction=GOOGLE_CERT_DISCOVERER_PROMPT,
    tools=[fetch_rising_posts],
    output_key="google_cert_candidates",
)


parallel_discovery = ParallelAgent(
    name="parallel_discovery",
    description="Runs four Reddit discoverers concurrently.",
    sub_agents=[
        tech_trends_discoverer,
        google_news_discoverer,
        google_training_discoverer,
        google_cert_discoverer,
    ],
)


trend_finalizer = LlmAgent(
    name="trend_finalizer",
    model=_FINALIZER_MODEL,
    description="Selects the best candidate trend from Reddit rising posts.",
    instruction=TREND_FINALIZER_PROMPT,
    tools=[get_recent_blog_topics],
    output_key="selected_trend",
)


# FIX 1: renamed from `researcher` to `researcher_agent` to match
# sub_agents/__init__.py which imports `researcher_agent`.
# FIX 2: all imports above are now relative (..prompts, ..tools)
# to be consistent with every other sub-agent in this package.
researcher_agent = SequentialAgent(
    name="researcher",
    description="Two-stage research pipeline: parallel Reddit discovery then finalization.",
    sub_agents=[parallel_discovery, trend_finalizer],
)