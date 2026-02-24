import json, yaml
from pathlib import Path
from datetime import datetime

with open("config.yaml") as f:
    config = yaml.safe_load(f)

DATE_START = datetime.fromisoformat(config["github"]["date_range"]["start"])
DATE_END   = datetime.fromisoformat(config["github"]["date_range"]["end"])
RAW_DIR    = Path("data/raw")

ISSUE_REQUIRED = ["id", "title", "body", "state", "labels", "author", "created_at", "url", "repo"]
PR_REQUIRED    = ["id", "title", "body", "labels", "author", "created_at", "merged", "url", "repo"]
DOC_REQUIRED   = ["path", "content", "repo"]

passed = 0
failed = 0
warnings = 0
report = []

def check(condition, level, message):
    global passed, failed, warnings
    if condition:
        passed += 1
    else:
        if level == "ERROR":
            failed += 1
        else:
            warnings += 1
        report.append(f"  [{level}] {message}")

def in_date_range(date_str):
    if not date_str:
        return False
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", ""))
        return DATE_START <= dt <= DATE_END
    except Exception:
        return False

print("=" * 60)
print("  Data Validation Report")
print(f"  Date range: {DATE_START.date()} to {DATE_END.date()}")
print("=" * 60)

for repo_dir in sorted(RAW_DIR.iterdir()):
    if not repo_dir.is_dir():
        continue

    print(f"\n-- {repo_dir.name} --")

    # -- issues -----------------------------------------------
    issues_file = repo_dir / "issues.json"
    check(issues_file.exists(), "ERROR", f"issues.json missing in {repo_dir.name}")

    if issues_file.exists():
        issues = json.load(open(issues_file))
        check(len(issues) > 0, "ERROR", f"{repo_dir.name}/issues.json is empty")
        print(f"  issues.json:  {len(issues):>5} records")

        missing_fields, null_titles, null_bodies, out_of_range, dup_ids = 0, 0, 0, 0, 0
        seen_ids = set()

        for r in issues:
            # Required fields
            if not all(k in r for k in ISSUE_REQUIRED):
                missing_fields += 1
            # Null / empty title
            if not r.get("title", "").strip():
                null_titles += 1
            # Null / empty body
            if not r.get("body", "").strip():
                null_bodies += 1
            # Date range
            if not in_date_range(r.get("created_at", "")):
                out_of_range += 1
            # Duplicate IDs
            rid = r.get("id")
            if rid in seen_ids:
                dup_ids += 1
            seen_ids.add(rid)

        check(missing_fields == 0, "ERROR",   f"{repo_dir.name}/issues: {missing_fields} records missing required fields")
        check(null_titles == 0,    "WARNING", f"{repo_dir.name}/issues: {null_titles} records with empty title")
        check(null_bodies == 0,    "WARNING", f"{repo_dir.name}/issues: {null_bodies} records with empty body")
        check(out_of_range == 0,   "WARNING", f"{repo_dir.name}/issues: {out_of_range} records outside date range")
        check(dup_ids == 0,        "ERROR",   f"{repo_dir.name}/issues: {dup_ids} duplicate IDs")

        if null_titles:    print(f"    [WARNING] {null_titles} empty titles")
        if null_bodies:    print(f"    [WARNING] {null_bodies} empty bodies")
        if out_of_range:   print(f"    [WARNING] {out_of_range} outside date range")
        if dup_ids:        print(f"    [ERROR]   {dup_ids} duplicate IDs")

    # -- pull requests -----------------------------------------
    prs_file = repo_dir / "prs.json"
    check(prs_file.exists(), "ERROR", f"prs.json missing in {repo_dir.name}")

    if prs_file.exists():
        prs = json.load(open(prs_file))
        check(len(prs) > 0, "ERROR", f"{repo_dir.name}/prs.json is empty")
        print(f"  prs.json:     {len(prs):>5} records")

        missing_fields, null_titles, out_of_range, dup_ids = 0, 0, 0, 0
        seen_ids = set()

        for r in prs:
            if not all(k in r for k in PR_REQUIRED):
                missing_fields += 1
            if not r.get("title", "").strip():
                null_titles += 1
            if not in_date_range(r.get("created_at", "")):
                out_of_range += 1
            rid = r.get("id")
            if rid in seen_ids:
                dup_ids += 1
            seen_ids.add(rid)

        check(missing_fields == 0, "ERROR",   f"{repo_dir.name}/prs: {missing_fields} records missing required fields")
        check(null_titles == 0,    "WARNING", f"{repo_dir.name}/prs: {null_titles} records with empty title")
        check(out_of_range == 0,   "WARNING", f"{repo_dir.name}/prs: {out_of_range} records outside date range")
        check(dup_ids == 0,        "ERROR",   f"{repo_dir.name}/prs: {dup_ids} duplicate IDs")

        if null_titles:    print(f"    [WARNING] {null_titles} empty titles")
        if out_of_range:   print(f"    [WARNING] {out_of_range} outside date range")
        if dup_ids:        print(f"    [ERROR]   {dup_ids} duplicate IDs")

    # -- docs -------------------------------------------------
    docs_file = repo_dir / "docs.json"
    check(docs_file.exists(), "ERROR", f"docs.json missing in {repo_dir.name}")

    if docs_file.exists():
        docs = json.load(open(docs_file))
        check(len(docs) > 0, "WARNING", f"{repo_dir.name}/docs.json is empty")
        print(f"  docs.json:    {len(docs):>5} records")

        missing_fields, empty_content = 0, 0
        for r in docs:
            if not all(k in r for k in DOC_REQUIRED):
                missing_fields += 1
            if not r.get("content", "").strip():
                empty_content += 1

        check(missing_fields == 0, "ERROR",   f"{repo_dir.name}/docs: {missing_fields} records missing required fields")
        check(empty_content == 0,  "WARNING", f"{repo_dir.name}/docs: {empty_content} records with empty content")

        if empty_content: print(f"    [WARNING] {empty_content} empty content")

# -- summary -------------------------------------------------------------------

total = passed + failed + warnings
print("\n" + "=" * 60)
print(f"  SUMMARY")
print(f"  Checks passed:  {passed:>4}")
print(f"  Warnings:       {warnings:>4}")
print(f"  Errors:         {failed:>4}")
print("=" * 60)

if report:
    print("\nIssues found:")
    for r in report:
        print(r)
else:
    print("\n  All checks passed — data looks clean!")

# Save report
out = Path("results/validation_report.txt")
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w") as f:
    f.write(f"Validation Report\nDate range: {DATE_START.date()} to {DATE_END.date()}\n\n")
    f.write(f"Passed: {passed}  Warnings: {warnings}  Errors: {failed}\n\n")
    if report:
        f.write("Issues:\n")
        for r in report:
            f.write(r + "\n")
    else:
        f.write("All checks passed.\n")

print(f"\nReport saved to {out}")