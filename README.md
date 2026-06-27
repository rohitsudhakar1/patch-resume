# Patch Resume

Upload any resume → **Claude** turns it into clean, ATS-ready LaTeX → improve it by chatting or by pasting a job description → condense it to exactly one page → export.

The idea underneath it: **a safe way to let an LLM edit a structured document.** The model proposes a change, the system **validates it against a hard check** (it has to compile, it has to be one page), and a human approves — so nothing broken ever ships.

![Status](https://img.shields.io/badge/status-active-brightgreen)
![Python](https://img.shields.io/badge/python-3.11+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)
![React](https://img.shields.io/badge/React-18-blue)
![Claude](https://img.shields.io/badge/LLM-Claude%20(Anthropic)-7c5cff)

---

## What it does

- **📤 Upload** a PDF, DOCX, or TXT resume → text is extracted and **Claude (`claude-opus-4-8`)** rewrites it into clean, ATS-friendly LaTeX → live PDF preview.
- **💬 Chat to edit** in plain English. Every AI edit is **test-compiled before it's accepted**; if the LaTeX fails to build, the compiler error is fed back to Claude and auto-repaired.
- **🎯 Tailor to a job description.** Paste a JD and it rewrites the summary, bullets, and skills to match the role — **truthfully** (it won't invent skills or employers).
- **📃 Fit to 1 page.** One click runs a real loop: compile → count PDF pages → if it's over one, ask Claude to condense (tighten wording, drop the weakest bullet, never merge into run-ons) → recompile → repeat until it's exactly one page.

The thread that ties it together: **structured generation → hard validation → human-in-the-loop.**

---

## Tech stack

| Layer | Stack |
|---|---|
| Backend | Python, FastAPI, **Anthropic SDK** (`claude-opus-4-8`) |
| Front-end | React + TypeScript + Vite + Tailwind / shadcn-ui |
| PDF | **Tectonic** (LaTeX → PDF), **PyPDF2** (page counting) |
| Parsing | PyPDF2 (PDF), python-docx (DOCX) |

State is kept in-memory with a JSON backup — **no database, Redis, or Docker required** to run it.

---

## Quick start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **Tectonic** (the LaTeX engine) installed and on your `PATH` — https://tectonic-typesetting.github.io
- An **Anthropic API key** — https://console.anthropic.com

### 1. Clone + configure
```bash
git clone https://github.com/rohitsudhakar1/patch-resume.git
cd patch-resume
cp env.example .env
# open .env and set ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Backend (terminal 1)
```bash
pip install -r requirements.txt
python -m uvicorn main:app --app-dir backend --port 8000
```
> On Windows, prefix with `set PYTHONUTF8=1` (or `$env:PYTHONUTF8="1"` in PowerShell) so the debug logs render.

### 3. Front-end (terminal 2)
```bash
npm install
npm run dev
```

Open **http://localhost:8080**. (Backend API + docs at `http://localhost:8000/docs`.)

---

## How to use
1. **Drag in a resume** (or use the included `test_resume.txt`) → clean PDF renders on the right.
2. **Type an edit** in the chat — e.g. *"tighten my summary and add a metric."* The change is validated, then the PDF updates.
3. **Tailor to a job description** — click the button, paste a JD (try `test_jd.txt`), hit **Tailor my resume**.
4. **Fit to 1 page** — click the toolbar button; it loops until the resume is a single page.

---

## How it works (the loops)

**Edit / tailor — validate then auto-repair** (`backend/main.py`):
```
Claude rewrites the LaTeX  →  test-compile it
   ├─ compiles?  → accept, update the project, re-render the PDF
   └─ fails?     → send the compiler error back to Claude → retry (up to 3x)
```

**Fit to one page — a real agentic loop** (`/llm/fit-one-page`):
```
compile → count pages (PyPDF2)
   ├─ pages == 1 → done
   └─ pages > 1  → ask Claude to condense → recompile → count again  (cap: 5 iterations)
```

Every AI call goes through a single helper, `claude_complete()` — the model's output is always treated as a proposal, never trusted blind.

---

## Project structure
```
patch-resume/
├── backend/
│   ├── main.py              # FastAPI app: ingest, chat-edit, tailor, fit-one-page, compile
│   ├── config.py            # settings
│   └── services/
│       ├── template_service.py  # structured data → clean ATS LaTeX
│       └── compile_service.py   # LaTeX → PDF via Tectonic
├── src/                     # React front-end (ChatPanel, PDFViewer, Workspace, …)
├── test_resume.txt          # sample resume input
├── test_jd.txt              # sample job description
├── env.example              # copy to .env and add your key
└── requirements.txt
```

## Key endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/ingest` | Upload a resume → parse → LaTeX |
| `POST` | `/llm/chat` | Natural-language edit (validated) |
| `POST` | `/llm/fit-one-page` | Loop-condense to a single page |
| `GET`  | `/artifact/pdf/{id}` | Compiled PDF |
| `GET`  | `/health` | Health check |

## Notes
- The AI features require `ANTHROPIC_API_KEY`. Without it, ingest falls back to a template render but chat/tailor/fit are disabled.
- Image-only (scanned) PDFs need Tesseract for OCR; text-based PDFs work out of the box.

## License
MIT — see [LICENSE](LICENSE).
