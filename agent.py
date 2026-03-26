"""
Dev Workflow Agent - LegalSeva Assignment 2
Autonomously analyzes code: understands, debugs, documents, tests, and reports.
Copied from proven Synapse AI News pattern — urllib + retry rounds + sleep between steps.
"""

import os
import sys
import re
import json
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
GITHUB_TOKEN       = os.environ.get("GITHUB_TOKEN", "")
ANALYSIS_TARGET    = os.environ.get("ANALYSIS_TARGET", "")

FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "google/gemma-3-12b-it:free",
    "meta-llama/llama-3.2-3b-instruct:free",
]


# ── LLM Call — exact Synapse pattern ──────────────────────────────────────────
def call_ai(prompt, max_tokens=2000):
    """Try each free model in order. On 429, wait and retry all models up to 3 rounds."""
    RETRY_ROUNDS = 3
    RETRY_WAIT   = 60

    for round_num in range(1, RETRY_ROUNDS + 1):
        for model in FREE_MODELS:
            try:
                payload = json.dumps({
                    "model": model,
                    "temperature": 0.4,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}]
                }).encode("utf-8")

                req = urllib.request.Request(
                    "https://openrouter.ai/api/v1/chat/completions",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "HTTP-Referer": "https://github.com",
                        "X-Title": "DevWorkflowAgent"
                    }
                )
                with urllib.request.urlopen(req, timeout=90) as response:
                    result = json.loads(response.read().decode("utf-8"))

                content = result["choices"][0]["message"]["content"]
                print(f"  ✅ Model used: {model}")
                return content

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    print(f"  ⏳ {model} rate-limited (429), trying next...")
                else:
                    print(f"  ⚠️  {model} failed: HTTP {e.code}, trying next...")
                time.sleep(5)
                continue
            except Exception as e:
                print(f"  ⚠️  {model} failed: {e}, trying next...")
                time.sleep(5)
                continue

        if round_num < RETRY_ROUNDS:
            print(f"  🔄 All models rate-limited (round {round_num}/{RETRY_ROUNDS}). Waiting {RETRY_WAIT}s...")
            time.sleep(RETRY_WAIT)

    raise ValueError("All models failed after 3 retry rounds — try again later")


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

    def gh_get(url):
        req = urllib.request.Request(url, headers=gh_headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    info = gh_get(f"https://api.github.com/repos/{owner}/{repo}")
    branch = info.get("default_branch", "main")
    print(f"  Branch: {branch}")

    tree_data = gh_get(f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
    tree = tree_data.get("tree", [])
    print(f"  Total items: {len(tree)}")

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
        try:
            req = urllib.request.Request(raw_url, headers=gh_headers)
            with urllib.request.urlopen(req, timeout=20) as r:
                files[path] = r.read().decode("utf-8")[:3000]
            print(f"  ✓ {path}")
        except Exception as e:
            print(f"  ✗ {path}: {e}")

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
    return call_ai(f"""You are a senior software engineer. Analyze this code from '{source}' and provide:
1. **Purpose** - What does this project do?
2. **Structure** - Key files, classes, functions
3. **Tech Stack** - Languages, libraries, frameworks
4. **Entry Points** - Where does execution start?

CODE:
{code[:4000]}""")


def step_debug(source, code):
    print("\n[STEP 2/4] Debugging and reviewing...")
    return call_ai(f"""You are a code reviewer. Review this code from '{source}' and identify:
1. **Bugs** - Logic errors, edge cases, crashes
2. **Security Issues** - Hardcoded secrets, injection risks
3. **Code Quality** - Bad practices, missing error handling
4. **Performance** - Inefficiencies, memory leaks

For each issue: describe the problem and suggest the fix.

CODE:
{code[:4000]}""")


def step_document(source, code):
    print("\n[STEP 3/4] Generating documentation...")
    return call_ai(f"""You are a technical writer. Generate documentation for '{source}':
1. **README Overview** - Project description, setup, usage
2. **Docstrings** - For the 3 most important functions
3. **API Reference** - Public functions with parameters and return values

CODE:
{code[:4000]}""")


def step_test(source, code):
    print("\n[STEP 4/4] Writing unit tests...")
    return call_ai(f"""You are a QA engineer. Write unit tests for '{source}':
1. Identify the 3-5 most important functions to test
2. Write pytest-compatible tests for each
3. Include happy path, edge cases, and error cases
4. Use mocking for external calls (requests, DB, etc.)

CODE:
{code[:4000]}""")


# ── Report ─────────────────────────────────────────────────────────────────────
def build_report(source, understanding, debug, docs, tests):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"""# 🤖 Dev Workflow Agent Report
**Source:** {source}
**Generated:** {now}

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

    print(f"\n  API Key present: yes")
    print(f"  Target: {target[:80]}")

    source, code = prepare_code_context(target)

    understanding = step_understand(source, code)
    time.sleep(8)

    debug = step_debug(source, code)
    time.sleep(8)

    docs = step_document(source, code)
    time.sleep(8)

    tests = step_test(source, code)

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
