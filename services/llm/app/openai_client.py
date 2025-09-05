import os
import time
import json
import logging

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from httpx import ReadTimeout, ConnectTimeout, HTTPError

from .settings import settings
from . import metrics

logging.basicConfig(level=logging.INFO, format="%(message)s")


class OpenAIClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = OpenAI(api_key=api_key or settings.openai_api_key)
        self.model = model or settings.openai_model
        self.timeout = settings.request_timeout_seconds

    @retry(
        reraise=True,
        stop=stop_after_attempt(2),
        wait=wait_fixed(0.4),
        retry=retry_if_exception_type((ReadTimeout, ConnectTimeout, HTTPError)),
    )
    def get_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Call OpenAI to get a JSON object and return it as a dict."""
        # start timing for latency metrics
        start = time.perf_counter()

        # Call Chat Completions with a structured JSON response
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            timeout=self.timeout,
        )

        # Parse JSON content from the first choice
        payload: dict = {}
        try:
            content = resp.choices[0].message.content
        except Exception:
            content = None

        if content:
            try:
                payload = json.loads(content)
            except Exception:
                # Fallback: return raw content if it wasn't valid JSON
                payload = {"raw": content}

        # --- metrics hook: tokens, latency, estimated cost ---
        try:
            latency_ms = int((time.perf_counter() - start) * 1000)
            usage = getattr(resp, "usage", None)
            pt = ct = tt = None
            if usage is not None:
                # Handle both Chat Completions (prompt/completion) and Responses API (input/output)
                pt = getattr(usage, "prompt_tokens", None)
                if pt is None:
                    pt = getattr(usage, "input_tokens", None)
                ct = getattr(usage, "completion_tokens", None)
                if ct is None:
                    ct = getattr(usage, "output_tokens", None)
                tt = getattr(usage, "total_tokens", None)

            # Normalize to the configured model for metrics bucketing.
            raw_model = getattr(resp, "model", None)
            model_used = self.model
            req_id = getattr(resp, "id", None)

            # Per-1K prices come from settings (env or models.py defaults)
            ci = getattr(settings, "cost_input_per_1k", 0.0) or 0.0
            co = getattr(settings, "cost_output_per_1k", 0.0) or 0.0
            est_cost = None
            if pt is not None and ct is not None and (ci or co):
                est_cost = round((pt / 1000.0) * ci + (ct / 1000.0) * co, 6)

            metrics.record_usage(model_used, pt, ct, tt, latency_ms, req_id, est_cost)
        except Exception:
            # Never break the request on metrics issues
            pass
        # --- end metrics hook ---

        return payload