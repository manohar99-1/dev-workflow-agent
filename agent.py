"""
Dev Workflow Agent - LegalSeva Assignment 2
Autonomously analyzes code: understands, debugs, documents, tests, and reports.
Supports GitHub repo URL or direct code paste via ANALYSIS_TARGET secret/input.
"""

import os
import sys
import json
import re
import requests
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
MODEL = "mistralai/mistral-7b-instruct:free"
ANALYSIS_TARGET = os.getenv("ANALYSIS_TARGET", "")  # repo URL or raw code

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com",
    "X-Title": "DevWorkflowAgent"
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def call_llm(system: str, user: str) -> str:
    """Call OpenRouter LLM and return response text."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "max_tokens": 1500,
        "temperature": 0.2
    }
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=HEADERS,
        json=payload,
        timeout=60
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def fetch_github_repo(repo_url: str) -> dict:
    """
    Fetch Python files from a GitHub repo URL.
    Supports: https://github.com/owner/repo
    Returns dict of {filename: content}
    """
    # Parse owner/repo from URL
    match = re.search(r"github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$", repo_url)
    if not match:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")

    owner, repo = match.group(1), match.group(2)
    print(f"  Fetching repo: {owner}/{repo}")

    gh_headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        gh_headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    # Get default branch
    repo_info = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=gh_headers, timeout=30
    ).json()
    branch = repo_info.get("default_branch", "main")

    # Get file tree
    tree_resp = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
        headers=gh_headers, timeout=30
    ).json()

    files = {}
    for item in tree_resp.get("tree", []):
        path = item.get("path", "")
        # Grab Python files, JS files, or README — skip node_modules/vendor
        if item["type"] == "blob" and any(path.endswith(ext) for ext in [".py", ".js", ".ts", ".md"]):
            if any(skip in path for skip in ["node_modules", "vendor", ".min.", "dist/"]):
                continue
            if len(files) >= 10:  # cap at 10 files to stay within token limits
                break
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
            try:
                content = requests.get(raw_url, timeout=20).text
                files[path] = content[:3000]  # cap each file at 3000 chars
            except Exception:
                pass

    return files


def detect_input_type(target: str) -> str:
    """Return 'github' or 'code'."""
    if target.strip().startswith("https://github.com") or target.strip().startswith("http://github.com"):
        return "github"
    return "code"


def prepare_code_context(target: str) -> tuple[str, str]:
    """
    Returns (source_label, combined_code_string).
    """
    input_type = detect_input_type(target)

    if input_type == "github":
        print(f"\n[INPUT] GitHub repo detected: {target}")
        files = fetch_github_repo(target)
        if not files:
            raise ValueError("No analyzable files found in repo.")
        combined = ""
        for fname, content in files.items():
            combined += f"\n\n### FILE: {fname}\n```\n{content}\n```"
        return target, combined
    else:
        print("\n[INPUT] Direct code input detected.")
        return "Pasted Code", target


# ── Agent Nodes ───────────────────────────────────────────────────────────────
def step_understand(source: str, code: str) -> str:
    print("\n[STEP 1/4] Understanding codebase...")
    system = "You are a senior software engineer. Analyze code and give a clear, structured summary."
    user = f"""Analyze this code from '{source}' and provide:
1. **Purpose** – What does this code/project do?
2. **Structure** – Key files, classes, functions
3. **Tech Stack** – Languages, libraries, frameworks used
4. **Entry Points** – Where does execution start?

CODE:
{code[:4000]}"""
    return call_llm(system, user)


def step_debug(source: str, code: str) -> str:
    print("[STEP 2/4] Debugging and reviewing...")
    system = "You are a code reviewer specializing in finding bugs, security issues, and code smells."
    user = f"""Review this code from '{source}' and identify:
1. **Bugs** – Logic errors, edge cases, crashes
2. **Security Issues** – Hardcoded secrets, injection risks, unsafe calls
3. **Code Quality** – Bad practices, missing error handling, dead code
4. **Performance** – Inefficiencies, N+1 queries, memory leaks

For each issue: state the file/line if visible, describe the problem, and suggest the fix.

CODE:
{code[:4000]}"""
    return call_llm(system, user)


def step_document(source: str, code: str) -> str:
    print("[STEP 3/4] Generating documentation...")
    system = "You are a technical writer. Generate clear, professional documentation."
    user = f"""Generate documentation for the code from '{source}':
1. **README Overview** – Project description, setup steps, usage
2. **Function/Class Docstrings** – For the 3 most important functions/classes, write proper docstrings
3. **API Reference** – List public functions with parameters and return values

CODE:
{code[:4000]}"""
    return call_llm(system, user)


def step_test(source: str, code: str) -> str:
    print("[STEP 4/4] Writing unit tests...")
    system = "You are a QA engineer. Write thorough, runnable unit tests."
    user = f"""Write unit tests for the code from '{source}':
1. Identify the 3-5 most important functions to test
2. Write pytest-compatible unit tests for each
3. Include: happy path, edge cases, and error cases
4. Use mocking where external calls are needed (requests, DB, etc.)

CODE:
{code[:4000]}"""
    return call_llm(system, user)


# ── Report Builder ─────────────────────────────────────────────────────────────
def build_report(source: str, understanding: str, debug: str, docs: str, tests: str) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    report = f"""# 🤖 Dev Workflow Agent Report
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
    return report


# ── Main Pipeline ──────────────────────────────────────────────────────────────
def run_agent(target: str):
    print("=" * 60)
    print("  DEV WORKFLOW AGENT — LegalSeva Assignment 2")
    print("=" * 60)

    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY not set.")
        sys.exit(1)

    if not target:
        print("ERROR: ANALYSIS_TARGET not set. Provide a GitHub URL or code.")
        sys.exit(1)

    # Prepare code
    source, code = prepare_code_context(target)

    # Run all 4 steps
    understanding = step_understand(source, code)
    debug = step_debug(source, code)
    docs = step_document(source, code)
    tests = step_test(source, code)

    # Build report
    report = build_report(source, understanding, debug, docs, tests)

    # Terminal output
    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)

    # File output
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"reports/report_{timestamp}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n✅ Report saved to: {filename}")
    return filename


if __name__ == "__main__":
    target = ANALYSIS_TARGET or (sys.argv[1] if len(sys.argv) > 1 else "")
    run_agent(target)
