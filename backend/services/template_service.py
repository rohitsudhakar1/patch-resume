"""
Template service for rendering structured resume data to LaTeX
Produces a clean, single-column, ATS-friendly resume:
  - prominent centered name + contact line
  - bold section headings (no decorative rules)
  - two-line entries with right-aligned dates (\\hfill)
  - tight, professional spacing
"""
import re
from typing import Dict, Any, List


class TemplateService:
    """Render structured resume data to professional, ATS-friendly LaTeX."""

    def _get_preamble(self) -> str:
        return r"""\documentclass[11pt,letterpaper]{article}

% ---------- Margins ----------
\usepackage[margin=0.65in]{geometry}

% ---------- Links ----------
\usepackage[hidelinks]{hyperref}

% ---------- Lists ----------
\usepackage{enumitem}

% ---------- Spacing ----------
\setlength{\parindent}{0pt}
\setlength{\parskip}{2pt}
\renewcommand{\baselinestretch}{1.04}

% ---------- Section headings: clean bold, no horizontal rules ----------
\newcommand{\sectiontitle}[1]{\vspace{7pt}{\large\bfseries #1}\par\vspace{3pt}}

% ---------- Compact, ATS-friendly bullets ----------
\setlist[itemize]{leftmargin=15pt, label=\textbullet, topsep=1pt, itemsep=1pt, parsep=0pt, before=\vspace{-2pt}}

"""

    def __init__(self):
        pass

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #
    def render_resume(self, resume_data: Dict[str, Any]) -> str:
        print("🎨 DEBUG: Rendering resume with professional ATS template")

        latex_parts = [self._get_preamble(), "\\begin{document}\n"]

        header = self._render_header(resume_data.get('basics', {}))
        if header:
            latex_parts.append(header)
            latex_parts.append("")

        sections = [
            ('summary', 'Summary'),
            ('experience', 'Experience'),
            ('education', 'Education'),
            ('projects', 'Projects'),
            ('skills', 'Skills'),
        ]
        for key, title in sections:
            content = self._render_section(key, resume_data.get(key, []), title)
            if content:
                latex_parts.append(content)
                latex_parts.append("")

        latex_parts.append("\\end{document}")
        return '\n'.join(latex_parts)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _row(self, left: str, right: str = "") -> str:
        """One paragraph: `left` flush-left, `right` flush-right via \\hfill."""
        left = (left or "").strip()
        right = (right or "").strip()
        if left and right:
            return f"{left} \\hfill {right}\\par"
        if left:
            return f"{left}\\par"
        if right:
            return f"\\hspace*{{\\fill}}{right}\\par"
        return ""

    def _dates(self, entry: Dict[str, Any]) -> str:
        start = self._escape_latex(entry.get('start_date', '') or '')
        end = self._escape_latex(entry.get('end_date', '') or '')
        if start and end:
            return f"{start} -- {end}"
        return start or end

    # ------------------------------------------------------------------ #
    # Header
    # ------------------------------------------------------------------ #
    def _render_header(self, basics: Dict[str, Any]) -> str:
        if not basics:
            return ""

        lines = ["\\begin{center}"]

        name = self._escape_latex(basics.get('name', '') or '')
        if name:
            lines.append(f"{{\\LARGE\\bfseries {name}}}\\\\")
            lines.append("\\vspace{3pt}")

        contact: List[str] = []
        for key in ('email', 'phone', 'location'):
            val = basics.get(key)
            if val:
                contact.append(self._escape_latex(val))
        linkedin = basics.get('linkedin')
        if linkedin:
            clean = str(linkedin).strip()
            url = clean if clean.startswith('http') else f"https://{clean}"
            contact.append(f"\\href{{{url}}}{{{self._escape_latex(clean)}}}")

        if contact:
            lines.append(" $|$ ".join(contact))

        lines.append("\\end{center}")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Section dispatch
    # ------------------------------------------------------------------ #
    def _render_section(self, key: str, data: Any, title: str) -> str:
        if not data:
            return ""

        parts = [f"\\sectiontitle{{{title}}}"]

        if key == 'summary':
            parts.append(self._escape_latex(str(data)))
        elif key == 'experience':
            parts.extend(self._render_experience(data))
        elif key == 'education':
            parts.extend(self._render_education(data))
        elif key == 'projects':
            parts.extend(self._render_projects(data))
        elif key == 'skills':
            parts.extend(self._render_skills(data))

        return '\n'.join(p for p in parts if p)

    # ------------------------------------------------------------------ #
    # Experience
    # ------------------------------------------------------------------ #
    def _render_experience(self, experience: list) -> list:
        parts: List[str] = []
        for entry in experience:
            if not entry:
                continue

            title = self._escape_latex(entry.get('title', '') or '')
            company = self._escape_latex(entry.get('company', '') or '')
            location = self._escape_latex(entry.get('location', '') or '')
            dates = self._dates(entry)

            # Line 1: bold title (left) — dates (right)
            if title or dates:
                parts.append(self._row(f"\\textbf{{{title}}}" if title else "", dates))
            # Line 2: italic company (left) — location (right)
            if company or location:
                parts.append(self._row(f"\\textit{{{company}}}" if company else "", location))

            parts.extend(self._bullets(entry.get('description')))
            parts.append("\\vspace{5pt}")
        return parts

    # ------------------------------------------------------------------ #
    # Education
    # ------------------------------------------------------------------ #
    def _render_education(self, education: list) -> list:
        parts: List[str] = []
        for entry in education:
            if not entry:
                continue

            school = self._escape_latex(entry.get('school', '') or '')
            degree = self._escape_latex(entry.get('degree', '') or '')
            gpa = self._escape_latex(entry.get('gpa', '') or '')
            dates = self._dates(entry)

            if school or dates:
                parts.append(self._row(f"\\textbf{{{school}}}" if school else "", dates))

            right2 = f"GPA: {gpa}" if gpa else ""
            if degree or right2:
                parts.append(self._row(f"\\textit{{{degree}}}" if degree else "", right2))

            if entry.get('honors'):
                parts.append(self._row(self._escape_latex(entry['honors'])))

            parts.append("\\vspace{5pt}")
        return parts

    # ------------------------------------------------------------------ #
    # Projects
    # ------------------------------------------------------------------ #
    def _render_projects(self, projects: list) -> list:
        parts: List[str] = []
        for project in projects:
            if not project:
                continue

            name = self._escape_latex(project.get('name', '') or '')
            tech = self._escape_latex(project.get('tech_stack', '') or '')
            dates = self._dates(project)

            left = f"\\textbf{{{name}}}" if name else ""
            if tech:
                left = f"{left} $|$ \\textit{{{tech}}}" if left else f"\\textit{{{tech}}}"
            if left or dates:
                parts.append(self._row(left, dates))

            parts.extend(self._bullets(project.get('description')))
            parts.append("\\vspace{5pt}")
        return parts

    # ------------------------------------------------------------------ #
    # Skills
    # ------------------------------------------------------------------ #
    def _render_skills(self, skills: Any) -> list:
        if not skills:
            return []
        if isinstance(skills, str):
            return [self._escape_latex(skills)]
        if isinstance(skills, list):
            cleaned = [self._escape_latex(s) for s in skills if str(s).strip()]
            return [", ".join(cleaned)] if cleaned else []
        if isinstance(skills, dict):
            rows = []
            for category, items in skills.items():
                if not items:
                    continue
                if isinstance(items, (list, tuple)):
                    items = ", ".join(str(i) for i in items)
                rows.append(f"\\textbf{{{self._escape_latex(category)}:}} {self._escape_latex(items)}\\par")
            return rows
        return [self._escape_latex(str(skills))]

    # ------------------------------------------------------------------ #
    # Bullets
    # ------------------------------------------------------------------ #
    def _bullets(self, description: Any) -> list:
        if not description:
            return []
        items = description
        if isinstance(items, str):
            items = [items]
        cleaned = [d.strip() for d in items if str(d).strip()]
        if not cleaned:
            return []
        out = ["\\begin{itemize}"]
        for d in cleaned:
            out.append(f"\\item {self._escape_latex(d)}")
        out.append("\\end{itemize}")
        return out

    # ------------------------------------------------------------------ #
    # Escaping
    # ------------------------------------------------------------------ #
    def _escape_latex(self, text: str) -> str:
        if not text:
            return ""
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
