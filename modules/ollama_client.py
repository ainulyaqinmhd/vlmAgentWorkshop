"""
Ollama client
Sends prompts (optionally with an image) to the local Ollama server, either waiting
for the full answer or streaming it token by token.
"""

import base64
import json
import re
from io import BytesIO

import requests
from PIL import Image

from .config import (
    logger,
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_VLM_MODEL,
    OLLAMA_THINKING,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_PREDICT,
    TEMPERATURE,
    REQUEST_TIMEOUT,
)

MAX_IMAGE_SIZE = (1024, 1024)  # Larger images are shrunk: saves time and image tokens


def encode_image(image_path: str) -> str:
    """Resize an image if needed and return it as a base64 PNG string"""
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def strip_think_tags(text: str) -> str:
    """Remove inline <think>...</think> blocks, including an unclosed one still streaming"""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()


def _build_payload(prompt, image_path, system, stream, json_mode):
    payload = {
        "model": OLLAMA_VLM_MODEL if image_path else OLLAMA_MODEL,
        "prompt": prompt,
        "stream": stream,
        "think": OLLAMA_THINKING,
        "options": {
            "num_ctx": OLLAMA_NUM_CTX,
            "num_predict": OLLAMA_NUM_PREDICT,
            "temperature": TEMPERATURE,
        },
    }
    if image_path:
        payload["images"] = [encode_image(image_path)]
    if system:
        payload["system"] = system
    if json_mode:
        payload["format"] = "json"
    return payload


def _warn_if_cut_off(done_reason: str):
    if done_reason == "length":
        logger.warning(
            "The model hit its token limit (OLLAMA_NUM_PREDICT=%s), so the answer may be cut off. "
            "Turn thinking off or raise OLLAMA_NUM_PREDICT in config.py.",
            OLLAMA_NUM_PREDICT,
        )


def generate(prompt: str, image_path: str = None, system: str = None, json_mode: bool = False) -> str:
    """Send a prompt and wait for the complete answer"""
    payload = _build_payload(prompt, image_path, system, stream=False, json_mode=json_mode)
    response = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    _warn_if_cut_off(data.get("done_reason", ""))
    return strip_think_tags(data.get("response", ""))


def stream(prompt: str, image_path: str = None, system: str = None):
    """
    Send a prompt and stream the answer.
    Yields (thinking_so_far, answer_so_far) every time new tokens arrive.
    """
    payload = _build_payload(prompt, image_path, system, stream=True, json_mode=False)
    response = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, stream=True, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    thinking = ""
    answer = ""
    for line in response.iter_lines():
        if not line:
            continue
        data = json.loads(line)
        thinking += data.get("thinking", "")
        answer += data.get("response", "")
        if data.get("thinking") or data.get("response"):
            yield thinking, strip_think_tags(answer)
        if data.get("done"):
            _warn_if_cut_off(data.get("done_reason", ""))
            logger.info("Streamed answer: %d chars (thinking: %d chars)", len(answer), len(thinking))
