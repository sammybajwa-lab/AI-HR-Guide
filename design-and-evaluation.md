# Design and Evaluation

**Prepared by:** Sammy Bajwa

## 1. Design objective

Morrowfen People Desk is a deliberately small agentic HR system built around one principle: employee facts and policy facts should come from controlled sources rather than from model memory.

A request enters the FastAPI application, the agent checks whether the required fields are present, and the agent then uses MCP-exposed tools to retrieve structured employee data, run supported deterministic checks, and retrieve policy evidence. The final response includes policy citations and a concise operational trace.

The system does not claim that hallucinations are impossible. The engineering goal is to reduce unsupported output, expose the evidence used, and fail visibly when information is missing.

## 2. System architecture

```text
Browser
  |
  v
FastAPI /chat
  |
  v
Agent orchestrator
  |
  v
MCP client  --stdio-->  MCP server
                         |-- search_policy_documents --> RAG index
                         |-- get_policy_section -------> RAG index
                         |-- lookup_employee_profile --> employees.json
                         |-- check_pto_balance --------> pto_balances.json
                         |-- lookup_benefits_status ---> benefits.json
                         |-- check_policy_compliance --> supported deterministic rules
                         |-- create_mock_hr_ticket ----> synthetic runtime record
                         `-- draft_hr_email -----------> draft only

Optional LLM synthesis
  |
  v
Citation check / deterministic fallback
```

The normal graded path uses MCP over stdio. A local tool adapter is retained for lightweight offline testing only.

## 3. MCP design

The MCP server exposes eight tools:

| Tool | Role | Source |
|---|---|---|
| `search_policy_documents` | top-k policy retrieval | RAG index |
| `get_policy_section` | named-policy section retrieval | RAG index |
| `lookup_employee_profile` | employee attributes | synthetic JSON |
| `check_pto_balance` | current PTO balance | synthetic JSON |
| `lookup_benefits_status` | benefits status | synthetic JSON |
| `check_policy_compliance` | supported workflow checks | deterministic logic + synthetic data |
| `create_mock_hr_ticket` | preview/write synthetic ticket | runtime JSON; confirmation gated |
| `draft_hr_email` | draft only | synthetic employee data |

The user-facing trace records tool names, arguments, elapsed time, and bounded result summaries. It is an operational trace, not hidden model reasoning.

## 4. Policy corpus and ingestion

The corpus contains 16 controlled files in Markdown, HTML, and TXT. `policy_corpus/corpus_manifest.json` records 9,824 words and a 31-page planning estimate at 325 words per page.

The loader preserves:

- document ID;
- title;
- section heading;
- source file;
- chunk text.

Chunking is heading-aware. Longer sections are divided into approximately 1,500-character windows with 180-character overlap so rules crossing a window boundary are less likely to be lost.

## 5. Retrieval

### Production path

The production configuration uses a persistent Chroma collection. Retrieval returns policy text plus document and section metadata used for citations. The default retrieval depth is controlled by `RAG_TOP_K`.

The final submission should record the actual embedding configuration used by the installed Chroma stack. If the embedding model is changed or made explicit before deployment, update this section and the README so the documentation matches the final code.

### Offline path

`LexicalRAG` is used for fast deterministic tests and the checked-in offline baseline. It is not presented as the production embedding system.

## 6. Grounding and safety controls

The main controls are:

- required-field checks before employee-specific workflows run;
- structured lookup for employee-specific facts;
- deterministic compliance checks for supported scenarios;
- policy retrieval before policy statements are presented;
- citation tokens tied to retrieved document/section metadata;
- deterministic fallback if optional LLM synthesis fails citation checks or errors;
- confirmation-gated mock ticket creation;
- draft-only email behavior;
- escalation of sensitive workplace cases rather than credibility or disciplinary findings.

Two limits are important. First, citation identity does not prove that every sentence is semantically entailed by the cited section. Second, nearest-neighbor retrieval can return a weakly related policy even when the corpus does not contain the answer. For that reason, unsupported-policy behavior and citation support must be included in the final manual review.

## 7. Demo workflow A: international remote work

Prompt:

`E104 wants to work from France for six weeks, Monday-Friday. Can she do it?`

Expected tool sequence:

1. `lookup_employee_profile(E104)`
2. `check_policy_compliance(... destination=France, working_days=30, international=true)`
3. `search_policy_documents(...)`
4. final cited response

The request states a Monday-Friday schedule for six weeks, which is 30 working days. The synthetic policy uses a 20-working-day standard temporary international allowance in a rolling 12-month period. The supported outcome is therefore that the request falls outside the standard temporary arrangement and needs formal review and the required approvals before work begins.

The current deterministic check evaluates the stated request length. It does not maintain a complete history of earlier international work periods. The demo should not imply that a rolling annual balance was calculated from historical travel records.

## 8. Demo workflow B: PTO

Prompt:

`E102 wants to use 24 hours of PTO. Does the balance support it, and what approval is still needed?`

Expected tool sequence:

1. `lookup_employee_profile(E102)`
2. `check_pto_balance(E102)`
3. `check_policy_compliance(... requested_hours=24)`
4. `search_policy_documents(...)`
5. final cited response

The synthetic PTO record contains 56 hours. A 24-hour request would leave 32 hours if approved. The response should distinguish balance sufficiency from approval and notice requirements.

## 9. Failure and ambiguity handling

| Situation | Expected behavior |
|---|---|
| Missing employee ID | ask for the ID |
| Remote-work request gives weeks but no work schedule | ask for working days unless the schedule is explicit |
| PTO request is stated only in days | ask for hours rather than assuming eight hours/day |
| Expense request is missing item or amount | ask for the missing value |
| Employee record is not found | return cannot-determine / clarification behavior |
| MCP is unavailable | surface a tool error rather than a successful HR decision |
| Mock ticket is not confirmed | preview only; no write |
| Sensitive conduct issue | route for human review |
| Corpus does not contain the requested policy | return an evidence limitation; verify manually before submission |

## 10. Evaluation design

`evaluation/eval_set.json` contains 25 cases spanning:

- PTO;
- remote work;
- expenses;
- benefits;
- onboarding;
- workplace conduct;
- general policy retrieval;
- missing-information clarification;
- one out-of-scope request.

The automated evaluator reports status accuracy, required-tool selection, a workflow-completion proxy, groundedness/citation proxies, expected-source hit rate, action-safety pass rate, and latency.

These are engineering proxies. They should not be described as proof of perfect factual or citation quality. In particular, required-tool checks do not fully penalize extra tools, source-hit logic does not necessarily require every expected source in a multi-document case, and citation identity does not prove semantic support.

## 11. Measured offline baseline

The following baseline was generated in the current build environment using:

```bash
RAG_BACKEND=lexical MCP_TRANSPORT=local LLM_ENABLED=false \
python -m evaluation.evaluate --out evaluation/baseline_results.json
```

| Metric | Offline result |
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

These local in-process timings are not deployed latency figures.

## 12. Retrieval comparison

The checked-in lexical comparison reports:

- `k=3`: expected-source hit rate 0.950
- `k=5`: expected-source hit rate 0.950

On this small test set, increasing lexical retrieval depth from 3 to 5 did not improve that proxy. The final submission should repeat the comparison using the production retrieval path if practical and report the measured result rather than assuming the same outcome.

## 13. Production evaluation to insert before submission

Run:

```bash
RAG_BACKEND=chroma MCP_TRANSPORT=stdio LLM_ENABLED=true \
python -m evaluation.evaluate --out evaluation/production_results.json
```

Then replace the table below with the measured final values.

| Metric | Production result |
|---|---:|
| Status accuracy | `TO_BE_MEASURED` |
| Required-tool selection proxy | `TO_BE_MEASURED` |
| Workflow-completion proxy | `TO_BE_MEASURED` |
| Groundedness proxy | `TO_BE_MEASURED` |
| Citation-accuracy proxy | `TO_BE_MEASURED` |
| Expected-source hit rate | `TO_BE_MEASURED` |
| Action-safety pass rate | `TO_BE_MEASURED` |
| p50 latency | `TO_BE_MEASURED` |
| p95 latency | `TO_BE_MEASURED` |

### Manual review sample

Before recording, manually review at least the two demo workflows plus several difficult cases. Record only observations you actually verified.

| Case | Answer supported? | Citation supports claim? | Tool sequence reasonable? | Notes |
|---|---|---|---|---|
| Remote-work demo | `___` | `___` | `___` | `________________` |
| PTO demo | `___` | `___` | `___` | `________________` |
| Unsupported policy question | `___` | `N/A` | `___` | `________________` |
| Sensitive-conduct case | `___` | `___` | `___` | `________________` |
| Mock-ticket safety case | `___` | `___` | `___` | `________________` |

## 14. CI/CD

`.github/workflows/ci.yml` runs on push and pull request. It:

1. installs dependencies;
2. imports the FastAPI app as a start check;
3. runs the test suite, including the MCP test when dependencies are available;
4. runs an evaluation smoke pass;
5. exposes a deploy-gate job only after tests pass.

The final recording should show a successful GitHub Actions run rather than only the workflow file.

## 15. Deployment

The intended deployment is a single service containing the web app, agent, MCP client/server process, retrieval index, and synthetic data. This is sufficient for the assignment and avoids a paid database.

Synthetic ticket writes are demonstration-only and should not be presented as durable HR records on an ephemeral free host.

## 16. Known limits

- The policies and records are fictional.
- The production dependency path must be verified on the final machine/host.
- The current compliance logic supports selected scenarios rather than every HR policy question.
- Remote-work checks do not maintain a complete historical rolling-period ledger.
- Citation identity is not the same as semantic entailment.
- Automated evaluation metrics are proxies and require manual review.
- Final latency depends on hosting cold starts, retrieval initialization, MCP startup, and LLM provider latency.
