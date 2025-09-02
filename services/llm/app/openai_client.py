import json
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from httpx import ReadTimeout, ConnectTimeout, HTTPError
from .settings import settings

class OpenAIClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = OpenAI(api_key=api_key or settings.openai_api_key)
        self.model = model or settings.openai_model
        self.timeout = settings.request_timeout_seconds

    @retry(
        reraise=True,
        stop=stop_after_attempt(2),
        wait=wait_fixed(0.4),
        retry=retry_if_exception_type((ReadTimeout, ConnectTimeout, HTTPError))
    )
    def get_json(self, system_prompt: str, user_prompt: str) -> dict:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            timeout=self.timeout
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)
