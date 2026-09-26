"""Gemini image-generation cover-image tool.

Uses the Gemini image model that replaces the retired Imagen 4 endpoints.

Runs against Vertex AI (project + region + ADC) for consistency with
the rest of the pipeline, then uploads the returned bytes to Cloud
Storage explicitly.
"""
import os
import uuid
import datetime
import logging

from google import genai
from google.genai import types
from google.cloud import storage

logger = logging.getLogger(__name__)


def generate_cover_image(prompt: str, aspect_ratio: str = "16:9") -> dict:
    """Generate a blog cover image and save it to Cloud Storage.

    Call this tool exactly ONCE per blog post, with a short visual
    description of the desired cover image. The returned URL is
    immediately embeddable in an HTML <img> tag.

    Args:
        prompt: One sentence describing the desired image. No logos,
            faces, or rendered text. Example: "A minimalist illustration
            of a glowing neural network over a city skyline at dusk,
            vector art style."
        aspect_ratio: One of "1:1", "3:4", "4:3", "16:9", "9:16".
            Default "16:9" for blog headers.

    Returns:
        On success: {"cover_image_url": "<https URL>", "gcs_uri": "<gs:// URI>"}
        On failure: {"error": "<reason>"}
    """
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("VERTEX_IMAGEN_LOCATION", "us-central1")
    bucket_name = os.environ.get("IMAGE_BUCKET")
    if not project or not bucket_name:
        return {"error": "GOOGLE_CLOUD_PROJECT or IMAGE_BUCKET env var not set"}

    # --- 1. Generate the image ---
    try:
        client = genai.Client(vertexai=True, project=project, location=location)
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                ),
            ),
        )
    except Exception as e:
        logger.exception("Imagen API call failed")
        return {"error": f"Imagen API call failed: {e}"}

    image_bytes = next(
        (
            part.inline_data.data
            for candidate in response.candidates or []
            if candidate.content
            for part in candidate.content.parts or []
            if part.inline_data and part.inline_data.data
        ),
        None,
    )
    if not image_bytes:
        return {"error": "Gemini returned no image (likely safety-filtered)"}

    # --- 2. Upload to Cloud Storage explicitly ---
    today = datetime.date.today().isoformat()
    blob_name = f"blog-covers/{today}/{uuid.uuid4().hex}.png"

    try:
        storage_client = storage.Client(project=project)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(image_bytes, content_type="image/png")
    except Exception as e:
        logger.exception("Cloud Storage upload failed")
        return {"error": f"Cloud Storage upload failed: {e}"}

    gcs_uri = f"gs://{bucket_name}/{blob_name}"
    public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"

    return {"cover_image_url": public_url, "gcs_uri": gcs_uri}