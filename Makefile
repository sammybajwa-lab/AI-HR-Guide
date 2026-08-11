.PHONY: test run index eval smoke

test:
	RAG_BACKEND=lexical LLM_ENABLED=false python -m pytest -q

index:
	RAG_BACKEND=chroma python -m scripts.build_index

run:
	RAG_BACKEND=chroma MCP_TRANSPORT=stdio uvicorn app.main:app --reload

smoke:
	RAG_BACKEND=lexical MCP_TRANSPORT=stdio LLM_ENABLED=false python -m scripts.smoke_demo

eval:
	RAG_BACKEND=chroma MCP_TRANSPORT=stdio python -m evaluation.evaluate --out evaluation/production_results.json
