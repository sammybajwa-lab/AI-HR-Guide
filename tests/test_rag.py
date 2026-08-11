from core.rag import LexicalRAG


def test_retrieval_finds_pto_policy():
    rag = LexicalRAG()
    hits = rag.search("three consecutive PTO days manager approval notice", top_k=5)
    assert any(hit["document_id"] == "MF-POL-101" for hit in hits)


def test_retrieval_finds_remote_policy():
    rag = LexicalRAG()
    hits = rag.search("international remote work 20 working days tax security approval", top_k=5)
    ids = {h["document_id"] for h in hits}
    assert "MF-POL-201" in ids or "MF-POL-202" in ids
