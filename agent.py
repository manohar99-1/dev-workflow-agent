"""
Dev Workflow Agent - LegalSeva Assignment 2
Autonomously analyzes code: understands, debugs, documents, tests, and reports.
Supports GitHub repo URL or direct code paste via ANALYSIS_TARGET env var.
"""

import os
import sys
import re
import requests
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
GITHUB_TOKEN       = os.environ.get("GITHUB_TOKEN", "")
ANALYSIS_TARGET    = os.environ.get("ANALYSIS_TARGET", "")

# openrouter/free auto-selects from all available free models — no stale IDs
# Specific models are fallbacks in case the router itself is rate-limited
MODELS = [
    "openrouter/free",                              # auto-router, always up to date
    "meta-llama/llama-3.3-70b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "google/gemma-3-27b-it:free",
    "google/gemma-3-12b-it:free",
    "google/gemma-3-4b-it:free",
]


def get_headers():
    """Build headers fresh (so API key is read after env is loaded)."""
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
        "X-Title": "DevWorkflowAgent"
    }


# ── LLM Call with fallback + retry on 429 ────────────────────────────────────
def call_llm(system: str, user: str) -> str:
    import time
    last_error = None
    for model in MODELS:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user}
            ],
            "max_tokens": 1500,
            "temperature": 0.2
        }
        # Retry up to 3 times on 429 before moving to next model
        for attempt in range(3):
            try:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=get_headers(),
                    json=payload,
                    timeout=90
                )
                if resp.status_code == 429:
                    wait = 5 * (attempt + 1)  # 5s, 10s, 15s
                    print(f"  Model {model} rate limited (429), waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if resp.status_code in (404, 503):
                    print(f"  Model {model} failed ({resp.status_code}), trying next...")
                    last_error = resp.text
                    break  # skip to next model
                if not resp.ok:
                    print(f"  LLM error {resp.status_code}: {resp.text[:200]}")
                    resp.raise_for_status()
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content")
                )
                if not content:
                    print(f"  Model {model} returned empty content, trying next...")
                    last_error = "empty response"
                    break
                print(f"  ✓ Model used: {model}")
                return content.strip()
            except requests.exceptions.Timeout:
                print(f"  Model {model} timed out (attempt {attempt+1}), retrying...")
                last_error = "timeout"
                continue
            except Exception as e:
                print(f"  Model {model} error: {e}")
                last_error = str(e)
                break
        else:
            print(f"  Model {model} exhausted retries, trying next...")

    raise RuntimeError(f"All models failed. Last error: {last_error}")


# ── GitHub Fetcher ─────────────────────────────────────────────────────────────
def fetch_github_repo(repo_url: str) -> dict:
    if not repo_url.startswith("http"):
        repo_url = "https://github.com/" + repo_url
    match = re.search(r"github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$", repo_url)
    if not match:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")

    owner, repo = match.group(1), match.group(2)
    print(f"  Fetching repo: {owner}/{repo}")

    gh_headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        gh_headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    # Get repo info
    r = requests.get(f"https://api.github.com/repos/{owner}/{repo}", headers=gh_headers, timeout=30)
    print(f"  Repo API status: {r.status_code}")
    if r.status_code != 200:
        print(f"  Error: {r.json().get('message', 'unknown')}")
        return {}

    branch = r.json().get("default_branch", "main")
    print(f"  Default branch: {branch}")

    # Get file tree
    t = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
        headers=gh_headers, timeout=30
    )
    print(f"  Tree API status: {t.status_code}")
    tree = t.json().get("tree", [])
    print(f"  Total items in tree: {len(tree)}")

    files = {}
    for item in tree:
        path = item.get("path", "")
        if item["type"] != "blob":
            continue
        if not any(path.endswith(ext) for ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".md"]):
            continue
        if any(skip in path for skip in ["node_modules", "vendor", ".min.", "dist/", ".lock"]):
            continue
        if len(files) >= 10:
            break
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        rc = requests.get(raw_url, headers=gh_headers, timeout=20)
        if rc.status_code == 200:
            files[path] = rc.text[:3000]
            print(f"  ✓ {path}")
        else:
            print(f"  ✗ {path} ({rc.status_code})")

    print(f"  Files fetched: {len(files)}")
    return files


# ── Input Preparation ──────────────────────────────────────────────────────────
def prepare_code_context(target: str):
    target = target.strip()
    if "github.com" in target or re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", target):
        print(f"\n[INPUT] GitHub repo detected: {target}")
        files = fetch_github_repo(target)
        if not files:
            raise ValueError("No files fetched. Repo may be private or empty.")
        combined = ""
        for fname, content in files.items():
            combined += f"\n\n### FILE: {fname}\n```\n{content}\n```"
        return target, combined
    else:
        print("\n[INPUT] Direct code input detected.")
        return "Pasted Code", target


# ── Agent Steps ────────────────────────────────────────────────────────────────
def step_understand(source, code):
    print("\n[STEP 1/4] Understanding codebase...")
    return call_llm(
        "You are a senior software engineer. Analyze code and give a clear, structured summary.",
        f"""Analyze this code from '{source}' and provide:
1. **Purpose** – What does this code/project do?
2. **Structure** – Key files, classes, functions
3. **Tech Stack** – Languages, libraries, frameworks used
4. **Entry Points** – Where does execution start?

CODE:
{code[:4000]}"""
    )


def step_debug(source, code):
    print("[STEP 2/4] Debugging and reviewing...")
    return call_llm(
        "You are a code reviewer specializing in finding bugs, security issues, and code smells.",
        f"""Review this code from '{source}' and identify:
1. **Bugs** – Logic errors, edge cases, crashes
2. **Security Issues** – Hardcoded secrets, injection risks, unsafe calls
3. **Code Quality** – Bad practices, missing error handling, dead code
4. **Performance** – Inefficiencies, memory leaks

For each issue: file/line if visible, describe the problem, suggest the fix.

CODE:
{code[:4000]}"""
    )


def step_document(source, code):
    print("[STEP 3/4] Generating documentation...")
    return call_llm(
        "You are a technical writer. Generate clear, professional documentation.",
        f"""Generate documentation for the code from '{source}':
1. **README Overview** – Project description, setup steps, usage
2. **Function/Class Docstrings** – For the 3 most important functions, write proper docstrings
3. **API Reference** – List public functions with parameters and return values

CODE:
{code[:4000]}"""
    )


def step_test(source, code):
    print("[STEP 4/4] Writing unit tests...")
    return call_llm(
        "You are a QA engineer. Write thorough, runnable unit tests.",
        f"""Write unit tests for the code from '{source}':
1. Identify the 3-5 most important functions to test
2. Write pytest-compatible unit tests for each
3. Include: happy path, edge cases, and error cases
4. Use mocking where external calls are needed

CODE:
{code[:4000]}"""
    )


# ── Report ─────────────────────────────────────────────────────────────────────
def build_report(source, understanding, debug, docs, tests):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"""# 🤖 Dev Workflow Agent Report
**Source:** {source}
**Generated:** {now}
**Model:** {MODEL}

---

## 📋 Step 1: Code Understanding

{understanding}

---

## 🐛 Step 2: Debug & Code Review

{debug}

---

## 📝 Step 3: Documentation

{docs}

---

## 🧪 Step 4: Unit Tests

{tests}

---
*Generated by Dev Workflow Agent — LegalSeva Assignment 2*
"""


# ── Main ───────────────────────────────────────────────────────────────────────
def run_agent(target: str):
    print("=" * 60)
    print("  DEV WORKFLOW AGENT — LegalSeva Assignment 2")
    print("=" * 60)

    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY not set.")
        sys.exit(1)

    if not target:
        print("ERROR: ANALYSIS_TARGET not set.")
        sys.exit(1)

    print(f"\n  API Key present: {'yes' if OPENROUTER_API_KEY else 'NO'}")
    print(f"  Target: {target[:80]}")

    source, code = prepare_code_context(target)

    understanding = step_understand(source, code)
    debug         = step_debug(source, code)
    docs          = step_document(source, code)
    tests         = step_test(source, code)

    report = build_report(source, understanding, debug, docs, tests)

    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)

    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"reports/report_{timestamp}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n✅ Report saved to: {filename}")


if __name__ == "__main__":
    target = ANALYSIS_TARGET or (sys.argv[1] if len(sys.argv) > 1 else "")
    run_agent(target)
