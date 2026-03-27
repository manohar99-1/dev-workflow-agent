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
GITHUB_TOKEN       = os.environ.get("GITHUB_TOKEN", "")
ANALYSIS_TARGET    = os.environ.get("ANALYSIS_TARGET", "")


def _call(url, headers, model, prompt, max_tokens):
    """Removed - using rule-based analysis instead."""
    pass


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


# ── Rule-Based Code Analysis (No LLM needed) ──────────────────────────────────
def analyze_code_structure(filename, code):
    """Analyze code structure using rule-based pattern matching."""
    lines = code.split('\n')
    total_lines = len(lines)
    code_lines = len([l for l in lines if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('//')])
    comment_lines = len([l for l in lines if l.strip().startswith('#') or l.strip().startswith('//')])
    
    # Detect language
    ext = filename.split('.')[-1] if '.' in filename else ''
    lang_map = {
        'py': 'Python', 'js': 'JavaScript', 'jsx': 'React/JSX', 
        'ts': 'TypeScript', 'tsx': 'React/TypeScript', 'md': 'Markdown'
    }
    language = lang_map.get(ext, ext.upper() if ext else 'Unknown')
    
    # Extract imports/dependencies
    imports = []
    for line in lines[:50]:  # Check first 50 lines
        if 'import ' in line or 'from ' in line or 'require(' in line:
            imports.append(line.strip())
    
    # Extract functions/classes
    functions = []
    classes = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('def ') and '(' in stripped:
            func_name = stripped.split('def ')[1].split('(')[0]
            functions.append(f"Line {i+1}: {func_name}()")
        elif stripped.startswith('function ') or 'const ' in stripped and '=>' in stripped:
            if 'function ' in stripped:
                func_name = stripped.split('function ')[1].split('(')[0].strip()
            else:
                func_name = stripped.split('const ')[1].split('=')[0].strip()
            functions.append(f"Line {i+1}: {func_name}()")
        elif stripped.startswith('class '):
            class_name = stripped.split('class ')[1].split('(')[0].split(':')[0].split('{')[0].strip()
            classes.append(f"Line {i+1}: {class_name}")
    
    return {
        'language': language,
        'total_lines': total_lines,
        'code_lines': code_lines,
        'comment_lines': comment_lines,
        'imports': imports[:10],  # First 10 imports
        'functions': functions[:15],  # First 15 functions
        'classes': classes[:10]  # First 10 classes
    }


def detect_issues(filename, code):
    """Detect common code issues using pattern matching."""
    issues = {
        'bugs': [],
        'security': [],
        'quality': [],
        'performance': []
    }
    
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        lower_line = line.lower()
        
        # Bug patterns
        if 'todo' in lower_line or 'fixme' in lower_line:
            issues['bugs'].append(f"Line {i}: TODO/FIXME comment found")
        if 'except:' in line or 'except :' in line:
            issues['bugs'].append(f"Line {i}: Bare except clause (catches all exceptions)")
        if '== None' in line or '!= None' in line:
            issues['bugs'].append(f"Line {i}: Use 'is None' instead of '== None'")
        
        # Security patterns
        if 'api_key' in lower_line or 'password' in lower_line or 'secret' in lower_line:
            if '=' in line and '"' in line:
                issues['security'].append(f"Line {i}: Potential hardcoded credential")
        if 'eval(' in line:
            issues['security'].append(f"Line {i}: Use of eval() is dangerous")
        if 'dangerouslySetInnerHTML' in line:
            issues['security'].append(f"Line {i}: XSS risk with dangerouslySetInnerHTML")
        
        # Quality patterns
        if len(line) > 120:
            issues['quality'].append(f"Line {i}: Line too long ({len(line)} chars)")
        if line.count('    ') > 5:  # Deep nesting
            issues['quality'].append(f"Line {i}: Deep nesting detected (refactor recommended)")
        
        # Performance patterns
        if '.append(' in line and ('for ' in lower_line or 'while ' in lower_line):
            issues['performance'].append(f"Line {i}: List append in loop (consider list comprehension)")
        if 'time.sleep(' in line:
            issues['performance'].append(f"Line {i}: Blocking sleep call")
    
    return issues


def generate_tests(filename, code):
    """Generate test cases based on code analysis."""
    analysis = analyze_code_structure(filename, code)
    tests = []
    
    # Generate tests for each function found
    for func in analysis['functions'][:5]:  # Top 5 functions
        func_name = func.split(': ')[1].replace('()', '')
        tests.append(f"""
def test_{func_name}_happy_path():
    \"\"\"Test {func_name} with valid inputs\"\"\"
    result = {func_name}(valid_test_input)
    assert result is not None
    # Add specific assertions based on expected behavior

def test_{func_name}_edge_cases():
    \"\"\"Test {func_name} with edge cases\"\"\"
    assert {func_name}(None) handles None appropriately
    assert {func_name}("") handles empty string
    assert {func_name}(0) handles zero value
""")
    
    return '\n'.join(tests) if tests else "No testable functions detected in this file."


# ── Agent Steps (Rule-Based) ───────────────────────────────────────────────────
def step_understand(filename, code):
    """Analyze code structure without LLM."""
    print(f"\n[ANALYZING] {filename}")
    analysis = analyze_code_structure(filename, code)
    
    report = f"""**Language**: {analysis['language']}

**Metrics**:
- Total Lines: {analysis['total_lines']}
- Code Lines: {analysis['code_lines']}
- Comment Lines: {analysis['comment_lines']}
- Comment Ratio: {(analysis['comment_lines']/analysis['total_lines']*100):.1f}%

**Dependencies** ({len(analysis['imports'])} found):
"""
    for imp in analysis['imports']:
        report += f"\n- `{imp}`"
    
    if not analysis['imports']:
        report += "\n- No imports detected"
    
    report += f"\n\n**Structure**:"
    
    if analysis['classes']:
        report += f"\n\nClasses ({len(analysis['classes'])}):"
        for cls in analysis['classes']:
            report += f"\n- {cls}"
    
    if analysis['functions']:
        report += f"\n\nFunctions ({len(analysis['functions'])}):"
        for func in analysis['functions']:
            report += f"\n- {func}"
    
    if not analysis['classes'] and not analysis['functions']:
        report += "\n- No classes or functions detected (likely config/data file)"
    
    return report


def step_debug(filename, code):
    """Find issues using pattern matching."""
    print(f"[DEBUGGING] {filename}")
    issues = detect_issues(filename, code)
    
    report = ""
    
    if issues['bugs']:
        report += f"**Potential Bugs** ({len(issues['bugs'])} found):\n"
        for bug in issues['bugs'][:10]:
            report += f"- {bug}\n"
    else:
        report += "**Potential Bugs**: None detected ✓\n"
    
    if issues['security']:
        report += f"\n**Security Concerns** ({len(issues['security'])} found):\n"
        for sec in issues['security'][:10]:
            report += f"- {sec}\n"
    else:
        report += "\n**Security Concerns**: None detected ✓\n"
    
    if issues['quality']:
        report += f"\n**Code Quality** ({len(issues['quality'])} found):\n"
        for qual in issues['quality'][:10]:
            report += f"- {qual}\n"
    else:
        report += "\n**Code Quality**: No issues detected ✓\n"
    
    if issues['performance']:
        report += f"\n**Performance** ({len(issues['performance'])} found):\n"
        for perf in issues['performance'][:10]:
            report += f"- {perf}\n"
    else:
        report += "\n**Performance**: No issues detected ✓\n"
    
    return report


def step_document(filename, code):
    """Generate documentation template."""
    print(f"[DOCUMENTING] {filename}")
    analysis = analyze_code_structure(filename, code)
    
    report = f"**File**: `{filename}`\n\n"
    report += f"**Purpose**: {analysis['language']} file with {len(analysis['functions'])} functions and {len(analysis['classes'])} classes.\n\n"
    
    if analysis['functions']:
        report += "**Key Functions**:\n"
        for func in analysis['functions'][:5]:
            func_name = func.split(': ')[1]
            report += f"\n- `{func_name}`: [Add description]\n"
            report += f"  - Parameters: [Document parameters]\n"
            report += f"  - Returns: [Document return value]\n"
    
    if analysis['classes']:
        report += "\n**Classes**:\n"
        for cls in analysis['classes'][:5]:
            cls_name = cls.split(': ')[1]
            report += f"\n- `{cls_name}`: [Add description]\n"
    
    return report


def step_test(filename, code):
    """Generate test templates."""
    print(f"[TESTING] {filename}")
    return generate_tests(filename, code)


# ── Report ─────────────────────────────────────────────────────────────────────
def build_file_report(filename, understanding, debug, docs, tests):
    """Build report for a single file."""
    return f"""
## 📄 File: `{filename}`

### 📋 Code Analysis
{understanding}

### 🐛 Issues & Quality Check
{debug}

### 📝 Documentation Template
{docs}

### 🧪 Test Cases
{tests}

---
"""


def build_final_report(source, file_reports, file_count):
    """Build the complete multi-file report."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    
    summary = f"""# 🤖 Dev Workflow Agent Report
**Source**: {source}
**Generated**: {now}
**Files Analyzed**: {file_count}

---

## 📊 Repository Summary

This repository contains **{file_count} analyzable files** across the following structure:
"""
    
    return summary + "\n" + file_reports + "\n" + "*Generated by Dev Workflow Agent — LegalSeva Assignment 2*"


# ── Main ───────────────────────────────────────────────────────────────────────
def run_agent(target: str):
    print("=" * 60)
    print("  DEV WORKFLOW AGENT — LegalSeva Assignment 2")
    print("  RULE-BASED CODE ANALYSIS (NO LLM REQUIRED)")
    print("=" * 60)

    if not target:
        print("ERROR: ANALYSIS_TARGET not set.")
        sys.exit(1)

    print(f"  Target: {target[:80]}\n")

    # Get all files
    if "github.com" in target or re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", target):
        print(f"[INPUT] GitHub repo detected: {target}")
        files = fetch_github_repo(target)
        source = target
    else:
        print("[INPUT] Direct code input detected.")
        files = {"pasted_code": target}
        source = "Pasted Code"
    
    if not files:
        print("ERROR: No files to analyze.")
        sys.exit(1)
    
    file_count = len(files)
    print(f"\n{'='*60}")
    print(f"  FOUND {file_count} FILES TO ANALYZE")
    print(f"{'='*60}\n")
    
    # Analyze each file independently
    all_file_reports = ""
    
    for idx, (filename, code) in enumerate(files.items(), 1):
        print(f"\n{'─'*60}")
        print(f"  FILE {idx}/{file_count}: {filename}")
        print(f"{'─'*60}")
        
        # Run 4 steps for this file
        understanding = step_understand(filename, code)
        debug = step_debug(filename, code)
        docs = step_document(filename, code)
        tests = step_test(filename, code)
        
        # Build report for this file
        file_report = build_file_report(filename, understanding, debug, docs, tests)
        all_file_reports += file_report
        
        print(f"  ✅ Analysis complete for {filename}")
    
    # Build final combined report
    final_report = build_final_report(source, all_file_reports, file_count)
    
    print("\n" + "=" * 60)
    print("  REPORT GENERATION COMPLETE")
    print("=" * 60)
    
    # Save report
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"reports/report_{timestamp}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(final_report)
    
    print(f"\n✅ Full report saved to: {filename}")
    print(f"📊 Total files analyzed: {file_count}")
    print(f"📄 Report size: {len(final_report)} characters")
    
    # Print summary to terminal
    print("\n" + "=" * 60)
    print("REPORT PREVIEW")
    print("=" * 60)
    print(final_report[:2000])
    print("\n... (see full report in file) ...")


if __name__ == "__main__":
    target = ANALYSIS_TARGET or (sys.argv[1] if len(sys.argv) > 1 else "")
    run_agent(target)
