import os
import httpx
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


def request_google_indexing(url: str) -> dict:
    """
    Pings Google Indexing API to request crawl of a newly published URL.
    Called directly from run_agent.py — no LLM agent needed.
    """
    try:
        creds = Credentials(
            token=None,
            refresh_token=os.environ["BLOGGER_REFRESH_TOKEN"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ["BLOGGER_CLIENT_ID"],
            client_secret=os.environ["BLOGGER_CLIENT_SECRET"],
            scopes=["https://www.googleapis.com/auth/indexing"],
        )
        creds.refresh(Request())

        response = httpx.post(
            "https://indexing.googleapis.com/v3/urlNotifications:publish",
            headers={
                "Authorization": f"Bearer {creds.token}",
                "Content-Type": "application/json",
            },
            json={"url": url, "type": "URL_UPDATED"},
            timeout=30,
        )

        if response.status_code == 200:
            meta = response.json().get("urlNotificationMetadata", {})
            return {
                "success": True,
                "url": meta.get("url", url),
                "notify_time": meta.get("latestUpdate", {}).get("notifyTime", ""),
            }

        return {
            "error": f"Indexing API {response.status_code}: {response.text}"
        }

    except Exception as e:
        return {"error": str(e)}