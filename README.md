# 📄 Patch Resume - AI-Powered Resume Builder

A modern, full-stack resume builder that converts your existing resume to clean LaTeX format and allows AI-powered improvements through an intuitive chat interface. Built with React, TypeScript, and Python FastAPI.

![Resume Builder Demo](https://img.shields.io/badge/Status-Active-brightgreen)
![React](https://img.shields.io/badge/React-18.3.1-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-5.8.3-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green)

## ✨ Features

### 🎯 **Core Functionality**

- **📤 Universal Upload**: Support for PDF, DOCX, and TXT files
- **🔄 LaTeX Conversion**: Automatic conversion to clean, ATS-friendly LaTeX format
- **🤖 AI-Powered Editing**: Chat with AI to improve your resume content
- **👁️ Visual Change Review**: See additions (green) and removals (red) like Cursor IDE
- **📄 Live PDF Preview**: Real-time PDF generation with page indicators
- **⚡ Real-time Sync**: Changes reflect instantly across all views

### 🎨 **User Experience**

- **🌙 Dark Theme**: Modern, professional dark UI
- **📱 Responsive Design**: Works on desktop and mobile
- **⌨️ Keyboard Shortcuts**: Efficient workflow with hotkeys
- **🔄 Auto-save**: Never lose your work
- **📊 Progress Tracking**: Visual feedback for all operations

### 🔧 **Technical Features**

- **🛠️ Multi-Compiler Support**: Tectonic, pdflatex, xelatex, lualatex
- **🐳 Docker Ready**: One-command setup with Docker Compose
- **📦 Package Management**: Clean dependency management
- **🔒 Type Safety**: Full TypeScript coverage
- **⚡ Performance**: Optimized rendering and compilation

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd patch-resume

# Copy environment file
cp env.example .env

# Edit .env with your OpenAI API key
# OPENAI_API_KEY=your_openai_api_key_here

# Start all services
docker-compose up
```

**Access the application:**

- 🌐 Frontend: http://localhost:5173
- 🔧 Backend API: http://localhost:8000
- 📚 API Docs: http://localhost:8000/docs

### Option 2: Manual Setup

<details>
<summary>Click to expand manual setup instructions</summary>

#### Prerequisites

- **Node.js** (v18 or higher)
- **Python** (v3.11 or higher)
- **OpenAI API Key** (required for AI features)

#### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp env.example .env
# Edit .env with your OpenAI API key

# Start backend
python -m uvicorn backend.main:app --reload --port 8000
```

#### Frontend Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

</details>

## 🎯 How to Use

### 1. **Upload Your Resume**

- Drag and drop or click to upload PDF, DOCX, or TXT files
- The system automatically extracts content and converts to LaTeX
- Skip upload to start with a blank resume

### 2. **Chat to Improve**

Use natural language to request improvements:

- _"Make my experience section more impactful"_
- _"Add quantifiable metrics to my achievements"_
- _"Optimize for software engineering roles"_
- _"Fix grammar and improve clarity"_

### 3. **Review Changes**

- **Green highlights**: New content to be added
- **Red highlights**: Content to be removed
- **Accept/Reject**: Click individual changes or use "Accept All"
- **Switch Views**: Toggle between PDF preview and LaTeX source

### 4. **Export Results**

- Changes are automatically applied to your resume
- Download the updated PDF
- Copy the LaTeX source for further editing

## 🏗️ Architecture

### Frontend (React + TypeScript)

```
src/
├── components/           # UI Components
│   ├── ChatPanel.tsx    # AI chat interface
│   ├── LaTeXEditor.tsx  # LaTeX source editor
│   ├── PDFViewer.tsx    # PDF preview with page indicators
│   ├── Workspace.tsx    # Main workspace container
│   └── ui/              # Reusable UI components
├── lib/                 # Utilities and API client
└── pages/               # Application pages
```

### Backend (Python + FastAPI)

```
backend/
├── main.py              # FastAPI application
├── models.py            # Pydantic data models
├── database.py          # Database configuration
├── config.py            # Application settings
└── services/            # Business logic
    ├── llm_service.py   # OpenAI integration
    ├── patch_service.py # Change management
    └── compile_service.py # LaTeX compilation
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```bash
# Required: OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Customize settings
SECRET_KEY=your_secret_key_here
DEBUG=true
```

### LaTeX Compilation

The system supports multiple LaTeX compilers in order of preference:

1. **Tectonic** (recommended for Overleaf-like experience)
2. **pdflatex** (standard LaTeX)
3. **xelatex** (Unicode support)
4. **lualatex** (advanced features)

## 📚 API Documentation

### Main Endpoints

| Method | Endpoint             | Description                     |
| ------ | -------------------- | ------------------------------- |
| `POST` | `/ingest`            | Upload and process resume files |
| `POST` | `/llm/patch`         | Generate AI-powered changes     |
| `POST` | `/project/recreate`  | Create/update project           |
| `GET`  | `/artifact/pdf/{id}` | Download generated PDF          |
| `GET`  | `/projects/status`   | Check project status            |
| `GET`  | `/health`            | Health check                    |

### Example API Usage

```bash
# Upload a resume
curl -X POST "http://localhost:8000/ingest" \
  -F "file=@resume.pdf"

# Get AI suggestions
curl -X POST "http://localhost:8000/llm/patch" \
  -H "Content-Type: application/json" \
  -d '{"project_id": "123", "message": "Make it more ATS-friendly"}'

# Download PDF
curl -X GET "http://localhost:8000/artifact/pdf/123" \
  --output resume.pdf
```

## 🛠️ Development

### Project Structure

```
patch-resume/
├── backend/                 # Python FastAPI backend
│   ├── main.py             # Main application
│   ├── models.py           # Pydantic models
│   ├── database.py         # Database configuration
│   ├── config.py           # App settings
│   └── services/           # Business logic
├── src/                    # React frontend
│   ├── components/         # UI components
│   ├── lib/               # Utilities
│   └── pages/             # Application pages
├── temp_latex/            # LaTeX compilation workspace
├── requirements.txt        # Python dependencies
├── package.json           # Node.js dependencies
├── docker-compose.yml     # Docker setup
└── Dockerfile            # Backend container
```

### Available Scripts

```bash
# Frontend
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build
npm run lint         # Run ESLint

# Backend
python -m uvicorn backend.main:app --reload  # Start development server
```

### Adding Features

1. **Backend**: Add new endpoints in `backend/main.py`
2. **Frontend**: Add new components in `src/components/`
3. **Database**: Update models in `backend/models.py`
4. **Styling**: Use Tailwind CSS classes

## 🐛 Troubleshooting

### Common Issues

<details>
<summary><strong>PDF not generating</strong></summary>

- Check if LaTeX compilers are installed
- Verify the LaTeX code is valid
- Check backend logs for compilation errors
- Try the simplified LaTeX version

</details>

<details>
<summary><strong>AI features not working</strong></summary>

- Verify your OpenAI API key is correct
- Check you have sufficient API credits
- Ensure the API key has the required permissions

</details>

<details>
<summary><strong>File upload fails</strong></summary>

- Check file size (max 10MB)
- Ensure file type is supported (.pdf, .docx, .txt)
- Verify backend is running on port 8000

</details>

<details>
<summary><strong>Changes not applying</strong></summary>

- Refresh the page and try again
- Check browser console for errors
- Ensure project is properly created in backend

</details>

### Debug Mode

Enable debug logging by setting `DEBUG=true` in your `.env` file.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for providing the AI capabilities
- **LaTeX Community** for the typesetting system
- **React Team** for the amazing frontend framework
- **FastAPI** for the high-performance backend framework
- **Tailwind CSS** for the utility-first CSS framework

## 📞 Support

If you encounter any issues or have questions:

1. Check the [troubleshooting section](#-troubleshooting)
2. Review the [API documentation](http://localhost:8000/docs)
3. Open an issue on GitHub
4. Check the browser console and backend logs

---

**Made with ❤️ for better resumes**
