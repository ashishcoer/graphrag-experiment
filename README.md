# GraphRAG for Enterprise Work-Intake Triage

> **Schema-Aware Knowledge Graph Retrieval-Augmented Generation for Automated Work-Intake Classification in Enterprise Software Projects**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

This repository contains the code, data collection scripts, and evaluation pipeline for reproducing the experiments described in our paper submitted to *Information Processing & Management*.

---

## Overview

Enterprise software projects face a persistent bottleneck in work-intake triage — the process of classifying, routing, and prioritizing incoming issues. Current retrieval-augmented generation (RAG) approaches rely on flat vector similarity, losing the structural relationships (ownership chains, component dependencies, cross-team routing paths) that domain experts use for accurate triage decisions.

**GraphRAG** addresses this by combining schema-aware knowledge graph traversal with evidence-bound generation, producing responses where every claim traces to a specific knowledge graph entity.

### Key Results

| Pipeline | Faithfulness | Evidence Coverage | Latency |
|----------|:-----------:|:-----------------:|:-------:|
| BM25 Baseline | 0.67 | 0.12 | 12.1s |
| Vector RAG | 0.72 | 0.15 | 13.9s |
| Graph-Only | 0.78 | 0.41 | 15.2s |
| **GraphRAG (Ours)** | **0.89** | **0.84** | **16.4s** |

*Replace these with your actual experimental results.*

---

## Repository Structure

```
graphrag-experiment/
│
├── config.yaml                  # Experiment configuration
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup
├── LICENSE                      # MIT License
├── README.md                    # This file
│
├── scripts/
│   ├── collect_github_data.py   # Step 1: Data collection from GitHub
│   ├── extract_entities.py      # Step 2: Entity and relation extraction
│   ├── build_knowledge_graph.py # Step 3: Load KG into Neo4j
│   ├── create_benchmark.py      # Step 4: Benchmark creation
│   ├── run_experiment.py        # Step 5: Run all pipelines
│   ├── compute_metrics.py       # Step 6: Statistical analysis
│   └── create_figures.py        # Step 7: Generate publication figures
│
├── pipelines/
│   ├── __init__.py
│   ├── llm_client.py            # Unified LLM API wrapper (OpenAI/Anthropic)
│   ├── bm25/
│   │   ├── __init__.py
│   │   └── bm25_pipeline.py     # BM25 baseline
│   ├── vector_rag/
│   │   ├── __init__.py
│   │   └── vector_pipeline.py   # Vector RAG baseline
│   ├── graph_only/
│   │   ├── __init__.py
│   │   └── graph_only_pipeline.py  # Graph retrieval without evidence binding
│   └── graphrag/
│       ├── __init__.py
│       └── graphrag_pipeline.py # Full GraphRAG pipeline (our method)
│
├── evaluation/
│   ├── automated/               # Pipeline outputs (generated at runtime)
│   └── human/                   # Human evaluation forms
│
└── results/
    ├── stats/                   # Computed metrics and statistical tests
    └── figures/                 # Publication-ready figures
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker Desktop (for Neo4j)
- API keys: GitHub (free), OpenAI ($20 credit), Anthropic (optional, $10 credit)

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

```bash
# Windows PowerShell
$env:GITHUB_TOKEN = "ghp_your_token"
$env:OPENAI_API_KEY = "sk-your_key"
$env:ANTHROPIC_API_KEY = "sk-ant-your_key"  # Optional

# macOS/Linux
export GITHUB_TOKEN="ghp_your_token"
export OPENAI_API_KEY="sk-your_key"
export ANTHROPIC_API_KEY="sk-ant-your_key"  # Optional
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

### 4. Run the Full Pipeline

```bash
# Step 1: Collect data (~4-8 hours, resumes on crash)
python scripts/collect_github_data.py

# Step 2: Extract entities (~10 minutes)
python scripts/extract_entities.py

# Step 3: Build knowledge graph (~30-60 minutes)
python scripts/build_knowledge_graph.py

# Step 4: Create benchmark
python scripts/create_benchmark.py

# Step 5: Run experiment (~4-8 hours, ~$30-50 in API costs)
python scripts/run_experiment.py --pipeline bm25
python scripts/run_experiment.py --pipeline vector_rag
python scripts/run_experiment.py --pipeline graph_only
python scripts/run_experiment.py --pipeline graphrag

# Step 6: Compute metrics
python scripts/compute_metrics.py

# Step 7: Generate figures
python scripts/create_figures.py
```

---

## Configuration

All experiment parameters are in `config.yaml`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `models.provider` | `openai` | LLM provider (`openai` or `anthropic`) |
| `models.openai.generation_model` | `gpt-4o-2024-05-13` | Generation model |
| `retrieval.seed_k` | `10` | Number of seed nodes for graph traversal |
| `retrieval.max_hops` | `3` | Maximum graph traversal depth |
| `retrieval.prune_threshold` | `0.35` | Relevance threshold for subgraph pruning |
| `project.seed` | `42` | Random seed for reproducibility |

---

## Estimated Costs

| Component | Cost |
|-----------|------|
| GitHub data collection | Free |
| Neo4j (Docker) | Free |
| OpenAI API (full experiment) | ~$30–50 |
| Anthropic API (robustness check) | ~$5–10 |
| **Total** | **~$35–60** |

---

## Citation

Paper under review, citation details will be added upon acceptance.

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Data sourced from public GitHub repositories: [Kubernetes](https://github.com/kubernetes/kubernetes), [VS Code](https://github.com/microsoft/vscode), [Home Assistant](https://github.com/home-assistant/core), [Apache Airflow](https://github.com/apache/airflow)
- Built with [Neo4j](https://neo4j.com/), [OpenAI API](https://openai.com/), [Sentence-Transformers](https://www.sbert.net/)
