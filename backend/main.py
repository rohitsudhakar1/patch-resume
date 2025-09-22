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
    """Convert extracted text to LaTeX using OpenAI"""
    
    # Clean the text content first
    text_content = clean_text_content(text_content)
    
    print(f"🔍 DEBUG: Converting text content (length: {len(text_content)})")
    print(f"📝 DEBUG: First 200 chars: {text_content[:200]}...")
    print(f"🔍 DEBUG: OpenAI API key status: {'Found' if openai.api_key else 'Missing'}")
    
    if not openai.api_key:
        print("⚠️ WARNING: No OpenAI API key found, using fallback template")
        return convert_to_latex_fallback(text_content)
    
    try:
        print("🤖 DEBUG: Calling OpenAI API...")
        
        system_prompt = """You are a LaTeX resume expert. Convert the provided resume text into a well-formatted LaTeX document.

Requirements:
1. Use proper LaTeX syntax with \\documentclass{article}
2. Include packages: \\usepackage[letterpaper,margin=0.75in]{geometry}, \\usepackage{enumitem}, \\usepackage{hyperref}
3. Structure with sections: Professional Summary, Experience, Education, Projects, Skills
4. Use \\textbf{} for job titles, company names, and project names
5. Use \\textit{} for dates and locations
6. Use \\item for bullet points in \\begin{itemize}
7. Escape special LaTeX characters properly (& becomes \\&, % becomes \\%, etc.)
8. NEVER use backslashes followed by words that are not LaTeX commands (like \\Personal, \\Jan, etc.)
9. NEVER use \\n\\ or similar problematic sequences
10. Use proper line breaks with \\\\ for line breaks within sections
11. Make it professional and well-formatted

IMPORTANT: Avoid any sequences like \\Personal, \\Jan, \\n\\, or any backslash followed by a word that is not a LaTeX command. These cause compilation errors.

Return ONLY the LaTeX code, no explanations."""

        user_prompt = f"""Convert this resume text to LaTeX:

{text_content}"""

        print(f"📤 DEBUG: Sending to OpenAI - System prompt length: {len(system_prompt)}, User prompt length: {len(user_prompt)}")
        print(f"🔍 DEBUG: System prompt: {system_prompt[:200]}...")
        print(f"🔍 DEBUG: User prompt: {user_prompt[:200]}...")
        
        client = openai.OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=3000,
            temperature=0.1
        )
        
        latex_content = response.choices[0].message.content
        print(f"📥 DEBUG: Received from OpenAI - Length: {len(latex_content)}")
        print(f"📄 DEBUG: First 300 chars of response: {latex_content[:300]}...")
        print(f"✅ DEBUG: OpenAI API call successful!")
        
        return latex_content
        
    except Exception as e:
        print(f"❌ ERROR: OpenAI API failed: {str(e)}")
        print("🔄 DEBUG: Falling back to template method")
        return convert_to_latex_fallback(text_content)

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
    
    # Remove backslashes that are not part of legitimate LaTeX commands
    # Keep common LaTeX commands but remove problematic ones
    legitimate_latex_commands = ['textbf', 'textit', 'section', 'subsection', 'itemize', 'item', 'begin', 'end', 'documentclass', 'usepackage', 'href', 'url']
    
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
    """Fallback conversion using template approach"""
    print("🔧 DEBUG: Using fallback template conversion")
    
    # Clean the text content first
    text_content = clean_text_content(text_content)
    
    # Simple heuristic-based conversion
    lines = text_content.split('\n')
    
    # Initialize structure
    resume_data = {
        "name": "",
        "email": "",
        "phone": "",
        "linkedin": "",
        "github": "",
        "summary": "",
        "experience": [],
        "education": [],
        "projects": [],
        "skills": []
    }
    
    current_section = None
    current_item = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect sections
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in ["contact", "personal", "name", "@", "phone"]):
            current_section = "basics"
        elif any(keyword in line_lower for keyword in ["summary", "objective", "profile", "about"]):
            current_section = "summary"
        elif any(keyword in line_lower for keyword in ["experience", "employment", "work", "career"]):
            current_section = "experience"
        elif any(keyword in line_lower for keyword in ["education", "academic", "degree", "university"]):
            current_section = "education"
        elif any(keyword in line_lower for keyword in ["skills", "technologies", "competencies"]):
            current_section = "skills"
        else:
            # Process based on current section
            if current_section == "basics":
                if "@" in line and not resume_data["email"]:
                    resume_data["email"] = line
                elif any(char.isdigit() for char in line) and "phone" in line_lower:
                    resume_data["phone"] = line
                elif "linkedin" in line_lower:
                    resume_data["linkedin"] = line
                elif "github" in line_lower:
                    resume_data["github"] = line
                elif not resume_data["name"] and len(line.split()) <= 3:
                    resume_data["name"] = line
            elif current_section == "summary":
                resume_data["summary"] += line + " "
            elif current_section == "experience":
                current_item = _parse_experience_line_improved(line, resume_data["experience"], current_item)
            elif current_section == "education":
                if line and not line.startswith("•") and not line.startswith("-"):
                    resume_data["education"].append({"degree": line, "school": "", "year": ""})
            elif current_section == "projects":
                if line and not line.startswith("•") and not line.startswith("-"):
                    resume_data["projects"].append({"name": line, "description": ""})
            elif current_section == "skills":
                resume_data["skills"].extend([s.strip() for s in line.split(',')])
    
    # Add final experience item
    if current_item:
        resume_data["experience"].append(current_item)
    
    # Generate LaTeX
    latex = generate_latex_template(resume_data)
    print(f"📄 DEBUG: Generated LaTeX (length: {len(latex)})")
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

def generate_latex_template(data: dict) -> str:
    """Generate LaTeX from structured data"""
    
    # Escape LaTeX special characters
    def escape_latex(text: str) -> str:
        if not text:
            return ""
        replacements = {
            '\\': r'\\',
            '{': r'\{',
            '}': r'\}',
            '$': r'\$',
            '&': r'\&',
            '%': r'\%',
            '#': r'\#',
            '^': r'\textasciicircum{}',
            '_': r'\_',
            '~': r'\textasciitilde{}'
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        return text
    
    # Build contact info
    contact_parts = []
    if data["email"]:
        contact_parts.append(f"Email: {data['email']}")
    if data["phone"]:
        contact_parts.append(f"Phone: {data['phone']}")
    if data["linkedin"]:
        contact_parts.append(f"LinkedIn: {data['linkedin']}")
    if data["github"]:
        contact_parts.append(f"GitHub: {data['github']}")
    
    contact_info = " $\\bullet$ ".join(contact_parts) + r"\\" if contact_parts else ""
    
    latex = f"""\\documentclass{{article}}
\\usepackage[letterpaper,margin=0.75in]{{geometry}}
\\usepackage{{enumitem}}
\\usepackage{{hyperref}}
\\usepackage{{url}}

\\begin{{document}}

\\begin{{center}}
{{\\Large \\textbf{{{escape_latex(data['name'] or 'Your Name')}}}}}\\\\
{contact_info}
\\end{{center}}

\\section*{{Professional Summary}}
{escape_latex(data['summary'] or 'Experienced professional with strong background in relevant field.')}

\\section*{{Experience}}
"""
    
    for exp in data["experience"]:
        role = exp.get('role', '')
        company = exp.get('company', '')
        dates = exp.get('dates', '')
        location = exp.get('location', '')
        bullets = exp.get('bullets', [])
        
        if not role:
            continue
            
        latex += f"\\textbf{{{escape_latex(role)}}}"
        
        if dates:
            latex += f" \\hfill \\textit{{{escape_latex(dates)}}}"
        
        latex += "\\\\\n"
        
        if company:
            latex += f"\\textit{{{escape_latex(company)}}}"
            if location:
                latex += f" \\hfill \\textit{{{escape_latex(location)}}}"
            latex += "\\\\\n"
        
        if bullets:
            latex += "\\begin{itemize}[leftmargin=0.5in]\n"
            for bullet in bullets:
                if bullet.strip():
                    latex += f"\\item {escape_latex(bullet)}\n"
            latex += "\\end{itemize}\n"
    
    if data["education"]:
        latex += """
\\section*{Education}
"""
        for edu in data["education"]:
            degree = edu.get('degree', '')
            school = edu.get('school', '')
            year = edu.get('year', '')
            gpa = edu.get('gpa', '')
            
            if not degree:
                continue
                
            latex += f"\\textbf{{{escape_latex(degree)}}}"
            
            if year:
                latex += f" \\hfill \\textit{{{escape_latex(year)}}}"
            
            latex += "\\\\\n"
            
            if school:
                latex += f"\\textit{{{escape_latex(school)}}}"
                if gpa:
                    latex += f" \\hfill {escape_latex(gpa)}"
                latex += "\\\\\n"
    
    if data["projects"]:
        latex += """
\\section*{Projects}
"""
        for project in data["projects"]:
            name = project.get('name', '')
            description = project.get('description', '')
            
            if not name:
                continue
                
            latex += f"\\textbf{{{escape_latex(name)}}}"
            if description:
                latex += f" \\hfill {escape_latex(description)}"
            latex += "\\\\\n"
    
    if data["skills"]:
        skills_text = ", ".join([s for s in data["skills"] if s])
        if skills_text:
            latex += f"""
\\section*{{Skills}}
{escape_latex(skills_text)}
"""
    
    latex += """
\\end{document}
"""
    
    return latex

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
        
        # Get current project from request or use first available
        project_id = request.project_id if hasattr(request, 'project_id') and request.project_id else (list(projects.keys())[0] if projects else str(uuid.uuid4()))
        project = projects.get(project_id, {})
        
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

@app.post("/changes/apply")
async def apply_changes(
    request: ApplyChangesRequest,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Apply accepted changes"""
    try:
        project_id = list(projects.keys())[0] if projects else str(uuid.uuid4())
        
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
    """Get latest PDF for project"""
    print(f"🔍 DEBUG: PDF request for project: {project_id}")
    print(f"📁 DEBUG: Available projects: {list(projects.keys())}")
    print(f"📁 DEBUG: Project details: {projects}")
    
    try:
        if project_id not in projects:
            print(f"❌ ERROR: Project {project_id} not found")
            print(f"📁 DEBUG: Available projects: {list(projects.keys())}")
            print(f"📁 DEBUG: Looking for exact match...")
            
            # Try to find project with similar ID
            for pid in projects.keys():
                if project_id in pid or pid in project_id:
                    print(f"🔍 DEBUG: Found similar project ID: {pid}")
            
            # Project not found - return 404 error
            print(f"❌ ERROR: Project {project_id} not found in backend")
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found. Please upload a resume first.")
        
        project = projects[project_id]
        print(f"✅ DEBUG: Found project, generating PDF")
        print(f"📄 DEBUG: Project LaTeX length: {len(project.get('resume_tex', ''))}")
        
        # Create a temporary LaTeX file in a simple path to avoid Windows short path issues
        import tempfile
        import subprocess
        import os
        import re
        
        # Create temp file in current directory to avoid Windows short path issues
        temp_dir = os.path.join(os.getcwd(), 'temp_latex')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create a minimal LaTeX document that doesn't require additional packages
        minimal_latex = project["resume_tex"]
        
        # Clean the LaTeX content to remove problematic sequences
        minimal_latex = clean_text_content(minimal_latex)
        
        # Remove ALL usepackage commands that cause interactive installation
        minimal_latex = re.sub(r'\\usepackage\[[^\]]*\]\{[^}]+\}', '', minimal_latex)
        minimal_latex = re.sub(r'\\usepackage\{[^}]+\}', '', minimal_latex)
        
        # Also remove any remaining usepackage lines
        lines = minimal_latex.split('\n')
        lines = [line for line in lines if not line.strip().startswith('\\usepackage')]
        minimal_latex = '\n'.join(lines)
        
        # Ensure proper document structure
        if not minimal_latex.strip().startswith('\\documentclass'):
            minimal_latex = '\\documentclass{article}\n' + minimal_latex
        if '\\begin{document}' not in minimal_latex:
            minimal_latex += '\n\\begin{document}\n\\end{document}'
        
        # Clean up any remaining problematic sequences
        minimal_latex = re.sub(r'\\[^a-zA-Z]', '', minimal_latex)  # Remove backslash followed by non-letters
        minimal_latex = re.sub(r'\\n\\', '\n', minimal_latex)  # Remove \n\ sequences
        minimal_latex = re.sub(r'\\Personal', 'Personal', minimal_latex)  # Fix \Personal
        minimal_latex = re.sub(r'\\Jan', 'Jan', minimal_latex)  # Fix \Jan
        
        # Clean up multiple newlines
        minimal_latex = re.sub(r'\n\s*\n\s*\n', '\n\n', minimal_latex)
        
        # Add basic document structure if missing
        if '\\documentclass' not in minimal_latex:
            minimal_latex = '\\documentclass{article}\n' + minimal_latex
        if '\\begin{document}' not in minimal_latex:
            minimal_latex += '\n\\begin{document}\n\\end{document}'
        
        tex_file_path = os.path.join(temp_dir, f'resume_{project_id}.tex')
        with open(tex_file_path, 'w', encoding='utf-8') as tex_file:
            tex_file.write(minimal_latex)
        
        try:
            # Use Tectonic as primary compiler (Overleaf-style)
            # Fallback to MiKTeX if Tectonic not available
            miktex_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs", "MiKTeX", "miktex", "bin", "x64")
            
            # Ensure we use absolute paths and proper path separators
            tex_file_path_abs = os.path.abspath(tex_file_path)
            output_dir = os.path.dirname(tex_file_path_abs)
            
            # Try Tectonic first (Overleaf-style compilation)
            compilers = [
                ('tectonic', ['tectonic', '--synctex', '-Z', 'continue-on-errors', tex_file_path_abs]),
                ('pdflatex', [os.path.join(miktex_path, 'pdflatex.exe'), '-interaction=nonstopmode', '-halt-on-error', '-file-line-error', '-output-directory', output_dir, tex_file_path_abs]),
                ('xelatex', [os.path.join(miktex_path, 'xelatex.exe'), '-interaction=nonstopmode', '-halt-on-error', '-file-line-error', '-output-directory', output_dir, tex_file_path_abs]),
                ('lualatex', [os.path.join(miktex_path, 'lualatex.exe'), '-interaction=nonstopmode', '-halt-on-error', '-file-line-error', '-output-directory', output_dir, tex_file_path_abs])
            ]
            
            # Try Docker-based compilation as fallback
            docker_compilers = [
                ('docker-pdflatex', ['docker', 'run', '--rm', '-v', f'{os.path.dirname(tex_file_path)}:/workspace', 'texlive/texlive:latest', 'pdflatex', '-interaction=nonstopmode', f'/workspace/{os.path.basename(tex_file_path)}']),
                ('docker-xelatex', ['docker', 'run', '--rm', '-v', f'{os.path.dirname(tex_file_path)}:/workspace', 'texlive/texlive:latest', 'xelatex', '-interaction=nonstopmode', f'/workspace/{os.path.basename(tex_file_path)}'])
            ]
            
            pdf_path = tex_file_path_abs.replace('.tex', '.pdf')
            compilation_success = False
            
            # Try local compilers first
            all_compilers = compilers + docker_compilers
            
            for compiler_name, cmd in all_compilers:
                try:
                    print(f"🔧 DEBUG: Trying {compiler_name} compiler...")
                    
                    # Check if compiler is available (skip version check for Docker)
                    if not compiler_name.startswith('docker-'):
                        if os.path.exists(cmd[0]):
                            print(f"✅ DEBUG: {compiler_name} found at {cmd[0]}, compiling to PDF")
                        else:
                            print(f"⚠️ DEBUG: {compiler_name} not found at {cmd[0]}, skipping")
                            continue
                    else:
                        print(f"🐳 DEBUG: Trying Docker-based {compiler_name} compilation...")
                    
                    print(f"🔧 DEBUG: Running command: {' '.join(cmd)}")
                    print(f"🔧 DEBUG: Working directory: {os.path.dirname(tex_file_path)}")
                    
                    # Run the compiler
                    result = subprocess.run(
                        cmd, 
                        capture_output=True, 
                        text=True, 
                        timeout=15,  # Shorter timeout to avoid hanging
                        cwd=os.path.dirname(tex_file_path)
                    )
                    
                    print(f"🔧 DEBUG: {compiler_name} finished with return code: {result.returncode}")
                    print(f"🔧 DEBUG: stdout: {result.stdout[:500]}")
                    print(f"🔧 DEBUG: stderr: {result.stderr[:500]}")
                    
                    if result.returncode == 0 and os.path.exists(pdf_path):
                        print(f"✅ DEBUG: PDF generated successfully with {compiler_name} at {pdf_path}")
                        compilation_success = True
                        break
                    else:
                        print(f"⚠️ DEBUG: {compiler_name} failed: {result.stderr}")
                        # Clean up failed compilation files
                        for ext in ['.aux', '.log', '.out', '.synctex.gz']:
                            aux_file = tex_file_path.replace('.tex', ext)
                            if os.path.exists(aux_file):
                                try:
                                    os.unlink(aux_file)
                                except:
                                    pass
                        
                except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                    print(f"⚠️ DEBUG: {compiler_name} not available: {str(e)}")
                    continue
            
            if compilation_success:
                print(f"✅ DEBUG: PDF compilation successful, serving file: {pdf_path}")
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
                print("❌ ERROR: All LaTeX compilers failed")
                raise Exception("No LaTeX compiler available")
                
        except Exception as e:
            print(f"❌ ERROR: PDF compilation error: {str(e)}")
            print("🔄 DEBUG: Using HTML fallback for LaTeX rendering")
            
            # Create HTML version of the LaTeX content
            html_content = convert_latex_to_html(project["resume_tex"])
            
            from fastapi.responses import HTMLResponse
            return HTMLResponse(
                content=html_content,
                headers={"Content-Disposition": f"inline; filename=resume_{project_id}.html"}
            )
        finally:
            # Clean up temporary files
            try:
                if os.path.exists(tex_file_path):
                    os.unlink(tex_file_path)
                # Clean up auxiliary files
                for ext in ['.aux', '.log', '.out']:
                    aux_file = tex_file_path.replace('.tex', ext)
                    if os.path.exists(aux_file):
                        os.unlink(aux_file)
            except:
                pass
        
    except Exception as e:
        print(f"❌ ERROR: PDF endpoint failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/project/recreate")
async def recreate_project(request: dict):
    """Recreate a project from frontend data"""
    try:
        print(f"🔄 DEBUG: Recreating project from frontend data")
        print(f"📄 DEBUG: Request data: {request}")
        
        project_id = request.get("id")
        if not project_id:
            raise HTTPException(status_code=400, detail="Project ID is required")
        
        # Store the project data
        projects[project_id] = request
        
        print(f"✅ DEBUG: Project {project_id} recreated successfully")
        return {"success": True, "project_id": project_id}
        
    except Exception as e:
        print(f"❌ ERROR: Project recreation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/project/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get current project state"""
    try:
        print(f"🔍 DEBUG: Getting project: {project_id}")
        print(f"📁 DEBUG: Available projects: {list(projects.keys())}")
        
        if project_id not in projects:
            print(f"❌ ERROR: Project {project_id} not found")
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found. Please upload a resume first.")
        
        project = projects[project_id]
        return ProjectResponse(
            id=project["id"],
            resume_tex=project["resume_tex"],
            compile_status=project["compile_status"],
            outline=project["outline"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    print("🔍 DEBUG: Health check requested")
    return {"status": "healthy", "service": "resume-builder-api"}


@app.get("/project/{project_id}")
async def get_project(project_id: str):
    """Get project by ID"""
    print(f"🔍 DEBUG: Getting project: {project_id}")
    print(f"📁 DEBUG: Available projects: {list(projects.keys())}")
    
    if project_id not in projects:
        print(f"❌ ERROR: Project {project_id} not found")
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = projects[project_id]
    print(f"✅ DEBUG: Found project: {project_id}")
    
    return {
        "id": project_id,
        "resume_tex": project.get('resume_tex', ''),
        "pdf_url": f"http://localhost:8000/artifact/pdf/{project_id}",
        "reconstruction_note": project.get('reconstruction_note', 'Resume converted using AI-powered approach')
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )