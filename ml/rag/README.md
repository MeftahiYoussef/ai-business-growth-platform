# Future RAG Plan

RAG is not implemented yet. No embeddings, vector indexes, pgvector migrations,
or retrieval endpoints are added in this phase.

Expected future sources:

- business profile
- brand voice
- approved content
- historical reports
- trend observations
- trend predictions
- competitor records
- strategy records
- uploaded business documents

Future retrieval interface:

```python
Retriever.search(
    business_id,
    query,
    top_k,
    filters,
)
```

Tenant isolation rule: every retrieved record must be scoped to `business_id`.

Planned default storage: PostgreSQL with pgvector, unless later architecture
work shows a stronger reason to choose another store.

Future prompt context contract:

```text
SYSTEM
task rules

BUSINESS CONTEXT
retrieved trusted business facts

ANALYTICS CONTEXT
computed deterministic metrics

TREND CONTEXT
computed trend signals/predictions

RETRIEVED DOCUMENTS
top-k RAG chunks with source IDs

USER REQUEST
```

The model must distinguish supplied facts from recommendations, never invent
numeric metrics, cite retrieved source IDs internally where appropriate, and
state when evidence is insufficient.
