"""
Parse service for converting raw text to structured resume data
"""
import re
from typing import Dict, Any, List

class ParseService:
    """Service for parsing raw resume text into structured data"""
    
    def __init__(self):
        pass
    
    def parse_resume_text(self, text: str) -> Dict[str, Any]:
        """
        Parse raw resume text into structured data
        
        Args:
            text: Raw resume text content
            
        Returns:
            Dictionary containing structured resume data
        """
        print("📝 DEBUG: Parsing resume text into structured data")
        
        # Clean the input text first
        cleaned_text = self._clean_text_content(text)
        
        # Initialize resume structure
        resume_data = {
            'basics': {},
            'summary': '',
            'experience': [],
            'education': [],
            'projects': [],
            'skills': []
        }
        
        # Parse different sections
        self._parse_basics(cleaned_text, resume_data['basics'])
        self._parse_summary(cleaned_text, resume_data)
        self._parse_experience(cleaned_text, resume_data['experience'])
        self._parse_education(cleaned_text, resume_data['education'])
        self._parse_projects(cleaned_text, resume_data['projects'])
        self._parse_skills(cleaned_text, resume_data['skills'])
        
        print(f"✅ DEBUG: Parsed resume with {len(resume_data['experience'])} experiences, {len(resume_data['education'])} education entries")
        
        return resume_data
    
    def _clean_text_content(self, text: str) -> str:
        """Clean raw text content - only for input text, not LaTeX"""
        if not text:
            return ""
        
        # Remove problematic sequences that shouldn't be in raw text
        text = re.sub(r'\\n\\', '\n', text)  # Fix \n\ sequences
        text = re.sub(r'\\Personal', 'Personal', text)  # Fix \Personal
        text = re.sub(r'\\Jan', 'Jan', text)  # Fix \Jan
        text = re.sub(r'\\&', '&', text)  # Fix \&
        
        # Normalize whitespace but preserve line breaks
        text = re.sub(r'[ \t]+', ' ', text)  # Replace multiple spaces/tabs with single space
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Remove excessive newlines
        
        return text.strip()
    
    def _parse_basics(self, text: str, basics: Dict[str, Any]):
        """Parse basic information (name, contact, etc.)"""
        lines = text.split('\n')
        
        # First, try to find the name (usually the first line)
        if lines and not basics.get('name'):
            first_line = lines[0].strip()
            if first_line and len(first_line.split()) <= 4 and not any(x in first_line.lower() for x in ['@', '(', 'linkedin', 'github', 'education', 'experience']):
                basics['name'] = first_line
        
        # Then parse contact information
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            line_lower = line.lower()
            
            # Email
            if '@' in line and '.com' in line:
                basics['email'] = line
            
            # Phone
            elif re.match(r'\(\d{3}\)-\d{3}-\d{4}', line) or re.match(r'\d{3}-\d{3}-\d{4}', line):
                basics['phone'] = line
            
            # LinkedIn
            elif 'linkedin' in line_lower:
                basics['linkedin'] = line
            
            # Location
            elif any(city in line_lower for city in ['madison', 'coimbatore', 'india', 'wi']):
                basics['location'] = line
    
    def _parse_summary(self, text: str, resume_data: Dict[str, Any]):
        """Parse professional summary"""
        # Look for summary section
        summary_match = re.search(r'(?:summary|profile|objective|about)\s*:?\s*(.+?)(?=\n\s*(?:experience|education|skills|projects)|$)', text, re.IGNORECASE | re.DOTALL)
        if summary_match:
            resume_data['summary'] = summary_match.group(1).strip()
    
    def _parse_experience(self, text: str, experience: List[Dict[str, Any]]):
        """Parse work experience entries"""
        # Find experience section
        exp_match = re.search(r'(?:work\s+experience|experience|employment)\s*(.*?)(?=\n\s*(?:education|projects|skills)|$)', text, re.IGNORECASE | re.DOTALL)
        if not exp_match:
            return
        
        exp_text = exp_match.group(1)
        
        # Split into individual entries (look for company names or job titles)
        current_entry = {}
        current_description = []
        
        lines = exp_text.split('\n')
        in_description = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            line_lower = line.lower()
            
            # Check if this is a new experience entry
            if self._is_experience_header(line, line_lower):
                # Save previous entry if exists
                if current_entry:
                    if current_description:
                        current_entry['description'] = current_description
                    experience.append(current_entry)
                
                # Start new entry
                current_entry = self._parse_experience_header(line, line_lower)
                current_description = []
                in_description = False
            
            # Check if this is a bullet point
            elif line.startswith('•') or line.startswith('-') or line.startswith('*'):
                current_description.append(line[1:].strip())
                in_description = True
            
            # Check if this is a date line
            elif re.search(r'\d{4}', line) and any(word in line_lower for word in ['present', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
                if current_entry:
                    self._parse_experience_dates(line, current_entry)
            
            # Regular description line
            elif in_description and current_entry:
                current_description.append(line)
        
        # Add final entry
        if current_entry:
            if current_description:
                current_entry['description'] = current_description
            experience.append(current_entry)
    
    def _is_experience_header(self, line: str, line_lower: str) -> bool:
        """Check if line is likely an experience header (company/job title)"""
        # Look for company indicators
        company_indicators = ['capital', 'lab', 'solutions', 'limited', 'inc', 'corp', 'llc', 'ltd']
        
        # Look for job title indicators
        job_indicators = ['intern', 'engineer', 'developer', 'analyst', 'manager', 'director', 'researcher']
        
        return (any(indicator in line_lower for indicator in company_indicators) or
                any(indicator in line_lower for indicator in job_indicators)) and len(line.split()) >= 2
    
    def _parse_experience_header(self, line: str, line_lower: str) -> Dict[str, Any]:
        """Parse experience header line"""
        entry = {}
        
        # Try to extract company and title
        if '---' in line:
            parts = line.split('---')
            if len(parts) >= 2:
                entry['title'] = parts[0].strip()
                entry['company'] = parts[1].strip()
        elif '|' in line:
            parts = line.split('|')
            if len(parts) >= 2:
                entry['title'] = parts[0].strip()
                entry['company'] = parts[1].strip()
        else:
            # Try to guess if it's a title or company
            if any(word in line_lower for word in ['intern', 'engineer', 'developer', 'analyst']):
                entry['title'] = line
            else:
                entry['company'] = line
        
        return entry
    
    def _parse_experience_dates(self, line: str, entry: Dict[str, Any]):
        """Parse date information from experience entry"""
        # Extract dates
        date_match = re.search(r'(\w{3}\s+\d{4})\s*[–-]\s*(\w{3}\s+\d{4}|Present)', line)
        if date_match:
            entry['start_date'] = date_match.group(1)
            entry['end_date'] = date_match.group(2)
        else:
            # Single date
            date_match = re.search(r'(\w{3}\s+\d{4})', line)
            if date_match:
                entry['start_date'] = date_match.group(1)
        
        # Extract location
        location_match = re.search(r'\|([^|]+)$', line)
        if location_match:
            entry['location'] = location_match.group(1).strip()
    
    def _parse_education(self, text: str, education: List[Dict[str, Any]]):
        """Parse education entries"""
        # Find education section
        edu_match = re.search(r'(?:education|academic)\s*(.*?)(?=\n\s*(?:experience|projects|skills)|$)', text, re.IGNORECASE | re.DOTALL)
        if not edu_match:
            return
        
        edu_text = edu_match.group(1)
        lines = edu_text.split('\n')
        
        current_entry = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            line_lower = line.lower()
            
            # University/school name
            if any(word in line_lower for word in ['university', 'college', 'institute', 'school']):
                if current_entry:
                    education.append(current_entry)
                current_entry = {'school': line}
            
            # Degree information
            elif any(word in line_lower for word in ['bachelor', 'master', 'phd', 'degree', 'bs', 'ms', 'ba', 'ma']):
                if current_entry:
                    current_entry['degree'] = line
            
            # GPA
            elif 'gpa' in line_lower:
                gpa_match = re.search(r'gpa\s*:?\s*([\d.]+)', line_lower)
                if gpa_match:
                    current_entry['gpa'] = gpa_match.group(1)
            
            # Dates
            elif re.search(r'\d{4}', line):
                if 'expected' in line_lower or 'may' in line_lower:
                    current_entry['end_date'] = line
        
        # Add final entry
        if current_entry:
            education.append(current_entry)
    
    def _parse_projects(self, text: str, projects: List[Dict[str, Any]]):
        """Parse project entries"""
        # Find projects section
        proj_match = re.search(r'(?:projects|project)\s*(.*?)(?=\n\s*(?:experience|education|skills)|$)', text, re.IGNORECASE | re.DOTALL)
        if not proj_match:
            return
        
        proj_text = proj_match.group(1)
        
        # Split into individual projects
        current_project = {}
        current_description = []
        
        lines = proj_text.split('\n')
        in_description = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Project title (usually starts with bold or has tech stack)
            if ('(' in line and ')' in line) or any(tech in line.lower() for tech in ['python', 'react', 'java', 'javascript']):
                # Save previous project
                if current_project:
                    if current_description:
                        current_project['description'] = current_description
                    projects.append(current_project)
                
                # Start new project
                current_project = self._parse_project_header(line)
                current_description = []
                in_description = False
            
            # Bullet points
            elif line.startswith('•') or line.startswith('-') or line.startswith('*'):
                current_description.append(line[1:].strip())
                in_description = True
            
            # Regular description
            elif in_description:
                current_description.append(line)
        
        # Add final project
        if current_project:
            if current_description:
                current_project['description'] = current_description
            projects.append(current_project)
    
    def _parse_project_header(self, line: str) -> Dict[str, Any]:
        """Parse project header line"""
        project = {}
        
        # Extract tech stack from parentheses
        tech_match = re.search(r'\(([^)]+)\)', line)
        if tech_match:
            project['tech_stack'] = tech_match.group(1)
            project['name'] = line.split('(')[0].strip()
        else:
            project['name'] = line
        
        return project
    
    def _parse_skills(self, text: str, skills: List[str]):
        """Parse skills section"""
        # Find skills section
        skills_match = re.search(r'(?:skills|technical\s+skills)\s*:?\s*(.*?)(?=\n\s*(?:experience|education|projects)|$)', text, re.IGNORECASE | re.DOTALL)
        if not skills_match:
            return
        
        skills_text = skills_match.group(1)
        
        # Split by common separators
        skill_items = re.split(r'[,\n]', skills_text)
        
        for item in skill_items:
            item = item.strip()
            if item and not item.lower().startswith(('programming', 'frameworks', 'databases', 'tools')):
                skills.append(item)
