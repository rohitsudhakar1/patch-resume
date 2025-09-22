@echo off
set MIKTEX_AUTO_INSTALL=1
set MIKTEX_ADMIN=0
set MIKTEX_SHARED=0
set MIKTEX_QUIET=1
set MIKTEX_NON_INTERACTIVE=1
set MIKTEX_DISABLE_INSTALLER=1
set MIKTEX_DISABLE_MAINTENANCE=1
set MIKTEX_DISABLE_UPDATE=1
set MIKTEX_DISABLE_UPDATE_CHECK=1
set MIKTEX_DISABLE_MAINTENANCE_MODE=1
"C:\Users\Rohit Sudhakar\AppData\Local\Programs\MiKTeX\miktex\bin\x64\lualatex.exe" -interaction=nonstopmode -halt-on-error -file-line-error -quiet -output-directory "C:\Users\Rohit Sudhakar\Desktop\Coding\patch-resume\temp_latex" "C:\Users\Rohit Sudhakar\Desktop\Coding\patch-resume\temp_latex\resume_latex-1758416316503.tex"
