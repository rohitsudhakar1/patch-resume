# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Patch Resume** is an AI-powered resume builder that converts uploaded resumes (PDF/DOCX/TXT) to LaTeX format and enables iterative improvements through a chat interface. The application provides real-time PDF preview, visual change tracking (like Cursor's diff view), and professional formatting.

## Tech Stack

- **Frontend**: React 18 + TypeScript, Vite, shadcn/ui components, Tailwind CSS
- **Backend**: Python 3.11+ FastAPI, OpenAI API (GPT-4)
- **LaTeX**: Multiple compiler support (Tectonic, pdflatex, xelatex, lualatex)
- **State**: In-memory project storage with file-based backup (`projects_backup.json`)

## Development Commands

### Frontend
```bash
npm run dev          # Start Vite dev server (port 5173)
npm run build        # Production build
npm run build:dev    # Development build
npm run preview      # Preview production build
npm run lint         # Run ESLint
```

### Backend
```bash
# Start development server (from project root)
python -m uvicorn backend.main:app --reload --port 8000

# Or use PowerShell script
.\start_services.ps1
```

### Docker
```bash
docker-compose up    # Start all services (PostgreSQL, Redis, backend)
```

### Environment Setup
- Copy `env.example` to `.env` and add your OpenAI API key
- Required: `OPENAI_API_KEY=your_key_here`

## Architecture

### Backend Services (Modular Design)

The backend follows a service-oriented architecture with clear separation of concerns:

- **`backend/main.py`**: FastAPI application with comprehensive LaTeX cleaning system (`clean_latex_content`, `BAD_LATEX_PATTERNS`) and core endpoints
- **`backend/services/clean_parse_service.py`**: Parses raw resume text into structured data (name, experience, education, projects, skills)
- **`backend/services/template_service.py`**: Renders structured data to ATS-friendly LaTeX with professional formatting
- **`backend/services/compile_service.py`**: Multi-engine LaTeX compiler with fallback support (Tectonic → pdflatex → xelatex → lualatex)

### Key Backend Functions

**LaTeX Processing Pipeline:**
1. `extract_text_from_file()` - Extracts text from PDF/DOCX/TXT uploads
2. `convert_to_latex_with_chat()` - Uses OpenAI GPT-4o-mini to parse resume text into structured JSON
3. `template_service.render_resume()` - Converts structured data to LaTeX using professional template
4. `clean_latex_content()` - Comprehensive cleaning with 3-pass iterative fixing (removes malformed commands, fixes braces, validates structure)
5. `compile_service.compile_latex()` - Compiles to PDF with multi-engine fallback

**Change Management:**
- `generate_patch()` - Uses OpenAI GPT-4 to generate targeted changes based on user instructions
- `validate_change_scope()` - Prevents overly broad changes for simple requests (e.g., name changes)
- `validate_and_improve_changes()` - Expands partial removals to full experience blocks
- `apply_changes_to_latex()` - Applies accepted changes with validation and cleaning
- `fix_compilation_errors()` - Sends failed LaTeX back to AI for fixing (max 3 attempts)

**AI Error Recovery:**
- If PDF compilation fails, system automatically sends error + LaTeX to GPT-4 for fixing
- Supports up to 3 fix attempts before falling back to original content

### Frontend Components

- **`src/components/Workspace.tsx`**: Main container with PDF/LaTeX tab switching
- **`src/components/PDFViewer.tsx`**: Live PDF preview with page indicators and auto-refresh
- **`src/components/LaTeXEditor.tsx`**: Syntax-highlighted LaTeX editor with change visualization
- **`src/components/ChatPanel.tsx`**: AI chat interface with auto-apply for simple changes
- **`src/components/ResumeEditor.tsx`**: Top-level orchestrator component

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ingest` | Upload resume file → extract text → convert to LaTeX → create project |
| `POST` | `/llm/patch` | Generate AI-powered changes for instruction + project |
| `POST` | `/llm/chat` | Chat with AI assistant (auto-applies simple changes like name/email) |
| `POST` | `/changes/apply` | Apply accepted changes to project |
| `POST` | `/project/recreate` | Recreate project from frontend data (state sync) |
| `GET` | `/artifact/pdf/{id}` | Download/preview PDF (triggers compilation with cleaning + AI recovery) |
| `GET` | `/projects/status` | Debug endpoint showing all projects in memory |
| `GET` | `/health` | Health check |

### Data Flow

1. **Upload**: User uploads resume → `/ingest` → `extract_text_from_file()` → `convert_to_latex_with_chat()` (AI parsing) → `template_service.render_resume()` → project created
2. **Chat**: User sends message → `/llm/chat` → auto-applies simple changes or returns suggestions → frontend updates
3. **Patch**: User request → `/llm/patch` → GPT-4 generates changes with validation → frontend displays diff → user accepts/rejects → `/changes/apply`
4. **Compile**: Frontend requests PDF → `/artifact/pdf/{id}` → `clean_latex_content()` → `compile_service.compile_latex()` → AI recovery if errors → PDF returned

### State Management

- **Backend**: In-memory `projects` dict persisted to `projects_backup.json` on changes
- **Frontend**: React state in `ResumeEditor` component, no global state library
- **Sync**: Frontend can recreate backend state via `/project/recreate` if needed

## Important Implementation Details

### LaTeX Cleaning System

The backend implements a **3-pass iterative cleaning system** (`clean_latex_content()`) that:
- Removes malformed commands (e.g., `ewcommand` without backslash)
- Fixes incomplete braces and commands
- Ensures proper document structure
- Validates brace matching and auto-fixes mismatches
- Returns issues found for debugging

**Always clean LaTeX before compilation** - the system runs cleaning at:
1. Initial project creation
2. Before applying changes
3. Before PDF compilation
4. After AI fixes

### Change Validation

Two critical validation steps prevent unintended edits:

1. **`validate_change_scope()`**: For simple changes (name, email, phone), blocks changes spanning >5 lines or containing structural LaTeX
2. **`validate_and_improve_changes()`**: For removals, expands partial blocks to include full experience entries (from `\textbf{Company}` through `\end{itemize}`)

### AI Prompting Strategy

The system uses **different models for different tasks**:
- **GPT-4o-mini** (fast, cheap): Resume parsing, text extraction
- **GPT-4** (accurate, expensive): Change generation, error fixing, chat responses

**Change generation prompt includes**:
- Explicit rules for minimal changes (single-line replacements for simple edits)
- Examples showing correct line ranges and content structure
- Special handling for name changes (must always generate a change)
- PDF region coordinates for visual highlighting (placeholder system)

### LaTeX Compiler Fallback

The `CompileService` tries compilers in order:
1. **Tectonic** (modern, Overleaf-like, self-contained)
2. **pdflatex** (standard LaTeX)
3. **xelatex** (Unicode support)
4. **lualatex** (advanced features)

Check compiler availability in `compile_service.py:_get_compilers()`. On Windows, looks for MiKTeX in `~/AppData/Local/Programs/MiKTeX/` and Tectonic in `~/scoop/shims/`.

## Testing & Debugging

### Test Files in Root
- `test_functionality.py` - Full end-to-end tests
- `test_patch.py` - Change generation tests
- `test_name_fix.py` - Name change validation tests
- `debug_test.py`, `debug_500.py` - Debug scripts

### Debug Output
Backend prints extensive debug logs with emoji prefixes:
- 🔍 Inspection/analysis
- 🤖 AI/OpenAI operations
- 📄 LaTeX content
- ✅ Success
- ❌ Errors
- 🔧 Fixes/validation
- 💾 Persistence

Watch backend console when developing - it shows the full pipeline execution.

### Common Issues

**PDF not generating**: Check backend logs for LaTeX errors → ensure `clean_latex_content()` is called → verify compiler availability → check AI recovery logs

**Changes not applying**: Ensure project exists in backend (`/projects/status`) → check if change validation blocked it (look for 🔧 DEBUG logs) → verify line numbers match LaTeX content

**Chat not auto-applying**: Check `looks_like_update` logic in `/llm/chat` → verify project exists in backend before calling `generate_patch()` → ensure `apply_changes_to_latex()` succeeds

## Git History Notes

Recent commits show:
- Professional LaTeX preamble preservation
- AI chat formatting improvements
- Scrollbar styling polish
- UI modernization
- Parse and template service additions

The codebase has evolved from a monolithic approach to modular services architecture.

## API Key Security

The OpenAI API key is loaded from the `OPENAI_API_KEY` environment variable (see `backend/.env`, which is gitignored). Never commit API keys to version control.