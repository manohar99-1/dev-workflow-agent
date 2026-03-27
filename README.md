# 🤖 Dev Workflow Agent

An autonomous AI agent that analyzes codebases and assists with development workflows .

## What It Does

Given a GitHub repo URL or raw code, the agent autonomously runs 4 steps:

| Step | Task |
|------|------|
| 1️⃣ Understand | Summarizes purpose, structure, tech stack, entry points |
| 2️⃣ Debug | Finds bugs, security issues, code smells, performance problems |
| 3️⃣ Document | Generates README overview, docstrings, API reference |
| 4️⃣ Test | Writes pytest unit tests with edge cases and mocks |

Output is printed to terminal **and** saved as a Markdown report in `/reports/`.

---

## How to Run (GitHub Actions — no local setup needed)

### 1. Fork or create this repo on GitHub

### 2. Add your API key secrets
Go to: `Settings → Secrets → Actions → New repository secret`

**Option A: OpenRouter (recommended)**
- Name: `OPENROUTER_API_KEY`
- Value: your OpenRouter API key from https://openrouter.ai

**Option B: HuggingFace (free alternative)**
- Name: `HF_TOKEN`
- Value: your HuggingFace token from https://huggingface.co/settings/tokens

**No API key?** The agent will run in demo mode with rule-based analysis templates.

### 3. Run the agent
Go to: `Actions → Dev Workflow Agent → Run workflow`

Enter either:
- A GitHub repo URL: `https://github.com/owner/repo`
- Or paste code directly into the input box

### 4. Get your report
- View output live in the Actions log
- Download the report from **Artifacts** after the run
- Report is also committed back to `reports/` folder automatically

---

## Tech Stack

- **Python 3.11**
- **OpenRouter** (free LLaMA/Gemma models) OR **HuggingFace Inference API**
- **GitHub Actions** (runs on every trigger, no server needed)
- **GitHub API** (fetches repo files automatically)
- **Demo fallback** (works even without API keys)

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
