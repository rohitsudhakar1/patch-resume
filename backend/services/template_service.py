"""
Template service for rendering structured resume data to LaTeX
"""
import re
from typing import Dict, Any

class TemplateService:
    """Service for rendering structured resume data to LaTeX with professional formatting"""
    
    def _get_preamble(self) -> str:
        """Generate clean LaTeX preamble"""
        return r"""\documentclass[a4paper]{article}

% ---------- Margins ----------
\usepackage[left=0.7in, right=0.7in, top=0.5in, bottom=0.5in]{geometry}

% ---------- Links ----------
\usepackage[hidelinks]{hyperref}

% ---------- Lists / Titles ----------
\usepackage{enumitem}
\usepackage{titlesec}

% ---------- Global tight spacing ----------
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\renewcommand{\baselinestretch}{0.84}
\footnotesize

% Compact section spacing
\titlespacing*{\section}{0pt}{0.3ex}{0.5ex}
\titleformat{\section}{\normalsize\bfseries}{}{}{}[]

% Compact bullets (global)
\setlist[itemize]{leftmargin=*, label=\textbullet, nosep, topsep=0.2ex, itemsep=0.2ex, parsep=0pt, partopsep=0pt}

% Thin separator line used under section titles
\newcommand{\sectionline}{%
  \par\vspace{0.2ex}%
  \noindent\rule{\linewidth}{0.25pt}%
  \par\vspace{0.2ex}%
}

% Small vertical spacer between entries
\newcommand{\entryspace}{\vspace{0.35em}}

"""
    
    def __init__(self):
        pass
    
    def render_resume(self, resume_data: Dict[str, Any]) -> str:
        """
        Render structured resume data to professional LaTeX format
        
        Args:
            resume_data: Dictionary containing structured resume data
            
        Returns:
            Complete LaTeX document as string
        """
        print("🎨 DEBUG: Rendering resume with professional template")
        
        # Start with preamble
        latex_parts = [self._get_preamble()]
        latex_parts.append("\\begin{document}\n")
        
        # Add centered header
        header_latex = self._render_header(resume_data.get('basics', {}))
        if header_latex:
            latex_parts.append(header_latex)
            latex_parts.append("")  # Blank line after header
        
        # Add sections
        sections = [
            ('summary', 'Professional Summary'),
            ('experience', 'Work Experience'),
            ('education', 'Education'),
            ('projects', 'Projects'),
            ('skills', 'Technical Skills')
        ]
        
        for section_key, section_title in sections:
            section_content = self._render_section(section_key, resume_data.get(section_key, []), section_title)
            if section_content:
                latex_parts.append(section_content)
                latex_parts.append("")  # Blank line after section
        
        latex_parts.append("\\end{document}")
        
        return '\n'.join(latex_parts)
    
    def _render_header(self, basics: Dict[str, Any]) -> str:
        """Render the centered header section"""
        if not basics:
            return ""
        
        header_parts = []
        
        # Name
        if basics.get('name'):
            header_parts.append(f"\\textbf{{{self._escape_latex(basics['name'])}}}")
        
        # Contact info
        contact_items = []
        if basics.get('email'):
            contact_items.append(self._escape_latex(basics['email']))
        if basics.get('phone'):
            contact_items.append(self._escape_latex(basics['phone']))
        if basics.get('location'):
            contact_items.append(self._escape_latex(basics['location']))
        if basics.get('linkedin'):
            contact_items.append(f"\\href{{{basics['linkedin']}}}{{linkedin.com/in/rohit-sudhakar-ce}}")
        
        if contact_items:
            header_parts.append(" \\\\ ".join(contact_items))
        
        if header_parts:
            return "\\begin{center}\n" + " \\\\\n".join(header_parts) + "\n\\end{center}"
        
        return ""
    
    def _render_section(self, section_key: str, section_data: Any, section_title: str) -> str:
        """Render a specific section"""
        if not section_data:
            return ""
        
        section_parts = [f"\\section*{{{section_title}}}", "\\sectionline"]
        
        if section_key == 'summary':
            section_parts.append(self._escape_latex(str(section_data)))
        elif section_key == 'experience':
            section_parts.extend(self._render_experience(section_data))
        elif section_key == 'education':
            section_parts.extend(self._render_education(section_data))
        elif section_key == 'projects':
            section_parts.extend(self._render_projects(section_data))
        elif section_key == 'skills':
            section_parts.extend(self._render_skills(section_data))
        
        return '\n'.join(section_parts)
    
    def _render_experience(self, experience: list) -> list:
        """Render experience entries"""
        if not experience:
            return []
        
        parts = []
        for entry in experience:
            if not entry:
                continue
                
            # Job title and company
            title = entry.get('title', '')
            company = entry.get('company', '')
            if title and company:
                parts.append(f"\\textbf{{{self._escape_latex(title)} at {self._escape_latex(company)}}}")
            elif title:
                parts.append(f"\\textbf{{{self._escape_latex(title)}}}")
            elif company:
                parts.append(f"\\textbf{{{self._escape_latex(company)}}}")
            
            # Dates and location with hfill alignment
            date_location = []
            if entry.get('start_date') or entry.get('end_date'):
                dates = []
                if entry.get('start_date'):
                    dates.append(self._escape_latex(entry['start_date']))
                if entry.get('end_date'):
                    dates.append(self._escape_latex(entry['end_date']))
                date_location.append(" - ".join(dates))
            
            if entry.get('location'):
                date_location.append(self._escape_latex(entry['location']))
            
            if date_location:
                parts.append(f"\\textit{{{' | '.join(date_location)}}}")
            
            # Bullet points
            if entry.get('description'):
                parts.append("\\begin{itemize}")
                # Handle both string and list descriptions
                descriptions = entry['description']
                if isinstance(descriptions, str):
                    descriptions = [descriptions]
                
                for desc in descriptions:
                    if desc.strip():
                        parts.append(f"\\item {self._escape_latex(desc.strip())}")
                
                parts.append("\\end{itemize}")
                parts.append("\\entryspace")  # Add spacing after experience entry
        
        return parts
    
    def _render_education(self, education: list) -> list:
        """Render education entries"""
        if not education:
            return []
        
        parts = []
        for entry in education:
            if not entry:
                continue
            
            # School name
            school = entry.get('school', '')
            if school:
                parts.append(f"\\textbf{{{self._escape_latex(school)}}}")
            
            # Degree and dates with hfill alignment
            degree_info = []
            if entry.get('degree'):
                degree_info.append(self._escape_latex(entry['degree']))
            
            if entry.get('start_date') or entry.get('end_date'):
                dates = []
                if entry.get('start_date'):
                    dates.append(self._escape_latex(entry['start_date']))
                if entry.get('end_date'):
                    dates.append(self._escape_latex(entry['end_date']))
                if dates:
                    degree_info.append("\\textit{" + " - ".join(dates) + "}")
            
            if degree_info:
                parts.append(" \\\\ ".join(degree_info))
            
            # GPA and other details
            if entry.get('gpa'):
                parts.append(f"GPA: {self._escape_latex(entry['gpa'])}")
            
            if entry.get('honors'):
                parts.append(self._escape_latex(entry['honors']))
            
            parts.append("")  # Blank line after education entry
        
        return parts
    
    def _render_projects(self, projects: list) -> list:
        """Render project entries"""
        if not projects:
            return []
        
        parts = []
        for project in projects:
            if not project:
                continue
            
            # Project name and tech stack
            name = project.get('name', '')
            tech_stack = project.get('tech_stack', '')
            
            if name and tech_stack:
                parts.append(f"\\textbf{{{self._escape_latex(name)}}} ({self._escape_latex(tech_stack)})")
            elif name:
                parts.append(f"\\textbf{{{self._escape_latex(name)}}}")
            
            # Dates
            if project.get('start_date') or project.get('end_date'):
                dates = []
                if project.get('start_date'):
                    dates.append(self._escape_latex(project['start_date']))
                if project.get('end_date'):
                    dates.append(self._escape_latex(project['end_date']))
                if dates:
                    parts.append(f"\\textit{{{' - '.join(dates)}}}")
            
            # Description
            if project.get('description'):
                parts.append("\\begin{itemize}")
                descriptions = project['description']
                if isinstance(descriptions, str):
                    descriptions = [descriptions]
                
                for desc in descriptions:
                    if desc.strip():
                        parts.append(f"\\item {self._escape_latex(desc.strip())}")
                
                parts.append("\\end{itemize}")
                parts.append("\\entryspace")
        
        return parts
    
    def _render_skills(self, skills: Any) -> list:
        """Render skills section"""
        if not skills:
            return []
        
        if isinstance(skills, str):
            return [self._escape_latex(skills)]
        elif isinstance(skills, list):
            return [self._escape_latex(" | ".join(skills))]
        elif isinstance(skills, dict):
            parts = []
            for category, skill_list in skills.items():
                if skill_list:
                    parts.append(f"{self._escape_latex(category)}: {self._escape_latex(', '.join(skill_list))}")
            return parts
        
        return [str(skills)]
    
    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters in user text"""
        if not text:
            return ""
        
        # Escape special characters
        text = str(text)
        text = text.replace('\\', '\\textbackslash ')
        text = text.replace('{', '\\{')
        text = text.replace('}', '\\}')
        text = text.replace('$', '\\$')
        text = text.replace('&', '\\&')
        text = text.replace('%', '\\%')
        text = text.replace('#', '\\#')
        text = text.replace('^', '\\textasciicircum ')
        text = text.replace('_', '\\_')
        text = text.replace('~', '\\textasciitilde ')
        
        return text
