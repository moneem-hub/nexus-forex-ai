"""LLM clients. GroqLLM talks to Groq's OpenAI-compatible chat API with tool calling. FakeLLM is for tests."""
import os
import time

import requests


class LLMError(RuntimeError):
    pass


class GroqLLM:
    URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        if not self.api_key:
            raise LLMError("GROQ_API_KEY is not set (put it in .env)")

    def chat(self, messages: list, tools: list) -> dict:
        body = {"model": self.model, "messages": messages, "tools": tools, "tool_choice": "auto", "temperature": 0.2}
        last = ""
        for attempt in range(3):
            try:
                r = requests.post(self.URL, json=body, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=40)
            except requests.RequestException as e:
                last = str(e).replace(self.api_key, "***")
            else:
                if r.ok:
                    return r.json()["choices"][0]["message"]
                last = f"HTTP {r.status_code}: {r.text[:300]}"
                if r.status_code not in (429, 500, 502, 503):
                    break
            time.sleep(2 * (attempt + 1))
        raise LLMError(last)


class FakeLLM:
    """Scripted stand-in: `script(messages) -> assistant message dict`. Used to test the loop without any API."""

    def __init__(self, script):
        self.script, self.calls = script, 0

    def chat(self, messages, tools):
        self.calls += 1
        out = self.script(messages)
        if isinstance(out, Exception):
            raise out
        return out
