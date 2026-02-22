import httpx
import json
from app.core.config import settings

async def stream_openrouter(model: str, messages: list, max_tokens: int, timeout: int):
    # Google AI Studio API (Gemini)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={settings.GOOGLE_API_KEY}"

    # Convert OpenAI-style messages to Google format
    system_prompt = ""
    google_messages = []

    for msg in messages:
        if msg["role"] == "system":
            system_prompt = msg["content"]
        elif msg["role"] == "user":
            google_messages.append({
                "role": "user",
                "parts": [{"text": msg["content"]}]
            })
        elif msg["role"] == "assistant":
            google_messages.append({
                "role": "model",
                "parts": [{"text": msg["content"]}]
            })

    payload = {
        "contents": google_messages,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
        }
    }

    if system_prompt:
        payload["systemInstruction"] = {
            "parts": [{"text": system_prompt}]
        }

    headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            if response.status_code != 200:
                body = await response.aread()
                raise Exception(f"HTTP {response.status_code} from Google: {body.decode()}")
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                if "text" in part:
                                    yield part["text"]
                    except json.JSONDecodeError:
                        continue
