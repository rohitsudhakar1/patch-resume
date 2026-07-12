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
import anthropic
from dotenv import load_dotenv

# Import services
from services.template_service import TemplateService
from services.compile_service import CompileService
from services.clean_parse_service import CleanParseService

# Load environment variables from .env file
try:
    load_dotenv()
except Exception as e:
    print(f"⚠️ WARNING: Could not load .env file: {e}")

# --- Anthropic (Claude) client setup ---
# This app was originally wired to OpenAI; it now runs on Claude via the
# Anthropic SDK. Set ANTHROPIC_API_KEY in your .env to enable AI features.
LLM_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "claude-opus-4-8"
anthropic_client = anthropic.Anthropic(api_key=LLM_API_KEY) if LLM_API_KEY else None
if not LLM_API_KEY:
    print("⚠️ WARNING: ANTHROPIC_API_KEY not set in environment")


def claude_complete(system: str, user: str, max_tokens: int = 2000) -> str:
    """Call Claude with a system + single user message and return the text.

    Mirrors the old OpenAI chat-completion helper: pass the system prompt
    separately (Anthropic takes `system` as its own parameter) and read the
    text out of the first content block.
    """
    if anthropic_client is None:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is required for AI features")
    response = anthropic_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _with_canonical_preamble(latex: str) -> str:
    """Force the known-good template preamble onto AI-generated LaTeX.

    Every AI edit regenerates the whole document, and the model sometimes
    rewrites the preamble badly (breaking the \\sectiontitle command so
    section headings render inline, or reintroducing the stray "[1]1"
    artifact). We keep the model's BODY (from \\begin{document} onward) and
    swap in the canonical preamble so formatting can never drift.
    """
    if not latex:
        return latex
    idx = latex.find("\\begin{document}")
    if idx == -1:
        return latex  # no body marker found — leave untouched
    try:
        preamble = TemplateService()._get_preamble()
    except Exception:
        return latex
    return preamble + latex[idx:]


# --- Comprehensive LaTeX Cleaning System ---

# Patterns for broken/malformed LaTeX commands
BAD_LATEX_PATTERNS = [
    # Broken command patterns
    r'(?i)\bewcommand\b',  # broken \newcommand
    r'(?i)^\s*ewcommand',  # bare ewcommand without backslash
    r'(?i)ewcommand\[1\]1',  # specific broken pattern
    r'(?i)\bparindent\s+\d+pt\b',  # bare parindent
    r'(?i)\bparskip\s+\d+pt\b',   # bare parskip
    r'(?i)\baselinestretch\s*[\d.]+\b',  # bare baselinestretch
    r'(?i)^\s*(parindent|parskip|aselinestretch|aselinespread)\b',  # other bare commands
    r'(?i)\\\\(?!\s*$|\s*\\)',  # double backslashes not at line end or before command
    r'\\[a-zA-Z]+\{[^}]*$',  # incomplete commands with opening brace but no closing
    r'^[^\\]*\}[^\\]*$',  # lines with closing brace but no opening command
    r'(?i)undefined\s*control\s*sequence',  # LaTeX error text
    r'(?i)missing\s*\$\s*inserted',  # LaTeX error text
]

# Comprehensive LaTeX cleaning function
def clean_latex_content(tex: str, max_iterations: int = 3) -> tuple[str, bool, list]:
    """
    Comprehensive LaTeX cleaning that removes malformed commands and fixes formatting.
    Returns (cleaned_tex, was_changed, issues_found)
    """
    if not tex:
        return tex, False, []
    
    original_tex = tex
    issues_found = []
    changed = False
    
    for iteration in range(max_iterations):
        iteration_changed = False
        
        # Step 1: Remove bad patterns
        for pattern in BAD_LATEX_PATTERNS:
            if re.search(pattern, tex):
                old_tex = tex
                tex = re.sub(pattern, '', tex)
                if tex != old_tex:
                    iteration_changed = True
                    issues_found.append(f"Removed bad pattern: {pattern}")
        
        # Step 2: Fix specific broken commands
        fixes = [
            (r'\\textbf\{([^}]*)$', r'\\textbf{\1}'),  # Fix incomplete textbf
            (r'\\textit\{([^}]*)$', r'\\textit{\1}'),  # Fix incomplete textit
            (r'\\section\*?\{([^}]*)$', r'\\section*{\1}'),  # Fix incomplete sections
            (r'\\begin\{([^}]+)\}\s*$\s*(?!\\end)', r'\\begin{\1}\n\\end{\1}'),  # Fix incomplete environments
            # Remove a TRULY bare "ewcommand" (a corruption artifact) but never the
            # "ewcommand" inside valid \newcommand / \renewcommand (both preceded by "n").
            (r'(?<![\\a-zA-Z])ewcommand', r''),
            (r'\\\\\\+', r'\\\\'),  # Fix multiple backslashes
            (r'\n\s*\n\s*\n+', r'\n\n'),  # Fix excessive blank lines
            # NOTE: we intentionally do NOT collapse {{ -> { or }} -> } here.
            # Adjacent braces are valid, common LaTeX (e.g. the closing of a
            # \newcommand body that ends in \vspace{6pt}}), and collapsing them
            # silently eats real closing braces.
        ]
        
        for pattern, replacement in fixes:
            if re.search(pattern, tex):
                old_tex = tex
                tex = re.sub(pattern, replacement, tex)
                if tex != old_tex:
                    iteration_changed = True
                    issues_found.append(f"Applied fix: {pattern} -> {replacement}")
        
        # Step 3: Ensure proper LaTeX structure
        lines = tex.split('\n')
        cleaned_lines = []
        in_document = False
        has_documentclass = False
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines at the beginning
            if not line and not cleaned_lines:
                continue
                
            # Check for document class
            if '\\documentclass' in line:
                has_documentclass = True
            elif '\\begin{document}' in line:
                in_document = True
            elif '\\end{document}' in line:
                in_document = False
                cleaned_lines.append(line)
                break  # Stop after end document
            
            # Skip lines that are clearly malformed
            if (
                line and not line.startswith('\\') and 
                not in_document and 
                re.search(r'^[a-zA-Z]+\s*\d*\s*$', line)
            ):
                iteration_changed = True
                issues_found.append(f"Removed malformed line: {line}")
                continue
            
            cleaned_lines.append(line)
        
        # Ensure minimal LaTeX structure if missing
        if not has_documentclass:
            cleaned_lines.insert(0, '\\documentclass{article}')
            cleaned_lines.insert(1, '\\usepackage[letterpaper,margin=0.75in]{geometry}')
            cleaned_lines.insert(2, '\\usepackage{enumitem}')
            cleaned_lines.insert(3, '\\usepackage[colorlinks=true,linkcolor=black,urlcolor=blue]{hyperref}')
            cleaned_lines.insert(4, '')
            iteration_changed = True
            issues_found.append("Added missing LaTeX preamble")
        
        tex = '\n'.join(cleaned_lines)
        
        if iteration_changed:
            changed = True
        else:
            break  # No changes in this iteration, we're done
    
    # Final validation - check for unmatched braces
    open_braces = tex.count('{')
    close_braces = tex.count('}')
    if open_braces != close_braces:
        issues_found.append(f"Brace mismatch: {open_braces} open, {close_braces} close")
        # Try to fix by adding missing braces
        if open_braces > close_braces:
            tex += '}' * (open_braces - close_braces)
            changed = True
            issues_found.append("Added missing closing braces")
    
    return tex, changed, issues_found

def sanitize_preamble(tex: str) -> tuple[str, bool]:
    """
    Legacy function - now uses the comprehensive cleaning system
    """
    cleaned_tex, changed, issues = clean_latex_content(tex)
    return cleaned_tex, changed

# Simple in-memory storage for demo
projects = {}
patches = {}

# Initialize services
template_service = TemplateService()
compile_service = CompileService()
parse_service = CleanParseService()

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

# Check Anthropic API key on startup
if LLM_API_KEY:
    print("✅ DEBUG: Anthropic API key found - AI features enabled")
else:
    print("⚠️ WARNING: No Anthropic API key found - using fallback template mode")
    print("💡 TIP: Set ANTHROPIC_API_KEY environment variable to enable AI features")

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
    
    # Use AI to parse the compressed text properly
    print("🤖 DEBUG: Using AI to parse compressed text")
    
    # Create a clean, professional prompt for the AI to parse messy text
    parse_prompt = f"""
    Parse this resume text and extract structured data. Be precise and professional.

    Text: {text_content}

    Extract:
    1. Personal info: name, email, phone, location, LinkedIn
    2. Work experience: company, title, dates, location, descriptions
    3. Education: school, degree, dates, GPA
    4. Projects: name, technologies, dates, descriptions
    5. Skills: all technical skills

    Rules:
    - Extract everything you can find
    - Remove duplicates
    - Use empty strings for missing data
    - Be clean and professional

    Return JSON:
    {{
        "basics": {{"name": "", "email": "", "phone": "", "location": "", "linkedin": ""}},
        "experience": [{{"company": "", "title": "", "start_date": "", "end_date": "", "location": "", "description": []}}],
        "education": [{{"school": "", "degree": "", "start_date": "", "end_date": "", "gpa": ""}}],
        "projects": [{{"name": "", "tech_stack": "", "start_date": "", "description": []}}],
        "skills": []
    }}
    """
    
    try:
        # Use Claude to parse the text
        print(" DEBUG: Calling Anthropic API...")
        ai_response = claude_complete(
            system="You are a professional resume parsing expert. Extract structured data from compressed resume text with high accuracy. Return clean, professional JSON with complete information extraction. Focus on clarity and precision.",
            user=parse_prompt,
            max_tokens=4000,
        )

        print(f"🤖 DEBUG: Anthropic response received: {len(ai_response)} characters")

        # Parse the JSON response (json is imported at module level)
        print(f"🤖 DEBUG: AI response preview: {ai_response[:200]}...")
        
        # Clean the response (remove markdown code blocks if present)
        if ai_response.startswith('```json'):
            ai_response = ai_response[7:]  # Remove ```json
        if ai_response.startswith('```'):
            ai_response = ai_response[3:]  # Remove ```
        if ai_response.endswith('```'):
            ai_response = ai_response[:-3]  # Remove trailing ```
        
        ai_response = ai_response.strip()
        print(f"🤖 DEBUG: Cleaned AI response preview: {ai_response[:200]}...")
        
        resume_data = json.loads(ai_response)
        print(f"✅ DEBUG: AI parsed resume with {len(resume_data.get('experience', []))} experiences, {len(resume_data.get('education', []))} education entries")
        
    except json.JSONDecodeError as e:
        print(f"⚠️ DEBUG: JSON parsing failed: {e}")
        print(f"⚠️ DEBUG: AI response was: {ai_response[:500]}...")
        # Fallback to CleanParseService
        parse_service = CleanParseService()
        resume_data = parse_service.parse_resume_text(text_content)
        
    except Exception as e:
        print(f"⚠️ DEBUG: AI parsing failed, using fallback: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to CleanParseService
        parse_service = CleanParseService()
        resume_data = parse_service.parse_resume_text(text_content)
    
    # Generate LaTeX using TemplateService
    template_service = TemplateService()
    latex = template_service.render_resume(resume_data)
    
    print(f"📄 DEBUG: Generated LaTeX using improved parsing (length: {len(latex)})")
    print(f"📄 DEBUG: LaTeX preview: {latex[:200]}...")
    
    # The template service already generates clean LaTeX, no need for additional formatting
    
    return latex

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

def validate_and_improve_changes(changes_data: list, resume_tex: str) -> list:
    """
    Backstop: if a removal doesn't span the full experience block, expand it.
    A block is: \textbf{Company} ... \end{itemize} (+ optional \vspace and blank lines).

    IMPORTANT: Only expand structural removals (experience blocks).
    Do NOT expand simple field changes (name, email, etc.)
    """
    lines = resume_tex.splitlines()
    N = len(lines)
    def expand_block(start0: int, end0: int) -> tuple[int, int]:
        # move start up to nearest \textbf{...} or section header
        s = start0
        while s > 0 and not (lines[s].lstrip().startswith(r'\textbf{') or
                             lines[s].lstrip().startswith(r'\section*{') or
                             'Experience' in lines[s]):
            s -= 1
        # if we didn't land on a bold header, keep original
        if not lines[s].lstrip().startswith(r'\textbf{'):
            s = start0
        # move end down through \end{itemize}, optional \vspace, and trailing blank
        e = max(end0, s)
        while e < N-1 and not lines[e].lstrip().startswith(r'\end{itemize}'):
            e += 1
        if e < N-1 and lines[e].lstrip().startswith(r'\end{itemize}'):
            # include optional \vspace and one following blank line
            if e+1 < N and re.match(r'^\s*\\vspace\{[^}]+\}\s*$', lines[e+1]):
                e += 1
            if e+1 < N and lines[e+1].strip() == '':
                e += 1
        return s, e

    improved = []
    for ch in (changes_data or []):
        # Only expand removals, NOT replacements (replacements are often simple field changes)
        if (ch.get('type') or ch.get('change_type')) == 'removal':
            # 1-indexed → 0-indexed
            s0 = max(0, (ch.get('start_line') or ch.get('startLine') or 1) - 1)
            e0 = max(s0, (ch.get('end_line') or ch.get('endLine') or (s0+1)) - 1)
            # if content shows only items or a partial block, expand
            body = ch.get('content') or ''
            looks_partial = ('\\item' in body and '\\textbf{' not in body) or ('\\textbf{' in body and '\\end{itemize}' not in body)
            if looks_partial:
                s, e = expand_block(s0, e0)
                ch['start_line'] = s + 1
                ch['end_line'] = e + 1
                ch['content'] = '\n'.join(lines[s:e+1])
                print(f"🔧 DEBUG: Expanded removal from lines {s0+1}-{e0+1} to {s+1}-{e+1}")
        improved.append(ch)
    return improved

def find_experience_block_end(lines: list, start_line: int) -> int:
    """Legacy helper: keep for other callers; ends at \end{itemize} (+ optional vspace/blank)."""
    i = start_line
    N = len(lines)
    while i < N and not lines[i].lstrip().startswith(r'\end{itemize}'):
        i += 1
    if i < N and lines[i].lstrip().startswith(r'\end{itemize}'):
        if i+1 < N and re.match(r'^\s*\\vspace\{[^}]+\}\s*$', lines[i+1]):
            i += 1
        if i+1 < N and lines[i+1].strip() == '':
            i += 1
    return min(i, N-1)

def validate_change_scope(changes_data: list, instruction: str, resume_tex: str) -> list:
    """
    Simplified validation that trusts AI-generated changes more.
    Only validates truly problematic cases.
    """
    if not changes_data:
        return changes_data

    instruction_lower = instruction.lower()

    print(f"🔧 DEBUG: Validating {len(changes_data)} changes for instruction: '{instruction[:50]}...'")

    # Check if this is a removal/deletion request - these should allow structural changes
    is_removal_request = any(keyword in instruction_lower for keyword in ['remove', 'delete', 'take out', 'get rid of'])

    if is_removal_request:
        print(f"✅ DEBUG: Removal request detected - allowing structural changes")
        return changes_data

    # Check if this is an addition request - these should also allow structural changes
    is_addition_request = any(keyword in instruction_lower for keyword in ['add', 'insert', 'include', 'put in'])

    if is_addition_request:
        print(f"✅ DEBUG: Addition request detected - allowing structural changes")
        return changes_data

    # Only for simple single-field changes (name, email, phone), validate scope
    simple_field_keywords = ['name', 'email', 'phone']
    is_simple_field = any(word in instruction_lower for word in simple_field_keywords)

    if is_simple_field:
        print(f"🔧 DEBUG: Simple field change detected - validating scope")

        # Allow changes from AI, but warn if they seem too broad
        valid_changes = []
        for change in changes_data:
            start_line = change.get('start_line', 1)
            end_line = change.get('end_line', 1)
            span = end_line - start_line + 1

            # Allow changes up to 10 lines (most simple changes should be 1-3 lines)
            if span > 10:
                print(f"⚠️ DEBUG: Change spans {span} lines which seems broad for a simple field change")
                print(f"⚠️ DEBUG: But trusting AI and allowing it anyway")

            valid_changes.append(change)

        return valid_changes

    # For all other cases, trust the AI completely
    print(f"✅ DEBUG: Trusting AI-generated changes")
    return changes_data

def apply_changes_to_latex(latex_content: str, changes: list) -> str:
    """Apply changes directly to LaTeX content with comprehensive validation"""
    if not changes or not latex_content:
        return latex_content
    
    # First, clean the original content
    print(f"🔧 DEBUG: Cleaning original LaTeX content before applying changes")
    latex_content, was_cleaned, initial_issues = clean_latex_content(latex_content)
    
    if was_cleaned:
        print(f"🔧 DEBUG: Fixed {len(initial_issues)} initial issues in LaTeX")
        for issue in initial_issues[:3]:  # Show first 3 issues
            print(f"   - {issue}")
    
    lines = latex_content.split('\n')
    
    # Group changes by line number and handle them together
    changes_by_line = {}
    for change in changes:
        # Handle both dict and Pydantic Change objects
        if hasattr(change, 'start_line'):
            start_line = change.start_line - 1  # Convert to 0-indexed
        else:
            start_line = change.get('start_line', 1) - 1  # Convert to 0-indexed
        if start_line not in changes_by_line:
            changes_by_line[start_line] = []
        changes_by_line[start_line].append(change)
    
    # Process changes line by line in descending order
    for line_num in sorted(changes_by_line.keys(), reverse=True):
        line_changes = changes_by_line[line_num]
        
        # Handle removals first, then additions/replacements
        removals = [c for c in line_changes if (hasattr(c, 'type') and c.type == 'removal') or (hasattr(c, 'get') and c.get('type') == 'removal')]
        additions = [c for c in line_changes if (hasattr(c, 'type') and c.type == 'addition') or (hasattr(c, 'get') and c.get('type') == 'addition')]
        replacements = [c for c in line_changes if (hasattr(c, 'type') and c.type == 'replacement') or (hasattr(c, 'get') and c.get('type') == 'replacement')]
        
        print(f"🔧 DEBUG: Processing line {line_num + 1}: {len(removals)} removals, {len(additions)} additions, {len(replacements)} replacements")
        
        # Apply removals first
        for change in removals:
            if hasattr(change, 'end_line'):
                end_line = change.end_line - 1
            elif hasattr(change, 'get'):
                end_line = change.get('end_line', line_num + 1) - 1
            else:
                end_line = line_num
            print(f"🔧 DEBUG: Removing lines {line_num + 1}-{end_line + 1}")
            lines = lines[:line_num] + lines[end_line + 1:]
        
        # Apply additions/replacements with validation
        for change in additions + replacements:
            if hasattr(change, 'content'):
                content = change.content
            elif hasattr(change, 'get'):
                content = change.get('content', '')
            else:
                content = ''
            
            # Clean the content before applying it
            content, content_cleaned, content_issues = clean_latex_content(content)
            if content_cleaned:
                print(f"🔧 DEBUG: Cleaned change content: {len(content_issues)} issues fixed")
            
            # Determine if this is a replacement (same start and end line)
            if hasattr(change, 'end_line'):
                end_line = change.end_line - 1
            elif hasattr(change, 'get'):
                end_line = change.get('end_line', line_num + 1) - 1
            else:
                end_line = line_num
            
            new_lines = content.split('\n')
            
            # If it's a single-line replacement (start_line == end_line), replace that line
            if line_num == end_line:
                print(f"🔧 DEBUG: Replacing single line {line_num + 1} with: {content[:50]}...")
                if line_num < len(lines):
                    lines[line_num] = content
                else:
                    lines.append(content)
            else:
                # Multi-line replacement or addition
                print(f"🔧 DEBUG: Adding content at line {line_num + 1}")
                lines = lines[:line_num] + new_lines + lines[line_num:]
    
    # Final comprehensive cleaning pass
    result = '\n'.join(lines)
    result, final_cleaned, final_issues = clean_latex_content(result)
    
    if final_cleaned:
        print(f"🔧 DEBUG: Final cleaning pass fixed {len(final_issues)} issues")
        for issue in final_issues[:3]:  # Show first 3 issues
            print(f"   - {issue}")
    
    return result

def fix_compilation_errors(latex_content: str, original_request: str, project_id: str, max_attempts: int = 3) -> tuple[str, bool]:
    """Validate LaTeX by compiling it; on failure, send the compiler error
    back to the AI for repair (up to max_attempts).

    Returns (latex, compiled_ok). Callers must treat compiled_ok=False as a
    rejected proposal and keep their last-known-good content — the gate
    fails closed.
    """
    if not latex_content:
        return latex_content, False

    for attempt in range(max_attempts):
        print(f" DEBUG: Testing compilation (attempt {attempt + 1}/{max_attempts})")

        # Test compilation
        success, pdf_path, error_msg = compile_service.compile_latex(latex_content, f"{project_id}_test")

        if success:
            print(f"DEBUG: LaTeX compiles successfully")
            return latex_content, True
        
        print(f"DEBUG: Compilation failed: {error_msg}")
        
        if attempt < max_attempts - 1:
            # Send error back to AI for fixing
            try:
                print(f" DEBUG: Sending compilation error to AI for fixing...")
        
                fix_prompt = f"""The LaTeX code I generated has compilation errors. Please fix it.

Original request: {original_request}

Current LaTeX code:
{latex_content}

Compilation error: {error_msg}

Please provide the corrected LaTeX code that will compile without errors. Return only the LaTeX code, no explanations."""
                
                fixed_latex = claude_complete(
                    system="You are a LaTeX expert. Fix compilation errors and return clean, working LaTeX code.",
                    user=fix_prompt,
                    max_tokens=4000,
                ).strip()
                
                # Clean up the response (remove markdown code blocks if present)
                if fixed_latex.startswith('```latex'):
                    fixed_latex = fixed_latex[8:]
                if fixed_latex.startswith('```'):
                    fixed_latex = fixed_latex[3:]
                if fixed_latex.endswith('```'):
                    fixed_latex = fixed_latex[:-3]
                fixed_latex = fixed_latex.strip()
                
                print(f"🔧 DEBUG: AI provided fixed LaTeX (length: {len(fixed_latex)})")
                latex_content = fixed_latex
                
            except Exception as e:
                print(f"❌ DEBUG: AI fix attempt failed: {e}")
                break
        else:
            print(f"❌ DEBUG: Max attempts reached, rejecting the edit")
            break

    return latex_content, False

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

# Removed problematic function - using AI parsing instead
# def _parse_experience_line_improved_removed(line: str, experience: list, current_item: dict):
#     """Parse experience section with improved logic"""
#     line = line.strip()
#     if not line:
#         return current_item
        
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
    
    # Use CleanParseService for parsing (preserve full content with correct sections)
    parse_service = CleanParseService()
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
        print(f"🔍 DEBUG: Anthropic API key status: {'Found' if LLM_API_KEY else 'Missing'}")
        
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
        
        if not LLM_API_KEY:
            print("❌ ERROR: No Anthropic API key provided")
            raise HTTPException(status_code=500, detail="Anthropic API key is required for patch generation")

        print("🤖 DEBUG: Using Claude for patch generation")
        try:
            # Use OpenAI to generate real patches
            system_prompt = """You are a LaTeX resume expert. Generate specific, targeted changes to improve a resume based on the user's instruction.

CRITICAL RULES FOR GENERATING CHANGES:
1. BE PRECISE AND MINIMAL: Only change what the user explicitly requests
2. For simple edits (name, email, phone, dates), create single-line replacements (start_line = end_line)
3. For content additions, add new bullet points or sections without removing existing content
4. For content improvements, enhance existing text while preserving structure
5. NEVER generate changes that span more than 3-5 lines unless explicitly removing large blocks
6. When adding content, use type='addition' and insert at appropriate locations
7. When replacing content, use type='replacement' with exact line ranges
8. When removing content, use type='removal' only when explicitly requested

SPECIAL HANDLING FOR NAME CHANGES:
- Look for \\textbf{Current Name} patterns in the LaTeX
- Replace ONLY the name inside the braces
- Keep the \\textbf{} command intact
- Always generate a change for name replacement requests

EXAMPLE PATTERNS:

Name change (ALWAYS generate this for name requests):
[{
  "id": "name_change",
  "type": "replacement",
  "start_line": 8,
  "end_line": 8,
  "content": "\\textbf{Jennifer Adams}",
  "pdf_regions": [{"x": 50, "y": 100, "width": 400, "height": 30}]
}]

Email change:
[{
  "id": "email_change",
  "type": "replacement",
  "start_line": 9,
  "end_line": 9,
  "content": "Email: jennifer.adams@email.com | Phone: (555) 123-4567",
  "pdf_regions": [{"x": 50, "y": 120, "width": 400, "height": 20}]
}]

Add new bullet point:
[{
  "id": "bullet_addition", 
  "type": "addition",
  "start_line": 25,
  "end_line": 25,
  "content": "\\item Implemented new feature that increased efficiency by 20%",
  "pdf_regions": [{"x": 70, "y": 350, "width": 450, "height": 20}]
}]

Improve existing bullet point:
[{
  "id": "bullet_improvement",
  "type": "replacement", 
  "start_line": 23,
  "end_line": 23,
  "content": "\\item Enhanced system architecture resulting in 40% performance improvement and $50K cost savings",
  "pdf_regions": [{"x": 70, "y": 330, "width": 450, "height": 20}]
}]

IMPORTANT: 
- Always return valid JSON array
- Each change must have all required fields: id, type, start_line, end_line, content, pdf_regions
- For name changes, ALWAYS generate at least one change - never return empty array
- Look carefully at the LaTeX to find the correct line numbers"""

            user_prompt = f"""Instruction: {request.instruction}

Current LaTeX content:
{project.get('resume_tex', 'No content available')}

IMPORTANT: 
- If the instruction is to change a name, only modify the \\textbf{{Name}} line
- If the instruction is to change contact info, only modify the contact line
- If the instruction is to remove a specific company/project/school, then delete the entire block
- Make MINIMAL changes - don't delete more than necessary
- Focus on the specific request, not making broad changes

Generate specific changes to implement this instruction."""

            print(f"📤 DEBUG: Sending patch request to OpenAI")
            print(f"🔍 DEBUG: System prompt: {system_prompt[:200]}...")
            print(f"🔍 DEBUG: User prompt: {user_prompt[:200]}...")
            
            ai_response = claude_complete(
                system=system_prompt,
                user=user_prompt,
                max_tokens=4000,
            )
            print(f"📥 DEBUG: Received from OpenAI: {ai_response[:200]}...")
            
            # Parse AI response
            try:
                # Clean the AI response to fix escape sequences
                cleaned_response = ai_response.replace('\\', '\\\\')  # Fix escape sequences
                changes_data = json.loads(cleaned_response)
                
                # Validate and improve multi-line deletions
                changes_data = validate_and_improve_changes(changes_data, project.get('resume_tex', ''))
                
                # Additional validation to prevent overly broad changes
                changes_data = validate_change_scope(changes_data, request.instruction, project.get('resume_tex', ''))
                
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
    """Improved chat with direct LaTeX updates - simpler and more reliable"""
    try:
        message = request.get('message', '')
        chat_history = request.get('chat_history', [])
        current_resume = request.get('current_resume', '')
        context = request.get('context', {})

        print(f"🤖 DEBUG: Chat request: {message[:100]}...")
        print(f"📚 DEBUG: Chat history length: {len(chat_history)}")
        print(f"📄 DEBUG: Current resume length: {len(current_resume) if current_resume else 0}")

        if not LLM_API_KEY:
            raise HTTPException(status_code=500, detail="Anthropic API key is required")

        # Enhanced system prompt for better resume editing
        system_prompt = """You are an expert AI resume editor and career advisor. You help users create, edit, and perfect their resumes through natural conversation.

CORE CAPABILITIES:
✓ Instant resume edits - change names, contact info, dates, descriptions
✓ Content optimization - improve bullet points with metrics and impact
✓ Structure management - add/remove/reorganize sections
✓ Length optimization - fit to 1-page, 2-page, or custom length
✓ ATS optimization - ensure compatibility with applicant tracking systems
✓ Role targeting - tailor resumes for specific job positions

EDITING PHILOSOPHY:
- Make changes immediately when user gives clear instructions
- Ask clarifying questions only when truly necessary

RESPONSE STYLE (important):
- Keep your chat reply SHORT — one or two plain sentences, max.
- Just say what you changed, like a helpful colleague. No preamble, no headers, no bullet lists, no "A few honest notes" sections.
- Sound natural and human, not formal or robotic. Don't restate the resume back.
- Only flag something extra (e.g. a missing skill) if it's genuinely important, and keep it to one short sentence.
- The detailed change summary goes in the JSON "explanation" field, NOT in your chat reply — don't repeat it.

WHEN USER WANTS TO EDIT (name, email, dates, content, etc.):
1. If you have the current LaTeX resume, make the edit directly
2. Return the complete updated LaTeX in your response
3. Use this JSON format in your response:
   ```json
   {
     "action": "update_resume",
     "updated_latex": "complete updated LaTeX here",
     "explanation": "brief explanation of what changed"
   }
   ```

WHEN USER ASKS QUESTIONS OR WANTS ADVICE:
- Provide helpful, actionable advice
- Reference specific parts of their resume if available
- No JSON response needed for pure conversation

LATEX EDITING RULES:
- Preserve document structure and formatting
- Maintain professional ATS-friendly layout
- Use strong action verbs and quantifiable metrics
- Keep bullet points concise (1-2 lines max)
- Ensure proper LaTeX syntax (matched braces, valid commands)

EXAMPLE INTERACTIONS:

User: "Change my name to Jennifer Adams"
Assistant: I've updated your name to Jennifer Adams.
```json
{
  "action": "update_resume",
  "updated_latex": "\\documentclass{article}...\n\\begin{center}\n\\textbf{Jennifer Adams}\n...",
  "explanation": "Updated name from previous name to Jennifer Adams"
}
```

User: "Make this a 1-page resume"
Assistant: I'll condense your resume to fit on one page by removing older experiences and tightening descriptions.
```json
{
  "action": "update_resume",
  "updated_latex": "condensed LaTeX content...",
  "explanation": "Condensed to 1 page by removing 2 older positions and shortening bullet points"
}
```

User: "What should I emphasize for a software engineering role?"
Assistant: For software engineering roles, emphasize: technical skills (languages, frameworks), quantifiable achievements (performance improvements, scale), system design experience, and collaborative projects. Your current experience with distributed systems and API development would be great to highlight.

Remember: You're having a natural conversation. Be helpful, concise, and proactive!"""

        # Claude takes the system prompt separately (not as a message). Fold the
        # resume context into the system prompt.
        full_system = system_prompt
        if current_resume and len(current_resume) > 0:
            full_system += f"\n\nCurrent resume LaTeX:\n```latex\n{current_resume}\n```"

        # Build conversation messages (user/assistant only). Claude rejects a
        # leading assistant turn, so drop any until the first user message.
        convo = []
        for msg in chat_history[-6:]:
            role = 'assistant' if msg.get('role') == 'assistant' else 'user'
            if not convo and role != 'user':
                continue
            convo.append({"role": role, "content": msg.get('content', '')})
        convo.append({"role": "user", "content": message})

        print(f"📤 DEBUG: Sending to Claude with {len(convo)} messages")

        response = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4000,
            system=full_system,
            messages=convo,
        )

        ai_response = "".join(block.text for block in response.content if block.type == "text")
        print(f"📥 DEBUG: Received response ({len(ai_response)} chars)")

        # Parse AI response for LaTeX updates
        is_resume_update = False
        update_rejected = False
        resume_data = None
        explanation = ""

        # Check if AI returned JSON with updated LaTeX
        try:
            # Look for JSON code block in response
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                update_data = json.loads(json_str)

                if update_data.get('action') == 'update_resume' and update_data.get('updated_latex'):
                    resume_data = update_data['updated_latex']
                    explanation = update_data.get('explanation', '')

                    # Clean and validate the LaTeX
                    resume_data, was_cleaned, issues = clean_latex_content(resume_data)
                    if was_cleaned:
                        print(f"🧹 DEBUG: Cleaned AI-generated LaTeX ({len(issues)} issues fixed)")

                    # Validation gate: the edit must compile (with AI repair
                    # attempts). Fail CLOSED — a candidate that never compiles
                    # is discarded and the stored resume stays untouched.
                    project_id = context.get('project_id', 'default')
                    resume_data, compiled_ok = fix_compilation_errors(resume_data, message, project_id)

                    if not compiled_ok:
                        print(f"❌ DEBUG: Edit rejected — never compiled; keeping last good version")
                        update_rejected = True
                        resume_data = None
                        explanation = ""
                    else:
                        # The candidate passed the compile gate, but it is NOT
                        # persisted here. It goes back to the user as a proposal;
                        # the frontend applies it via /project/recreate only after
                        # the user explicitly approves. Model proposes, gate
                        # validates, human approves.
                        is_resume_update = True
                        print(f"✅ DEBUG: Validated candidate returned for user approval")
        except json.JSONDecodeError as e:
            print(f"⚠️ DEBUG: No JSON update found in response: {e}")
        except Exception as e:
            print(f"⚠️ DEBUG: Error parsing AI response: {e}")

        # Extract clean response text (remove JSON block)
        response_text = re.sub(r'```json\s*\{.*?\}\s*```', '', ai_response, flags=re.DOTALL).strip()

        if update_rejected:
            rejection_note = ("I couldn't apply that change safely — the edited document "
                              "failed to compile even after repair attempts, so your resume "
                              "was left unchanged. Try rephrasing the request.")
            response_text = f"{response_text}\n\n{rejection_note}".strip() if response_text else rejection_note

        return {
            "response": response_text,
            "is_resume_update": is_resume_update,
            "resume_data": resume_data,
            "requires_approval": is_resume_update,
            "explanation": explanation,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"❌ ERROR: Chat failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


def _count_pdf_pages(pdf_path: str):
    """Return the number of pages in a compiled PDF, or None if unknown."""
    try:
        import PyPDF2
        with open(pdf_path, 'rb') as f:
            return len(PyPDF2.PdfReader(f).pages)
    except Exception as e:
        print(f"⚠️ DEBUG: page count failed: {e}")
        return None


def _strip_latex_fences(text: str) -> str:
    """Strip markdown ```latex ... ``` fences from an AI response."""
    t = (text or "").strip()
    if t.startswith("```latex"):
        t = t[8:]
    elif t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    return t.strip()


@app.post("/llm/fit-one-page")
def fit_one_page(request: dict):
    """Iteratively condense the resume until its compiled PDF is a single page.

    Loop: compile -> count pages -> if > 1, ask Claude to condense -> repeat,
    up to a hard cap. Each candidate is validated by compiling it.
    """
    project_id = request.get('project_id')
    if not project_id or project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    if not LLM_API_KEY:
        raise HTTPException(status_code=500, detail="Anthropic API key is required")

    project = projects[project_id]
    latex = request.get('resume') or project.get('resume_tex', '')
    if not latex:
        raise HTTPException(status_code=400, detail="No resume content to fit")

    MAX_ITERS = 5
    pages = None
    iterations = 0
    success = False
    last_good = None  # last draft that actually compiled

    for i in range(MAX_ITERS + 1):
        # Compile the current draft and count its pages.
        cleaned, _, _ = clean_latex_content(latex)
        latex = cleaned
        success, pdf_path, err = compile_service.compile_latex(latex, f"{project_id}_fit")
        if success:
            last_good = latex
        pages = _count_pdf_pages(pdf_path) if success and pdf_path else None
        print(f"📏 DEBUG: fit-one-page iter {i}: compiled={success}, pages={pages}")

        if pages is not None and pages <= 1:
            print("✅ DEBUG: resume now fits on one page")
            break
        if i == MAX_ITERS:
            print("⚠️ DEBUG: hit max fit iterations; using best effort")
            break

        # Ask Claude to condense, getting more aggressive the further over we are.
        system_prompt = (
            "You are a LaTeX resume expert. You condense resumes to EXACTLY one page "
            "while keeping them truthful, professional, and ATS-friendly."
        )
        user_prompt = f"""This resume currently compiles to {pages if pages else 'more than 1'} pages. Rewrite the FULL LaTeX so it fits on EXACTLY ONE page.

Shorten in this order of preference:
1. Tighten wording — make each bullet a single crisp idea; cut filler and weak qualifiers.
2. Trim the least-relevant or oldest content — drop a weak bullet, or the oldest/least-relevant role, if needed.
3. Reduce vertical spacing (\\vspace, \\parskip). You may set the font to 10pt and margins to ~0.5in.

Rules:
- Keep bullets ATOMIC — one accomplishment per bullet, ideally one line. NEVER merge several accomplishments into one long run-on sentence; to save space, drop the weakest bullet instead of merging.
- Stay truthful — do not invent experience, employers, metrics, or credentials.
- Keep the same overall structure and section style.
- Keep the most relevant experience and the contact header.
- Return ONLY the full updated LaTeX document, no commentary, no markdown fences.

Current LaTeX:
{latex}"""

        try:
            resp = claude_complete(system=system_prompt, user=user_prompt, max_tokens=4000)
            candidate = _strip_latex_fences(resp)
            if candidate and "\\documentclass" in candidate and "\\end{document}" in candidate:
                latex = candidate
                iterations += 1
            else:
                print("⚠️ DEBUG: condense returned unusable LaTeX; stopping")
                break
        except Exception as e:
            print(f"❌ ERROR: fit-one-page condense failed: {e}")
            break

    # Fail closed: never persist a draft that doesn't compile.
    if not success and last_good:
        print("⚠️ DEBUG: final draft didn't compile; reverting to last compiling version")
        latex = last_good

    project["resume_tex"] = latex
    project["last_updated"] = datetime.utcnow().isoformat()
    projects[project_id] = project
    save_projects()

    return {
        "resume_tex": latex,
        "pages": pages,
        "fit": pages == 1,
        "iterations": iterations,
    }


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
        
        # Comprehensive LaTeX cleaning and validation
        print(f"🧹 DEBUG: Starting comprehensive LaTeX cleaning")
        original_length = len(latex_content)
        latex_content, was_cleaned, issues_found = clean_latex_content(latex_content)
        
        if was_cleaned:
            project["resume_tex"] = latex_content
            print(f"🧹 DEBUG: LaTeX cleaned successfully - {len(issues_found)} issues fixed")
            print(f"   Length changed: {original_length} -> {len(latex_content)} chars")
            for issue in issues_found[:5]:  # Show first 5 issues
                print(f"   - {issue}")
        else:
            print(f"✅ DEBUG: LaTeX content is already clean")
        
        print(f"✅ DEBUG: Found project, compiling LaTeX to PDF")
        print(f"📄 DEBUG: LaTeX content length: {len(latex_content)}")
        
        # Use compile service to generate PDF
        success, pdf_path, error_msg = compile_service.compile_latex(latex_content, project_id)
        
        # If compilation fails due to LaTeX errors, try regenerating with Claude
        if not success and error_msg and any(keyword in error_msg.lower() for keyword in ['undefined', 'missing', 'error', 'ewcommand']):
            print(f" DEBUG: PDF compilation failed with LaTeX errors, attempting AI-powered recovery")
            print(f"   Error: {error_msg[:200]}...")
            
            try:
                # Use Claude to fix the LaTeX
                fix_prompt = f"""The following LaTeX code has compilation errors. Please fix it and return clean, valid LaTeX that will compile without errors.

Errors encountered: {error_msg}

LaTeX code to fix:
{latex_content}

Rules:
1. Return only valid LaTeX code
2. Remove any broken commands like 'ewcommand' without backslash
3. Ensure all braces are properly matched
4. Keep the content structure intact
5. Use standard LaTeX packages only"""
                
                fixed_latex = claude_complete(
                    system="You are a LaTeX expert. Fix broken LaTeX code and return clean, compilable LaTeX.",
                    user=fix_prompt,
                    max_tokens=4000,
                ).strip()
                
                # Clean up the AI response
                if fixed_latex.startswith('```latex'):
                    fixed_latex = fixed_latex[8:]
                elif fixed_latex.startswith('```'):
                    fixed_latex = fixed_latex[3:]
                if fixed_latex.endswith('```'):
                    fixed_latex = fixed_latex[:-3]
                fixed_latex = fixed_latex.strip()
                
                # Apply comprehensive cleaning to AI-fixed content
                fixed_latex, ai_cleaned, ai_issues = clean_latex_content(fixed_latex)
                
                print(f"🤖 DEBUG: AI fixed LaTeX, attempting recompilation")
                print(f"   AI fixes: {len(ai_issues)} additional issues resolved")
                
                # Update project with fixed content
                project["resume_tex"] = fixed_latex
                latex_content = fixed_latex
                
                # Retry compilation
                success, pdf_path, error_msg = compile_service.compile_latex(latex_content, project_id)
                
                if success:
                    print(f"✅ DEBUG: AI-powered recovery successful!")
                else:
                    print(f"❌ DEBUG: AI-powered recovery failed: {error_msg[:200]}...")
                    
            except Exception as e:
                print(f"❌ DEBUG: AI-powered recovery error: {e}")
        
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