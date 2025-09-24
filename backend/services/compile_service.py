"""
Compilation service for converting LaTeX to PDF using multiple engines
"""
import os
import subprocess
import tempfile
from typing import Tuple, Optional, List
from pathlib import Path

class CompileService:
    """Service for compiling LaTeX documents to PDF using multiple engines"""
    
    def __init__(self):
        # Compiler paths
        self.miktex_path = os.path.join(
            os.path.expanduser("~"), 
            "AppData", "Local", "Programs", "MiKTeX", "miktex", "bin", "x64"
        )
        self.tectonic_path = os.path.join(
            os.path.expanduser("~"), 
            "scoop", "shims", "tectonic.exe"
        )
    
    def compile_latex(self, latex_content: str, project_id: str, temp_dir: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Compile LaTeX content to PDF using multiple engines with fallback
        
        Args:
            latex_content: LaTeX document content
            project_id: Project identifier for file naming
            temp_dir: Optional temporary directory (will create if not provided)
            
        Returns:
            Tuple of (success: bool, pdf_path: str, error_message: str)
        """
        print(f"🔧 DEBUG: Starting LaTeX compilation for project {project_id}")
        
        # Create temporary directory if not provided
        if not temp_dir:
            temp_dir = os.path.join(os.getcwd(), 'temp_latex')
        
        os.makedirs(temp_dir, exist_ok=True)
        
        # Write LaTeX file
        tex_file_path = os.path.join(temp_dir, f'resume_{project_id}.tex')
        with open(tex_file_path, 'w', encoding='utf-8') as tex_file:
            tex_file.write(latex_content)
        
        # Define compilers in order of preference
        compilers = self._get_compilers(tex_file_path)
        
        pdf_path = tex_file_path.replace('.tex', '.pdf')
        
        # Try each compiler
        for compiler_name, cmd in compilers:
            try:
                print(f"🔧 DEBUG: Trying {compiler_name} compiler...")
                
                # Check if compiler exists
                if not os.path.exists(cmd[0]):
                    print(f"⚠️ DEBUG: {compiler_name} not found at {cmd[0]}, skipping")
                    continue
                
                print(f"✅ DEBUG: {compiler_name} found, compiling...")
                print(f"🔧 DEBUG: Command: {' '.join(cmd)}")
                
                # Clean up previous PDF
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)
                
                # Run compiler with timeout
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,  # 30 second timeout
                    cwd=os.path.dirname(tex_file_path)
                )
                
                print(f"🔧 DEBUG: {compiler_name} finished with return code: {result.returncode}")
                
                if result.returncode == 0 and os.path.exists(pdf_path):
                    print(f"✅ DEBUG: PDF generated successfully with {compiler_name}")
                    return True, pdf_path, ""
                else:
                    print(f"⚠️ DEBUG: {compiler_name} failed")
                    print(f"🔧 DEBUG: stdout: {result.stdout[:500]}")
                    print(f"🔧 DEBUG: stderr: {result.stderr[:500]}")
                    
                    # Clean up auxiliary files from failed compilation
                    self._cleanup_aux_files(tex_file_path)
                    
            except subprocess.TimeoutExpired:
                print(f"⏰ DEBUG: {compiler_name} timed out")
                continue
            except Exception as e:
                print(f"💥 DEBUG: {compiler_name} error: {str(e)}")
                continue
        
        # All compilers failed
        error_msg = "All LaTeX compilers failed. Please check your LaTeX syntax."
        print(f"❌ DEBUG: {error_msg}")
        return False, "", error_msg
    
    def _get_compilers(self, tex_file_path: str) -> List[Tuple[str, List[str]]]:
        """Get list of available compilers with their commands"""
        tex_file_path_abs = os.path.abspath(tex_file_path)
        output_dir = os.path.dirname(tex_file_path_abs)
        
        compilers = [
            # Tectonic (fastest, Overleaf-style)
            ('tectonic', [
                self.tectonic_path, 
                '--synctex', 
                '-Z', 
                'continue-on-errors', 
                tex_file_path_abs
            ]),
            
            # latexmk (automated, handles dependencies)
            ('latexmk', [
                os.path.join(self.miktex_path, 'latexmk.exe'), 
                '-pdf', 
                '-interaction=nonstopmode', 
                '-halt-on-error', 
                '-file-line-error', 
                '-output-directory', 
                output_dir, 
                tex_file_path_abs
            ]),
            
            # xelatex (Unicode support)
            ('xelatex', [
                os.path.join(self.miktex_path, 'xelatex.exe'), 
                '-interaction=nonstopmode', 
                '-halt-on-error', 
                '-file-line-error', 
                '-output-directory', 
                output_dir, 
                tex_file_path_abs
            ]),
            
            # pdflatex (standard, reliable)
            ('pdflatex', [
                os.path.join(self.miktex_path, 'pdflatex.exe'), 
                '-interaction=nonstopmode', 
                '-halt-on-error', 
                '-file-line-error', 
                '-output-directory', 
                output_dir, 
                tex_file_path_abs
            ]),
            
            # lualatex (advanced features)
            ('lualatex', [
                os.path.join(self.miktex_path, 'lualatex.exe'), 
                '-interaction=nonstopmode', 
                '-halt-on-error', 
                '-file-line-error', 
                '-output-directory', 
                output_dir, 
                tex_file_path_abs
            ])
        ]
        
        return compilers
    
    def _cleanup_aux_files(self, tex_file_path: str):
        """Clean up auxiliary files from failed compilation"""
        aux_extensions = ['.aux', '.log', '.out', '.synctex.gz', '.fls', '.fdb_latexmk']
        
        for ext in aux_extensions:
            aux_file = tex_file_path.replace('.tex', ext)
            if os.path.exists(aux_file):
                try:
                    os.unlink(aux_file)
                except:
                    pass
    
    def cleanup_temp_files(self, tex_file_path: str, pdf_path: str):
        """Clean up temporary files after successful compilation"""
        try:
            # Clean up auxiliary files
            self._cleanup_aux_files(tex_file_path)
            
            # Optionally clean up PDF (depending on use case)
            # if os.path.exists(pdf_path):
            #     os.unlink(pdf_path)
                
        except Exception as e:
            print(f"⚠️ DEBUG: Error cleaning up temp files: {str(e)}")
    
    def get_compiler_status(self) -> dict:
        """Get status of all available compilers"""
        status = {}
        
        compilers = [
            ('tectonic', self.tectonic_path),
            ('latexmk', os.path.join(self.miktex_path, 'latexmk.exe')),
            ('pdflatex', os.path.join(self.miktex_path, 'pdflatex.exe')),
            ('xelatex', os.path.join(self.miktex_path, 'xelatex.exe')),
            ('lualatex', os.path.join(self.miktex_path, 'lualatex.exe'))
        ]
        
        for name, path in compilers:
            status[name] = {
                'available': os.path.exists(path),
                'path': path
            }
            
            if os.path.exists(path):
                try:
                    # Try to get version
                    result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        status[name]['version'] = result.stdout.split('\n')[0].strip()
                except:
                    status[name]['version'] = 'Unknown'
        
        return status