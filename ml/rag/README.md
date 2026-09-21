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

## Embedding Model Shortlist

No embedding model is selected or downloaded yet. Future selection should be
based on retrieval tests over approved, non-private fixtures in English, French,
and Russian.

| Candidate | Dimensions | Multilingual notes | License | Local fit | Notes |
| --- | ---: | --- | --- | --- | --- |
| [`intfloat/multilingual-e5-small`](https://huggingface.co/intfloat/multilingual-e5-small) | 384 | Hugging Face lists 94 languages; model card notes broad multilingual training and possible low-resource degradation. | MIT | Strong first local candidate; small enough for local CPU/GPU embedding jobs. | Good default to benchmark first for short business text. |
| [`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2) | 384 | Hugging Face lists 50 languages. | Apache-2.0 | Very small and mature sentence-transformers baseline. | Useful as a conservative baseline, but older and lower capacity. |
| [`BAAI/bge-m3`](https://huggingface.co/BAAI/bge-m3) | 1024 | Multilingual retrieval model with dense/sparse/multi-vector positioning. | MIT | Heavier than the 384-dimensional candidates. | Better candidate for quality-oriented retrieval tests if resource use is acceptable. |

Selection criteria:

- Retrieval quality for short business, marketing, competitor, and report snippets.
- English, French, and Russian behavior.
- License compatibility.
- Embedding dimension and pgvector storage/query cost.
- Local inference latency and memory.
- Ability to split long uploaded documents without losing source attribution.
