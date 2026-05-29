"""BlogWriter — reads `selected_trend` from session state and writes a blog post."""
from google.adk.agents import LlmAgent

from ..prompts import WRITER_PROMPT

from pydantic import BaseModel, Field

class BlogDraft(BaseModel):
    title: str = Field(description="50-65 char SEO title")
    meta_description: str = Field(description="140-160 char meta")
    slug: str = Field(description="lowercase-hyphenated")
    html: str = Field(description="full HTML body")
    image_prompt: str = Field(description="one sentence")
    labels: list[str] = Field(description="3-5 tags")

writer_agent = LlmAgent(
    name="blog_writer",
    model="gemini-2.5-flash",
    instruction=WRITER_PROMPT,
    output_schema=BlogDraft,   # ← framework enforces validity
    output_key="blog_draft",   # ← state["blog_draft"] is now a dict
)