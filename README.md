# 🤖 Dev Workflow Agent

An autonomous code analysis agent that performs comprehensive rule-based analysis on any codebase.

## What It Does

Given a GitHub repo URL or raw code, the agent **analyzes each file independently** and runs 4 steps per file:

| Step | Task |
|------|------|
| 1️⃣ **Understand** | Extract structure, metrics, dependencies, functions, classes |
| 2️⃣ **Debug** | Detect bugs, security issues, quality problems, performance bottlenecks |
| 3️⃣ **Document** | Generate documentation templates with file purpose and API reference |
| 4️⃣ **Test** | Create pytest test case templates for each function |

**Key Feature**: Each file gets its own complete analysis section in the report.

Output is printed to terminal **and** saved as a detailed Markdown report in `/reports/`.

---

## How to Run (GitHub Actions — no local setup needed)

### 1. Fork this repo

### 2. Run the workflow
Go to: `Actions → Dev Workflow Agent → Run workflow`

Enter either:
- A GitHub repo URL: `https://github.com/owner/repo`
- Or paste code directly into the input box

### 3. Get your report
- View output live in the Actions log
- Download the report from **Artifacts** after the run
- Report is also committed back to `reports/` folder automatically

**No API keys needed** — uses 100% rule-based pattern matching and code analysis.

---

## Analysis Features

### Code Understanding
- Line counts (total, code, comments, ratio)
- Language detection
- Import/dependency extraction
- Function and class detection with line numbers
- Structure analysis

### Bug Detection
- TODO/FIXME markers
- Bare except clauses
- Incorrect None comparisons
- Common error patterns

### Security Analysis
- Hardcoded credentials detection
- Dangerous function usage (eval, exec)
- XSS vulnerabilities (dangerouslySetInnerHTML)
- Input validation issues

### Quality Checks
- Line length violations
- Deep nesting detection
- Code complexity indicators

### Performance Patterns
- Inefficient loop patterns
- Blocking operations
- Optimization opportunities

---

## Tech Stack

- **Python 3.11** (no external dependencies except urllib/json/re)
- **Rule-based pattern matching** (regex + heuristics)
- **GitHub Actions** (runs on every trigger, no server needed)
- **GitHub API** (fetches repo files automatically)

---

## Example Output

```
============================================================
  DEV WORKFLOW AGENT — LegalSeva Assignment 2
  RULE-BASED CODE ANALYSIS (NO LLM REQUIRED)
============================================================
  FOUND 10 FILES TO ANALYZE

──────────────────────────────────────────────────────────
  FILE 1/10: src/App.jsx
──────────────────────────────────────────────────────────
[ANALYZING] src/App.jsx
[DEBUGGING] src/App.jsx
[DOCUMENTING] src/App.jsx
[TESTING] src/App.jsx
  ✅ Analysis complete for src/App.jsx

... (repeats for each file) ...

✅ Full report saved to: reports/report_20260327_051234.md
📊 Total files analyzed: 10
```

---

*Built by Manohar Poleboina — LegalSeva AI Agent Developer Assignment*

---

## Example Output

```
DEV WORKFLOW AGENT — LegalSeva Assignment 2
============================================================
[INPUT] GitHub repo detected: https://github.com/owner/repo
  Fetching repo: owner/repo

[STEP 1/4] Understanding codebase...
[STEP 2/4] Debugging and reviewing...
[STEP 3/4] Generating documentation...
[STEP 4/4] Writing unit tests...

✅ Report saved to: reports/report_20260325_143022.md
```

---

*Built by Manohar Poleboina — LegalSeva AI Agent Developer Assignment*
