import json, re, yaml, numpy as np
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from pipelines.llm_client import generate
 
with open("config.yaml") as f:
    config = yaml.safe_load(f)
 
class GraphRAGPipeline:
    def __init__(self):
        self.embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.driver = GraphDatabase.driver(config["neo4j"]["uri"],
            auth=(config["neo4j"]["user"], config["neo4j"]["password"]))
        self.expansion_policy = {
            "Issue": [{"edge":"BELONGS_TO","target":"Component","max_depth":1},
                      {"edge":"OWNED_BY","target":"Owner","max_depth":1},
                      {"edge":"DEPENDS_ON","target":"Issue","max_depth":2}],
            "Component": [{"edge":"DEPENDS_ON","target":"Component","max_depth":2},
                          {"edge":"OWNED_BY","target":"Owner","max_depth":1}],
            "Owner": [{"edge":"MAINTAINS","target":"CodeModule","max_depth":1}]}
 
    def _get_seeds(self, query, k=10):
        qe = self.embed_model.encode(query, normalize_embeddings=True).tolist()
        with self.driver.session() as s:
            nodes = [dict(r) for r in s.run(
                "MATCH (n) WHERE n.embedding IS NOT NULL RETURN n.id AS id, labels(n)[0] AS label, n.text_payload AS text, n.embedding AS embedding")]
        scored = [{"id":n["id"],"label":n["label"],"text":n["text"],"embedding":n["embedding"],
                   "similarity":float(np.dot(qe,n["embedding"]))} for n in nodes if n["embedding"]]
        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:k]
 
    def _expand(self, seeds, max_hops=3):
        visited, nodes, edges = set(), [], []
        frontier = [(s, 0) for s in seeds]
        with self.driver.session() as s:
            while frontier:
                cur, depth = frontier.pop(0)
                if cur["id"] in visited or depth > max_hops: continue
                visited.add(cur["id"]); nodes.append(cur)
                for rule in self.expansion_policy.get(cur.get("label",""),[]):
                    if depth + 1 > rule["max_depth"]: continue
                    for r in s.run(f"MATCH (a {{id: $id}})-[r:{rule['edge']}]->(b:{rule['target']}) RETURN b.id AS id, labels(b)[0] AS label, b.text_payload AS text, b.embedding AS embedding, type(r) AS rt, r.confidence AS conf", id=cur["id"]):
                        nb = dict(r)
                        edges.append({"source":cur["id"],"target":nb["id"],"type":nb["rt"],"confidence":nb.get("conf",0.5)})
                        if nb["id"] not in visited:
                            frontier.append((nb, depth+1))
        return nodes, edges
 
    def _prune(self, query, nodes, edges, threshold=0.35):
        qe = self.embed_model.encode(query, normalize_embeddings=True)
        kept = [n for n in nodes if (float(np.dot(qe,n["embedding"])) if n.get("embedding") else 0.3) >= threshold]
        for n in kept: n["relevance"] = float(np.dot(qe, n["embedding"])) if n.get("embedding") else 0.3
        ids = {n["id"] for n in kept}
        return kept, [e for e in edges if e["source"] in ids and e["target"] in ids]
 
    def _serialize(self, nodes, edges):
        blocks, id_map = [], {}
        for i, n in enumerate(nodes):
            eid = f"[E{i+1}]"
            id_map[n["id"]] = eid
            blocks.append(f"{eid} {n.get('label','Entity')}: {n.get('text','')[:300]}")
        rels = [f"{id_map.get(e['source'],'?')} --[{e['type']}]--> {id_map.get(e['target'],'?')}" for e in edges]
        ctx = "=== EVIDENCE BLOCKS ===\n" + "\n".join(blocks) + "\n\n=== RELATIONSHIPS ===\n" + "\n".join(rels)
        return ctx, list(id_map.values())
 
    def run(self, query):
        seeds = self._get_seeds(query, k=config["retrieval"]["seed_k"])
        nodes, edges = self._expand(seeds, config["retrieval"]["max_hops"])
        nodes, edges = self._prune(query, nodes, edges, config["retrieval"]["prune_threshold"])
        context, valid_ids = self._serialize(nodes, edges)
        sys_prompt = "You are an expert enterprise planning assistant. Cite evidence [E1],[E2] etc for every claim. Only use provided evidence."
        prompt = f"{context}\n\n=== REQUEST ===\n{query}\n\n=== OUTPUT ===\n1. TAXONOMY CLASSIFICATION (cite evidence)\n2. ROUTING/OWNERSHIP (cite evidence)\n3. DEPENDENCIES (cite evidence)\n4. CLARIFICATION QUESTIONS\n5. ACCEPTANCE CRITERIA"
        result = generate(prompt, sys_prompt, purpose="graphrag_generation")
        output = result["text"]
        # Citation verification
        cited = set(re.findall(r'\[E\d+\]', output))
        invalid = cited - set(valid_ids)
        regen = False
        if invalid:
            fix = f"Your response cited non-existent evidence: {', '.join(invalid)}. Valid IDs: {', '.join(valid_ids)}. Revise, removing invalid citations.\n\nOriginal context:\n{context}\n\nYour response:\n{output}"
            result2 = generate(fix, purpose="citation_fix")
            output, regen = result2["text"], True
        return {"output":output,"context":context,"num_nodes":len(nodes),"num_edges":len(edges),"evidence_ids":valid_ids,"was_regenerated":regen}
