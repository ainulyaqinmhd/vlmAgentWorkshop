"""
Image analysis
Detects an image's domain and builds the prompt the vision model receives:
the domain's analysis or critique prompt + notes retrieved from the knowledge base.
"""

from .config import logger, DOMAINS, DEFAULT_DOMAIN, IMAGE_CONTEXT_CHARS
from .ollama_client import generate
from .prompts import load_prompt


def classify_domain(image_path: str) -> str:
    """Ask the vision model which domain the image belongs to; fall back to DEFAULT_DOMAIN"""
    prompt = load_prompt("classify_domain", domains=", ".join(f'"{name}"' for name in DOMAINS))
    answer = generate(prompt, image_path=image_path).strip().strip('"').strip("'")
    logger.info(f"Domain classifier answered: {answer!r}")

    # Accept answers like "UI/UX Design." or "The domain is Fine Art"
    for name in DOMAINS:
        if name.lower() in answer.lower():
            return name
    logger.info(f"Unclear classification, using default domain '{DEFAULT_DOMAIN}'")
    return DEFAULT_DOMAIN


def retrieval_query(domain: str, critique: bool) -> str:
    """What to search the knowledge base for, for this domain and mode"""
    settings = DOMAINS[domain]
    return settings["critique_query"] if critique else settings["analyze_query"]


def build_image_prompt(domain: str, critique: bool, context: str) -> str:
    """Combine the domain's task prompt with the retrieved notes"""
    settings = DOMAINS[domain]
    mode = "critique" if critique else "analyze"
    task = load_prompt(f"{mode}_{settings['prompt_key']}")

    if not context:
        return task

    # Cap the notes so they don't drown out the image
    return load_prompt(
        "image_with_context",
        task=task,
        theory=settings["theory"],
        context=context[:IMAGE_CONTEXT_CHARS],
    )
