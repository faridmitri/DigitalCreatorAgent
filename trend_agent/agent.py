from dotenv import load_dotenv
from google.adk.agents import SequentialAgent

load_dotenv()

from .sub_agents import (
    researcher_agent,
    writer_agent,
    draft_splitter_agent,
    image_creator_agent,
    blogger_publisher_agent,
    facebook_poster_agent,
)

root_agent = SequentialAgent(
    name="trend_to_blog_pipeline",
    description=(
        "Six-stage pipeline: researches one rising trend, writes a blog "
        "post, splits the draft into typed state keys, generates a matching "
        "cover image, publishes to Blogger, then cross-posts to a Facebook Page."
    ),
    sub_agents=[
        researcher_agent,
        writer_agent,
        draft_splitter_agent,
        image_creator_agent,
        blogger_publisher_agent,
        facebook_poster_agent,
    ],
)