"""
Visual Perception Agent - start the app
Run:  python main.py   then open http://127.0.0.1:7860
"""

from modules.config import logger, KNOWLEDGE_DIR
from modules.ui import create_interface, rag_engine, CSS

if __name__ == "__main__":
    logger.info("Starting Visual Perception Agent...")

    # Add any new files in knowledge/ to the knowledge base (only new files are processed)
    logger.info(rag_engine.ingest_directory(KNOWLEDGE_DIR))

    # Set share=True to get a temporary public link (e.g. to demo from another device)
    create_interface().launch(share=False, css=CSS)
