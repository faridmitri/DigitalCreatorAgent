from google.adk.agents import LlmAgent

from ..callbacks import make_quota_cooldown
from ..prompts import BLOGGER_PUBLISHER_PROMPT
from ..tools import publish_blog_post

blogger_publisher_agent = LlmAgent(
    name="blogger_publisher",
    model="gemini-2.5-flash",
    description="Publishes the finished blog post to Blogger and returns the live post URL.",
    instruction=BLOGGER_PUBLISHER_PROMPT,
    tools=[publish_blog_post],
    output_key="published_url",
    before_agent_callback=make_quota_cooldown("blogger_publisher"),
)
