"""
Service for OpenAI o3 integration and patch generation
"""
import openai
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import json
import difflib

from ..database import Project, PendingPatch, Change
from ..config import settings
from ..models import PatchRequest, PatchResponse

class LLMService:
    def __init__(self):
        openai.api_key = settings.openai_api_key
        self.model = settings.openai_model

    async def generate_patch(self, request: PatchRequest, db: Session) -> Dict[str, Any]:
        """Generate proposed changes using OpenAI o3"""
        
        # Get current project
        project = db.query(Project).first()  # In real app, get by project_id
        if not project:
            raise ValueError("No project found")
        
        # Prepare context slice
        context = await self._prepare_context(project.resume_tex, request)
        
        # Generate patch using OpenAI
        patch = await self._call_openai(request.instruction, context)
        
        # Parse and validate patch
        changes = self._parse_patch(patch, project.resume_tex)
        
        # Save to database
        pending_patch = PendingPatch(
            project_id=project.id,
            status="proposed"
        )
        db.add(pending_patch)
        db.flush()
        
        # Save changes
        for change_data in changes:
            change = Change(
                patch_id=pending_patch.id,
                type=change_data["type"],
                start_line=change_data["start_line"],
                end_line=change_data["end_line"],
                content=change_data["content"],
                accepted=None,
                pdf_regions=change_data.get("pdf_regions")
            )
            db.add(change)
        
        db.commit()
        
        return {
            "patch_id": str(pending_patch.id),
            "changes": changes,
            "project_id": str(project.id)
        }

    async def _prepare_context(self, resume_tex: str, request: PatchRequest) -> Dict[str, str]:
        """Prepare context slice for LLM"""
        
        if request.full_document:
            return {
                "full_document": resume_tex,
                "context_type": "full"
            }
        
        # If code slice provided, use it
        if request.code_slice:
            return {
                "code_slice": request.code_slice,
                "context_type": "slice"
            }
        
        # Otherwise, try to extract relevant section
        section = self._extract_relevant_section(resume_tex, request.instruction)
        
        return {
            "section": section,
            "context_type": "section",
            "section_name": self._detect_section_name(section)
        }

    def _extract_relevant_section(self, resume_tex: str, instruction: str) -> str:
        """Extract relevant section based on instruction"""
        instruction_lower = instruction.lower()
        
        # Map instruction keywords to LaTeX sections
        if any(keyword in instruction_lower for keyword in ["experience", "work", "job", "career"]):
            return self._extract_section(resume_tex, r"\\section\*\{Experience\}")
        elif any(keyword in instruction_lower for keyword in ["education", "degree", "school"]):
            return self._extract_section(resume_tex, r"\\section\*\{Education\}")
        elif any(keyword in instruction_lower for keyword in ["skills", "technical", "technology"]):
            return self._extract_section(resume_tex, r"\\section\*\{Skills\}")
        elif any(keyword in instruction_lower for keyword in ["summary", "objective", "about"]):
            return self._extract_section(resume_tex, r"\\section\*\{Professional Summary\}")
        elif any(keyword in instruction_lower for keyword in ["projects", "portfolio"]):
            return self._extract_section(resume_tex, r"\\section\*\{Projects\}")
        else:
            # Default to experience section
            return self._extract_section(resume_tex, r"\\section\*\{Experience\}")

    def _extract_section(self, resume_tex: str, section_pattern: str) -> str:
        """Extract specific section from LaTeX"""
        import re
        
        # Find section start
        section_match = re.search(section_pattern, resume_tex)
        if not section_match:
            return resume_tex[:500]  # Fallback to first 500 chars
        
        start_pos = section_match.start()
        
        # Find next section or end of document
        next_section_patterns = [
            r"\\section\*\{[^}]+\}",
            r"\\end\{document\}"
        ]
        
        end_pos = len(resume_tex)
        for pattern in next_section_patterns:
            match = re.search(pattern, resume_tex[start_pos + 100:])
            if match:
                end_pos = start_pos + 100 + match.start()
                break
        
        return resume_tex[start_pos:end_pos]

    def _detect_section_name(self, section: str) -> str:
        """Detect section name from LaTeX content"""
        import re
        match = re.search(r"\\section\*\{([^}]+)\}", section)
        return match.group(1) if match else "Unknown"

    async def _call_openai(self, instruction: str, context: Dict[str, str]) -> str:
        """Call OpenAI API to generate patch"""
        
        system_prompt = """You are a LaTeX resume expert. You will be given an instruction to modify a resume section, and you must respond with a unified diff patch showing the exact changes needed.

IMPORTANT: Before generating changes, analyze the instruction and ask clarifying questions if needed. If the instruction is vague or missing important details, ask for specific information.

Rules:
1. Always respond with a valid unified diff format
2. Show only the lines that need to change (with context lines)
3. Use --- for original file and +++ for modified file
4. Include line numbers in the format @@ -start,count +start,count @@
5. Be precise with LaTeX syntax
6. Maintain proper LaTeX formatting
7. Don't change unrelated sections
8. Follow the EXACT format of existing entries in the resume
9. For work experience, include: company name, position, location, dates, and bullet points with quantified achievements
10. For projects, include: project name, technologies, dates, and detailed descriptions
11. For education, include: institution, degree, graduation date, GPA, relevant coursework

Example format:
--- a/resume.tex
+++ b/resume.tex
@@ -12,3 +12,6 @@
 \\item Original bullet point
+\\item New bullet point with quantified impact
+\\item Another improvement
 \\item Existing bullet point"""

        user_prompt = f"""
Instruction: {instruction}

Context ({context['context_type']}):
{context.get('full_document', context.get('section', context.get('code_slice', '')))}

Please provide a unified diff showing the exact changes needed to implement this instruction. If the instruction is unclear or missing details, ask for clarification first.
"""

        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    def _parse_patch(self, patch_text: str, original_tex: str) -> List[Dict[str, Any]]:
        """Parse unified diff patch into structured changes"""
        changes = []
        
        try:
            # Parse unified diff
            diff_lines = patch_text.split('\n')
            current_hunk = None
            original_line_num = 0
            modified_line_num = 0
            
            for line in diff_lines:
                # Skip file headers
                if line.startswith('---') or line.startswith('+++'):
                    continue
                
                # Parse hunk header
                if line.startswith('@@'):
                    # Extract line numbers: @@ -start,count +start,count @@
                    import re
                    match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
                    if match:
                        original_line_num = int(match.group(1))
                        modified_line_num = int(match.group(3))
                    continue
                
                # Process diff lines
                if line.startswith('-'):
                    # Deletion
                    if current_hunk and current_hunk['type'] == 'addition':
                        changes.append(current_hunk)
                    
                    current_hunk = {
                        'type': 'removal',
                        'start_line': original_line_num,
                        'end_line': original_line_num,
                        'content': line[1:],  # Remove '-' prefix
                        'pdf_regions': []  # Will be calculated later
                    }
                    original_line_num += 1
                    
                elif line.startswith('+'):
                    # Addition
                    if current_hunk and current_hunk['type'] == 'removal':
                        changes.append(current_hunk)
                    
                    current_hunk = {
                        'type': 'addition',
                        'start_line': modified_line_num,
                        'end_line': modified_line_num,
                        'content': line[1:],  # Remove '+' prefix
                        'pdf_regions': []  # Will be calculated later
                    }
                    modified_line_num += 1
                    
                else:
                    # Context line
                    if current_hunk:
                        # Extend current hunk
                        current_hunk['content'] += '\n' + line
                        if line.startswith(' '):
                            current_hunk['end_line'] += 1
                            original_line_num += 1
                            modified_line_num += 1
                    else:
                        original_line_num += 1
                        modified_line_num += 1
            
            # Add final hunk
            if current_hunk:
                changes.append(current_hunk)
            
            # Calculate PDF regions for each change
            for change in changes:
                change['pdf_regions'] = self._calculate_pdf_regions(change, original_tex)
            
            return changes
            
        except Exception as e:
            raise Exception(f"Error parsing patch: {str(e)}")

    def _calculate_pdf_regions(self, change: Dict[str, Any], original_tex: str) -> List[Dict[str, int]]:
        """Calculate approximate PDF regions for changes"""
        # This is a simplified implementation
        # In a real system, you'd use SyncTeX data
        
        lines = original_tex.split('\n')
        change_line = change['start_line'] - 1  # Convert to 0-indexed
        
        if change_line < 0 or change_line >= len(lines):
            return []
        
        # Estimate PDF position based on line number
        # Assuming ~12 lines per page and standard margins
        page_height = 792  # 11 inches * 72 points/inch
        line_height = page_height / 12
        margin_top = 72  # 1 inch margin
        
        y_position = margin_top + (change_line % 12) * line_height
        
        return [{
            'x': 50,
            'y': int(y_position),
            'width': 400,
            'height': int(line_height * 2)  # Assume 2 lines for changes
        }]
