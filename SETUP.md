# Resume Builder - Setup Instructions

This is a full-stack resume builder application with a React frontend and Python FastAPI backend that converts resumes to LaTeX and allows AI-powered editing.

## Prerequisites

- **Node.js** (v18 or higher)
- **Python** (v3.11 or higher)
- **PostgreSQL** (v15 or higher)
- **Redis** (v7 or higher)
- **Tectonic** (LaTeX engine)
- **Tesseract OCR** (for PDF text extraction)

## Quick Start with Docker

The easiest way to get started is using Docker:

1. **Clone and setup environment:**

   ```bash
   git clone <your-repo>
   cd patch-resume
   cp env.example .env
   ```

2. **Edit `.env` file with your settings:**

   ```bash
   # Required: Get your OpenAI API key
   OPENAI_API_KEY=your_openai_api_key_here

   # Optional: Customize other settings
   SECRET_KEY=your_secret_key_here
   ```

3. **Start all services:**

   ```bash
   docker-compose up
   ```

4. **Access the application:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Manual Setup

### 1. Install System Dependencies

**Ubuntu/Debian:**

```bash
sudo apt update
sudo apt install -y postgresql redis-server tectonic tesseract-ocr tesseract-ocr-eng
```

**macOS:**

```bash
brew install postgresql redis tectonic tesseract
```

**Windows:**

- Install PostgreSQL from https://www.postgresql.org/download/
- Install Redis from https://redis.io/download
- Install Tectonic from https://tectonic-typesetting.github.io/
- Install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki

### 2. Setup Database

```bash
# Create database
sudo -u postgres createdb resume_builder

# Or using psql:
psql -U postgres
CREATE DATABASE resume_builder;
\q
```

### 3. Setup Backend

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp env.example .env

# Edit .env with your settings
nano .env

# Start backend
python -m uvicorn backend.main:app --reload --port 8000
```

### 4. Setup Frontend

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/resume_builder

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI (Required)
OPENAI_API_KEY=your_openai_api_key_here

# Security
SECRET_KEY=your_secret_key_here

# Storage
STORAGE_TYPE=local
STORAGE_PATH=./storage

# LaTeX Compilation
TECTONIC_PATH=tectonic

# OCR
TESSERACT_PATH=tesseract
```

### Frontend Environment

Create a `.env.local` file in the root directory:

```bash
VITE_API_URL=http://localhost:8000
```

## Usage

### 1. Upload Resume

- Start the application
- Upload a PDF, DOCX, or TXT file
- The system will extract content and convert to LaTeX

### 2. Chat to Improve

- Use the chat panel to ask for improvements
- Examples:
  - "Make my experience section more impactful"
  - "Add quantifiable metrics to my achievements"
  - "Optimize for software engineering roles"

### 3. Review Changes

- Changes appear as green (additions) and red (removals)
- Accept or reject each change individually
- Switch between PDF and LaTeX views

### 4. Apply Changes

- Click "Apply accepted" to compile the changes
- The system will generate a new PDF
- Use "Discard all" to cancel changes

## API Endpoints

The backend provides these main endpoints:

- `POST /ingest` - Upload and process resume files
- `POST /llm/patch` - Generate AI-powered changes
- `POST /changes/apply` - Apply accepted changes
- `GET /project/{id}` - Get project state
- `GET /artifact/pdf/{id}` - Download PDF
- `GET /health` - Health check

See http://localhost:8000/docs for full API documentation.

## Architecture

### Frontend (React + TypeScript)

- Chat panel for AI interactions
- PDF/LaTeX workspace with change review
- Real-time change highlighting
- Accept/reject functionality

### Backend (Python + FastAPI)

- File processing with OCR support
- OpenAI o3 integration for AI suggestions
- LaTeX compilation with Tectonic
- PostgreSQL for data storage
- Redis for caching and queuing

### Key Features

- **Universal LaTeX Format**: Single, ATS-friendly template
- **SyncTeX Integration**: PDF ↔ LaTeX coordinate mapping
- **Change Review**: Visual diff system like Cursor
- **Auto-repair**: Intelligent LaTeX error fixing
- **Background Processing**: Non-blocking compilation

## Troubleshooting

### Common Issues

1. **"Tectonic not found"**

   - Ensure Tectonic is installed and in PATH
   - Check `TECTONIC_PATH` in .env

2. **"Database connection failed"**

   - Verify PostgreSQL is running
   - Check database credentials in .env

3. **"OpenAI API error"**

   - Verify your API key is correct
   - Check you have sufficient credits

4. **"File upload fails"**
   - Check file size limits (10MB default)
   - Ensure file type is supported (.pdf, .docx, .txt)

### Logs

Backend logs are available in the console where you started the server.

Frontend logs are in the browser developer console.

## Development

### Project Structure

```
patch-resume/
├── backend/                 # Python FastAPI backend
│   ├── main.py             # Main application
│   ├── database.py         # Database models
│   ├── config.py           # Configuration
│   ├── models.py           # Pydantic models
│   └── services/           # Business logic
├── src/                    # React frontend
│   ├── components/         # UI components
│   ├── lib/               # Utilities
│   └── pages/             # Pages
├── requirements.txt        # Python dependencies
├── package.json           # Node.js dependencies
├── docker-compose.yml     # Docker setup
└── Dockerfile            # Backend container
```

### Adding Features

1. **Backend**: Add new endpoints in `backend/main.py`
2. **Frontend**: Add new components in `src/components/`
3. **Database**: Update models in `backend/database.py`

## Production Deployment

For production deployment:

1. Set `NODE_ENV=production` and `DEBUG=false`
2. Use a production database (AWS RDS, etc.)
3. Configure proper Redis instance
4. Set up file storage (S3, etc.)
5. Use a reverse proxy (nginx)
6. Enable HTTPS

## Support

If you encounter issues:

1. Check the logs for error messages
2. Verify all dependencies are installed
3. Ensure environment variables are set correctly
4. Try the Docker setup for a clean environment
