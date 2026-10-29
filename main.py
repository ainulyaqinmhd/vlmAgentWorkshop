"""
Visual Perception Agent - start the app
Run:  python main.py   then open http://127.0.0.1:7860
"""

import os
import sys

# Don't send usage statistics to Gradio (must be set before gradio is imported)
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import requests  # noqa: E402

from modules.config import logger, KNOWLEDGE_DIR, OLLAMA_HOST, EMBED_MODEL  # noqa: E402
from modules.ui import create_interface, rag_engine, CSS  # noqa: E402

if __name__ == "__main__":
    logger.info("Starting Visual Perception Agent...")

    # Bring the knowledge base up to date with knowledge/ (new, edited and deleted files)
    try:
        logger.info(rag_engine.ingest_directory(KNOWLEDGE_DIR))
    except requests.exceptions.ConnectionError:
        sys.exit(f"\nCan't reach Ollama at {OLLAMA_HOST}.\n"
                 "Start the Ollama app (or run 'ollama serve' in another terminal), then run python main.py again.")
    except requests.exceptions.HTTPError as e:
        sys.exit(f"\nOllama couldn't create embeddings ({e}).\n"
                 f"Is the embedding model downloaded? Run: ollama pull {EMBED_MODEL}")

    # Set share=True to get a temporary public link (e.g. to demo from another device)
    create_interface().launch(share=False, css=CSS)
