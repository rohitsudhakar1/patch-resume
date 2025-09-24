"""
FastAPI backend for resume builder application
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import tempfile
import json
import uuid
import re
from datetime import datetime
import openai
from dotenv import load_dotenv

# Import services
from services.template_service import TemplateService
from services.compile_service import CompileService
from services.simple_parse_service import SimpleParseService

# Load environment variables from .env file
try:
    load_dotenv()
except Exception as e:
    print(f"⚠️ WARNING: Could not load .env file: {e}")

# Set OpenAI API key directly
openai.api_key = "***REMOVED***"
print("✅ DEBUG: OpenAI API key set successfully")

# Simple in-memory storage for demo
projects = {}
patches = {}

# Initialize services
template_service = TemplateService()
compile_service = CompileService()
parse_service = ParseService()

# Load projects from file if it exists
PROJECTS_FILE = "projects_backup.json"
try:
    if os.path.exists(PROJECTS_FILE):
        with open(PROJECTS_FILE, 'r') as f:
            projects = json.load(f)
        print(f"✅ DEBUG: Loaded {len(projects)} projects from backup file")
except Exception as e:
    print(f"⚠️ DEBUG: Could not load projects backup: {e}")

def save_projects():
    """Save projects to backup file"""
    try:
        with open(PROJECTS_FILE, 'w') as f:
            json.dump(projects, f, default=str)
        print(f"💾 DEBUG: Saved {len(projects)} projects to backup file")
    except Exception as e:
        print(f"⚠️ DEBUG: Could not save projects backup: {e}")

# Check OpenAI API key on startup
if openai.api_key:
    print("✅ DEBUG: OpenAI API key found - AI features enabled")
else:
    print("⚠️ WARNING: No OpenAI API key found - using fallback template mode")
    print("💡 TIP: Set OPENAI_API_KEY environment variable to enable AI features")

app = FastAPI(
    title="Resume Builder API",
    description="Python backend for resume builder with LaTeX compilation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ProjectResponse(BaseModel):
    id: str
    resume_tex: str
    compile_status: str
    outline: Dict[str, Any]

class ProjectRecreateRequest(BaseModel):
    id: str
    resume_tex: str
    pdf_url: Optional[str] = None
    reconstruction_note: Optional[str] = None

class ChangeRequest(BaseModel):
    change_id: str
    accepted: bool

class ApplyChangesRequest(BaseModel):
    changes: List[ChangeRequest]
    project_id: str

class PatchRequest(BaseModel):
    instruction: str
    code_slice: Optional[str] = None
    full_document: bool = False
    project_id: Optional[str] = None
    project_data: Optional[Any] = None

class IngestResponse(BaseModel):
    project_id: str
    resume_tex: str
    pdf_url: str
    reconstruction_note: Optional[str] = None

class Change(BaseModel):
    id: str
    type: str
    start_line: int
    end_line: int
    content: str
    accepted: Optional[bool] = None
    pdf_regions: Optional[List[dict]] = []

class PatchResponse(BaseModel):
    patch_id: str
    changes: List[Change]
    project_id: str

def extract_text_from_file(file_path: str, content_type: str) -> str:
    """Extract text from uploaded file"""
    try:
        if content_type == "text/plain":
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif content_type == "application/pdf":
            # Simple PDF text extraction
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
            except ImportError:
                return "PDF processing not available. Please install PyPDF2."
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            # Simple DOCX text extraction
            try:
                import docx
                doc = docx.Document(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            except ImportError:
                return "DOCX processing not available. Please install python-docx."
        else:
            return "Unsupported file type"
    except Exception as e:
        return f"Error reading file: {str(e)}"

def convert_to_latex_with_chat(text_content: str) -> str:
    """Convert extracted text to LaTeX using improved parsing for better formatting preservation"""
    
    print(f"🔍 DEBUG: Converting text content (length: {len(text_content)})")
    print(f"📝 DEBUG: First 200 chars: {text_content[:200]}...")
    
    # Use improved parsing approach that preserves formatting better
    print("🔧 DEBUG: Using improved parsing approach for better formatting preservation")
    
    # Use SimpleParseService for better structure preservation
    parse_service = SimpleParseService()
    resume_data = parse_service.parse_resume_text(text_content)
    
    # Generate LaTeX using TemplateService
    template_service = TemplateService()
    latex = template_service.render_resume(resume_data)
    
    print(f"📄 DEBUG: Generated LaTeX using improved parsing (length: {len(latex)})")
    print(f"📄 DEBUG: LaTeX preview: {latex[:200]}...")
    
    return latex

def validate_and_improve_changes(changes_data: list, resume_tex: str) -> list:
    """Validate and improve changes to ensure multi-line deletions work correctly"""
    lines = resume_tex.split('\n')
    improved_changes = []
    
    for change in changes_data:
        if change.get('type') == 'removal':
            # Check if this is a single-line removal that should be multi-line
            start_line = change.get('start_line', 1) - 1  # Convert to 0-indexed
            content = change.get('content', '')
            
            # If it's a company name line, try to find the complete block
            if '\\textbf{' in content and ('Capital' in content or 'Lab' in content or 'Solutions' in content):
                # Find the complete experience block
                end_line = find_experience_block_end(lines, start_line)
                if end_line > start_line:
                    # Reconstruct the complete content
                    complete_content = '\n'.join(lines[start_line:end_line + 1])
                    change['end_line'] = end_line + 1  # Convert back to 1-indexed
                    change['content'] = complete_content
                    print(f"🔧 DEBUG: Improved removal to multi-line: lines {start_line + 1}-{end_line + 1}")
        
        improved_changes.append(change)
    
    return improved_changes

def find_experience_block_end(lines: list, start_line: int) -> int:
    """Find the end of an experience block starting from start_line"""
    # Look for the next \textbf{ or \section*{ or end of document
    for i in range(start_line + 1, len(lines)):
        line = lines[i].strip()
        if (line.startswith('\\textbf{') and ('Capital' in line or 'Lab' in line or 'Solutions' in line)) or \
           line.startswith('\\section*{') or \
           line.startswith('\\end{document}'):
            return i - 1
    
    # If not found, return the last line
    return len(lines) - 1

def clean_text_content(text_content: str) -> str:
    """Clean and normalize text content to remove unwanted characters and sequences"""
    if not text_content:
        return ""
    
    # Handle specific problematic sequences that appear in the resume
    # Remove \n\ sequences (newline followed by backslash)
    text_content = re.sub(r'\\n\\', '\n', text_content)
    
    # Remove standalone \n sequences (but preserve actual newlines)
    text_content = re.sub(r'(?<!\\)\\n(?!\\)', '\n', text_content)
    
    # Handle specific problematic patterns that cause LaTeX compilation errors
    text_content = re.sub(r'\\Personal\s*', 'Personal ', text_content)
    text_content = re.sub(r'\\Jan\s*', 'Jan ', text_content)
    text_content = re.sub(r'\\&', '&', text_content)
    
    # Only clean raw text content, not LaTeX commands
    # This function should only be used for raw text input, not LaTeX output
    # Remove backslashes that are not part of legitimate LaTeX commands
    # Keep common LaTeX commands but remove problematic ones
    legitimate_latex_commands = ['textbf', 'textit', 'section', 'subsection', 'itemize', 'item', 'begin', 'end', 'documentclass', 'usepackage', 'href', 'url', 'newcommand', 'noindent', 'par', 'vspace', 'rule', 'linewidth', 'entryspace', 'sectionline', 'baselinestretch', 'footnotesize', 'normalsize', 'bfseries', 'textbullet', 'leftmargin', 'nosep', 'topsep', 'itemsep', 'parsep', 'partopsep', 'titlespacing', 'titleformat']
    
    # Remove backslashes that are not followed by legitimate LaTeX commands
    text_content = re.sub(r'\\(?!' + '|'.join(legitimate_latex_commands) + r')\w+', '', text_content)
    
    # Remove standalone backslashes that are not part of LaTeX commands
    text_content = re.sub(r'(?<!\\)\\(?!\w)', '', text_content)
    
    # Normalize whitespace
    text_content = re.sub(r'\n\s*\n', '\n\n', text_content)  # Multiple newlines to double newline
    text_content = re.sub(r'[ \t]+', ' ', text_content)  # Multiple spaces to single space
    text_content = re.sub(r'\n[ \t]+', '\n', text_content)  # Remove leading spaces from lines
    
    # Clean up any remaining problematic sequences
    text_content = re.sub(r'\\[^a-zA-Z]', '', text_content)  # Remove backslash followed by non-letters
    
    return text_content.strip()

def _parse_experience_line_improved(line: str, experience: list, current_item: dict):
    """Parse experience section with improved logic"""
    line = line.strip()
    if not line:
        return current_item
        
    # Check if this is a bullet point
    if line.startswith("•") or line.startswith("-") or line.startswith("*"):
        if current_item and "bullets" in current_item:
            current_item["bullets"].append(line[1:].strip())
        return current_item
    
    # Check if this looks like a job title (usually shorter, contains keywords)
    job_keywords = ["intern", "engineer", "developer", "analyst", "manager", "specialist", "coordinator", "assistant"]
    if any(keyword in line.lower() for keyword in job_keywords) and len(line.split()) <= 6:
        # Start new experience item
        if current_item and "role" in current_item:
            experience.append(current_item)
        current_item = {"role": line, "company": "", "dates": "", "location": "", "bullets": []}
        return current_item
    
    # Check if this looks like a company name (usually contains company indicators)
    company_indicators = ["ltd", "inc", "corp", "llc", "private", "solutions", "systems", "capital", "lab", "university"]
    if any(indicator in line.lower() for indicator in company_indicators):
        if current_item and "company" not in current_item:
            current_item["company"] = line
        return current_item
    
    # Check if this looks like dates (contains month/year patterns)
    import re
    date_pattern = r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december).*\d{4}'
    if re.search(date_pattern, line.lower()):
        if current_item and "dates" not in current_item:
            current_item["dates"] = line
        return current_item
    
    # Check if this looks like a location (contains location indicators)
    location_indicators = ["india", "usa", "madison", "wi", "coimbatore", "present", "remote"]
    if any(indicator in line.lower() for indicator in location_indicators):
        if current_item and "location" not in current_item:
            current_item["location"] = line
        return current_item
    
    # If we have a current item and this doesn't match any pattern, treat as bullet point
    if current_item and "bullets" in current_item:
        current_item["bullets"].append(line)
    
    return current_item

def convert_to_latex_fallback(text_content: str) -> str:
    """Fallback conversion using improved parsing to preserve formatting"""
    print("🔧 DEBUG: Using improved fallback template conversion")
    
    # Use SimpleParseService for better parsing
    parse_service = SimpleParseService()
    resume_data = parse_service.parse_resume_text(text_content)
    
    # Generate LaTeX using TemplateService
    template_service = TemplateService()
    latex = template_service.render_resume(resume_data)
    print(f"📄 DEBUG: Generated LaTeX using ParseService + TemplateService (length: {len(latex)})")
    return latex

def convert_latex_to_html(latex_content: str) -> str:
    """Convert LaTeX content to HTML for display with improved formatting"""
    print("🔄 DEBUG: Converting LaTeX to HTML with improved formatting")
    
    # Basic LaTeX to HTML conversion with better handling
    html = latex_content
    
    # Remove document structure
    html = html.replace(r'\documentclass{article}', '')
    html = html.replace(r'\usepackage[letterpaper,margin=0.75in]{geometry}', '')
    html = html.replace(r'\usepackage{enumitem}', '')
    html = html.replace(r'\usepackage{hyperref}', '')
    html = html.replace(r'\begin{document}', '')
    html = html.replace(r'\end{document}', '')
    html = html.replace(r'\noindent', '')
    
    # Convert formatting with better regex handling
    import re
    
    # Handle bold text
    html = re.sub(r'\\textbf\{([^}]+)\}', r'<strong>\1</strong>', html)
    
    # Handle italic text
    html = re.sub(r'\\textit\{([^}]+)\}', r'<em>\1</em>', html)
    
    # Handle sections
    html = re.sub(r'\\section\*\{([^}]+)\}', r'<h2>\1</h2>', html)
    html = re.sub(r'\\subsection\*\{([^}]+)\}', r'<h3>\1</h3>', html)
    
    # Handle itemize environments
    html = re.sub(r'\\begin\{itemize\}', '<ul>', html)
    html = re.sub(r'\\end\{itemize\}', '</ul>', html)
    html = re.sub(r'\\item\s+', '<li>', html)
    
    # Handle center environments
    html = re.sub(r'\\begin\{center\}', '<div style="text-align: center;">', html)
    html = re.sub(r'\\end\{center\}', '</div>', html)
    
    # Handle line breaks
    html = html.replace(r'\\', '<br>')
    
    # Handle hyperlinks
    html = re.sub(r'\\href\{([^}]+)\}\{([^}]+)\}', r'<a href="\1">\2</a>', html)
    
    # Clean up any remaining LaTeX artifacts
    html = html.replace(r'\\', '<br>')
    
    # Create full HTML document with better styling
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Resume Preview</title>
        <style>
            body {{
                font-family: 'Times New Roman', serif;
                line-height: 1.6;
                max-width: 800px;
                margin: 0 auto;
                padding: 40px 20px;
                background: white;
                color: #333;
            }}
            h2 {{
                font-size: 20px;
                font-weight: bold;
                margin-top: 32px;
                margin-bottom: 16px;
                padding-bottom: 6px;
                border-bottom: 2px solid #333;
                color: #333;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            h3 {{
                font-size: 16px;
                font-weight: bold;
                margin-top: 20px;
                margin-bottom: 10px;
                color: #333;
            }}
            ul {{
                margin: 12px 0;
                padding-left: 24px;
            }}
            li {{
                margin-bottom: 6px;
                line-height: 1.5;
            }}
            strong {{
                font-weight: bold;
                color: #222;
            }}
            em {{
                font-style: italic;
                color: #555;
            }}
            a {{
                color: #0066cc;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            .resume-header {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 1px solid #ddd;
            }}
            .resume-content {{
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="resume-content">
            {html}
        </div>
    </body>
    </html>
    """
    
    return full_html


@app.post("/ingest", response_model=IngestResponse)
async def ingest_resume(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Process uploaded resume file and convert to LaTeX"""
    try:
        print(f"🔍 DEBUG: Starting file upload - {file.filename}, type: {file.content_type}")
        print(f"🔍 DEBUG: OpenAI API key status: {'Found' if openai.api_key else 'Missing'}")
        
        # Validate file type
        if not file.content_type.startswith(('application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain')):
            print(f"❌ ERROR: Unsupported file type: {file.content_type}")
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        print(f"📁 DEBUG: Saved file to: {tmp_file_path}")
        
        try:
            # Extract text from file
            print("📝 DEBUG: Extracting text from file...")
            text_content = extract_text_from_file(tmp_file_path, file.content_type)
            print(f"📄 DEBUG: Extracted text length: {len(text_content)}")
            print(f"📄 DEBUG: First 200 chars: {text_content[:200]}...")
            
            # Convert to LaTeX using OpenAI or fallback
            print("🤖 DEBUG: Converting to LaTeX...")
            latex_content = convert_to_latex_with_chat(text_content)
            print(f"📄 DEBUG: Generated LaTeX length: {len(latex_content)}")
            
            # Create project
            project_id = str(uuid.uuid4())
            projects[project_id] = {
                "id": project_id,
                "resume_tex": latex_content,
                "compile_status": "success",
                "outline": {"sections": ["basics", "summary", "experience", "education", "projects", "skills"]},
                "created_at": datetime.utcnow()
            }
            
            print(f"✅ DEBUG: Created project {project_id} with LaTeX content length: {len(latex_content)}")
            print(f"📄 DEBUG: LaTeX preview: {latex_content[:200]}...")
            
            # Save to backup file
            save_projects()
            
            print(f"✅ DEBUG: Created project {project_id}")
            
            return IngestResponse(
                project_id=project_id,
                resume_tex=latex_content,
                pdf_url=f"http://localhost:8000/artifact/pdf/{project_id}",
                reconstruction_note="Resume converted using AI-powered approach"
            )
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
                print(f"🗑️ DEBUG: Cleaned up temp file")
            except:
                pass
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ ERROR: Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/llm/patch", response_model=PatchResponse)
def generate_patch(request: PatchRequest):
    """Generate proposed changes using OpenAI or template approach"""
    try:
        print(f"🔍 DEBUG: Generating patch for instruction: '{request.instruction}'")
        print(f"📝 DEBUG: Code slice: {request.code_slice}")
        print(f"📄 DEBUG: Full document: {request.full_document}")
        
        patch_id = str(uuid.uuid4())
        
        # Get current project from request - require project_id
        if not hasattr(request, 'project_id') or not request.project_id:
            raise HTTPException(status_code=400, detail="Project ID is required")
        
        project_id = request.project_id
        if project_id not in projects:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        project = projects[project_id]
        
        print(f"📁 DEBUG: Using project ID: {project_id}")
        print(f"📁 DEBUG: Available projects: {list(projects.keys())}")
        
        # If project doesn't exist but we have project data from frontend, recreate it
        if not project and request.project_data:
            print(f"🔄 DEBUG: Project {project_id} not found in backend, recreating from frontend data")
            project = request.project_data
            projects[project_id] = project
            print(f"✅ DEBUG: Recreated project {project_id} in backend")
        elif not project:
            print(f"❌ ERROR: No project found with ID: {project_id}")
            raise HTTPException(status_code=404, detail=f"No project found. Please upload a resume first.")
        
        if not openai.api_key:
            print("❌ ERROR: No OpenAI API key provided")
            raise HTTPException(status_code=500, detail="OpenAI API key is required for patch generation")
        
        print("🤖 DEBUG: Using OpenAI for patch generation")
        try:
            # Use OpenAI to generate real patches
            system_prompt = """You are a LaTeX resume expert. Generate specific changes to improve a resume based on the user's instruction.

IMPORTANT: When deleting experience entries, projects, or education entries, you MUST delete the ENTIRE multi-line block, not just single lines.

For experience entries, this includes:
- The \\textbf{Company Name} line
- The \\textit{date} line  
- The \\begin{itemize} block
- All \\item entries inside
- The \\end{itemize} line
- Any empty lines after

Return your response as a JSON array of changes, where each change has:
- id: unique identifier
- type: "addition" or "removal" 
- start_line: line number where change starts
- end_line: line number where change ends (for multi-line deletions, this should be the last line of the block)
- content: the actual LaTeX content to add/remove (for multi-line, include all lines separated by \\n)
- pdf_regions: [{"x": 50, "y": 200, "width": 400, "height": 60}] for visual positioning

Example for deleting an experience entry:
[
  {
    "id": "change1",
    "type": "removal",
    "start_line": 15,
    "end_line": 25,
    "content": "\\textbf{Company Name} --- Role |Location\\n\\textit{Date Range}\\n\\begin{itemize}\\n\\item Achievement 1\\n\\item Achievement 2\\n\\end{itemize}\\n",
    "pdf_regions": [{"x": 50, "y": 200, "width": 400, "height": 200}]
  }
]

Example for single line addition:
[
  {
    "id": "change1",
    "type": "addition", 
    "start_line": 12,
    "end_line": 12,
    "content": "\\item New bullet point with quantified impact",
    "pdf_regions": [{"x": 50, "y": 200, "width": 400, "height": 60}]
  }
]"""

            user_prompt = f"""Instruction: {request.instruction}

Current LaTeX content:
{project.get('resume_tex', 'No content available')}

Generate specific changes to implement this instruction."""

            print(f"📤 DEBUG: Sending patch request to OpenAI")
            print(f"🔍 DEBUG: System prompt: {system_prompt[:200]}...")
            print(f"🔍 DEBUG: User prompt: {user_prompt[:200]}...")
            
            client = openai.OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            ai_response = response.choices[0].message.content
            print(f"📥 DEBUG: Received from OpenAI: {ai_response[:200]}...")
            
            # Parse AI response
            try:
                # Clean the AI response to fix escape sequences
                cleaned_response = ai_response.replace('\\', '\\\\')  # Fix escape sequences
                changes_data = json.loads(cleaned_response)
                
                # Validate and improve multi-line deletions
                changes_data = validate_and_improve_changes(changes_data, project.get('resume_tex', ''))
                
                mock_changes = [Change(**change) for change in changes_data]
            except Exception as parse_error:
                print(f"❌ ERROR: Failed to parse AI response: {parse_error}")
                print(f"📄 DEBUG: Raw AI response: {ai_response}")
                raise HTTPException(status_code=500, detail=f"Failed to parse AI response: {str(parse_error)}")
                
        except Exception as e:
            print(f"❌ ERROR: OpenAI patch generation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OpenAI patch generation failed: {str(e)}")
        
        patches[patch_id] = {
            "patch_id": patch_id,
            "changes": mock_changes,
            "project_id": project_id
        }
        
        print(f"✅ DEBUG: Generated {len(mock_changes)} changes")
        
        return PatchResponse(
            patch_id=patch_id,
            changes=mock_changes,
            project_id=project_id
        )
        
    except Exception as e:
        print(f"❌ ERROR: Patch generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/llm/chat")
def chat_with_agent(request: dict):
    """Chat with the AI resume agent"""
    try:
        message = request.get('message', '')
        chat_history = request.get('chat_history', [])
        current_resume = request.get('current_resume')
        context = request.get('context', {})
        
        print(f"🤖 DEBUG: Chat request: {message[:100]}...")
        print(f"📚 DEBUG: Chat history length: {len(chat_history)}")
        print(f"📄 DEBUG: Has current resume: {bool(current_resume)}")
        
        if not openai.api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key is required")
        
        # Build conversation context
        system_prompt = """You are an expert AI resume assistant. You help users build, improve, and customize their resumes.

Key capabilities:
- Build resumes from scratch
- Improve existing resumes
- Adjust resume length (1-page, 2-page, etc.)
- Optimize for specific job roles
- Fix formatting and content issues
- Provide career advice

Guidelines:
- Always maintain a helpful, professional tone
- Ask clarifying questions when needed
- If user wants a 1-page resume, ensure content fits
- If content is too long, suggest what to remove or condense
- Provide specific, actionable advice
- When updating resume, return structured data

Formatting and writing quality:
- Prefer concise, high-impact bullet points that start with strong verbs
- Where possible, include metrics (%, x, time saved) and outcomes
- Avoid first person; keep bullets single-line if possible
- No run-on sentences; avoid clumsy wording
- Keep sections clearly separated: Education, Work Experience, Projects, Skills
- Do NOT left-align everything; assume a standard LaTeX article with clear sections and itemized bullets

When user asks for resume changes, respond with:
- Clear explanation of what you're doing
- Specific changes made
- Any recommendations
- Ask if they want further adjustments

Remember: You're having a conversation, so be natural and engaging."""

        # Build messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat history
        for msg in chat_history[-10:]:  # Keep last 10 messages for context
            messages.append({
                "role": msg.get('role', 'user'),
                "content": msg.get('content', '')
            })
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        print(f"📤 DEBUG: Sending to OpenAI with {len(messages)} messages")
        
        client = openai.OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        print(f"📥 DEBUG: Received response: {ai_response[:200]}...")
        
        # Check if this is a resume update request
        is_resume_update = False
        resume_data = None
        
        # Simple heuristics to detect resume update or formatting requests
        lowered = message.lower()
        update_keywords = ['update', 'change', 'modify', 'add', 'remove', 'delete', 'improve', 'fix']
        format_keywords = ['format', 'formatting', 'make it one page', 'one page', 'polish', 'align', 'layout', 'clean up', 'make it professional', 'reformat', 'structure']

        def _looks_like_latex(text: str) -> bool:
            if not isinstance(text, str):
                return False
            return ('\\begin{document}' in text) or ('\\section*{' in text) or ('\\textbf{' in text)

        def format_resume_latex(resume_tex: str) -> str:
            """Normalize LaTeX resume for professional layout and alignment.
            - Ensures documentclass, geometry, hyperref, enumitem
            - Centers name/header block
            - Uses \section* with consistent spacing
            - Itemize with leftmargin=*, tight spacing
            - Removes excessive blank lines and fixes spacing
            """
            try:
                if not resume_tex:
                    return resume_tex

                import re

                tex = resume_tex
                # Ensure minimal preamble
                if '\\documentclass' not in tex:
                    tex = ("\\documentclass{article}\n"
                           "\\usepackage[letterpaper,margin=0.75in]{geometry}\n"
                           "\\usepackage{enumitem}\n\\setlist[itemize]{leftmargin=*, itemsep=0.2em, topsep=0.2em}\n"
                           "\\usepackage[colorlinks=true,linkcolor=black,urlcolor=blue]{hyperref}\n"
                           "\\begin{document}\n\n" + tex)
                    if not tex.strip().endswith('\\end{document}'):
                        tex += "\n\\end{document}\n"

                # Ensure required packages and enumitem options
                if 'enumitem' not in tex:
                    tex = tex.replace('\\usepackage{hyperref}', '\\usepackage{enumitem}\n\\setlist[itemize]{leftmargin=*, itemsep=0.2em, topsep=0.2em}\n\\usepackage{hyperref}')
                if '\\setlist[itemize]' not in tex:
                    tex = tex.replace('\\usepackage{enumitem}', '\\usepackage{enumitem}\n\\setlist[itemize]{leftmargin=*, itemsep=0.2em, topsep=0.2em}')

                # Center the very first bold line (name) by wrapping with center if not already
                lines = tex.split('\n')
                try:
                    begin_doc_idx = next(i for i, l in enumerate(lines) if '\\begin{document}' in l)
                except StopIteration:
                    begin_doc_idx = 0

                # Find first meaningful line after begin{document}
                for i in range(begin_doc_idx + 1, min(begin_doc_idx + 10, len(lines))):
                    if lines[i].strip() == '':
                        continue
                    # If not already centered, center block of first 1-3 lines (name + contact)
                    if '\\begin{center}' not in '\n'.join(lines[i:i+5]):
                        block = []
                        j = i
                        while j < len(lines) and j < i + 5 and lines[j].strip() != '':
                            block.append(lines[j])
                            j += 1
                        centered = ['\\begin{center}'] + block + ['\\end{center}', '']
                        lines = lines[:i] + centered + lines[j:]
                    break

                tex = '\n'.join(lines)

                # Normalize sections to \section*
                tex = re.sub(r"\\section\s*\{([^}]+)\}", r"\\section*{\1}", tex)
                # Ensure a blank line after each section header
                tex = re.sub(r"(\\section\*\{[^}]+\})\s*", r"\1\n", tex)

                # Tighten multiple blank lines
                tex = re.sub(r"\n{3,}", "\n\n", tex)

                # Ensure itemize environments are well-formed
                tex = tex.replace('\\begin{itemize}', '\\begin{itemize}')  # idempotent, placeholder for future checks
                tex = tex.replace('\\end{itemize}', '\\end{itemize}')

                return tex
            except Exception:
                return resume_tex

        if any(k in lowered for k in format_keywords):
            # Formatting intent detected
            source = current_resume if _looks_like_latex(current_resume or '') else ai_response
            if _looks_like_latex(source):
                formatted = format_resume_latex(source)
                is_resume_update = True
                resume_data = formatted

        if resume_data is None and any(keyword in lowered for keyword in update_keywords):
            is_resume_update = True
            # Default behavior: pass through current resume; frontend may apply targeted patches
            resume_data = current_resume
        
        return {
            "response": ai_response,
            "is_resume_update": is_resume_update,
            "resume_data": resume_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ ERROR: Chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.post("/changes/apply")
async def apply_changes(
    request: ApplyChangesRequest,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Apply accepted changes"""
    try:
        # Use project_id from request
        project_id = request.project_id
        if project_id not in projects:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        # In a real implementation, you would apply the changes to the LaTeX
        # For now, just return success
        
        return {"success": True, "project_id": project_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/project/recreate")
async def recreate_project(project_data: ProjectRecreateRequest):
    """Recreate a project from frontend data"""
    try:
        project_id = project_data.id
        if not project_id:
            raise HTTPException(status_code=400, detail="Project ID is required")
        
        print(f"🔄 DEBUG: Recreating project {project_id} from frontend data")
        print(f"📄 DEBUG: Resume content length: {len(project_data.resume_tex)}")
        print(f"📄 DEBUG: Resume content preview: {project_data.resume_tex[:200]}")
        
        # Store the project in memory
        projects[project_id] = {
            "id": project_data.id,
            "resume_tex": project_data.resume_tex,
            "pdf_url": project_data.pdf_url,
            "reconstruction_note": project_data.reconstruction_note,
            "compile_status": "success",
            "outline": {"sections": ["basics", "summary", "experience", "education", "skills"]},
            "created_at": datetime.utcnow()
        }
        
        # Save to backup file
        save_projects()
        
        print(f"✅ DEBUG: Project {project_id} recreated successfully")
        print(f"📁 DEBUG: Available projects: {list(projects.keys())}")
        
        return {"success": True, "project_id": project_id}
        
    except Exception as e:
        print(f"❌ ERROR: Failed to recreate project: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to recreate project: {str(e)}")

@app.get("/projects/status")
async def get_projects_status():
    """Get status of all projects"""
    return {
        "total_projects": len(projects),
        "project_ids": list(projects.keys()),
        "projects": projects
    }

@app.get("/artifact/pdf/{project_id}")
async def get_pdf(project_id: str, t: Optional[str] = None):
    """Get latest PDF for project using modular compile service"""
    print(f"🔍 DEBUG: PDF request for project: {project_id}")
    
    try:
        if project_id not in projects:
            print(f"❌ ERROR: Project {project_id} not found")
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found. Please upload a resume first.")
        
        project = projects[project_id]
        latex_content = project["resume_tex"]
        
        if not latex_content:
            raise HTTPException(status_code=400, detail="No LaTeX content found for project")
        
        print(f"✅ DEBUG: Found project, compiling LaTeX to PDF")
        print(f"📄 DEBUG: LaTeX content length: {len(latex_content)}")
        
        # Use compile service to generate PDF
        success, pdf_path, error_msg = compile_service.compile_latex(latex_content, project_id)
        
        if success and pdf_path and os.path.exists(pdf_path):
            print(f"✅ DEBUG: PDF generated successfully at {pdf_path}")
            return FileResponse(
                path=pdf_path,
                media_type="application/pdf",
                filename=f"resume_{project_id}.pdf",
                headers={
                    "Content-Disposition": f"inline; filename=resume_{project_id}.pdf",
                    "X-Content-Type-Options": "nosniff",
                    "Cache-Control": "no-store, no-cache, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
                    "Access-Control-Allow-Headers": "*"
                }
            )
        else:
            print(f"❌ ERROR: PDF compilation failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"PDF compilation failed: {error_msg}")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERROR: PDF endpoint failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    print("🔍 DEBUG: Health check requested")
    return {"status": "healthy", "service": "resume-builder-api"}




if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )