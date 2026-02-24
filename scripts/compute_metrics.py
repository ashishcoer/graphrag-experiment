import json, re, time, numpy as np
from scipy import stats
from pathlib import Path
from openai import OpenAI

# ── helpers ──────────────────────────────────────────────────────────────────

def faithfulness(output, context):
    sents = [s.strip() for s in re.split(r'[.!?]+', output) if len(s.strip()) > 10]
    if not sents: return 0.0
    ctx_words = set(context.lower().split())
    supported = sum(1 for s in sents if len(set(s.lower().split()) & ctx_words) / max(len(s.split()),1) > 0.3)
    return supported / len(sents)

def evidence_coverage(output):
    sents = [s.strip() for s in re.split(r'[.!?]+', output) if len(s.strip()) > 10]
    if not sents: return 0.0
    return sum(1 for s in sents if re.search(r'\[E\d+\]', s)) / len(sents)

SECTIONS = ["taxonomy", "routing", "dependenc", "question", "criteria"]
def structural_completeness(output):
    lower = output.lower()
    return sum(1 for s in SECTIONS if s in lower) / len(SECTIONS)

JUDGE_SYSTEM = (
    "You are an expert evaluator of AI-generated work-intake planning outputs. "
    "Score the output on three dimensions (1=poor, 5=excellent):\n"
    "- relevance: does it address the query?\n"
    "- completeness: does it cover taxonomy, routing, and dependencies?\n"
    "- coherence: is it well-structured and clear?\n"
    "Respond with ONLY valid JSON: "
    '{\"relevance\": X, \"completeness\": X, \"coherence\": X, \"overall\": X}'
)

def llm_judge(client, query, output, retries=3):
    prompt = f"Query: {query}\n\nOutput:\n{output[:3000]}"
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM},
                    {"role": "user",   "content": prompt}
                ],
                max_tokens=80, temperature=0.0
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"    Judge error: {e}")
                return {"relevance": 0, "completeness": 0, "coherence": 0, "overall": 0}

# ── load / score each pipeline ───────────────────────────────────────────────

results_dir  = Path("evaluation/automated")
judge_cache  = Path("results/stats/judge_cache.json")
judge_cache.parent.mkdir(parents=True, exist_ok=True)

# Load existing judge scores so we can resume if interrupted
cache = json.load(open(judge_cache)) if judge_cache.exists() else {}

client = OpenAI()
metrics = {}

for fp in sorted(results_dir.glob("results_*.json")):
    name = fp.stem.replace("results_", "")
    data = json.load(open(fp))
    print(f"\nScoring {name} ({len(data)} instances)...")

    faith, cov, struct, lat = [], [], [], []
    judge_rel, judge_comp, judge_coh, judge_overall = [], [], [], []

    for i, r in enumerate(data):
        output  = r.get("output", "")
        context = r.get("context", "")
        query   = r.get("query", "")

        faith.append(faithfulness(output, context))
        cov.append(evidence_coverage(output))
        struct.append(structural_completeness(output))
        lat.append(r.get("latency_seconds", 0))

        # LLM-as-judge with caching
        cache_key = f"{name}_{r['instance_id']}"
        if cache_key not in cache:
            scores = llm_judge(client, query, output)
            cache[cache_key] = scores
            if i % 50 == 0:
                json.dump(cache, open(judge_cache, "w"), indent=2)
                print(f"  {i}/{len(data)} done...")
        else:
            scores = cache[cache_key]

        judge_rel.append(scores.get("relevance", 0))
        judge_comp.append(scores.get("completeness", 0))
        judge_coh.append(scores.get("coherence", 0))
        judge_overall.append(scores.get("overall", 0))

    # Save cache after each pipeline
    json.dump(cache, open(judge_cache, "w"), indent=2)

    metrics[name] = {
        "n": len(data),
        "faith_mean":   float(np.mean(faith)),   "faith_std":   float(np.std(faith)),
        "struct_mean":  float(np.mean(struct)),  "struct_std":  float(np.std(struct)),
        "lat_mean":     float(np.mean(lat)),
        "judge_relevance_mean":    float(np.mean(judge_rel)),
        "judge_completeness_mean": float(np.mean(judge_comp)),
        "judge_coherence_mean":    float(np.mean(judge_coh)),
        "judge_overall_mean":      float(np.mean(judge_overall)),
        "raw_judge": judge_overall,
    }

# ── statistical comparisons ───────────────────────────────────────────────────

graphrag_j = metrics.get("graphrag", {}).get("raw_judge", [])
comps = {}
for bl in ["bm25", "vector_rag", "graph_only"]:
    bj = metrics.get(bl, {}).get("raw_judge", [])
    n = min(len(graphrag_j), len(bj))
    if n < 2: continue
    diff = np.array(graphrag_j[:n]) - np.array(bj[:n])
    _, p_norm = stats.shapiro(diff) if n < 5000 else (0, 0.01)
    if p_norm > 0.05:
        stat, pval = stats.ttest_rel(graphrag_j[:n], bj[:n]); test = "paired t-test"
    else:
        stat, pval = stats.wilcoxon(graphrag_j[:n], bj[:n]); test = "Wilcoxon"
    d = float(np.mean(diff) / np.std(diff)) if np.std(diff) > 0 else 0.0
    comps[bl] = {"test": test, "stat": float(stat), "p": float(pval),
                 "p_corr": float(min(pval * 3, 1)), "d": d}

# ── print results ─────────────────────────────────────────────────────────────

print("\n" + "=" * 80)
print(f"{'Pipeline':<15} {'Judge Overall':>14} {'Struct.':>10} {'Faithfulness':>14} {'Latency':>10} {'N':>6}")
print("-" * 75)
for name in ["bm25", "vector_rag", "graph_only", "graphrag"]:
    m = metrics.get(name, {})
    print(f"{name:<15} "
          f"{m.get('judge_overall_mean',0):.3f}          "
          f"{m.get('struct_mean',0):.3f}    "
          f"{m.get('faith_mean',0):.3f} ({m.get('faith_std',0):.3f})  "
          f"{m.get('lat_mean',0):.1f}s   "
          f"{m.get('n',0):>5}")

print("\nStatistical Comparisons — LLM-as-judge (GraphRAG vs baselines):")
for bl, c in comps.items():
    sig = "***" if c["p_corr"] < 0.001 else "**" if c["p_corr"] < 0.01 else "*" if c["p_corr"] < 0.05 else "ns"
    print(f"  vs {bl}: {c['test']}, p={c['p_corr']:.4f} {sig}, Cohen's d={c['d']:.2f}")

# ── save ──────────────────────────────────────────────────────────────────────

out = Path("results/stats")
out.mkdir(parents=True, exist_ok=True)
json.dump(
    {"per_pipeline": {k: {kk: vv for kk, vv in v.items() if kk != "raw_judge"}
                      for k, v in metrics.items()},
     "comparisons": comps},
    open(out / "all_metrics.json", "w"), indent=2, default=str
)
print("\nSaved to results/stats/all_metrics.json")