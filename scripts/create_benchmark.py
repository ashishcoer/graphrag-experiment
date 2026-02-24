import json, random, yaml
from pathlib import Path
from neo4j import GraphDatabase
 
random.seed(42)
with open("config.yaml") as f:
    config = yaml.safe_load(f)
driver = GraphDatabase.driver(config["neo4j"]["uri"],
    auth=(config["neo4j"]["user"], config["neo4j"]["password"]))
 
with driver.session() as s:
    result = s.run("MATCH (i:Issue) WHERE i.labels_str IS NOT NULL AND i.text_payload IS NOT NULL AND size(i.text_payload) > 50 RETURN i.id AS id, i.title AS title, i.text_payload AS text, i.labels_str AS labels")
    all_issues = [dict(r) for r in result]
print(f"Candidate issues: {len(all_issues)}")
 
by_repo = {}
for issue in all_issues:
    repo = issue["id"].split(":")[0]
    by_repo.setdefault(repo, []).append(issue)
 
benchmark = []
target = min(config["benchmark"]["total_instances"], len(all_issues))
tasks = ["routing","taxonomy","dependency"]
for repo, issues in by_repo.items():
    n = max(50, int(target * len(issues) / len(all_issues)))
    for i, issue in enumerate(random.sample(issues, min(n, len(issues)))):
        benchmark.append({"instance_id": f"bench_{len(benchmark):04d}",
            "issue_id": issue["id"], "title": issue["title"],
            "text": issue["text"][:3000], "labels": issue["labels"],
            "task_type": tasks[i % 3], "repo": repo,
            "gold_labels": {"routing":"","taxonomy":"","dependencies":[]}})
benchmark = benchmark[:target]
 
out = Path("data/benchmark"); out.mkdir(exist_ok=True)
json.dump(benchmark, open(out/"benchmark_raw.json","w"), indent=2)
print(f"Benchmark: {len(benchmark)} instances")
for t_name in tasks:
    print(f"  {t_name}: {sum(1 for b in benchmark if b['task_type']==t_name)}")
driver.close()
