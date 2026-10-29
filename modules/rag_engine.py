"""
Knowledge base (RAG engine)
Loads the files in knowledge/, splits them into chunks, embeds them with Ollama,
stores them in ChromaDB, and retrieves the chunks most relevant to a question.
"""

import os
import shutil
from typing import List, Optional

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import logger, CHROMA_DIR, EMBED_MODEL, OLLAMA_HOST, KNOWLEDGE_DIR, RAG_TOP_K

TEXT_EXTENSIONS = (".md", ".txt")
SUPPORTED_EXTENSIONS = (".pdf",) + TEXT_EXTENSIONS

CHUNK_SIZE = 1500  # Characters per chunk
CHUNK_OVERLAP = 300  # Characters shared between neighbouring chunks
MIN_CHUNK_CHARS = 200  # Shorter chunks (stray headers, captions) are dropped
FETCH_K = 25  # Candidates fetched before removing duplicates and keeping the top k


class RAGEngine:
    def __init__(self, persist_directory: str = CHROMA_DIR):
        self.persist_directory = persist_directory
        # Embeddings run inside Ollama, so no PyTorch or model download is needed here
        self.embedding_function = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_HOST)
        self.vector_store = None
        if os.path.exists(persist_directory):
            self.vector_store = Chroma(persist_directory=persist_directory, embedding_function=self.embedding_function)
            logger.info(f"Loaded existing knowledge base from {persist_directory}")

    # -------------------------------------------------------------------------
    # Ingestion
    # -------------------------------------------------------------------------
    def get_ingested_sources(self) -> set:
        """File paths already in the vector database"""
        if not self.vector_store:
            return set()
        metadatas = self.vector_store._collection.get(include=["metadatas"]).get("metadatas", [])
        return {meta["source"] for meta in metadatas if meta and "source" in meta}

    def ingest_directory(self, directory_path: str = KNOWLEDGE_DIR) -> str:
        """Add every new .md, .txt and .pdf file in the directory to the knowledge base"""
        if not os.path.exists(directory_path):
            return f"Directory not found: {directory_path}"

        files = [
            os.path.join(directory_path, f)
            for f in sorted(os.listdir(directory_path))
            if f.lower().endswith(SUPPORTED_EXTENSIONS)
        ]
        new_files = [f for f in files if f not in self.get_ingested_sources()]
        if not new_files:
            return f"Knowledge base up to date ({len(files)} files)."

        documents = []
        for path in new_files:
            try:
                documents.extend(self._load_file(path))
            except Exception as e:
                logger.error(f"Could not load {path}: {e}")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            # Split notes on '## ' headings first, so each chunk stays one concept
            separators=["\n## ", "\n\n", "\n", ". ", "? ", "! ", " "],
        )
        chunks = [c for c in splitter.split_documents(documents) if len(c.page_content.strip()) >= MIN_CHUNK_CHARS]
        if not chunks:
            return "No usable text found in the new files."

        if self.vector_store is None:
            self.vector_store = Chroma.from_documents(
                documents=chunks, embedding=self.embedding_function, persist_directory=self.persist_directory
            )
        else:
            self.vector_store.add_documents(chunks)
        return f"Added {len(new_files)} file(s) to the knowledge base as {len(chunks)} chunks."

    def _load_file(self, path: str) -> List[Document]:
        if path.lower().endswith(TEXT_EXTENSIONS):
            with open(path, "r", encoding="utf-8") as f:
                return [Document(page_content=f.read(), metadata={"source": path})]

        pages = PyPDFLoader(path).load()
        if sum(len(p.page_content.strip()) for p in pages) < 100:
            logger.warning(f"{os.path.basename(path)} has no text layer (scanned PDF?), skipping it")
            return []
        return self._filter_junk_pages(pages)

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

    def _filter_junk_pages(self, pages: List[Document]) -> List[Document]:
        total = len(pages)
        kept = [p for p in pages if not self._is_junk_page(p.page_content, p.metadata.get("page", 0), total)]
        if len(kept) < total:
            source = os.path.basename(pages[0].metadata.get("source", "unknown"))
            logger.info(f"Junk-page filter: removed {total - len(kept)}/{total} pages from {source}")
        return kept

    # -------------------------------------------------------------------------
    # Retrieval
    # -------------------------------------------------------------------------
    def query(self, query_text: str, knowledge_files: Optional[List[str]] = None, k: int = RAG_TOP_K) -> str:
        """
        Return the k most relevant chunks as one text block, each labelled with its source.
        knowledge_files limits the search to those files in knowledge/ (e.g. one domain's notes).
        """
        if not self.vector_store:
            return ""

        source_filter = None
        if knowledge_files:
            paths = [os.path.join(KNOWLEDGE_DIR, f) for f in knowledge_files if os.path.exists(os.path.join(KNOWLEDGE_DIR, f))]
            if len(paths) == 1:
                source_filter = {"source": paths[0]}
            elif paths:
                source_filter = {"$or": [{"source": p} for p in paths]}

        docs = self.vector_store.similarity_search(query_text, k=FETCH_K, filter=source_filter)
        if not docs and source_filter:
            # The domain's files had nothing relevant; search everything instead
            docs = self.vector_store.similarity_search(query_text, k=FETCH_K)

        # Drop duplicate chunks, keep the best k
        unique, seen = [], set()
        for doc in docs:
            text = doc.page_content.strip()
            if text not in seen:
                seen.add(text)
                unique.append(doc)
        top = unique[:k]

        logger.info(f"Retrieved {len(top)} chunks for: {query_text[:80]}")
        return "\n\n".join(
            f"[Source: {os.path.splitext(os.path.basename(d.metadata.get('source', 'Unknown')))[0]}]\n{d.page_content}"
            for d in top
        )

    def clear(self):
        """Delete the whole knowledge base; it is rebuilt from knowledge/ on the next start"""
        if self.vector_store:
            self.vector_store.delete_collection()
            self.vector_store = None
        shutil.rmtree(self.persist_directory, ignore_errors=True)
