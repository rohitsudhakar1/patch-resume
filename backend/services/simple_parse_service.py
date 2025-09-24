"""
Simple parse service that preserves original formatting better
"""
import re
from typing import Dict, Any, List

class SimpleParseService:
    """Simple service for parsing resume text with better formatting preservation"""
    
    def __init__(self):
        pass
    
    def parse_resume_text(self, text: str) -> Dict[str, Any]:
        """
        Parse raw resume text into structured data with better formatting preservation
        """
        print("📝 DEBUG: Parsing resume text with simple approach")
        
        # Initialize resume structure
        resume_data = {
            'basics': {},
            'summary': '',
            'experience': [],
            'education': [],
            'projects': [],
            'skills': []
        }
        
        # Clean text but preserve structure
        cleaned_text = self._clean_text_preserve_structure(text)
        
        # Parse sections
        self._parse_basics_simple(cleaned_text, resume_data['basics'])
        self._parse_experience_simple(cleaned_text, resume_data['experience'])
        self._parse_education_simple(cleaned_text, resume_data['education'])
        self._parse_projects_simple(cleaned_text, resume_data['projects'])
        self._parse_skills_simple(cleaned_text, resume_data['skills'])
        
        print(f"✅ DEBUG: Parsed resume with {len(resume_data['experience'])} experiences, {len(resume_data['education'])} education entries")
        
        return resume_data
    
    def _clean_text_preserve_structure(self, text: str) -> str:
        """Clean text while preserving line breaks and structure"""
        if not text:
            return ""
        
        # Remove problematic sequences
        text = re.sub(r'\\n\\', '\n', text)
        text = re.sub(r'\\Personal', 'Personal', text)
        text = re.sub(r'\\Jan', 'Jan', text)
        text = re.sub(r'\\&', '&', text)
        
        # Normalize whitespace but preserve line breaks
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single space
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Remove excessive newlines
        
        return text.strip()
    
    def _parse_basics_simple(self, text: str, basics: Dict[str, Any]):
        """Parse basic information with simple logic"""
        lines = text.split('\n')
        
        # Name is usually first line
        if lines:
            first_line = lines[0].strip()
            if first_line and len(first_line.split()) <= 4:
                basics['name'] = first_line
        
        # Parse contact info from second line
        if len(lines) > 1:
            contact_line = lines[1].strip()
            if contact_line:
                # Extract email
                email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', contact_line)
                if email_match:
                    basics['email'] = email_match.group(1)
                
                # Extract phone
                phone_match = re.search(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})', contact_line)
                if phone_match:
                    basics['phone'] = phone_match.group(1)
                
                # Extract LinkedIn
                if 'linkedin' in contact_line.lower():
                    basics['linkedin'] = contact_line
    
    def _parse_experience_simple(self, text: str, experience: List[Dict[str, Any]]):
        """Parse experience with simple, robust logic"""
        # Find experience section
        exp_match = re.search(r'(?:work\s+experience|experience)\s*(.*?)(?=\n\s*(?:education|projects|skills)|$)', text, re.IGNORECASE | re.DOTALL)
        if not exp_match:
            return
        
        exp_text = exp_match.group(1)
        lines = exp_text.split('\n')
        
        current_entry = {}
        current_bullets = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a company/job header (contains company name and dates)
            if self._is_company_header(line):
                # Save previous entry
                if current_entry:
                    if current_bullets:
                        current_entry['bullets'] = current_bullets
                    experience.append(current_entry)
                
                # Start new entry
                current_entry = self._parse_company_header(line)
                current_bullets = []
            
            # Check if this is a bullet point
            elif line.startswith('•') or line.startswith('-') or line.startswith('*'):
                bullet_text = line[1:].strip()
                if bullet_text:
                    current_bullets.append(bullet_text)
        
        # Add final entry
        if current_entry:
            if current_bullets:
                current_entry['bullets'] = current_bullets
            experience.append(current_entry)
    
    def _is_company_header(self, line: str) -> bool:
        """Check if line is a company header"""
        # Look for company indicators and dates
        company_indicators = ['capital', 'lab', 'solutions', 'limited', 'inc', 'corp', 'llc', 'ltd', 'private']
        date_indicators = ['may', 'june', 'july', 'aug', 'sept', 'oct', 'nov', 'dec', 'jan', 'feb', 'mar', 'apr', 'present', 'current']
        
        line_lower = line.lower()
        has_company = any(indicator in line_lower for indicator in company_indicators)
        has_date = any(indicator in line_lower for indicator in date_indicators)
        
        return has_company and has_date
    
    def _parse_company_header(self, line: str) -> Dict[str, Any]:
        """Parse company header line"""
        # Extract company name (before — or at)
        if '—' in line:
            parts = line.split('—')
            company_part = parts[0].strip()
        elif ' at ' in line:
            parts = line.split(' at ')
            company_part = parts[0].strip()
        else:
            company_part = line
        
        # Extract job title and company
        if '—' in company_part:
            title_company = company_part.split('—')
            if len(title_company) >= 2:
                title = title_company[0].strip()
                company = title_company[1].strip()
            else:
                title = company_part
                company = ""
        else:
            title = company_part
            company = ""
        
        return {
            'company': company,
            'position': title,
            'location': '',
            'startDate': '',
            'endDate': ''
        }
    
    def _parse_education_simple(self, text: str, education: List[Dict[str, Any]]):
        """Parse education with simple logic"""
        # Find education section
        edu_match = re.search(r'(?:education|academic)\s*(.*?)(?=\n\s*(?:projects|skills|experience)|$)', text, re.IGNORECASE | re.DOTALL)
        if not edu_match:
            return
        
        edu_text = edu_match.group(1)
        lines = edu_text.split('\n')
        
        current_entry = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a university name
            if any(word in line.lower() for word in ['university', 'college', 'institute', 'school']):
                if current_entry:
                    education.append(current_entry)
                current_entry = {
                    'institution': line,
                    'area': '',
                    'studyType': '',
                    'startDate': '',
                    'endDate': ''
                }
            elif current_entry and line:
                # This might be degree info
                if not current_entry.get('area'):
                    current_entry['area'] = line
        
        # Add final entry
        if current_entry:
            education.append(current_entry)
    
    def _parse_projects_simple(self, text: str, projects: List[Dict[str, Any]]):
        """Parse projects with simple logic"""
        # Find projects section
        proj_match = re.search(r'(?:projects|project)\s*(.*?)(?=\n\s*(?:skills|technical|education)|$)', text, re.IGNORECASE | re.DOTALL)
        if not proj_match:
            return
        
        proj_text = proj_match.group(1)
        lines = proj_text.split('\n')
        
        current_entry = {}
        current_bullets = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a project title (contains parentheses with technologies)
            if '(' in line and ')' in line and any(word in line.lower() for word in ['react', 'python', 'java', 'flask', 'sql', 'mongodb']):
                # Save previous entry
                if current_entry:
                    if current_bullets:
                        current_entry['bullets'] = current_bullets
                    projects.append(current_entry)
                
                # Start new entry
                current_entry = {
                    'name': line,
                    'description': '',
                    'technologies': ''
                }
                current_bullets = []
            
            # Check if this is a bullet point
            elif line.startswith('•') or line.startswith('-') or line.startswith('*'):
                bullet_text = line[1:].strip()
                if bullet_text:
                    current_bullets.append(bullet_text)
        
        # Add final entry
        if current_entry:
            if current_bullets:
                current_entry['bullets'] = current_bullets
            projects.append(current_entry)
    
    def _parse_skills_simple(self, text: str, skills: List[str]):
        """Parse skills with simple logic"""
        # Find skills section
        skills_match = re.search(r'(?:technical\s+skills|skills)\s*(.*?)$', text, re.IGNORECASE | re.DOTALL)
        if not skills_match:
            return
        
        skills_text = skills_match.group(1)
        
        # Extract skills from the text
        # Look for common skill patterns
        skill_patterns = [
            r'Programming:\s*([^\\n]+)',
            r'Frameworks/Libraries:\s*([^\\n]+)',
            r'Databases:\s*([^\\n]+)',
            r'Tools:\s*([^\\n]+)',
            r'Dev/Scripting:\s*([^\\n]+)'
        ]
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, skills_text, re.IGNORECASE)
            for match in matches:
                # Split by common separators
                skill_list = re.split(r'[,|]', match)
                for skill in skill_list:
                    skill = skill.strip()
                    if skill and skill not in skills:
                        skills.append(skill)
        
        # Also look for skills separated by | in the text
        if '|' in skills_text:
            pipe_skills = skills_text.split('|')
            for skill in pipe_skills:
                skill = skill.strip()
                if skill and skill not in skills:
                    skills.append(skill)
