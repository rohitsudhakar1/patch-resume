# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Patch Resume is an AI-powered resume builder that converts existing resumes to clean LaTeX format and allows AI-powered improvements through an intuitive chat interface. The application is built with React/TypeScript frontend and Python FastAPI backend.

### Core Architecture

**Frontend Stack (React/TypeScript)**:
- **Vite** dev server with React/SWC plugin
- **Radix UI** component library with shadcn/ui wrapper
- **TanStack Query** for API state management
- **Tailwind CSS** for styling
- **React Router** for routing

**Backend Stack (Python/FastAPI)**:
- **FastAPI** web framework with Pydantic models
- **OpenAI GPT-4** for AI-powered resume improvements
- **Tectonic/LaTeX** for PDF compilation
- **PyPDF2/python-docx** for file ingestion
- **In-memory storage** with JSON backup (projects_backup.json)

### Key Data Flow

1. **File Upload** → Text extraction → AI parsing → LaTeX conversion → PDF generation
2. **AI Chat** → Instruction processing → Change generation → LaTeX modification → PDF update
3. **Change Management** → Visual diff → Accept/reject → LaTeX patching → Compilation

## Development Commands

### Quick Start
```bash
# Recommended: Docker setup
docker-compose up

# Manual setup
# Backend
python -m uvicorn backend.main:app --reload --port 8000
# Frontend
npm run dev
```

### Essential Commands
```bash
# Frontend development
npm install                    # Install dependencies
npm run dev                   # Start dev server (port 5173)
npm run build                 # Build for production
npm run build:dev             # Build in development mode
npm run lint                  # Run ESLint
npm run preview               # Preview production build

# Backend development
pip install -r requirements.txt  # Install Python dependencies
python -m uvicorn backend.main:app --reload --port 8000  # Start backend
python backend/main.py            # Alternative start method

# Docker commands
docker-compose up -d              # Start services in background
docker-compose down               # Stop all services
docker-compose logs backend       # View backend logs
docker-compose logs -f            # Follow all logs
```

### Testing & Quality
```bash
# Frontend
npm run lint                  # ESLint checking
# Note: No test suite currently configured

# Backend
# Note: No test suite currently configured - tests should be added
```

## Architecture Details

### Backend Service Layer (`backend/services/`)

The backend uses a modular service architecture:

- **`template_service.py`**: Generates LaTeX from structured resume data
- **`compile_service.py`**: Handles LaTeX → PDF compilation with Tectonic
- **`clean_parse_service.py`**: Parses unstructured resume text into structured data
- **`llm_service.py`**: Manages OpenAI API interactions for improvements
- **`patch_service.py`**: Handles change generation and application
- **`ingest_service.py`**: Processes uploaded resume files

### Frontend Component Architecture (`src/components/`)

- **`Workspace.tsx`**: Main container with PDF/LaTeX tab switching
- **`ChatPanel.tsx`**: AI chat interface with message history
- **`PDFViewer.tsx`**: Embedded PDF display with page indicators  
- **`LaTeXEditor.tsx`**: Source code editor with syntax highlighting
- **`ResumeEditor.tsx`**: Combined edit/preview interface
- **`ApplyBar.tsx`**: Change acceptance/rejection UI
- **`UploadModal.tsx`**: File upload and project initialization

### State Management Pattern

The application uses a hybrid state management approach:
- **SessionStorage**: Persists current project data (`currentProject`)
- **Custom Events**: Coordinates updates between components
- **TanStack Query**: Manages API calls and caching
- **Component State**: Local UI state and form handling

Key events:
- `projectUpdated`: Signals resume content changes
- `changesGenerated`: Passes AI-generated changes to editor

### API Integration Patterns

**Backend Base URL**: `http://localhost:8000`

Critical endpoints:
- `POST /ingest`: File upload and LaTeX conversion
- `POST /llm/patch`: Generate AI improvement suggestions  
- `POST /llm/chat`: Conversational AI interface
- `POST /project/recreate`: Restore project state
- `GET /artifact/pdf/{id}`: PDF compilation and serving

### LaTeX Processing Pipeline

1. **File Ingestion**: Extract text from PDF/DOCX/TXT
2. **AI Parsing**: Convert unstructured text to structured JSON
3. **Template Rendering**: Generate LaTeX using predefined templates
4. **Compilation**: Use Tectonic to create PDF with error handling
5. **Change Management**: Apply visual diffs and patch LaTeX source

## Environment Configuration

### Required Environment Variables
```bash
# Backend (.env file)
OPENAI_API_KEY=your_openai_api_key_here  # Required for AI features
DATABASE_URL=postgresql://...            # Optional (uses in-memory if not set)
REDIS_URL=redis://...                   # Optional (for caching)
SECRET_KEY=your_secret_key              # Optional (has default)

# Frontend (.env.local file)  
VITE_API_URL=http://localhost:8000      # Backend URL
```

### Service Dependencies
- **Tectonic**: LaTeX engine for PDF compilation
- **Tesseract**: OCR for PDF text extraction (if needed)
- **PostgreSQL**: Database (optional, uses in-memory storage)
- **Redis**: Caching layer (optional)

## Common Development Patterns

### Adding New AI Chat Features

1. Extend the system prompt in `backend/main.py` → `/llm/chat` endpoint
2. Update frontend `ChatPanel.tsx` to handle new response types
3. Add corresponding event handlers if UI updates are needed

### Extending Resume Templates

1. Modify `backend/services/template_service.py`
2. Update the LaTeX template structure
3. Test compilation with various resume formats

### Adding New File Types

1. Extend `extract_text_from_file()` in `backend/main.py`
2. Update `allowed_file_types` in config
3. Add corresponding import libraries to requirements.txt

### Debugging LaTeX Compilation Issues

1. Check `temp_latex/` directory for intermediate files
2. Enable debug logging in `compile_service.py` 
3. Test LaTeX manually with `tectonic` command
4. Use `sanitize_preamble()` function for malformed LaTeX

## Development Tips

- **Frontend hot reload**: Vite automatically reloads on file changes
- **Backend auto-reload**: uvicorn `--reload` flag enables Python hot reload
- **CORS setup**: Backend allows localhost:5173, :3000, :8080 origins
- **Project persistence**: Projects auto-save to `projects_backup.json`
- **Error handling**: Both frontend and backend have comprehensive error boundaries
- **OpenAI integration**: Uses GPT-4 for chat and GPT-4o-mini for parsing

## Port Configuration

- **Frontend**: 5173 (Vite dev server) or 8080 (configured in vite.config.ts)
- **Backend**: 8000 (FastAPI server)
- **PostgreSQL**: 5432 (if using Docker setup)
- **Redis**: 6379 (if using Docker setup)

## File Structure Notes

- **Backend**: Modular services pattern in `/backend/services/`
- **Frontend**: Component-based architecture in `/src/components/`
- **Storage**: Local file storage in `temp_latex/` and project backup in JSON
- **Configuration**: Environment files, Docker setup, and TypeScript configs at root