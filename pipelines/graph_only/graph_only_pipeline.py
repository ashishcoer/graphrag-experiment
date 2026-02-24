import yaml
from pipelines.graphrag.graphrag_pipeline import GraphRAGPipeline
from pipelines.llm_client import generate
 
with open("config.yaml") as f:
    config = yaml.safe_load(f)
 
class GraphOnlyPipeline(GraphRAGPipeline):
    def run(self, query):
        seeds = self._get_seeds(query, k=config["retrieval"]["seed_k"])
        nodes, edges = self._expand(seeds)
        nodes, edges = self._prune(query, nodes, edges)
        flat = "\n\n".join([n.get("text","")[:300] for n in nodes])
        prompt = f"Context:\n{flat}\n\nRequest:\n{query}\n\nProvide: 1) Taxonomy 2) Routing 3) Dependencies 4) Questions 5) Criteria"
        result = generate(prompt, "You are an expert enterprise planning assistant.", purpose="graph_only_generation")
        return {"output":result["text"],"context":flat,"num_nodes":len(nodes),"num_edges":len(edges)}
