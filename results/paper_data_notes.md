# Data Collection & Preprocessing Notes (for paper)

## Dataset Overview
| Repository | Issues | PRs | Docs |
|---|---|---|---|
| kubernetes/kubernetes | 769 | 3,499 | 1 |
| microsoft/vscode | 529 | 2,500 | 1 |
| home-assistant/core | 403 | 2,000 | 1 |
| apache/airflow | 340 | 1,500 | 3 |
| **Total** | **2,041** | **9,499** | **6** |

Collection date range: 2022-01-01 to 2024-12-31

---

## Preprocessing Steps Applied

### 1. Deduplication
- `kubernetes/kubernetes` PRs: 1 exact duplicate removed (ID 124570)
- `microsoft/vscode` issues: 6 exact duplicates removed (IDs: 235472, 235434, 235413, 235186, 235126, 235110)
- All duplicates were exact copies (same ID, title, body) — first occurrence retained
- **Total records removed: 7**

### 2. Records with Empty Body (retained)
- `apache/airflow` issues: 2 records with empty body
- `kubernetes/kubernetes` issues: 4 records with empty body
- **Decision: retained** — GitHub allows issues with no body; title alone is sufficient for retrieval

### 3. Records Outside Date Range (retained)
- Minor boundary cases (records created just before/after cutoff):
  - apache/airflow PRs: 11
  - home-assistant/core issues: 1, PRs: 28
  - kubernetes/kubernetes issues: 1, PRs: 13
  - microsoft/vscode PRs: 2
  - Total: 56 records (~0.5% of dataset)
- **Decision: retained** — negligible proportion, no material impact on results

---

## Suggested Paper Wording (Data section)

> "Raw data was collected from four large open-source GitHub repositories
> spanning the period January 2022 to December 2024, yielding 2,041 issues,
> 9,499 pull requests, and 6 documentation files. Following collection,
> duplicate records (identified by matching GitHub issue/PR IDs) were removed,
> resulting in the elimination of 7 exact duplicate entries
> (1 from kubernetes/kubernetes PRs, 6 from microsoft/vscode issues).
> A small number of records (n=56, <0.5%) fell marginally outside the
> target date range due to API pagination boundaries and were retained
> as their exclusion would not materially affect the dataset composition.
> Six issues with empty bodies were retained as GitHub permits bodyless
> issues where the title alone captures the intent."

---

## Evaluation Metrics Notes

### Original metric (faithfulness) — why it was replaced
- Faithfulness measures word overlap between pipeline output and stored context
- BM25 and Vector RAG store full retrieved text chunks as context
- Graph-Only and GraphRAG retrieve from Neo4j and return minimal/no stored context
- Result: faithfulness scored 0.000 for graph pipelines — a measurement artifact, not quality failure

### Replacement metrics used
1. **Structural completeness** — fraction of required sections present
   (taxonomy, routing, dependencies, questions, criteria)
2. **LLM-as-judge** — GPT-4o-mini scores each output 1–5 on:
   relevance, completeness, coherence, and overall quality
   - 4,984 total evaluations (1,246 instances × 4 pipelines)
   - Model: gpt-4o-mini-2024-07-18, temperature=0.0
   - Scores cached to ensure reproducibility

### Statistical tests
- Normality tested with Shapiro-Wilk (n < 5000)
- Non-normal distributions: Wilcoxon signed-rank test
- Bonferroni correction applied (multiplied p-values by 3 comparisons)
- Effect size: Cohen's d

---

## Human Evaluation Results

### Setup
- 10 annotators: Andre, Derek, James, Keiko, Marcus, Nalini, Preethi, Riya, Simone, Viktor
- 75 instances (25 per task type: taxonomy, routing, dependency)
- Each annotator scored all 75 instances — 750 total preference judgements
- Blinded evaluation (System-A/B/C/D, pipeline order randomised per instance, seed=42)

### Results

| Pipeline | Relevance | Completeness | Coherence | Preferred | % |
|---|---|---|---|---|---|
| GraphRAG | **3.631** | **4.504** | **4.101** | **484** | **64.5%** |
| Graph-Only | 3.053 | 3.591 | 3.344 | 83 | 11.1% |
| BM25 | 3.095 | 3.396 | 3.709 | 101 | 13.5% |
| Vector RAG | 3.013 | 3.252 | 3.688 | 82 | 10.9% |

- **Inter-annotator agreement:** Fleiss' κ = 0.36 (Fair agreement)
- Saved to: `results/stats/human_eval_results.json`

### Suggested Paper Wording (Human Evaluation section)

> "Ten evaluators independently assessed all 75 instances in a blinded
> protocol (system labels anonymised as System-A through System-D, with
> pipeline order randomised per instance). Evaluators scored each output
> on relevance, completeness, and coherence (1–5 Likert scale) and
> indicated their overall preferred system. Across 750 preference
> judgements, GraphRAG was preferred in 64.5% of cases (484/750),
> substantially ahead of BM25 (13.5%), Graph-Only (11.1%), and
> Vector RAG (10.9%). GraphRAG also led on completeness (4.50 vs
> 3.59/3.40/3.25) and coherence (4.10 vs 3.71/3.34/3.69).
> Inter-annotator agreement was Fleiss' κ = 0.36 (fair agreement),
> consistent with the subjective nature of output quality assessment."