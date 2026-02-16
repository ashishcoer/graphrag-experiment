"""
collect_github_data.py — Fixed version with:
  - Timeout on every request (30 seconds)
  - Automatic retry (3 attempts) on network errors
  - Checkpoint/resume: skips repos that already have data
  - Progress saved after each repo
"""

import os, json, time, yaml, requests, base64
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

with open("config.yaml") as f:
    config = yaml.safe_load(f)

TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not TOKEN:
    raise ValueError("Set GITHUB_TOKEN environment variable! See Step 9.")

# === ROBUST SESSION WITH RETRIES AND TIMEOUTS ===
session = requests.Session()
session.headers.update({
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
})
retry_strategy = Retry(
    total=5,                    # Retry up to 5 times
    backoff_factor=2,           # Wait 2s, 4s, 8s, 16s, 32s between retries
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)
TIMEOUT = 30  # 30 second timeout per request

DATE_START = config["github"]["date_range"]["start"]
DATE_END = config["github"]["date_range"]["end"]
OUTPUT = Path("data/raw")


def safe_get(url, params=None):
    """Make a GET request with timeout and retry. Returns response or None."""
    for attempt in range(3):
        try:
            resp = session.get(url, params=params, timeout=TIMEOUT)
            if resp.status_code == 403:
                # Rate limited — wait and retry
                reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(reset - time.time() + 5, 10)
                print(f"    Rate limited. Waiting {wait:.0f}s...")
                time.sleep(wait)
                continue
            return resp
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            wait = 10 * (attempt + 1)
            print(f"    Network error (attempt {attempt+1}/3): {type(e).__name__}. Retrying in {wait}s...")
            time.sleep(wait)
    print("    WARNING: Failed after 3 attempts. Skipping this request.")
    return None


def rate_check():
    """Check rate limit, sleep if needed."""
    resp = safe_get("https://api.github.com/rate_limit")
    if resp is None:
        time.sleep(30)  # If we can't even check rate limit, wait a bit
        return
    try:
        data = resp.json()
        remaining = data["resources"]["core"]["remaining"]
        if remaining < 100:
            reset = data["resources"]["core"]["reset"]
            wait = max(reset - time.time() + 5, 10)
            print(f"    Rate limit low ({remaining}). Sleeping {wait:.0f}s...")
            time.sleep(wait)
    except (KeyError, json.JSONDecodeError):
        pass


def collect_issues(owner, repo, max_count):
    print(f"\n  Collecting issues from {owner}/{repo}...")
    issues = []
    page = 1

    while len(issues) < max_count:
        rate_check()
        resp = safe_get(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            params={
                "state": "all",
                "since": DATE_START + "T00:00:00Z",
                "per_page": 100,
                "page": page,
                "sort": "updated",      # Changed: sort by updated, not created
                "direction": "desc"
            }
        )

        if resp is None:
            print(f"    Skipping page {page} due to network error")
            page += 1
            if page > 200:
                break
            continue

        batch = resp.json()
        if not batch or not isinstance(batch, list):
            break

        added_this_page = 0
        for item in batch:
            # Skip pull requests
            if "pull_request" in item:
                continue

            created = item.get("created_at", "")
            if created < DATE_START + "T00:00:00Z" or created > DATE_END + "T23:59:59Z":
                continue

            issue = {
                "id": item["number"],
                "title": item["title"],
                "body": (item.get("body", "") or "")[:5000],
                "state": item["state"],
                "labels": [l["name"] for l in item.get("labels", [])],
                "assignees": [a["login"] for a in item.get("assignees", [])],
                "author": item["user"]["login"],
                "created_at": created,
                "closed_at": item.get("closed_at"),
                "url": item["html_url"],
                "repo": f"{owner}/{repo}"
            }

            # Get first 3 comments (skip if network is flaky)
            if item.get("comments", 0) > 0:
                cr = safe_get(item["comments_url"], params={"per_page": 3})
                if cr and cr.status_code == 200:
                    try:
                        issue["comments"] = [
                            {"author": c["user"]["login"], "body": c.get("body", "")}
                            for c in cr.json()[:3]
                        ]
                    except (KeyError, TypeError):
                        pass

            issues.append(issue)
            added_this_page += 1

        print(f"    Page {page}: {len(issues)} issues total (+{added_this_page} this page)")
        page += 1

        if len(batch) < 100:
            break
        if page > 200:  # Safety limit
            break

    return issues[:max_count]


def collect_prs(owner, repo, max_count):
    print(f"  Collecting PRs from {owner}/{repo}...")
    prs = []
    page = 1

    while len(prs) < max_count:
        rate_check()
        resp = safe_get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            params={
                "state": "all",
                "per_page": 100,
                "page": page,
                "sort": "updated",       # Changed: sort by updated
                "direction": "desc"
            }
        )

        if resp is None:
            print(f"    Skipping page {page} due to network error")
            page += 1
            if page > 200:
                break
            continue

        batch = resp.json()
        if not batch or not isinstance(batch, list):
            break

        added_this_page = 0
        for item in batch:
            created = item.get("created_at", "")
            if created < DATE_START + "T00:00:00Z" or created > DATE_END + "T23:59:59Z":
                continue

            pr = {
                "id": item["number"],
                "title": item["title"],
                "body": (item.get("body", "") or "")[:3000],
                "labels": [l["name"] for l in item.get("labels", [])],
                "assignees": [a["login"] for a in item.get("assignees", [])],
                "author": item["user"]["login"],
                "created_at": created,
                "merged": item.get("merged_at") is not None,
                "url": item["html_url"],
                "repo": f"{owner}/{repo}"
            }

            # Get files changed (skip on network error)
            fr = safe_get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{item['number']}/files",
                params={"per_page": 30}
            )
            if fr and fr.status_code == 200:
                try:
                    pr["files_changed"] = [f["filename"] for f in fr.json()[:30]]
                except (KeyError, TypeError):
                    pr["files_changed"] = []

            prs.append(pr)
            added_this_page += 1

        print(f"    Page {page}: {len(prs)} PRs total (+{added_this_page} this page)")
        page += 1

        if len(batch) < 100:
            break
        if page > 200:
            break

    return prs[:max_count]


def collect_docs(owner, repo):
    print(f"  Collecting docs from {owner}/{repo}...")
    docs = []

    # Get README
    rr = safe_get(f"https://api.github.com/repos/{owner}/{repo}/readme")
    if rr and rr.status_code == 200:
        try:
            content = base64.b64decode(rr.json().get("content", "")).decode("utf-8", errors="replace")
            docs.append({"path": "README.md", "content": content[:10000], "repo": f"{owner}/{repo}"})
        except Exception:
            pass

    # Get docs from tree
    for branch in ["main", "master"]:
        tr = safe_get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}",
            params={"recursive": "1"}
        )
        if tr is None or tr.status_code != 200:
            continue

        try:
            tree = tr.json().get("tree", [])
        except (json.JSONDecodeError, AttributeError):
            continue

        doc_files = [
            f for f in tree
            if any(f["path"].startswith(d + "/") for d in ["docs", "documentation", "doc"])
            and f["path"].endswith((".md", ".rst", ".txt"))
            and f["type"] == "blob"
        ][:100]

        for df in doc_files:
            br = safe_get(df["url"])
            if br and br.status_code == 200:
                try:
                    c = base64.b64decode(br.json().get("content", "")).decode("utf-8", errors="replace")
                    docs.append({"path": df["path"], "content": c[:5000], "repo": f"{owner}/{repo}"})
                except Exception:
                    pass
        break  # Found a valid branch, stop trying

    print(f"    {len(docs)} documentation files")
    return docs


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)

    for rc in config["github"]["repos"]:
        o, r = rc["owner"], rc["repo"]
        d = OUTPUT / f"{o}_{r}"
        d.mkdir(exist_ok=True)

        # === CHECKPOINT: Skip repos that already have data ===
        issues_file = d / "issues.json"
        prs_file = d / "prs.json"
        docs_file = d / "docs.json"

        if issues_file.exists() and prs_file.exists() and docs_file.exists():
            existing_issues = json.load(open(issues_file))
            existing_prs = json.load(open(prs_file))
            existing_docs = json.load(open(docs_file))
            print(f"\n  SKIPPING {o}/{r} — already collected: {len(existing_issues)} issues, {len(existing_prs)} PRs, {len(existing_docs)} docs")
            print(f"  (Delete the folder data/raw/{o}_{r} to re-collect)")
            continue

        print(f"\n{'='*50}\n  Processing {o}/{r}\n{'='*50}")

        # Collect issues
        if issues_file.exists():
            issues = json.load(open(issues_file))
            print(f"  Issues already saved: {len(issues)}")
        else:
            issues = collect_issues(o, r, rc["max_issues"])
            json.dump(issues, open(issues_file, "w"), indent=2)
            print(f"  Saved {len(issues)} issues")

        # Collect PRs
        if prs_file.exists():
            prs = json.load(open(prs_file))
            print(f"  PRs already saved: {len(prs)}")
        else:
            prs = collect_prs(o, r, rc["max_prs"])
            json.dump(prs, open(prs_file, "w"), indent=2)
            print(f"  Saved {len(prs)} PRs")

        # Collect docs
        if docs_file.exists():
            docs = json.load(open(docs_file))
            print(f"  Docs already saved: {len(docs)}")
        else:
            docs = collect_docs(o, r)
            json.dump(docs, open(docs_file, "w"), indent=2)
            print(f"  Saved {len(docs)} docs")

    # Final summary
    print("\n" + "="*50)
    print("  COLLECTION SUMMARY")
    print("="*50)
    total_issues, total_prs, total_docs = 0, 0, 0
    for rc in config["github"]["repos"]:
        d = OUTPUT / f"{rc['owner']}_{rc['repo']}"
        ni = len(json.load(open(d / "issues.json"))) if (d / "issues.json").exists() else 0
        np_ = len(json.load(open(d / "prs.json"))) if (d / "prs.json").exists() else 0
        nd = len(json.load(open(d / "docs.json"))) if (d / "docs.json").exists() else 0
        print(f"  {rc['owner']}/{rc['repo']}: {ni} issues, {np_} PRs, {nd} docs")
        total_issues += ni
        total_prs += np_
        total_docs += nd
    print(f"\n  TOTAL: {total_issues} issues, {total_prs} PRs, {total_docs} docs")
    print("\nData collection complete!")
