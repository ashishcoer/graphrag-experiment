import json, re
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm
 
def extract_components_from_labels(labels):
    comps = []
    for label in labels:
        for prefix in ["area/","component/","comp/","sig/","kind/","platform/"]:
            if label.lower().startswith(prefix):
                comps.append(label[len(prefix):].strip())
    return comps
 
def extract_components_from_paths(file_paths):
    comps = set()
    for path in file_paths:
        parts = path.split("/")
        if len(parts) >= 2: comps.add(parts[0])
        if len(parts) >= 3 and parts[0] in ["pkg","src","lib","cmd","internal"]:
            comps.add(parts[1])
    return list(comps)
 
def extract_deps_from_text(text):
    deps = []
    patterns = [(r"depends\s+on\s+#(\d+)","depends_on"),(r"blocked\s+by\s+#(\d+)","blocked_by"),
                (r"blocks\s+#(\d+)","blocks"),(r"related\s+to\s+#(\d+)","related_to"),
                (r"fixes\s+#(\d+)","fixes"),(r"closes\s+#(\d+)","closes")]
    for pattern, rel in patterns:
        for m in re.findall(pattern, text, re.IGNORECASE):
            deps.append({"target_id": int(m), "relation": rel})
    return deps
 
def process_repo(repo_dir):
    entities = {"issues":[],"components":[],"services":[],"owners":[],"code_modules":[],"doc_pages":[]}
    relations = []
    ip = repo_dir / "issues.json"
    if ip.exists():
        for issue in tqdm(json.load(open(ip)), desc=f"  Issues ({repo_dir.name})"):
            eid = f"{repo_dir.name}:issue:{issue['id']}"
            entities["issues"].append({"id":eid,"type":"Issue","number":issue["id"],
                "title":issue["title"],"body":issue.get("body","")[:2000],
                "labels":issue.get("labels",[]),"state":issue.get("state",""),"repo":issue.get("repo","")})
            for comp in extract_components_from_labels(issue.get("labels",[])):
                cid = f"{repo_dir.name}:component:{comp}"
                entities["components"].append({"id":cid,"type":"Component","name":comp})
                relations.append({"source":eid,"target":cid,"type":"belongs_to","confidence":0.95})
            for assignee in issue.get("assignees",[]):
                oid = f"{repo_dir.name}:owner:{assignee}"
                entities["owners"].append({"id":oid,"type":"Owner","name":assignee})
                relations.append({"source":eid,"target":oid,"type":"owned_by","confidence":0.90})
            text = f"{issue.get('title','')} {issue.get('body','')}"
            for dep in extract_deps_from_text(text):
                tid = f"{repo_dir.name}:issue:{dep['target_id']}"
                relations.append({"source":eid,"target":tid,"type":"depends_on","confidence":0.80})
    pp = repo_dir / "prs.json"
    if pp.exists():
        for pr in tqdm(json.load(open(pp)), desc=f"  PRs ({repo_dir.name})"):
            files = pr.get("files_changed",[])
            for comp in extract_components_from_paths(files):
                entities["code_modules"].append({"id":f"{repo_dir.name}:code:{comp}","type":"CodeModule","name":comp})
            author = pr.get("author","")
            if author:
                oid = f"{repo_dir.name}:owner:{author}"
                for comp in extract_components_from_paths(files)[:5]:
                    relations.append({"source":oid,"target":f"{repo_dir.name}:code:{comp}","type":"maintains","confidence":0.70})
    dp = repo_dir / "docs.json"
    if dp.exists():
        for doc in json.load(open(dp)):
            entities["doc_pages"].append({"id":f"{repo_dir.name}:doc:{doc['path']}",
                "type":"DocumentationPage","path":doc["path"],"content":doc.get("content","")[:3000]})
    for k in entities:
        seen = set()
        entities[k] = [e for e in entities[k] if e["id"] not in seen and not seen.add(e["id"])]
    return entities, relations
 
if __name__ == "__main__":
    all_entities = defaultdict(list)
    all_relations = []
    for repo_dir in sorted(Path("data/raw").iterdir()):
        if not repo_dir.is_dir(): continue
        print(f"\nProcessing {repo_dir.name}...")
        entities, relations = process_repo(repo_dir)
        for k, v in entities.items(): all_entities[k].extend(v)
        all_relations.extend(relations)
    out = Path("data/processed"); out.mkdir(exist_ok=True)
    for k, v in all_entities.items():
        json.dump(v, open(out/f"entities_{k}.json","w"), indent=2)
        print(f"  {k}: {len(v)} entities")
    json.dump(all_relations, open(out/"relations.json","w"), indent=2)
    print(f"  Relations: {len(all_relations)}")
    print(f"\nTotal nodes: {sum(len(v) for v in all_entities.values())}")
    print(f"Total edges: {len(all_relations)}")
