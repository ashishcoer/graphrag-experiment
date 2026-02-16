import json, re, numpy as np
from scipy import stats
from pathlib import Path
 
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
 
results_dir = Path("evaluation/automated")
metrics = {}
for fp in sorted(results_dir.glob("results_*.json")):
    name = fp.stem.replace("results_","")
    data = json.load(open(fp))
    faith = [faithfulness(r["output"], r.get("context","")) for r in data]
    cov = [evidence_coverage(r["output"]) for r in data]
    lat = [r.get("latency_seconds",0) for r in data]
    metrics[name] = {"faith_mean":np.mean(faith),"faith_std":np.std(faith),
        "cov_mean":np.mean(cov),"cov_std":np.std(cov),
        "lat_mean":np.mean(lat),"n":len(data),"raw_faith":faith}
 
graphrag_f = metrics.get("graphrag",{}).get("raw_faith",[])
comps = {}
for bl in ["bm25","vector_rag","graph_only"]:
    bf = metrics.get(bl,{}).get("raw_faith",[])
    n = min(len(graphrag_f), len(bf))
    if n < 2: continue
    diff = np.array(graphrag_f[:n]) - np.array(bf[:n])
    _, p_norm = stats.shapiro(diff) if n < 5000 else (0, 0.01)
    if p_norm > 0.05:
        stat, pval = stats.ttest_rel(graphrag_f[:n], bf[:n]); test = "paired t-test"
    else:
        stat, pval = stats.wilcoxon(graphrag_f[:n], bf[:n]); test = "Wilcoxon"
    d = np.mean(diff)/np.std(diff) if np.std(diff)>0 else 0
    comps[bl] = {"test":test,"stat":float(stat),"p":float(pval),"p_corr":float(min(pval*3,1)),"d":float(d)}
 
print("\n" + "="*70)
print(f"{'Pipeline':<15} {'Faithfulness':>14} {'Evid.Cov.':>12} {'Latency':>10} {'N':>6}")
print("-"*60)
for name in ["bm25","vector_rag","graph_only","graphrag"]:
    m = metrics.get(name,{})
    print(f"{name:<15} {m.get('faith_mean',0):.3f} ({m.get('faith_std',0):.3f})  {m.get('cov_mean',0):.3f}         {m.get('lat_mean',0):.1f}s   {m.get('n',0):>5}")
print("\nStatistical Comparisons (GraphRAG vs baselines):")
for bl, c in comps.items():
    sig = "***" if c["p_corr"]<0.001 else "**" if c["p_corr"]<0.01 else "*" if c["p_corr"]<0.05 else "ns"
    print(f"  vs {bl}: {c['test']}, p={c['p_corr']:.4f} {sig}, Cohen's d={c['d']:.2f}")
 
out = Path("results/stats"); out.mkdir(parents=True, exist_ok=True)
json.dump({"per_pipeline":{k:{kk:vv for kk,vv in v.items() if kk!="raw_faith"} for k,v in metrics.items()},"comparisons":comps},
    open(out/"all_metrics.json","w"), indent=2, default=str)
print("\nSaved to results/stats/all_metrics.json")
