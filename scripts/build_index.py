from __future__ import annotations

from core.rag import build_index

if __name__ == "__main__":
    count = build_index()
    print(f"Indexed {count} policy chunks.")
