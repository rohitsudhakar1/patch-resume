"""
Service for LaTeX compilation using Tectonic
"""
import os
import subprocess
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path
import shutil

from ..config import settings

class CompileService:
    def __init__(self):
        self.tectonic_path = settings.tectonic_path
        self.storage_path = Path(settings.storage_path)
        self.storage_path.mkdir(exist_ok=True)

    async def compile_latex(self, project_id: str, latex_content: str) -> Dict[str, Any]:
        """Compile LaTeX to PDF using Tectonic with SyncTeX"""
        
        # Create project directory
        project_dir = self.storage_path / project_id
        project_dir.mkdir(exist_ok=True)
        
        # Write LaTeX file
        tex_file = project_dir / "resume.tex"
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        
        try:
            # Compile with Tectonic
            result = await self._run_tectonic(project_dir)
            
            if result["success"]:
                pdf_file = project_dir / "resume.pdf"
                synctex_file = project_dir / "resume.synctex.gz"
                
                return {
                    "success": True,
                    "pdf_path": str(pdf_file),
                    "synctex_path": str(synctex_file) if synctex_file.exists() else None,
                    "project_id": project_id
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "project_id": project_id
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_id": project_id
            }

    async def _run_tectonic(self, project_dir: Path) -> Dict[str, Any]:
        """Run Tectonic compilation"""
        
        tex_file = project_dir / "resume.tex"
        
        # Tectonic command with SyncTeX enabled
        cmd = [
            self.tectonic_path,
            "--synctex",  # Enable SyncTeX
            "--keep-intermediates",  # Keep intermediate files
            str(tex_file)
        ]
        
        try:
            # Run Tectonic
            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            if result.returncode == 0:
                return {"success": True}
            else:
                # Parse error output
                error_lines = result.stderr.split('\n')
                error_msg = self._extract_error_message(error_lines)
                
                return {
                    "success": False,
                    "error": error_msg,
                    "full_stderr": result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Compilation timeout (30s)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Compilation error: {str(e)}"
            }

    def _extract_error_message(self, error_lines: list) -> str:
        """Extract meaningful error message from Tectonic output"""
        
        # Look for common error patterns
        for line in error_lines:
            if "Error:" in line:
                return line.strip()
            elif "Undefined control sequence" in line:
                return f"Undefined LaTeX command: {line.strip()}"
            elif "Missing $" in line:
                return "Missing math mode delimiters"
            elif "Runaway argument" in line:
                return "Unmatched braces or brackets"
            elif "File not found" in line:
                return "Missing required file or package"
        
        # Fallback to first non-empty line
        for line in error_lines:
            if line.strip():
                return line.strip()
        
        return "Unknown compilation error"

    async def get_pdf_path(self, project_id: str) -> Optional[str]:
        """Get path to compiled PDF"""
        pdf_path = self.storage_path / project_id / "resume.pdf"
        return str(pdf_path) if pdf_path.exists() else None

    async def get_synctex_path(self, project_id: str) -> Optional[str]:
        """Get path to SyncTeX file"""
        synctex_path = self.storage_path / project_id / "resume.synctex.gz"
        return str(synctex_path) if synctex_path.exists() else None

    async def sync_pdf_to_tex(self, project_id: str, pdf_x: float, pdf_y: float) -> Dict[str, Any]:
        """Convert PDF coordinates to LaTeX line numbers using SyncTeX"""
        
        synctex_path = await self.get_synctex_path(project_id)
        if not synctex_path:
            return {"success": False, "error": "No SyncTeX file found"}
        
        try:
            # Use synctex command line tool
            cmd = [
                "synctex",
                "view",
                "-i", f"{int(pdf_x)}:{int(pdf_y)}:1",  # page 1
                "-o", synctex_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse synctex output to get line numbers
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if 'Input:' in line and 'Line:' in line:
                        # Extract line number
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'Line:':
                                line_num = int(parts[i + 1])
                                return {
                                    "success": True,
                                    "line_number": line_num,
                                    "file": "resume.tex"
                                }
                
                return {"success": False, "error": "Could not map coordinates"}
            else:
                return {"success": False, "error": "SyncTeX failed"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def sync_tex_to_pdf(self, project_id: str, line_number: int) -> Dict[str, Any]:
        """Convert LaTeX line numbers to PDF coordinates using SyncTeX"""
        
        synctex_path = await self.get_synctex_path(project_id)
        if not synctex_path:
            return {"success": False, "error": "No SyncTeX file found"}
        
        try:
            # Use synctex command line tool
            cmd = [
                "synctex",
                "view",
                "-l", str(line_number),
                "-i", "1",  # page 1
                "-o", synctex_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse synctex output to get coordinates
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if 'Page:' in line and 'x:' in line and 'y:' in line:
                        # Extract coordinates
                        parts = line.split()
                        x, y = 0, 0
                        for i, part in enumerate(parts):
                            if part == 'x:':
                                x = float(parts[i + 1])
                            elif part == 'y:':
                                y = float(parts[i + 1])
                        
                        return {
                            "success": True,
                            "x": x,
                            "y": y,
                            "page": 1
                        }
                
                return {"success": False, "error": "Could not map line number"}
            else:
                return {"success": False, "error": "SyncTeX failed"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def auto_repair(self, project_id: str, error_line: int, error_context: str) -> Dict[str, Any]:
        """Attempt to auto-repair common LaTeX errors"""
        
        project_dir = self.storage_path / project_id
        tex_file = project_dir / "resume.tex"
        
        if not tex_file.exists():
            return {"success": False, "error": "No LaTeX file found"}
        
        # Read current content
        with open(tex_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Common repairs
        repairs = [
            self._repair_unmatched_braces,
            self._repair_missing_dollars,
            self._repair_undefined_commands,
            self._repair_encoding_issues
        ]
        
        for repair_func in repairs:
            repaired_content = repair_func(lines, error_line, error_context)
            if repaired_content != content:
                # Try compiling the repaired version
                test_result = await self._test_compilation(repaired_content, project_dir)
                if test_result["success"]:
                    # Save repaired content
                    with open(tex_file, 'w', encoding='utf-8') as f:
                        f.write(repaired_content)
                    
                    return {
                        "success": True,
                        "message": "Auto-repair successful",
                        "changes": test_result.get("changes", [])
                    }
        
        return {"success": False, "error": "Could not auto-repair"}

    def _repair_unmatched_braces(self, lines: list, error_line: int, error_context: str) -> str:
        """Repair unmatched braces"""
        # Simple brace matching - add missing closing braces
        content = '\n'.join(lines)
        open_braces = content.count('{')
        close_braces = content.count('}')
        
        if open_braces > close_braces:
            missing = open_braces - close_braces
            content += '\n' + '}' * missing
        
        return content

    def _repair_missing_dollars(self, lines: list, error_line: int, error_context: str) -> str:
        """Repair missing math mode delimiters"""
        content = '\n'.join(lines)
        
        # Look for unescaped special characters that should be in math mode
        import re
        
        # Common patterns that need math mode
        patterns = [
            (r'([^$])([0-9]+%)', r'\1$\2$'),  # Percentages
            (r'([^$])([0-9]+\.[0-9]+)', r'\1$\2$'),  # Decimals in context
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        return content

    def _repair_undefined_commands(self, lines: list, error_line: int, error_context: str) -> str:
        """Repair undefined LaTeX commands"""
        content = '\n'.join(lines)
        
        # Common undefined commands and their fixes
        fixes = {
            '\\textbf': '\\textbf',  # Already correct
            '\\textit': '\\textit',  # Already correct
            '\\item': '\\item',      # Already correct
            '\\section': '\\section', # Already correct
        }
        
        # Add missing packages for common commands
        if '\\usepackage{enumitem}' not in content and '\\item' in content:
            content = content.replace(
                '\\usepackage{hyperref}',
                '\\usepackage{hyperref}\n\\usepackage{enumitem}'
            )
        
        return content

    def _repair_encoding_issues(self, lines: list, error_line: int, error_context: str) -> str:
        """Repair encoding issues"""
        content = '\n'.join(lines)
        
        # Common encoding fixes
        fixes = {
            '"': r'``',  # Left double quote
            '"': r"''",  # Right double quote
            ''': r'`',   # Left single quote
            ''': r"'",   # Right single quote
            '–': r'--',  # En dash
            '—': r'---', # Em dash
        }
        
        for bad_char, good_char in fixes.items():
            content = content.replace(bad_char, good_char)
        
        return content

    async def _test_compilation(self, content: str, project_dir: Path) -> Dict[str, Any]:
        """Test compilation of content"""
        test_file = project_dir / "test.tex"
        
        try:
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            cmd = [self.tectonic_path, str(test_file)]
            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Clean up test file
            if test_file.exists():
                test_file.unlink()
            
            return {"success": result.returncode == 0}
            
        except Exception:
            return {"success": False}
