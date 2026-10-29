"""
Configuration module for Visual Perception Agent
All settings live here. Prompts live in the prompts/ folder, not in Python code.
"""

import logging
import os
import sys

# =============================================================================
# Ollama settings
# =============================================================================
# On a slow laptop, use "qwen3.5:2b". With a strong GPU, try "qwen3.5:9b".
# Run "ollama pull <model>" before switching.
OLLAMA_MODEL = "qwen3.5:4b"  # Text chat and research mode
OLLAMA_VLM_MODEL = "qwen3.5:4b"  # Image analysis
OLLAMA_HOST = "http://localhost:11434"

# Embedding model for the knowledge base (RAG)
EMBED_MODEL = "nomic-embed-text"

# Thinking / reasoning
# False = faster, direct answers (recommended on laptops).
# True  = the model reasons first; its reasoning streams live into the "Model Thinking" tab.
OLLAMA_THINKING = False

# Context and output limits.
# num_predict covers BOTH thinking tokens and answer tokens. If you turn thinking on,
# raise it (e.g. 8192) so reasoning doesn't use up the budget and cut off the answer.
OLLAMA_NUM_CTX = 8192
OLLAMA_NUM_PREDICT = 4096
TEMPERATURE = 0.7  # Higher = more varied answers, lower = more focused and repeatable
REQUEST_TIMEOUT = 300  # Seconds; the first request is slow while the model loads

# =============================================================================
# Analysis domains
# =============================================================================
# Each domain has:
#   prompt_key      -> the prompt files prompts/analyze_<key>.md and prompts/critique_<key>.md
#   theory          -> label shown to the model above the retrieved notes
#   knowledge_files -> files in knowledge/ searched for this domain
#   analyze_query / critique_query -> what the knowledge base is searched for
# To add a domain: add an entry here, create its two prompt files, and describe it in
# prompts/classify_domain.md. See prompts/README.md.
DOMAINS = {
    "Urban Sketching": {
        "prompt_key": "urban_sketching",
        "theory": "Gibson's Ecological Approach to Visual Perception",
        "knowledge_files": ["gibson_ecological_perception.md"],
        "analyze_query": "ambient optic array, texture gradients, affordances, invariants, ground plane",
        "critique_query": "depth cues, texture gradients, occlusion, optic flow, ground plane",
    },
    "UI/UX Design": {
        "prompt_key": "ui_ux_design",
        "theory": "Norman's Design Principles and Gestalt Grouping",
        "knowledge_files": ["norman_design.md"],
        "analyze_query": "signifiers, affordances, mapping, visual hierarchy, Gestalt grouping",
        "critique_query": "signifiers, feedback, mapping, discoverability, proximity, similarity",
    },
    "Fine Art": {
        "prompt_key": "fine_art",
        "theory": "Arnheim's Art Psychology and Gestalt Principles",
        "knowledge_files": ["arnheim_gestalt_art.md"],
        "analyze_query": "visual balance, visual weight, structural skeleton, figure and ground",
        "critique_query": "balance, visual weight, directed tension, figure-ground, simplicity",
    },
}
DEFAULT_DOMAIN = "Urban Sketching"  # Used when auto-detection gives an unclear answer

# =============================================================================
# Knowledge base (RAG)
# =============================================================================
RAG_TOP_K = 4  # How many chunks to retrieve per question
IMAGE_CONTEXT_CHARS = 1500  # Max characters of notes added to image prompts (keeps focus on the image)
CHAT_HISTORY_MESSAGES = 6  # How many recent messages are sent along with each chat question


# =============================================================================
# Paths (absolute, so the app works no matter which folder it is started from)
# =============================================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS_DIR = os.path.join(PROJECT_ROOT, "prompts")
KNOWLEDGE_DIR = os.path.join(PROJECT_ROOT, "knowledge")  # Notes and PDFs for RAG (.md, .txt, .pdf)
INDEX_DIR = os.path.join(PROJECT_ROOT, "knowledge_index")  # Search index of knowledge/, updated automatically
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, "uploads")
LOG_FILE = os.path.join(PROJECT_ROOT, "agent.log")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =============================================================================
# Logging
# =============================================================================
def setup_logging():
    """Log to the terminal and to agent.log"""
    # Ensure stdout handles UTF-8 on Windows
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILE, encoding="utf-8", errors="replace"),
        ],
    )
    # Keep the terminal readable: hide per-request logs from HTTP libraries
    for noisy in ("httpx", "urllib3", "arxiv", "primp"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return logging.getLogger("agent")


logger = setup_logging()
