"""
Knowledge base (RAG engine)
Loads the files in knowledge/, splits them into chunks, turns each chunk into an
embedding (a list of numbers that captures its meaning) with Ollama, and finds the
chunks closest in meaning to a question.

The index is saved in knowledge_index/ and updated automatically on startup:
new, edited and deleted files in knowledge/ are all picked up.
"""

import json
import os
from typing import List, Optional

import numpy as np
import requests
from pypdf import PdfReader

from .config import logger, INDEX_DIR, EMBED_MODEL, OLLAMA_HOST, KNOWLEDGE_DIR, RAG_TOP_K, REQUEST_TIMEOUT

TEXT_EXTENSIONS = (".md", ".txt")
SUPPORTED_EXTENSIONS = (".pdf",) + TEXT_EXTENSIONS

CHUNK_SIZE = 1500  # Max characters per chunk
MIN_CHUNK_CHARS = 200  # Shorter chunks (stray headers, captions) are dropped
EMBED_BATCH = 32  # Chunks sent to Ollama per request

# nomic-embed-text works best when documents and questions are labelled like this
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "


def embed(texts: List[str], prefix: str) -> np.ndarray:
    """Embed texts with Ollama; returns one normalized row per text"""
    vectors = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = [prefix + t for t in texts[i:i + EMBED_BATCH]]
        response = requests.post(f"{OLLAMA_HOST}/api/embed", json={"model": EMBED_MODEL, "input": batch},
                                 timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        vectors.extend(response.json()["embeddings"])
    matrix = np.array(vectors, dtype=np.float32)
    # Normalize, so a dot product equals cosine similarity
    return matrix / np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-12)


def pack(texts: List[str], size: int = CHUNK_SIZE) -> List[str]:
    """Combine paragraphs into chunks of at most `size` characters"""
    chunks, current = [], ""
    for text in texts:
        for para in (p.strip() for p in text.split("\n\n")):
            if not para:
                continue
            while len(para) > size:  # A single huge paragraph: cut it
                chunks.append(para[:size])
                para = para[size:]
            if current and len(current) + len(para) + 2 > size:
                chunks.append(current)
                current = ""
            current = f"{current}\n\n{para}" if current else para
    if current:
        chunks.append(current)
    return chunks


class RAGEngine:
    def __init__(self, index_dir: str = INDEX_DIR):
        self.index_dir = index_dir
        self.chunks = []  # [{"source": file name, "text": chunk text}]
        self.files = {}  # file name -> signature, to notice edits
        self.vectors = np.zeros((0, 0), dtype=np.float32)
        self._load()

    # -------------------------------------------------------------------------
    # Saving and loading the index
    # -------------------------------------------------------------------------
    def _load(self):
        meta_path = os.path.join(self.index_dir, "chunks.json")
        if not os.path.exists(meta_path):
            return
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("embed_model") != EMBED_MODEL:
                logger.info("Embedding model changed, the knowledge base will be rebuilt")
                return
            self.chunks, self.files = meta["chunks"], meta["files"]
            self.vectors = np.load(os.path.join(self.index_dir, "vectors.npy"))
        except Exception as e:
            logger.warning(f"Could not read the knowledge base index ({e}); it will be rebuilt")
            self.chunks, self.files = [], {}

    def _save(self):
        os.makedirs(self.index_dir, exist_ok=True)
        with open(os.path.join(self.index_dir, "chunks.json"), "w", encoding="utf-8") as f:
            json.dump({"embed_model": EMBED_MODEL, "files": self.files, "chunks": self.chunks}, f, ensure_ascii=False)
        np.save(os.path.join(self.index_dir, "vectors.npy"), self.vectors)

    # -------------------------------------------------------------------------
    # Ingestion
    # -------------------------------------------------------------------------
    def ingest_directory(self, directory_path: str = KNOWLEDGE_DIR) -> str:
        """Bring the index up to date with the .md, .txt and .pdf files in the directory"""
        os.makedirs(directory_path, exist_ok=True)
        current = {}
        for name in sorted(os.listdir(directory_path)):
            if name.lower().endswith(SUPPORTED_EXTENSIONS):
                stat = os.stat(os.path.join(directory_path, name))
                current[name] = f"{stat.st_size}-{int(stat.st_mtime)}"

        changed = [n for n, sig in current.items() if self.files.get(n) != sig]
        removed = [n for n in self.files if n not in current]
        if not changed and not removed:
            return f"Knowledge base up to date ({len(current)} files, {len(self.chunks)} chunks)."

        # Drop old chunks of edited or deleted files
        stale = set(changed) | set(removed)
        keep = [i for i, c in enumerate(self.chunks) if c["source"] not in stale]
        self.chunks = [self.chunks[i] for i in keep]
        self.vectors = self.vectors[keep] if len(keep) else np.zeros((0, 0), dtype=np.float32)
        for name in stale:
            self.files.pop(name, None)

        # Chunk and embed new or edited files
        new_chunks = []
        for name in changed:
            try:
                texts = self._chunk_file(os.path.join(directory_path, name))
                new_chunks.extend({"source": name, "text": t} for t in texts)
                logger.info(f"Read {name}: {len(texts)} chunks")
            except Exception as e:
                logger.error(f"Could not read {name}: {e}")
                continue
            self.files[name] = current[name]

        if new_chunks:
            logger.info(f"Embedding {len(new_chunks)} chunks with {EMBED_MODEL}...")
            new_vectors = embed([c["text"] for c in new_chunks], DOCUMENT_PREFIX)
            self.vectors = np.vstack([self.vectors, new_vectors]) if len(self.chunks) else new_vectors
            self.chunks.extend(new_chunks)

        self._save()
        return (f"Knowledge base updated: {len(changed)} new/edited, {len(removed)} removed file(s). "
                f"Total: {len(self.files)} files, {len(self.chunks)} chunks.")

    def _chunk_file(self, path: str) -> List[str]:
        if path.lower().endswith(TEXT_EXTENSIONS):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            # One section per '## ' heading, so each chunk stays one concept
            sections = text.split("\n## ")
            sections = [sections[0]] + [f"## {s}" for s in sections[1:]]
            chunks = [c for s in sections for c in pack([s])]
        else:
            pages = [page.extract_text() or "" for page in PdfReader(path).pages]
            if sum(len(p.strip()) for p in pages) < 100:
                logger.warning(f"{os.path.basename(path)} has no text layer (scanned PDF?), skipping it")
                return []
            pages = [p for i, p in enumerate(pages) if not self._is_junk_page(p, i, len(pages))]
            chunks = pack(pages)
        return [c for c in chunks if len(c.strip()) >= MIN_CHUNK_CHARS]

    @staticmethod
    def _is_junk_page(text: str, page_idx: int, total_pages: int) -> bool:
        """
        Detect title pages, tables of contents, bibliographies and indexes in PDFs.
        These pages match many searches (author names, topic keywords) but teach nothing.
        """
        text_lower = text.lower().strip()
        word_count = len(text_lower.split())
        digit_ratio = sum(c.isdigit() for c in text) / max(len(text), 1)

        # Skip the first pages (title, copyright) and last 8% (bibliography, index) of books
        if total_pages > 30 and (page_idx < 3 or page_idx >= int(total_pages * 0.92)):
            return True
        if any(kw in text_lower[:150] for kw in ["bibliography", "references", "works cited", "further reading"]):
            return True
        if "contents" in text_lower[:50] and digit_ratio > 0.03:
            return True
        if any(kw in text_lower[:80] for kw in ["subject index", "author index", "name index"]):
            return True
        # Mostly page numbers, or nearly empty
        return (word_count < 80 and digit_ratio > 0.04) or word_count < 30

    # -------------------------------------------------------------------------
    # Retrieval
    # -------------------------------------------------------------------------
    def query(self, query_text: str, knowledge_files: Optional[List[str]] = None, k: int = RAG_TOP_K) -> str:
        """
        Return the k most relevant chunks as one text block, each labelled with its source.
        knowledge_files limits the search to those files in knowledge/ (e.g. one domain's notes).
        """
        if not self.chunks:
            return ""

        scores = self.vectors @ embed([query_text], QUERY_PREFIX)[0]
        candidates = [i for i, c in enumerate(self.chunks) if not knowledge_files or c["source"] in knowledge_files]
        if not candidates:
            # The domain's files aren't in the knowledge base; search everything instead
            candidates = list(range(len(self.chunks)))

        top = sorted(candidates, key=lambda i: scores[i], reverse=True)[:k]
        logger.info(f"Retrieved {len(top)} chunks for: {query_text[:80]}")
        return "\n\n".join(
            f"[Source: {os.path.splitext(self.chunks[i]['source'])[0]}]\n{self.chunks[i]['text']}" for i in top
        )
