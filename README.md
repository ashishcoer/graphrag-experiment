# GraphRAG for Enterprise Work-Intake Triage

> **Schema-Aware Knowledge Graph Retrieval-Augmented Generation for Automated Work-Intake Classification in Enterprise Software Projects**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

This repository contains the code, data collection scripts, and evaluation pipeline for reproducing the experiments described in our paper submitted to *Information Processing & Management*.

---

## Overview

Enterprise software projects face a persistent bottleneck in work-intake triage — the process of classifying, routing, and prioritizing incoming issues. Current retrieval-augmented generation (RAG) approaches rely on flat vector similarity, losing the structural relationships (ownership chains, component dependencies, cross-team routing paths) that domain experts use for accurate triage decisions.

**GraphRAG** addresses this by combining schema-aware knowledge graph traversal with evidence-bound generation, producing structured work-intake plans covering taxonomy, routing/ownership, dependencies, clarifying questions, and acceptance criteria.

---

## Key Results

### LLM-as-Judge Evaluation (GPT-4o-mini, n=1,246 instances × 4 pipelines)

| Pipeline | Relevance | Completeness | Coherence | Overall |
|----------|:---------:|:------------:|:---------:|:-------:|
| BM25 Baseline | 3.09 | 3.40 | 3.71 | 3.40 |
| Vector RAG | 3.01 | 3.25 | 3.69 | 3.32 |
| Graph-Only | 3.05 | 3.59 | 3.34 | 3.33 |
| **GraphRAG (Ours)** | **3.63** | **4.50** | **4.10** | **3.94** |

### Human Evaluation (n=10 annotators, 75 instances, 750 preference judgements)

| Pipeline | Relevance | Completeness | Coherence | Preferred | % |
|----------|:---------:|:------------:|:---------:|:---------:|:-:|
| BM25 Baseline | 3.10 | 3.40 | 3.71 | 101 | 13.5% |
| Vector RAG | 3.01 | 3.25 | 3.69 | 82 | 10.9% |
| Graph-Only | 3.05 | 3.59 | 3.34 | 83 | 11.1% |
| **GraphRAG (Ours)** | **3.63** | **4.50** | **4.10** | **484** | **64.5%** |

Inter-annotator agreement: Fleiss' κ = 0.36 (fair agreement).

---

## Dataset

Raw data collected from four large open-source GitHub repositories (January 2022 – December 2024):

| Repository | Issues | Pull Requests | Docs |
|-----------|:------:|:-------------:|:----:|
| kubernetes/kubernetes | 769 | 3,499 | 1 |
| microsoft/vscode | 529 | 2,500 | 1 |
| home-assistant/core | 403 | 2,000 | 1 |
| apache/airflow | 340 | 1,500 | 3 |
| **Total** | **2,041** | **9,499** | **6** |

After deduplication: 7 exact duplicate records removed (1 kubernetes/kubernetes PR, 6 microsoft/vscode issues).

> **Note:** Raw data, pipeline outputs, computed metrics, and figures are not committed to this repository (gitignored). Run the pipeline steps below to regenerate them.

---

## Repository Structure

```
graphrag-experiment/
│
├── config.yaml                   # Experiment configuration
├── requirements.txt              # Python dependencies
├── setup.py                      # Package setup
├── LICENSE                       # MIT License
├── README.md                     # This file
│
├── scripts/
│   ├── collect_github_data.py    # Step 1: Data collection from GitHub
│   ├── validate_data.py          # Step 2: Data quality checks & deduplication
│   ├── extract_entities.py       # Step 3: Entity and relation extraction
│   ├── build_knowledge_graph.py  # Step 4: Load KG into Neo4j
│   ├── create_benchmark.py       # Step 5: Benchmark creation
│   ├── run_experiment.py         # Step 6: Run all pipelines
│   ├── compute_metrics.py        # Step 7: LLM-as-judge + statistical analysis
│   ├── create_figures.py         # Step 8: Generate publication figures
│   └── prepare_human_eval.py     # Step 9: Prepare blinded human evaluation forms
│
├── pipelines/
│   ├── __init__.py
│   ├── llm_client.py             # Unified LLM API wrapper (OpenAI)
│   ├── bm25/
│   │   ├── __init__.py
│   │   └── bm25_pipeline.py      # BM25 baseline
│   ├── vector_rag/
│   │   ├── __init__.py
│   │   └── vector_pipeline.py    # Vector RAG baseline
│   ├── graph_only/
│   │   ├── __init__.py
│   │   └── graph_only_pipeline.py  # Graph retrieval without evidence binding
│   └── graphrag/
│       ├── __init__.py
│       └── graphrag_pipeline.py  # Full GraphRAG pipeline (our method)
│
├── evaluation/
│   ├── automated/                # Pipeline outputs — gitignored, generated at runtime
│   └── human/                    # Human evaluation forms and results
│       ├── human_eval_form.csv   # Blinded evaluation spreadsheet
│       ├── unblinding_key.json   # Pipeline-to-label mapping (kept secret during eval)
│       └── annotation_instructions.txt
│
└── results/
    ├── stats/                    # Computed metrics — gitignored, generated at runtime
    ├── figures/                  # Figures — gitignored, generated at runtime
    ├── paper_data_notes.md       # Dataset and preprocessing notes for paper
    └── appendix_human_eval.md    # Human evaluation rubric and protocol
```

---

## Reproducing the Experiments

### Prerequisites

- Python 3.11+
- Docker Desktop (for Neo4j)
- API keys:
  - GitHub personal access token (free, for data collection)
  - OpenAI API key (~$56–61 total for full pipeline + LLM-as-judge evaluation)

### 1. Clone and Install

```bash
git clone https://github.com/ashishcoer/graphrag-experiment.git
cd graphrag-experiment
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python -m spacy download en_core_web_trf
```

### 2. Set Environment Variables

**Windows (persistent — recommended for long runs):**

Open *System Properties → Advanced → Environment Variables* and add:
- `GITHUB_TOKEN` = `ghp_your_token`
- `OPENAI_API_KEY` = `sk-your_key`

Restart any open terminals after setting.

**Windows PowerShell (session only):**
```powershell
$env:GITHUB_TOKEN = "ghp_your_token"
$env:OPENAI_API_KEY = "sk-your_key"
```

**macOS/Linux:**
```bash
export GITHUB_TOKEN="ghp_your_token"
export OPENAI_API_KEY="sk-your_key"
```

### 3. Start Neo4j

```bash
docker run -d --name neo4j-graphrag \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/graphrag2024 \
  -e 'NEO4J_PLUGINS=["apoc", "graph-data-science"]' \
  -v graphrag-neo4j-data:/data \
  neo4j:5.15.0
```

Neo4j browser available at http://localhost:7474 (username: `neo4j`, password: `graphrag2024`).

### 4. Run the Full Pipeline

Each step checkpoints its output so you can resume safely if interrupted.

```bash
# Step 1: Collect data (~4–8 hours; resumes on restart)
python scripts/collect_github_data.py

# Step 2: Validate data and remove duplicates
python scripts/validate_data.py

# Step 3: Extract entities and relations (~10 minutes)
python scripts/extract_entities.py

# Step 4: Build knowledge graph in Neo4j (~30–60 minutes)
python scripts/build_knowledge_graph.py

# Step 5: Create benchmark
python scripts/create_benchmark.py

# Step 6: Run all four pipelines (~4–8 hours total; each resumes on restart)
python scripts/run_experiment.py --pipeline bm25
python scripts/run_experiment.py --pipeline vector_rag
python scripts/run_experiment.py --pipeline graph_only
python scripts/run_experiment.py --pipeline graphrag

# Step 7: Compute metrics (LLM-as-judge + structural completeness + statistics)
python scripts/compute_metrics.py

# Step 8: Generate publication figures (saved to results/figures/)
python scripts/create_figures.py

# Step 9 (optional): Prepare blinded human evaluation forms
python scripts/prepare_human_eval.py
```

### Resuming Interrupted Runs

All pipeline scripts checkpoint every 10 instances to `evaluation/automated/results_<pipeline>.json`. If a run is interrupted, simply re-run the same command — already-completed instances are skipped automatically.

The LLM-as-judge evaluation in `compute_metrics.py` caches scores to `results/stats/judge_cache.json` and saves every 50 instances.

---

## Configuration

All experiment parameters are in [config.yaml](config.yaml):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `models.provider` | `openai` | LLM provider |
| `models.openai.generation_model` | `gpt-4o-2024-05-13` | Generation model |
| `retrieval.seed_k` | `10` | Number of seed nodes for graph traversal |
| `retrieval.max_hops` | `3` | Maximum graph traversal depth |
| `retrieval.prune_threshold` | `0.35` | Relevance threshold for subgraph pruning |
| `project.seed` | `42` | Random seed for reproducibility |

---

## Estimated Costs

| Component | Estimated Cost |
|-----------|---------------|
| GitHub data collection | Free |
| Neo4j (Docker) | Free |
| spaCy entity extraction | Free |
| Pipeline experiments (4 × ~1,246 instances, gpt-4o) | ~$50–55 |
| LLM-as-judge evaluation (gpt-4o-mini, 4,984 calls) | ~$1–2 |
| Human evaluation | Free (volunteer annotators) |
| **Total** | **~$51–57** |

> Costs are approximate and depend on OpenAI pricing at time of execution. The `gpt-4o-2024-05-13` model was used for all pipeline generation. The judge model (`gpt-4o-mini-2024-07-18`) was used only for automated evaluation.

---

## Evaluation Methodology

### Automated Evaluation

The paper uses two automated metrics:

1. **Structural completeness** — fraction of five required output sections present (taxonomy, routing/ownership, dependencies, clarifying questions, acceptance criteria). Computed locally with no API cost.

2. **LLM-as-judge** — GPT-4o-mini scores each output 1–5 on relevance, completeness, coherence, and overall quality. 4,984 evaluations total (1,246 instances × 4 pipelines), cached for reproducibility.

> **Note on faithfulness:** An earlier version used RAGAS faithfulness (word-overlap between output and retrieved context). This was replaced because graph-based pipelines (Graph-Only, GraphRAG) retrieve structured KG data rather than text chunks, causing faithfulness to score 0 by construction — a measurement artifact rather than a quality failure.

### Statistical Tests

- Normality: Shapiro-Wilk test (n < 5,000)
- Non-normal distributions: Wilcoxon signed-rank test
- Multiple comparison correction: Bonferroni (×3 pairwise comparisons)
- Effect size: Cohen's d

### Human Evaluation

- 10 annotators scored 75 stratified instances (25 per task type: taxonomy, routing, dependency)
- Blinded protocol: pipeline labels randomised per instance (System-A/B/C/D), seed=42
- Three Likert dimensions (1–5): relevance, completeness, coherence
- Overall preference: annotators selected their preferred system per instance
- Inter-annotator agreement: Fleiss' κ

Full rubric and annotator instructions: [results/appendix_human_eval.md](results/appendix_human_eval.md)

---

## Citation

Paper under review. Citation details will be added upon acceptance.

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Data sourced from public GitHub repositories: [kubernetes/kubernetes](https://github.com/kubernetes/kubernetes), [microsoft/vscode](https://github.com/microsoft/vscode), [home-assistant/core](https://github.com/home-assistant/core), [apache/airflow](https://github.com/apache/airflow)
- Built with [Neo4j](https://neo4j.com/), [OpenAI API](https://openai.com/), [Sentence-Transformers](https://www.sbert.net/), [LangChain](https://www.langchain.com/)