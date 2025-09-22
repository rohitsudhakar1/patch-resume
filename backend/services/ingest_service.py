"""
Service for processing uploaded resume files and converting to LaTeX
"""
import os
import tempfile
import io
from typing import Dict, Any, Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session
import PyPDF2
import docx
import pytesseract
from PIL import Image
try:
    import fitz  # PyMuPDF for better PDF processing
except ImportError:
    fitz = None

from ..database import Project
from ..models import IngestResponse
from ..config import settings

class IngestService:
    def __init__(self):
        self.tesseract_path = settings.tesseract_path
        if self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

    async def process_file(self, file: UploadFile, db: Session) -> IngestResponse:
        """Process uploaded file and convert to structured resume"""
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # Extract text based on file type
            if file.content_type == "application/pdf":
                text_content = await self._extract_from_pdf(tmp_file_path)
            elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                text_content = await self._extract_from_docx(tmp_file_path)
            elif file.content_type == "text/plain":
                text_content = await self._extract_from_txt(tmp_file_path)
            else:
                raise ValueError("Unsupported file type")

            # Parse and structure the resume
            structured_resume = await self._parse_resume_structure(text_content)
            
            # Generate LaTeX
            latex_content = await self._generate_latex(structured_resume)
            
            # Create project in database
            project = Project(
                owner="default_user",  # In real app, get from auth
                resume_tex=latex_content,
                compile_status="pending"
            )
            db.add(project)
            db.commit()
            db.refresh(project)
            
            return IngestResponse(
                project_id=str(project.id),
                resume_tex=latex_content,
                pdf_url=f"/artifact/pdf/{project.id}",
                reconstruction_note=self._get_reconstruction_note(structured_resume)
            )
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)

    async def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF with OCR fallback for scanned documents"""
        try:
            # Try PyMuPDF first (better for text-based PDFs) if available
            if fitz:
                doc = fitz.open(file_path)
                text_content = ""
                
                for page in doc:
                    page_text = page.get_text()
                    if page_text.strip():
                        text_content += page_text + "\n"
                    else:
                        # If no text found, try OCR
                        pix = page.get_pixmap()
                        img_data = pix.tobytes("png")
                        ocr_text = pytesseract.image_to_string(Image.open(io.BytesIO(img_data)))
                        text_content += ocr_text + "\n"
                
                doc.close()
                return text_content
            else:
                raise Exception("PyMuPDF not available")
            
        except Exception as e:
            # Fallback to PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
                return text_content

    async def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        doc = docx.Document(file_path)
        text_content = ""
        for paragraph in doc.paragraphs:
            text_content += paragraph.text + "\n"
        return text_content

    async def _extract_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file"""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def _clean_text_content(self, text: str) -> str:
        """Clean and normalize text content to remove unwanted characters and sequences"""
        if not text:
            return ""
        
        import re
        
        # Handle specific problematic sequences that appear in the resume
        # Remove \n\ sequences (newline followed by backslash)
        text = re.sub(r'\\n\\', '\n', text)
        
        # Remove standalone \n sequences (but preserve actual newlines)
        text = re.sub(r'(?<!\\)\\n(?!\\)', '\n', text)
        
        # Handle specific problematic patterns that cause LaTeX compilation errors
        text = re.sub(r'\\Personal\s*', 'Personal ', text)
        text = re.sub(r'\\Jan\s*', 'Jan ', text)
        text = re.sub(r'\\&', '&', text)
        
        # Remove backslashes that are not part of legitimate LaTeX commands
        # Keep common LaTeX commands but remove problematic ones
        legitimate_latex_commands = ['textbf', 'textit', 'section', 'subsection', 'itemize', 'item', 'begin', 'end', 'documentclass', 'usepackage', 'href', 'url']
        
        # Remove backslashes that are not followed by legitimate LaTeX commands
        text = re.sub(r'\\(?!' + '|'.join(legitimate_latex_commands) + r')\w+', '', text)
        
        # Remove standalone backslashes that are not part of LaTeX commands
        text = re.sub(r'(?<!\\)\\(?!\w)', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple newlines to double newline
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single space
        text = re.sub(r'\n[ \t]+', '\n', text)  # Remove leading spaces from lines
        
        # Clean up any remaining problematic sequences
        text = re.sub(r'\\[^a-zA-Z]', '', text)  # Remove backslash followed by non-letters
        
        return text.strip()

    async def _parse_resume_structure(self, text: str) -> Dict[str, Any]:
        """Parse unstructured text into structured resume format"""
        # Clean the text first
        text = self._clean_text_content(text)
        lines = text.split('\n')
        
        # Initialize structure
        resume = {
            "basics": {"name": "", "email": "", "phone": "", "linkedin": "", "github": ""},
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
            section = self._detect_section(line)
            if section:
                current_section = section
                continue
            
            # Process based on current section
            if current_section == "basics":
                self._parse_basics(line, resume["basics"])
            elif current_section == "summary":
                resume["summary"] += line + " "
            elif current_section == "experience":
                self._parse_experience_line(line, resume["experience"], current_item)
            elif current_section == "education":
                self._parse_education_line(line, resume["education"])
            elif current_section == "projects":
                self._parse_projects_line(line, resume["projects"])
            elif current_section == "skills":
                resume["skills"].extend([s.strip() for s in line.split(',')])
        
        # Clean up
        resume["summary"] = resume["summary"].strip()
        resume["skills"] = [s for s in resume["skills"] if s]
        
        return resume

    def _detect_section(self, line: str) -> Optional[str]:
        """Detect section headers using heuristics"""
        line_lower = line.lower()
        
        # Check for common section headers
        if any(keyword in line_lower for keyword in ["contact", "personal", "name", "@", "phone"]):
            return "basics"
        elif any(keyword in line_lower for keyword in ["summary", "objective", "profile", "about"]):
            return "summary"
        elif any(keyword in line_lower for keyword in ["experience", "employment", "work", "career"]):
            return "experience"
        elif any(keyword in line_lower for keyword in ["education", "academic", "degree", "university"]):
            return "education"
        elif any(keyword in line_lower for keyword in ["projects", "portfolio", "work samples"]):
            return "projects"
        elif any(keyword in line_lower for keyword in ["skills", "technologies", "competencies"]):
            return "skills"
        
        return None

    def _parse_basics(self, line: str, basics: Dict[str, str]):
        """Parse contact information"""
        if "@" in line and not basics["email"]:
            basics["email"] = line
        elif any(char.isdigit() for char in line) and "phone" in line.lower():
            basics["phone"] = line
        elif "linkedin" in line.lower():
            basics["linkedin"] = line
        elif "github" in line.lower():
            basics["github"] = line
        elif not basics["name"] and len(line.split()) <= 3:
            basics["name"] = line

    def _parse_experience_line(self, line: str, experience: list, current_item: dict):
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

    def _parse_education_line(self, line: str, education: list):
        """Parse education section with improved logic"""
        line = line.strip()
        if not line:
            return
            
        # Skip bullet points
        if line.startswith("•") or line.startswith("-") or line.startswith("*"):
            return
        
        # Check if this looks like a degree (contains degree keywords)
        degree_keywords = ["bachelor", "master", "phd", "doctorate", "associate", "diploma", "certificate", "degree"]
        if any(keyword in line.lower() for keyword in degree_keywords):
            education.append({"degree": line, "school": "", "year": "", "gpa": ""})
            return
        
        # Check if this looks like a university/school name
        school_indicators = ["university", "college", "institute", "school", "academy"]
        if any(indicator in line.lower() for indicator in school_indicators):
            if education and not education[-1].get("school"):
                education[-1]["school"] = line
            return
        
        # Check if this looks like a year or GPA
        import re
        if re.search(r'\d{4}', line) or re.search(r'gpa|g\.p\.a', line.lower()):
            if education and not education[-1].get("year"):
                education[-1]["year"] = line
            elif education and not education[-1].get("gpa"):
                education[-1]["gpa"] = line
            return
        
        # If we have education entries and this doesn't match any pattern, treat as additional info
        if education:
            if not education[-1].get("school"):
                education[-1]["school"] = line
            elif not education[-1].get("year"):
                education[-1]["year"] = line

    def _parse_projects_line(self, line: str, projects: list):
        """Parse projects section"""
        if line and not line.startswith("•") and not line.startswith("-"):
            projects.append({"name": line, "description": ""})

    async def _generate_latex(self, resume: Dict[str, Any]) -> str:
        """Generate LaTeX from structured resume"""
        
        latex = r"""
\documentclass{article}
\usepackage[letterpaper,margin=0.75in]{geometry}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{url}

\begin{document}

\begin{center}
{\Large \textbf{""" + self._escape_latex(resume["basics"]["name"]) + r"""}}\\
""" + self._format_contact_info(resume["basics"]) + r"""
\end{center}

\section*{Professional Summary}
""" + self._escape_latex(resume["summary"]) + r"""

\section*{Experience}
"""
        
        for exp in resume["experience"]:
            latex += self._format_experience(exp)
        
        if resume["education"]:
            latex += r"""
\section*{Education}
"""
            for edu in resume["education"]:
                latex += self._format_education(edu)
        
        if resume["projects"]:
            latex += r"""
\section*{Projects}
"""
            for project in resume["projects"]:
                latex += self._format_project(project)
        
        if resume["skills"]:
            latex += r"""
\section*{Skills}
""" + ", ".join(resume["skills"]) + r"""
"""
        
        latex += r"""
\end{document}
"""
        
        return latex.strip()

    def _escape_latex(self, text: str) -> str:
        """Escape LaTeX special characters"""
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

    def _format_contact_info(self, basics: Dict[str, str]) -> str:
        """Format contact information for LaTeX"""
        contact_parts = []
        
        if basics["email"]:
            contact_parts.append(f"Email: {basics['email']}")
        if basics["phone"]:
            contact_parts.append(f"Phone: {basics['phone']}")
        if basics["linkedin"]:
            contact_parts.append(f"LinkedIn: {basics['linkedin']}")
        if basics["github"]:
            contact_parts.append(f"GitHub: {basics['github']}")
        
        return " $\\bullet$ ".join(contact_parts) + r"\\"

    def _format_experience(self, exp: Dict[str, str]) -> str:
        """Format experience entry for LaTeX"""
        role = exp.get('role', '')
        company = exp.get('company', '')
        dates = exp.get('dates', '')
        location = exp.get('location', '')
        bullets = exp.get('bullets', [])
        
        if not role:
            return ""
        
        latex = f"""
\\textbf{{{self._escape_latex(role)}}}"""
        
        if dates:
            latex += f" \\hfill \\textit{{{self._escape_latex(dates)}}}"
        
        latex += "\\\\\n"
        
        if company:
            latex += f"\\textit{{{self._escape_latex(company)}}}"
            if location:
                latex += f" \\hfill \\textit{{{self._escape_latex(location)}}}"
            latex += "\\\\\n"
        
        if bullets:
            latex += "\\begin{itemize}[leftmargin=0.5in]\n"
            for bullet in bullets:
                if bullet.strip():
                    latex += f"\\item {self._escape_latex(bullet)}\n"
            latex += "\\end{itemize}\n"
        
        return latex

    def _format_education(self, edu: Dict[str, str]) -> str:
        """Format education entry for LaTeX"""
        degree = edu.get('degree', '')
        school = edu.get('school', '')
        year = edu.get('year', '')
        gpa = edu.get('gpa', '')
        
        if not degree:
            return ""
        
        latex = f"\\textbf{{{self._escape_latex(degree)}}}"
        
        if year:
            latex += f" \\hfill \\textit{{{self._escape_latex(year)}}}"
        
        latex += "\\\\\n"
        
        if school:
            latex += f"\\textit{{{self._escape_latex(school)}}}"
            if gpa:
                latex += f" \\hfill {self._escape_latex(gpa)}"
            latex += "\\\\\n"
        
        return latex

    def _format_project(self, project: Dict[str, str]) -> str:
        """Format project entry for LaTeX"""
        return f"""
\\textbf{{{self._escape_latex(project.get('name', ''))}}}\\\\
{self._escape_latex(project.get('description', ''))}
"""

    def _get_reconstruction_note(self, resume: Dict[str, Any]) -> Optional[str]:
        """Generate note about reconstruction process"""
        # Check if we had to make assumptions
        assumptions = []
        
        if not resume["basics"]["name"]:
            assumptions.append("name extraction")
        if not resume["summary"]:
            assumptions.append("summary creation")
        if len(resume["experience"]) == 0:
            assumptions.append("experience formatting")
        
        if assumptions:
            return f"Note: Some {', '.join(assumptions)} were approximated during processing."
        
        return None
