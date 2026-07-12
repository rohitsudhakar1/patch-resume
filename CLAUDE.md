# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Patch Resume** is an AI-powered resume builder: upload a resume (PDF/DOCX/TXT), Claude converts it to clean ATS-friendly LaTeX, then improve it by chatting, tailoring it to a pasted job description, or condensing it to exactly one page — with a live PDF preview throughout.

The core architecture: **the model proposes, a deterministic gate validates, a human approves.** Every AI-generated document must pass a real compile (and, for fit-to-one-page, a real page count) before it is persisted. Validation fails closed: a candidate that never compiles is discarded and the last-known-good document is kept.

## Tech Stack

- **Frontend**: React 18 + TypeScript, Vite (port 8080), shadcn/ui, Tailwind CSS
- **Backend**: Python 3.11+ FastAPI (port 8000), **Anthropic SDK — Claude (`claude-opus-4-8`)**
- **PDF**: Tectonic (preferred; strict mode — it IS the validation gate), falling back to latexmk/xelatex/pdflatex/lualatex if installed. PyPDF2 for page counting and PDF text extraction.
- **State**: In-memory `projects` dict persisted to `projects_backup.json`. No database, Redis, or Docker required.

## Development Commands

### Backend (from repo root)
```bash
pip install -r requirements.txt
python -m uvicorn main:app --app-dir backend --port 8000
```
Run with `--app-dir backend` (not `backend.main:app`) — `main.py` imports `services...` relative to `backend/`. On Windows, set `PYTHONUTF8=1` first (emoji debug logs crash under cp1252).

### Frontend
```bash
npm install
npm run dev          # Vite dev server on port 8080 (set in vite.config.ts)
npm run build        # Production build
npm run lint         # ESLint
```

### Environment
- Copy `env.example` to `.env` and set `ANTHROPIC_API_KEY=sk-ant-...`
- `.env` must be UTF-8 without BOM (a UTF-16 BOM breaks `load_dotenv()` → 500s on AI calls)
- Without a key, ingest falls back to template-only rendering; chat/tailor/fit are disabled

## Architecture

### Every AI call goes through one helper

`claude_complete(system, user, max_tokens)` in `backend/main.py` (~line 40) is the single chokepoint for AI calls (parse, patch, repair, condense). The one exception is `/llm/chat`, which calls the SDK directly because it needs multi-turn history. Model output is always treated as a **proposal** — callers must validate before persisting.

### The three loops that matter (`backend/main.py`)

1. **Ingest pipeline** (`/ingest`): extract text (`extract_text_from_file`) → Claude parses it into a **fixed JSON schema** (`convert_to_latex_with_chat`) → deterministic template renders LaTeX (`template_service.render_resume`). The model never writes the initial LaTeX freehand — AI for understanding, code for formatting. If AI parsing fails, `CleanParseService` (regex-only) fills the same schema.

2. **Validate + auto-repair** (`fix_compilation_errors`, used by `/llm/chat`): every AI edit is test-compiled; on failure the **real compiler error** is sent back to Claude for repair, up to 3 attempts. Returns `(latex, compiled_ok)` — on `compiled_ok=False` the edit is **rejected and not persisted** (fail closed), and the user is told nothing was changed.

3. **Fit to one page** (`/llm/fit-one-page`): compile → count pages with PyPDF2 → if >1, ask Claude to condense (tighten wording first, then drop weakest content, then shrink spacing; bullets stay atomic) → recompile → repeat, cap 5 iterations. The exit condition is the **measured page count**, never the model's own claim. Keeps the last compiling draft; never persists a non-compiling one.

### Services (`backend/services/`)

- **`template_service.py`** — structured JSON → ATS-friendly LaTeX. Hand-written, known-good preamble (`_get_preamble`); `_escape_latex()` escapes all user text (user data is data, never code).
- **`compile_service.py`** — LaTeX → PDF. Finds compilers via PATH (`shutil.which`) with legacy Windows paths as fallback; 30s subprocess timeout; success requires exit code 0 AND the PDF existing. On failure, returns the extracted compiler error (lines starting with `!` / containing `error`) so the repair loop gets a concrete signal. **Never pass `-Z continue-on-errors` to Tectonic** — it would let broken LaTeX through the gate with exit code 0.
- **`clean_parse_service.py`** — regex-only fallback parser. Never invents content: unknown titles/degrees/dates/GPAs stay blank.

### LaTeX cleaning (`clean_latex_content`, main.py)

A static scrubber run before every compile: removes known corruption (the `ewcommand` family — `\n` of `\newcommand` eaten as a JSON escape), fixes incomplete commands, balances braces. Up to 3 passes, stops when stable. Deliberately conservative: a negative lookbehind protects valid `\newcommand`, and adjacent braces are never collapsed (both were historical self-inflicted bugs). The compiler remains the source of truth; cleaning just saves repair round-trips.

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ingest` | Upload resume → extract → AI parse to JSON → template → project |
| `POST` | `/llm/chat` | Natural-language edit; whole-document rewrite validated by the compile gate (fail-closed) |
| `POST` | `/llm/fit-one-page` | Compile → count pages → condense loop until exactly 1 page |
| `POST` | `/llm/patch` | Legacy line-diff change generation (not the primary UI flow) |
| `POST` | `/changes/apply` | Legacy — accepts change list (stub) |
| `POST` | `/project/recreate` | Rehydrate backend state from the frontend's copy |
| `GET` | `/artifact/pdf/{id}` | Clean → compile → AI recovery on failure → PDF |
| `GET` | `/projects/status` | Debug: all projects in memory |
| `GET` | `/health` | Health check |

### Frontend (`src/components/`)

- **`ResumeEditor.tsx`** — orchestrator; owns `currentProject`, mirrors it to `sessionStorage`, undo/redo via `useVersionHistory` (every change is snapshotted — this is the human-approval layer).
- **`ChatPanel.tsx`** — chat UI; **Tailor-to-JD lives here** as a canned instruction sent through `/llm/chat` (a feature that is purely a new prompt on existing rails).
- **`PDFViewer.tsx`** — always-mounted iframe (unmounting it deadlocked the loading state historically) with cache-busted URLs; a PDF request is what triggers backend compilation.
- **`LaTeXEditor.tsx`** — manual editing; syncs to backend via `/project/recreate`.
- Components communicate via `window` CustomEvents (`projectUpdated`, `pdfRegenerate`) — no global state library.

## Important invariants

- **Always clean LaTeX before compiling** (`clean_latex_content`), and always compile before persisting AI output.
- **The gate fails closed**: never store a document that didn't compile. `fit_one_page` reverts to `last_good`; `/llm/chat` rejects the edit and says so.
- **Hard gates vs. soft guardrails**: "it compiles" and "it's one page" are hard, deterministic checks. "Stay truthful, don't invent experience" is a prompt-level guardrail plus human review — do not confuse the two.
- **Never fabricate resume content anywhere**, including fallback parsers — blank is honest, invented is not.
- Test compiles use suffixed project IDs (`{id}_test`, `{id}_fit`) so they never clobber the served PDF.

## Debugging

Backend prints emoji-prefixed debug logs (🔍 analysis, 🤖 AI calls, 📄 LaTeX, ✅ success, ❌ errors, 🔧 fixes, 💾 persistence). Watch the backend console — it shows the full pipeline execution including compile attempts and repair rounds.

Common issues:
- **PDF not generating**: check backend logs for the compiler error → verify a LaTeX engine is installed (`tectonic` on PATH) → check AI recovery logs.
- **AI calls 500**: `ANTHROPIC_API_KEY` missing or `.env` has a BOM.
- **Windows**: `PYTHONUTF8=1`; don't POST large LaTeX bodies via PowerShell `Invoke-RestMethod` (encoding mangling) — use the browser or Python.

## API Key Security

The Anthropic API key is loaded from the `ANTHROPIC_API_KEY` environment variable (`.env` is gitignored). Never commit API keys.
