from google.adk.agents import LlmAgent

from ..callbacks import make_quota_cooldown
from ..prompts import FACEBOOK_POSTER_PROMPT
from ..tools import post_to_facebook

facebook_poster_agent = LlmAgent(
    name="facebook_poster",
    model="gemini-2.5-flash",
    description="Composes and publishes a Facebook Page post linking to the new Blogger article.",
    instruction=FACEBOOK_POSTER_PROMPT,
    tools=[post_to_facebook],
    output_key="facebook_post_url",
    before_agent_callback=make_quota_cooldown("facebook_poster"),
)
