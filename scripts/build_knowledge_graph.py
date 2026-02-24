import json, yaml
from pathlib import Path
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
 
with open("config.yaml") as f:
    config = yaml.safe_load(f)
 
print("Loading embedding model...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
driver = GraphDatabase.driver(config["neo4j"]["uri"],
    auth=(config["neo4j"]["user"], config["neo4j"]["password"]))
 
def setup_schema(session):
    for label in ["Issue","Component","Service","Owner","CodeModule","DocumentationPage"]:
        session.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE")
 
def embed(text):
    if not text: text = ""
    return embed_model.encode(text[:2000], normalize_embeddings=True).tolist()
 
def load_entities(session, fpath, label):
    entities = json.load(open(fpath))
    print(f"  Loading {len(entities)} {label} nodes...")
    for e in tqdm(entities, desc=f"    {label}"):
        text = " ".join(filter(None, [e.get("title",""),e.get("name",""),
            e.get("body","")[:500],e.get("content","")[:500]])).strip()
        emb = embed(text)
        props = {"id":e["id"], "text_payload":text[:2000], "embedding":emb}
        for k in ["title","name","path","state","number"]:
            if k in e: props[k] = e[k]
        if "labels" in e: props["labels_str"] = ", ".join(e["labels"])
        session.run(f"MERGE (n:{label} {{id: $id}}) SET n += $props", id=e["id"], props=props)
 
def load_relations(session, fpath):
    relations = json.load(open(fpath))
    print(f"  Loading {len(relations)} relations...")
    for rel in tqdm(relations, desc="    Relations"):
        try:
            session.run(f"MATCH (a {{id: $src}}) MATCH (b {{id: $tgt}}) MERGE (a)-[r:{rel['type'].upper()}]->(b) SET r.confidence = $conf",
                src=rel["source"], tgt=rel["target"], conf=rel.get("confidence",0.5))
        except: pass
 
if __name__ == "__main__":
    processed = Path("data/processed")
    with driver.session() as s:
        print("Setting up schema...")
        setup_schema(s)
        files = {"entities_issues.json":"Issue","entities_components.json":"Component",
                 "entities_services.json":"Service","entities_owners.json":"Owner",
                 "entities_code_modules.json":"CodeModule","entities_doc_pages.json":"DocumentationPage"}
        for fname, label in files.items():
            fp = processed / fname
            if fp.exists(): load_entities(s, fp, label)
        rp = processed / "relations.json"
        if rp.exists(): load_relations(s, rp)
        nodes = s.run("MATCH (n) RETURN count(n) as c").single()["c"]
        edges = s.run("MATCH ()-[r]->() RETURN count(r) as c").single()["c"]
        print(f"\nKnowledge Graph: {nodes} nodes, {edges} edges")
    driver.close()
