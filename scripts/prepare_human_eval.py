"""
prepare_human_eval.py
Samples a stratified subset of benchmark instances and prepares a blinded
CSV for human annotators, plus a key file for unblinding after evaluation.
"""
import json, csv, random
from pathlib import Path
from collections import defaultdict

# ── config ────────────────────────────────────────────────────────────────────

SAMPLE_PER_TASK_TYPE = 25      # 25 x 3 task types = 75 total instances
RANDOM_SEED          = 42
PIPELINES            = ["bm25", "vector_rag", "graph_only", "graphrag"]
BLIND_LABELS         = ["System-A", "System-B", "System-C", "System-D"]

out_dir = Path("evaluation/human")
out_dir.mkdir(parents=True, exist_ok=True)

random.seed(RANDOM_SEED)

# ── load data ─────────────────────────────────────────────────────────────────

benchmark = json.load(open("data/benchmark/benchmark_raw.json"))
bench_map  = {b["instance_id"]: b for b in benchmark}

results = {}
for pipe in PIPELINES:
    data = json.load(open(f"evaluation/automated/results_{pipe}.json"))
    results[pipe] = {r["instance_id"]: r for r in data}

# ── stratified sample ─────────────────────────────────────────────────────────

by_type = defaultdict(list)
for b in benchmark:
    # Only keep instances that have outputs from all 4 pipelines
    if all(b["instance_id"] in results[p] for p in PIPELINES):
        by_type[b["task_type"]].append(b)

sampled = []
for task_type, instances in by_type.items():
    n = min(SAMPLE_PER_TASK_TYPE, len(instances))
    sampled.extend(random.sample(instances, n))

random.shuffle(sampled)
print(f"Sampled {len(sampled)} instances across {len(by_type)} task types")

# ── build blinded eval set ────────────────────────────────────────────────────

eval_rows  = []   # what annotators see (CSV)
key_rows   = []   # unblinding key (kept secret until after annotation)

for inst in sampled:
    iid = inst["instance_id"]

    # Randomise pipeline order per instance so annotators can't guess by position
    pipe_order = PIPELINES[:]
    random.shuffle(pipe_order)

    outputs = {}
    for label, pipe in zip(BLIND_LABELS, pipe_order):
        output = results[pipe][iid]["output"]
        # Truncate very long outputs for readability
        outputs[label] = output[:1500] + "..." if len(output) > 1500 else output

    eval_rows.append({
        "instance_id":    iid,
        "task_type":      inst["task_type"],
        "repo":           inst["repo"],
        "query":          inst["title"] + " " + inst["text"][:300],
        "output_A":       outputs["System-A"],
        "output_B":       outputs["System-B"],
        "output_C":       outputs["System-C"],
        "output_D":       outputs["System-D"],
        # Blank columns for annotators to fill in
        "relevance_A":    "",
        "relevance_B":    "",
        "relevance_C":    "",
        "relevance_D":    "",
        "completeness_A": "",
        "completeness_B": "",
        "completeness_C": "",
        "completeness_D": "",
        "coherence_A":    "",
        "coherence_B":    "",
        "coherence_C":    "",
        "coherence_D":    "",
        "best_system":    "",   # annotator picks A/B/C/D
        "notes":          "",
    })

    key_rows.append({
        "instance_id": iid,
        "System-A":    pipe_order[0],
        "System-B":    pipe_order[1],
        "System-C":    pipe_order[2],
        "System-D":    pipe_order[3],
    })

# ── save CSV for annotators ───────────────────────────────────────────────────

csv_path = out_dir / "human_eval_form.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=eval_rows[0].keys())
    writer.writeheader()
    writer.writerows(eval_rows)

print(f"Annotator form saved: {csv_path}")

# ── save unblinding key (keep secret until after annotation) ──────────────────

key_path = out_dir / "unblinding_key.json"
json.dump(key_rows, open(key_path, "w"), indent=2)
print(f"Unblinding key saved: {key_path}  <-- DO NOT share with annotators")

# ── save annotation instructions ─────────────────────────────────────────────

instructions = """HUMAN EVALUATION INSTRUCTIONS
==============================

You will evaluate outputs from 4 AI systems (labelled System-A to System-D)
on work-intake planning tasks from GitHub issues. The systems are blinded --
you will not know which system produced which output.

TASK
----
For each row in the spreadsheet:
1. Read the 'query' column (the GitHub issue title and description)
2. Read outputs from System-A, System-B, System-C, System-D
3. Score each output on three dimensions using a 1-5 scale:

SCORING DIMENSIONS
------------------
Relevance (1-5):
  5 = Directly and fully addresses the query
  4 = Mostly relevant with minor gaps
  3 = Partially relevant
  2 = Mostly off-topic
  1 = Completely irrelevant

Completeness (1-5):
  5 = Covers all of: taxonomy, routing, dependencies, questions, criteria
  4 = Covers 4 of the 5 sections
  3 = Covers 3 of the 5 sections
  2 = Covers 1-2 sections
  1 = Missing most or all sections

Coherence (1-5):
  5 = Exceptionally clear, well-structured, professional
  4 = Clear and well-organised
  3 = Adequate but some unclear parts
  2 = Difficult to follow
  1 = Incoherent or very poorly structured

BEST SYSTEM
-----------
After scoring all four, enter the label (A, B, C, or D) of the system
you found most useful overall in the 'best_system' column.

NOTES
-----
Use the 'notes' column for any observations, e.g. if outputs are very
similar, or if you found the task particularly easy or hard.

IMPORTANT
---------
- Score independently -- do not let one system's score influence another
- Ignore formatting differences (markdown headers etc.) -- focus on content
- If two systems are equally good, it is fine to give the same score
- Complete all rows before returning the form
"""

instr_path = out_dir / "annotation_instructions.txt"
open(instr_path, "w", encoding="utf-8").write(instructions)
print(f"Instructions saved:  {instr_path}")

# ── summary ───────────────────────────────────────────────────────────────────

from collections import Counter
type_counts = Counter(r["task_type"] for r in eval_rows)
repo_counts  = Counter(r["repo"] for r in eval_rows)

print("\n-- Sample breakdown --")
print("By task type:", dict(type_counts))
print("By repo:     ", dict(repo_counts))
print(f"\nTotal instances for human eval: {len(eval_rows)}")
print(f"Total outputs to score:         {len(eval_rows) * 4}")