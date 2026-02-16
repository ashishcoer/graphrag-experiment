import json, time, yaml, argparse, sys
from pathlib import Path
from tqdm import tqdm
 
sys.path.insert(0, ".")
from pipelines.bm25.bm25_pipeline import BM25Pipeline
from pipelines.vector_rag.vector_pipeline import VectorRAGPipeline
from pipelines.graphrag.graphrag_pipeline import GraphRAGPipeline
from pipelines.graph_only.graph_only_pipeline import GraphOnlyPipeline
from pipelines.llm_client import generate, get_total_cost, print_cost_summary
 
with open("config.yaml") as f:
    config = yaml.safe_load(f)
 
def load_checkpoint(name, out_dir):
    cp = out_dir / f"results_{name}.json"
    if cp.exists():
        existing = json.load(open(cp))
        done = {r["instance_id"] for r in existing}
        print(f"  Resuming: {len(done)} already done")
        return existing, done
    return [], set()
 
def save_checkpoint(results, name, out_dir):
    json.dump(results, open(out_dir/f"results_{name}.json","w"), indent=2)
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline", default="all")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
 
    benchmark = json.load(open("data/benchmark/benchmark_raw.json"))
    if args.limit: benchmark = benchmark[:args.limit]
 
    out_dir = Path("evaluation/automated"); out_dir.mkdir(parents=True, exist_ok=True)
    pipes = {}
    if args.pipeline in ["all","bm25"]: pipes["bm25"] = BM25Pipeline()
    if args.pipeline in ["all","vector_rag"]: pipes["vector_rag"] = VectorRAGPipeline()
    if args.pipeline in ["all","graph_only"]: pipes["graph_only"] = GraphOnlyPipeline()
    if args.pipeline in ["all","graphrag"]: pipes["graphrag"] = GraphRAGPipeline()
 
    if args.dry_run:
        n = len(benchmark) * len(pipes)
        print(f"Dry run: {n} API calls, est cost ~{n * 0.008:.2f} USD")
        sys.exit(0)
 
    for name, pipe in pipes.items():
        print(f"\n{'='*50}\n  Running: {name} ({len(benchmark)} instances)\n{'='*50}")
        results, done = load_checkpoint(name, out_dir)
        remaining = [b for b in benchmark if b["instance_id"] not in done]
        if not remaining: print("  Already complete!"); continue
 
        for inst in tqdm(remaining, desc=name):
            query = f"{inst['title']} {inst['text'][:500]}"
            start = time.time()
            try:
                if name in ["graphrag","graph_only"]:
                    r = pipe.run(query)
                    output, context = r["output"], r.get("context","")
                else:
                    retrieved = pipe.retrieve(query, top_k=10)
                    context = "\n\n".join([r["text"][:500] for r in retrieved])[:24000]
                    gr = generate(f"Context:\n{context}\n\nQuery:\n{query}\n\nProvide: taxonomy, routing, dependencies, questions, criteria.",
                        "You are an expert enterprise planning assistant.", purpose=f"{name}_gen")
                    output = gr["text"]
            except Exception as e:
                print(f"\n  Error: {e}"); output, context = f"ERROR: {e}", ""
            results.append({"instance_id":inst["instance_id"],"pipeline":name,
                "query":query[:200],"output":output,"context":context[:2000],
                "latency_seconds":round(time.time()-start,2),"task_type":inst["task_type"]})
            if len(results) % 10 == 0: save_checkpoint(results, name, out_dir)
        save_checkpoint(results, name, out_dir)
        print(f"  Done: {len(results)} instances")
 
    print_cost_summary()
    print(f"\nTotal cost: ${get_total_cost():.2f}")
