"""
Conversation state
Remembers the current image and domain between messages, so follow-up
questions are about the right image.
"""

from .config import logger

_DEFAULTS = {
    "image_path": None,  # Last analyzed image, sent along with follow-up questions
    "domain": None,  # Domain of the last analyzed image (used to focus retrieval)
}

state = dict(_DEFAULTS)


def reset():
    """Forget the current image and domain (updates the dict in place, so every module sees it)"""
    state.clear()
    state.update(_DEFAULTS)
    logger.info("Conversation reset")


def welcome_message() -> str:
    return (
        "Hi! I'm your Visual Perception assistant. Upload a sketch, artwork or interface design "
        "and I'll analyze it, or ask me a question about perception and design."
    )
