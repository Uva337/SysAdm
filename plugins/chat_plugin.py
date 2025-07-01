import os
from typing import List, Dict

import openai


def send_chat_completion(messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo") -> str:
    """Send chat messages to OpenAI and return the assistant reply."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")
    openai.api_key = api_key
    response = openai.ChatCompletion.create(model=model, messages=messages)
    return response.choices[0].message["content"].strip()
