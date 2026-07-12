"""
Compilation service for converting LaTeX to PDF using multiple engines
"""
import os
import shutil
import subprocess
import tempfile
from typing import Tuple, Optional, List
from pathlib import Path

class CompileService:
    """Service for compiling LaTeX documents to PDF using multiple engines"""

    def __init__(self):
        # Legacy Windows install locations, kept as fallbacks for machines
        # where the binaries exist but aren't on PATH.
        self.miktex_path = os.path.join(
            os.path.expanduser("~"),
            "AppData", "Local", "Programs", "MiKTeX", "miktex", "bin", "x64"
        )
        self.tectonic_path = os.path.join(
            os.path.expanduser("~"),
            "scoop", "shims", "tectonic.exe"
        )

    def _find_binary(self, name: str, fallback: str = "") -> Optional[str]:
        """Resolve a compiler binary: PATH first, then a known install path."""
        found = shutil.which(name)
        if found:
            return found
        if fallback and os.path.exists(fallback):
            return fallback
        return None

    @staticmethod
    def _extract_error(compiler_name: str, stdout: str, stderr: str) -> str:
        """Pull the meaningful error lines out of a failed compile.

        TeX engines report errors as lines starting with '!' (with the
        offending line number on a following 'l.<n>' line); Tectonic logs
        'error:' lines to stderr. Fall back to the output tail so the
        AI repair loop always gets something concrete to work with.
        """
        lines = (stdout or "").splitlines() + (stderr or "").splitlines()
        picked = []
        for i, line in enumerate(lines):
            if line.startswith("!") or "error" in line.lower():
                picked.extend(lines[i:i + 3])  # error + a little context
        if not picked:
            picked = lines[-15:]
        message = "\n".join(picked).strip()
        return f"{compiler_name} failed:\n{message[:1500]}"
    
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
        last_error = ""

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
                try:
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
                        # Keep the real compiler error so the AI repair loop
                        # gets a concrete signal, not a generic message.
                        last_error = self._extract_error(compiler_name, result.stdout, result.stderr)

                except subprocess.TimeoutExpired:
                    print(f"⚠️ DEBUG: {compiler_name} timed out after 30 seconds")
                    last_error = f"{compiler_name} timed out after 30 seconds"
                except Exception as e:
                    print(f"⚠️ DEBUG: {compiler_name} error: {e}")
                    last_error = f"{compiler_name} error: {e}"
                    # Clean up auxiliary files from failed compilation
                    self._cleanup_aux_files(tex_file_path)

            except Exception as e:
                print(f"💥 DEBUG: {compiler_name} error: {str(e)}")
                last_error = f"{compiler_name} error: {e}"
                continue

        # All compilers failed (or none were found)
        error_msg = last_error or "No LaTeX compiler found on this machine. Install Tectonic or a TeX distribution."
        print(f"❌ DEBUG: Compilation failed: {error_msg[:300]}")
        return False, "", error_msg
    
    def _get_compilers(self, tex_file_path: str) -> List[Tuple[str, List[str]]]:
        """Get list of available compilers with their commands"""
        tex_file_path_abs = os.path.abspath(tex_file_path)
        output_dir = os.path.dirname(tex_file_path_abs)

        latex_args = [
            '-interaction=nonstopmode',
            '-halt-on-error',
            '-file-line-error',
            '-output-directory',
            output_dir,
            tex_file_path_abs
        ]

        candidates = [
            # Tectonic (fastest, Overleaf-style). Strict mode on purpose:
            # this compile IS the validation gate, so an erroring document
            # must fail loudly — never pass -Z continue-on-errors here, or
            # broken LaTeX sails through with exit code 0.
            ('tectonic', self._find_binary('tectonic', self.tectonic_path),
             ['--synctex', tex_file_path_abs]),

            # latexmk (automated, handles dependencies)
            ('latexmk', self._find_binary('latexmk', os.path.join(self.miktex_path, 'latexmk.exe')),
             ['-pdf'] + latex_args),

            # xelatex (Unicode support)
            ('xelatex', self._find_binary('xelatex', os.path.join(self.miktex_path, 'xelatex.exe')),
             latex_args),

            # pdflatex (standard, reliable)
            ('pdflatex', self._find_binary('pdflatex', os.path.join(self.miktex_path, 'pdflatex.exe')),
             latex_args),

            # lualatex (advanced features)
            ('lualatex', self._find_binary('lualatex', os.path.join(self.miktex_path, 'lualatex.exe')),
             latex_args),
        ]

        return [(name, [binary] + args) for name, binary, args in candidates if binary]
    
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
            ('tectonic', self._find_binary('tectonic', self.tectonic_path)),
            ('latexmk', self._find_binary('latexmk', os.path.join(self.miktex_path, 'latexmk.exe'))),
            ('pdflatex', self._find_binary('pdflatex', os.path.join(self.miktex_path, 'pdflatex.exe'))),
            ('xelatex', self._find_binary('xelatex', os.path.join(self.miktex_path, 'xelatex.exe'))),
            ('lualatex', self._find_binary('lualatex', os.path.join(self.miktex_path, 'lualatex.exe')))
        ]

        for name, path in compilers:
            status[name] = {
                'available': bool(path),
                'path': path or 'not found'
            }

            if path and os.path.exists(path):
                try:
                    # Try to get version
                    result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        status[name]['version'] = result.stdout.split('\n')[0].strip()
                except:
                    status[name]['version'] = 'Unknown'
        
        return status