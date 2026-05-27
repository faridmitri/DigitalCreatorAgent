import asyncio
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

logging.getLogger("opentelemetry").setLevel(logging.CRITICAL)

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from trend_agent import root_agent


async def run_pipeline():
    session_service = InMemorySessionService()

    # Pre-initialize all discoverer state keys so prompts never
    # crash on missing keys if a subreddit returns zero posts
    session = await session_service.create_session(
        app_name="trend_agent",
        user_id="cloud_scheduler",
        state={
            "tech_trends_candidates": [],
            "google_news_candidates": [],
            "google_training_candidates": [],
            "google_cert_candidates": [],
        }
    )

    runner = Runner(
        agent=root_agent,
        app_name="trend_agent",
        session_service=session_service,
    )

    trigger = Content(
        role="user",
        parts=[Part(text="Run the full pipeline now.")],
    )

    print("Pipeline starting...")

    final_response = None
    async for event in runner.run_async(
        user_id="cloud_scheduler",
        session_id=session.id,
        new_message=trigger,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                text = event.content.parts[0].text
                if text and text.strip():
                    final_response = text
                    print(f"  ✓ Stage complete: {text[:80]}...")

    if final_response:
        print("\nPipeline complete:", final_response)
        sys.exit(0)
    else:
        print("ERROR: Pipeline produced no final response.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_pipeline())