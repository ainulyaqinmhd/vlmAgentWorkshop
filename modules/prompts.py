"""
Prompt loader
Every prompt the agent uses is a Markdown file in the prompts/ folder.

- Files are read fresh on every request, so edits take effect on the next message:
  no need to restart the app.
- Text inside <!-- ... --> is a note for humans and is never sent to the model.
- {{name}} placeholders are filled in by the code (e.g. {{question}}, {{context}}).
  Each prompt file lists the placeholders it supports at the top.
"""

import os
import re

from .config import PROMPTS_DIR, logger

_COMMENT = re.compile(r"<!--.*?-->", flags=re.DOTALL)
_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def load_prompt(name: str, **values) -> str:
    """
    Load prompts/<name>.md and fill in its {{placeholders}}.
    Unknown placeholders are left as they are, so a typo is visible in the log instead of crashing.
    """
    path = os.path.join(PROMPTS_DIR, f"{name}.md")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    text = _COMMENT.sub("", text)

    def fill(match):
        key = match.group(1)
        if key in values:
            return str(values[key])
        logger.warning(f"Prompt '{name}' uses {{{{{key}}}}}, but the code doesn't provide it")
        return match.group(0)

    return _PLACEHOLDER.sub(fill, text).strip()
