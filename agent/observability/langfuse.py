import base64
import json
import os
import urllib.request
from typing import Optional

from agent.observability.observer import Observer, Span


class LangfuseObserver(Observer):
    def __init__(self):
        self.host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")
        public_key = os.environ["LANGFUSE_PUBLIC_KEY"]
        secret_key = os.environ["LANGFUSE_SECRET_KEY"]
        token = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
        self.auth = f"Basic {token}"

    def end_span(self, span: Span, error: Optional[str] = None) -> None:
        span.finish(error)
        body = {
            "batch": [
                {
                    "type": "span-create",
                    "body": {
                        "id": f"span-{int(span.start * 1000000)}",
                        "name": span.name,
                        "startTime": span.start,
                        "endTime": span.end,
                        "metadata": span.attrs,
                        "level": "ERROR" if error else "DEFAULT",
                        "statusMessage": error,
                    },
                }
            ]
        }
        req = urllib.request.Request(
            f"{self.host}/api/public/ingestion",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": self.auth, "Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10).read()
