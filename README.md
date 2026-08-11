# Morrowfen People Desk

**Project author:** Sammy Bajwa

Morrowfen People Desk is a small HR policy and operations assistant built for the AI Engineering Techniques and Architectures project. Morrowfen Systems, its policies, employee records, leave balances, benefits records, and tickets are all fictional and used only for this assignment.

The application separates two kinds of information. Company-policy answers come from the controlled policy corpus. Employee-specific facts come from synthetic structured records. The agent accesses both through MCP-exposed tools and returns the tool trace and policy citations with the answer.

## What the project includes

- 16 policy and procedure files in Markdown, HTML, and TXT.
- Synthetic employee, PTO, benefits, and ticket data.
- Heading-aware document ingestion and chunking.
- A production Chroma retrieval path and a lightweight lexical test path.
- Eight MCP tools.
- A FastAPI chat interface with `/chat`, `/health`, and reproducible demo scenarios.
- Two multi-step demonstration workflows: international remote work and PTO guidance.
- CI checks, automated tests, a 25-case evaluation set, and a retrieval-depth comparison.
- Documentation covering architecture, evaluation, deployment, AI-tool use, and the recorded demo.

## Architecture

```text
Browser
  |
  v
FastAPI web application
  |
  v
Agent orchestrator
  |
  v
MCP client  --stdio-->  MCP server
                         |-- policy retrieval --> Chroma / policy corpus
                         |-- employee lookup --> synthetic employee data
                         |-- PTO lookup -------> synthetic PTO data
                         |-- benefits lookup --> synthetic benefits data
                         |-- compliance checks
                         |-- mock ticket preview/write
                         `-- draft-only email

Optional LLM synthesis
  |
  v
Citation check / grounded fallback
  |
  v
Final response + citations + tool trace
```

The graded path uses MCP over stdio. The local adapter exists only for lightweight offline tests where the MCP package cannot be started.

## MCP tools

| Tool | Purpose |
|---|---|
| `search_policy_documents` | Retrieve policy evidence from the corpus |
| `get_policy_section` | Retrieve a section from a named policy |
| `lookup_employee_profile` | Read a synthetic employee profile |
| `check_pto_balance` | Read a synthetic PTO balance |
| `lookup_benefits_status` | Read synthetic benefits status |
| `check_policy_compliance` | Apply deterministic checks for supported workflows |
| `create_mock_hr_ticket` | Preview or write a synthetic HR ticket; confirmation required |
| `draft_hr_email` | Create a draft only; no message is sent |

## Local setup

Python 3.12 is recommended.

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Build the production retrieval index:

```bash
RAG_BACKEND=chroma python -m scripts.build_index
```

Start the application:

```bash
RAG_BACKEND=chroma MCP_TRANSPORT=stdio uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Optional LLM synthesis

The application can return deterministic grounded responses without an external LLM. For the final LLM-enabled run, configure an OpenAI-compatible endpoint through environment variables:

```bash
export LLM_ENABLED=true
export OPENAI_API_KEY="..."
export OPENAI_MODEL="..."
# Set OPENAI_BASE_URL only if the provider requires it.
```

The LLM is given retrieved evidence and structured tool results for the current request. It is not given permission to invent missing employee or policy facts. Citation checks provide an additional guard, but they do not make hallucination mathematically impossible. Final answer quality is therefore evaluated as well as tested automatically.

## Demo task 1: international remote work

Prompt:

```text
E104 wants to work from France for six weeks, Monday-Friday. Can she do it?
```

Expected sequence:

1. `lookup_employee_profile`
2. `check_policy_compliance`
3. `search_policy_documents`
4. final cited response

The stated Monday-Friday schedule equals 30 working days. The synthetic international temporary-work rule allows up to 20 working days in a rolling 12-month period before formal review is required. The final answer should therefore say that the request is outside the standard temporary arrangement and identify the required review/approval path from the retrieved policies.

## Demo task 2: PTO balance and approval

Prompt:

```text
E102 wants to use 24 hours of PTO. Does the balance support it, and what approval is still needed?
```

Expected sequence:

1. `lookup_employee_profile`
2. `check_pto_balance`
3. `check_policy_compliance`
4. `search_policy_documents`
5. final cited response

The synthetic record contains a 56-hour balance. A 24-hour request leaves 32 hours if approved. The final answer should distinguish balance sufficiency from manager approval and notice requirements.

## Safety and evidence boundaries

The system is designed to avoid turning missing information into a confident HR decision. Supported workflows check required fields before acting. Ticket creation is confirmation-gated, and email generation is draft-only. Sensitive conduct concerns are routed for human review rather than decided by the assistant.

Unsupported policy questions must be tested manually before submission. A retrieval system can always return the nearest available text even when the corpus does not truly contain an answer. The final deployment should therefore be checked with clearly unsupported questions and should return an evidence limitation rather than a made-up policy.

## Testing

Offline tests:

```bash
RAG_BACKEND=lexical MCP_TRANSPORT=local LLM_ENABLED=false python -m pytest -q
```

In the current build environment, this command produced **10 passing tests**.

The graded MCP path should also be tested after dependencies are installed:

```bash
RAG_BACKEND=lexical MCP_TRANSPORT=stdio LLM_ENABLED=false python -m pytest -q
```

## Evaluation

The evaluation set contains 25 cases covering policy Q&A, multi-document retrieval, PTO, remote work, expenses, benefits, onboarding, sensitive-conduct routing, ambiguity, action safety, and one out-of-scope request.

The checked-in offline baseline uses lexical retrieval, the local tool adapter, and no external LLM. It is a reproducibility baseline only.

| Offline metric | Measured result |
|---|---:|
| Status accuracy | 1.000 |
| Required-tool selection proxy | 1.000 |
| Workflow-completion proxy | 1.000 |
| Groundedness proxy | 1.000 |
| Citation-accuracy proxy | 0.908 |
| Expected-source hit rate | 1.000 |
| Action-safety pass rate | 1.000 |
| p50 latency | 0.19 ms |
| p95 latency | 0.45 ms |

These are automated engineering proxies, not production-quality claims. The final report should use measured Chroma/MCP/LLM/deployed results and a manual answer review.

Run the production evaluation with:

```bash
RAG_BACKEND=chroma MCP_TRANSPORT=stdio LLM_ENABLED=true \
python -m evaluation.evaluate --out evaluation/production_results.json
```

## Deployment

`render.yaml` defines a single Python web service. After deploying, update `deployed.md` with the real application URL, health URL, environment settings actually used, and measured cold/warm behavior.

## Submission preparation

Before recording or submitting, work through:


The repository should be shared with `quantic-grader`, and the final submission should include the GitHub repository link and the recorded presentation link.

## Scope

This is a fictional demonstration system. It is not intended for real employment, legal, tax, immigration, medical, benefits, or security decisions.
