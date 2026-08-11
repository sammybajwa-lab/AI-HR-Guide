# Evaluation

`eval_set.json` contains 25 synthetic questions/tasks spanning policy Q&A, multi-step workflows, ambiguous inputs, tool-requiring questions, safety behavior, and one out-of-scope request.

Run the reproducible offline pass with:

```bash
RAG_BACKEND=lexical LLM_ENABLED=false python -m evaluation.evaluate --out evaluation/baseline_results.json
```

Run the production configuration after building the Chroma index and setting an LLM key:

```bash
RAG_BACKEND=chroma LLM_ENABLED=true python -m evaluation.evaluate --out evaluation/production_results.json
```

The script reports status accuracy, tool-selection accuracy, a workflow-completion proxy, groundedness/citation proxies, source recall, action-safety pass rate, and p50/p95 latency. These are automated checks, not a substitute for human review. For the final report, review a sample of answers against the gold expectations and record any policy nuance the automated checks miss.

`compare_retrieval.py` is the ablation harness. The repository includes the measured lexical k=3 versus k=5 result. Re-run the same comparison with the production retrieval backend before the final demo if time permits.
