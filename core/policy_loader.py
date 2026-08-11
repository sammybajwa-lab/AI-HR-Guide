from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class PolicyChunk:
    chunk_id: str
    document_id: str
    title: str
    section: str
    text: str
    source_path: str


def _doc_id_from_text(text: str, fallback: str) -> str:
    match = re.search(r"\b(MF-(?:POL|CAL|REF)-[0-9A-Z]+)\b", text)
    return match.group(1) if match else fallback.upper().replace(" ", "-")


def _split_markdown(path: Path) -> tuple[str, str, list[tuple[str, str]]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("# ")), path.stem)
    doc_id = _doc_id_from_text(text, path.stem)
    sections: list[tuple[str, str]] = []
    heading = "Overview"
    buf: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if buf:
                sections.append((heading, "\n".join(buf).strip()))
            heading = line[3:].strip()
            buf = []
        elif not line.startswith("# "):
            buf.append(line)
    if buf:
        sections.append((heading, "\n".join(buf).strip()))
    return doc_id, title, [(h, t) for h, t in sections if t]


def _split_html(path: Path) -> tuple[str, str, list[tuple[str, str]]]:
    raw = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    title_node = soup.find("h1") or soup.find("title")
    title = title_node.get_text(" ", strip=True) if title_node else path.stem
    doc_id = _doc_id_from_text(soup.get_text(" ", strip=True), path.stem)
    sections: list[tuple[str, str]] = []
    headings = soup.find_all(["h2", "h3"])
    if not headings:
        return doc_id, title, [("Overview", soup.get_text(" ", strip=True))]
    for heading in headings:
        parts: list[str] = []
        for sibling in heading.next_siblings:
            name = getattr(sibling, "name", None)
            if name in {"h2", "h3"}:
                break
            if hasattr(sibling, "get_text"):
                txt = sibling.get_text(" ", strip=True)
            else:
                txt = str(sibling).strip()
            if txt:
                parts.append(txt)
        sections.append((heading.get_text(" ", strip=True), "\n".join(parts)))
    return doc_id, title, [(h, t) for h, t in sections if t]


def _split_txt(path: Path) -> tuple[str, str, list[tuple[str, str]]]:
    text = path.read_text(encoding="utf-8")
    lines = [ln.rstrip() for ln in text.splitlines()]
    title = lines[0].strip() if lines else path.stem
    doc_id = _doc_id_from_text(text, path.stem)
    sections: list[tuple[str, str]] = []
    heading = "Overview"
    buf: list[str] = []
    for line in lines[1:]:
        is_heading = bool(line) and line == line.upper() and len(line.split()) <= 8 and not line.startswith("MF-")
        if is_heading:
            if buf:
                sections.append((heading, "\n".join(buf).strip()))
            heading = line.title()
            buf = []
        else:
            buf.append(line)
    if buf:
        sections.append((heading, "\n".join(buf).strip()))
    return doc_id, title, [(h, t) for h, t in sections if t]


def parse_policy(path: Path) -> tuple[str, str, list[tuple[str, str]]]:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return _split_markdown(path)
    if suffix in {".html", ".htm"}:
        return _split_html(path)
    if suffix == ".txt":
        return _split_txt(path)
    raise ValueError(f"Unsupported policy format: {path.name}")


def _window_text(text: str, max_chars: int = 1500, overlap: int = 180) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) <= max_chars:
        return [text]
    out: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
            if boundary > start + max_chars // 2:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            out.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return out


def load_chunks(corpus_dir: Path) -> list[PolicyChunk]:
    chunks: list[PolicyChunk] = []
    supported = {".md", ".markdown", ".html", ".htm", ".txt"}
    for path in sorted(p for p in corpus_dir.iterdir() if p.is_file() and p.suffix.lower() in supported):
        doc_id, title, sections = parse_policy(path)
        for section, body in sections:
            for idx, piece in enumerate(_window_text(body)):
                digest = hashlib.sha1(f"{doc_id}|{section}|{idx}|{piece}".encode("utf-8")).hexdigest()[:12]
                chunks.append(
                    PolicyChunk(
                        chunk_id=f"{doc_id}-{digest}",
                        document_id=doc_id,
                        title=title,
                        section=section,
                        text=piece,
                        source_path=path.name,
                    )
                )
    return chunks


def iter_supported_files(corpus_dir: Path) -> Iterable[Path]:
    supported = {".md", ".markdown", ".html", ".htm", ".txt"}
    yield from sorted(p for p in corpus_dir.iterdir() if p.is_file() and p.suffix.lower() in supported)
