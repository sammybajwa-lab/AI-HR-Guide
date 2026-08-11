from __future__ import annotations

import math
import re
from dataclasses import asdict
from functools import lru_cache
from typing import Any

from app.settings import settings
from core.policy_loader import PolicyChunk, load_chunks

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


class LexicalRAG:
    """Offline fallback for CI and development; production default is Chroma embeddings."""

    def __init__(self) -> None:
        self.chunks = load_chunks(settings.corpus_dir)
        self.token_sets = [_tokens(c.text) | _tokens(c.title) | _tokens(c.section) for c in self.chunks]

    def search(self, query: str, top_k: int = 4, document_id: str | None = None) -> list[dict[str, Any]]:
        q = _tokens(query)
        scored: list[tuple[float, PolicyChunk]] = []
        for chunk, toks in zip(self.chunks, self.token_sets):
            if document_id and chunk.document_id != document_id:
                continue
            if not q:
                score = 0.0
            else:
                overlap = len(q & toks)
                score = overlap / math.sqrt(max(1, len(q) * len(toks)))
            scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, chunk in scored[:top_k]:
            item = asdict(chunk)
            item["score"] = round(float(score), 4)
            item["snippet"] = chunk.text[:500].strip()
            out.append(item)
        return out

    def get_section(self, document_id: str, section_query: str) -> dict[str, Any] | None:
        candidates = [c for c in self.chunks if c.document_id == document_id]
        if not candidates:
            return None
        q = _tokens(section_query)
        candidates.sort(key=lambda c: len(q & _tokens(c.section)), reverse=True)
        best = candidates[0]
        if q and not (q & _tokens(best.section)):
            return None
        return {**asdict(best), "snippet": best.text[:1200]}


class ChromaRAG:
    def __init__(self) -> None:
        import chromadb

        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        self.collection = self.client.get_or_create_collection(name="morrowfen_policy_chunks")
        self._ensure_index()

    def _ensure_index(self) -> None:
        chunks = load_chunks(settings.corpus_dir)
        existing = self.collection.count()
        if existing == len(chunks) and existing > 0:
            return
        if existing:
            ids = self.collection.get().get("ids", [])
            if ids:
                self.collection.delete(ids=ids)
        batch = 80
        for start in range(0, len(chunks), batch):
            part = chunks[start : start + batch]
            self.collection.add(
                ids=[c.chunk_id for c in part],
                documents=[c.text for c in part],
                metadatas=[
                    {
                        "document_id": c.document_id,
                        "title": c.title,
                        "section": c.section,
                        "source_path": c.source_path,
                    }
                    for c in part
                ],
            )

    def search(self, query: str, top_k: int = 4, document_id: str | None = None) -> list[dict[str, Any]]:
        where = {"document_id": document_id} if document_id else None
        result = self.collection.query(
            query_texts=[query],
            n_results=max(1, top_k),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        ids = (result.get("ids") or [[]])[0]
        out: list[dict[str, Any]] = []
        for cid, doc, meta, dist in zip(ids, docs, metas, dists):
            similarity = (1.0 / (1.0 + float(dist))) if dist is not None else None
            out.append(
                {
                    "chunk_id": cid,
                    "document_id": meta["document_id"],
                    "title": meta["title"],
                    "section": meta["section"],
                    "source_path": meta["source_path"],
                    "text": doc,
                    "snippet": doc[:500].strip(),
                    "score": round(similarity, 4) if similarity is not None else None,
                }
            )
        return out

    def get_section(self, document_id: str, section_query: str) -> dict[str, Any] | None:
        hits = self.search(section_query, top_k=3, document_id=document_id)
        return hits[0] if hits else None


@lru_cache(maxsize=1)
def get_rag():
    if settings.rag_backend == "lexical":
        return LexicalRAG()
    if settings.rag_backend != "chroma":
        raise ValueError("RAG_BACKEND must be 'chroma' or 'lexical'.")
    return ChromaRAG()


def build_index() -> int:
    rag = get_rag()
    if isinstance(rag, ChromaRAG):
        return rag.collection.count()
    return len(rag.chunks)
