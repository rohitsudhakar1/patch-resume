import React, { useState, useEffect } from 'react';

interface Project {
  id: string;
  resume_tex: string;
  pdf_url?: string;
  reconstruction_note?: string;
}

interface PDFViewerProps {
  project?: Project;
}

export const PDFViewer: React.FC<PDFViewerProps> = ({ project }) => {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>('');

  // Listen for project updates to force PDF regeneration
  useEffect(() => {
    const handleProjectUpdate = (event: CustomEvent) => {
      console.log('🔄 DEBUG: PDFViewer received project update, regenerating PDF...');
      console.log('🔄 DEBUG: Project update event detail:', event.detail);
      
      if (event.detail && event.detail.id) {
        // Update the project state with the new data
        const updatedProject = event.detail;
        console.log('🔄 DEBUG: Updated project data:', updatedProject);
        
        // Force PDF regeneration by updating the URL
        const newPdfUrl = `http://localhost:8000/artifact/pdf/${updatedProject.id}?t=${Date.now()}`;
        console.log('🔄 DEBUG: Regenerating PDF with new URL:', newPdfUrl);
        setPdfUrl(newPdfUrl);
        setIsLoading(true);
        setPdfError(false);
        
        // Also trigger a full PDF reload
        setTimeout(() => {
          const reloadPdfUrl = `http://localhost:8000/artifact/pdf/${updatedProject.id}?t=${Date.now()}`;
          console.log('🔄 DEBUG: Force reloading PDF with URL:', reloadPdfUrl);
          setPdfUrl(reloadPdfUrl);
        }, 500);
      } else if (project?.id) {
        // Fallback to current project ID
        const newPdfUrl = `http://localhost:8000/artifact/pdf/${project.id}?t=${Date.now()}`;
        console.log('🔄 DEBUG: Regenerating PDF with current project URL:', newPdfUrl);
        setPdfUrl(newPdfUrl);
        setIsLoading(true);
        setPdfError(false);
      }
    };

    const handlePdfRegenerate = (event: CustomEvent) => {
      console.log('🔄 DEBUG: PDFViewer received PDF regenerate event:', event.detail);
      if (event.detail && event.detail.projectId) {
        const newPdfUrl = `http://localhost:8000/artifact/pdf/${event.detail.projectId}?t=${Date.now()}`;
        console.log('🔄 DEBUG: Regenerating PDF from regenerate event:', newPdfUrl);
        setPdfUrl(newPdfUrl);
        setIsLoading(true);
        setPdfError(false);
      }
    };

    window.addEventListener('projectUpdated', handleProjectUpdate as EventListener);
    window.addEventListener('pdfRegenerate', handlePdfRegenerate as EventListener);
    return () => {
      window.removeEventListener('projectUpdated', handleProjectUpdate as EventListener);
      window.removeEventListener('pdfRegenerate', handlePdfRegenerate as EventListener);
    };
  }, [project?.id]);

  useEffect(() => {
    if (project?.id) {
      console.log('📄 DEBUG: PDFViewer loaded project:', project);
      setIsLoading(true);
      setPdfError(false);
      setErrorMessage('');
      
      // Always recreate the project first to ensure backend has the data
      const loadPDF = async () => {
        try {
          console.log('🔄 DEBUG: Ensuring project exists in backend...');
          
          // Get the current content from sessionStorage
          const currentContent = sessionStorage.getItem('currentProject');
          let projectData = project;
          
          if (currentContent) {
            try {
              const currentProject = JSON.parse(currentContent);
              projectData = {
                ...project,
                resume_tex: currentProject.resume_tex || project.resume_tex
              };
              console.log('📄 DEBUG: Using data from sessionStorage');
              console.log('📄 DEBUG: Resume content length:', projectData.resume_tex.length);
              console.log('📄 DEBUG: Resume content preview:', projectData.resume_tex.substring(0, 200));
            } catch (e) {
              console.log('⚠️ DEBUG: Could not parse sessionStorage data, using project data');
            }
          }
          
          // Also try to get content from the LaTeX editor if available
          const latexEditorContent = (window as any).latexEditorContent;
          if (latexEditorContent && latexEditorContent.length > 0) {
            console.log('📄 DEBUG: Using content from LaTeX editor');
            console.log('📄 DEBUG: LaTeX editor content length:', latexEditorContent.length);
            console.log('📄 DEBUG: LaTeX editor content preview:', latexEditorContent.substring(0, 200));
            projectData = {
              ...project,
              resume_tex: latexEditorContent
            };
          }
          
          console.log('📄 DEBUG: Sending project data for recreation:', projectData);
          
          // Always recreate the project to ensure backend has the latest data
          const recreateResponse = await fetch('http://localhost:8000/project/recreate', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(projectData),
          });
          
          if (recreateResponse.ok) {
            console.log('✅ DEBUG: Project recreated successfully');
            // Now try to load the PDF
            const pdfUrl = `http://localhost:8000/artifact/pdf/${project.id}?t=${Date.now()}`;
            console.log('📄 DEBUG: Loading PDF from:', pdfUrl);
            setPdfUrl(pdfUrl);
            
            // Force PDF reload by updating the URL after a short delay to ensure regeneration
            setTimeout(() => {
              const newPdfUrl = `http://localhost:8000/artifact/pdf/${project.id}?t=${Date.now()}`;
              console.log('🔄 DEBUG: Forcing PDF reload with new URL:', newPdfUrl);
              setPdfUrl(newPdfUrl);
            }, 200);
            
            setIsLoading(false);
          } else {
            console.log('❌ DEBUG: Project recreation failed');
            setPdfError(true);
            setErrorMessage('Failed to recreate project');
            setIsLoading(false);
          }
        } catch (error) {
          console.log('❌ DEBUG: Error loading PDF:', error);
          setPdfError(true);
          setErrorMessage('Failed to load PDF');
          setIsLoading(false);
        }
      };
      
      loadPDF();
    }
  }, [project]);

  const handleChangeClick = (changeId: string) => {
    // Switch to LaTeX tab and highlight the change
    window.dispatchEvent(new CustomEvent('switchToLatex', { detail: changeId }));
  };

  const handlePdfLoad = () => {
    console.log('📄 DEBUG: PDF loaded successfully');
    setIsLoading(false);
    setPdfError(false);
  };

  const handlePdfError = (e?: any) => {
    console.log('❌ DEBUG: PDF load error:', e);
    console.log('❌ DEBUG: PDF URL:', pdfUrl);
    setIsLoading(false);
    setPdfError(true);
  };

  const retryPdfLoad = () => {
    if (project?.id) {
      console.log('🔄 DEBUG: Retrying PDF load...');
      setIsLoading(true);
      setPdfError(false);
      setErrorMessage('');
      
      // Recreate the project and load PDF
      const loadPDF = async () => {
        try {
          console.log('🔄 DEBUG: Recreating project for retry...');
          
          // Get the current content from sessionStorage
          const currentContent = sessionStorage.getItem('currentProject');
          let projectData = project;
          
          if (currentContent) {
            try {
              const currentProject = JSON.parse(currentContent);
              projectData = {
                ...project,
                resume_tex: currentProject.resume_tex || project.resume_tex
              };
            } catch (e) {
              console.log('⚠️ DEBUG: Could not parse sessionStorage data, using project data');
            }
          }
          
          // Also try to get content from the LaTeX editor if available
          const latexEditorContent = (window as any).latexEditorContent;
          if (latexEditorContent && latexEditorContent.length > 0) {
            projectData = {
              ...project,
              resume_tex: latexEditorContent
            };
          }
          
          // Recreate the project
          const recreateResponse = await fetch('http://localhost:8000/project/recreate', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(projectData),
          });
          
          if (recreateResponse.ok) {
            console.log('✅ DEBUG: Project recreated successfully for retry');
            const newPdfUrl = `http://localhost:8000/artifact/pdf/${project.id}?t=${Date.now()}`;
            setPdfUrl(newPdfUrl);
            setIsLoading(false);
          } else {
            console.log('❌ DEBUG: Project recreation failed for retry');
            setPdfError(true);
            setErrorMessage('Failed to recreate project');
            setIsLoading(false);
          }
        } catch (error) {
          console.log('❌ DEBUG: Error in retry:', error);
          setPdfError(true);
          setErrorMessage('Failed to retry PDF load');
          setIsLoading(false);
        }
      };
      
      loadPDF();
    }
  };

  if (!project) {
    console.log('❌ DEBUG: PDFViewer - No project provided');
    return (
      <div className="flex items-center justify-center h-full bg-slate-800">
        <div className="text-center">
          <div className="text-slate-400 mb-4">
            <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-slate-200 mb-2">No Resume Loaded</h3>
          <p className="text-slate-400">Upload a resume to see the PDF preview</p>
          <div className="text-xs text-slate-500 mt-2">
            Debug: Project prop is {project === null ? 'null' : project === undefined ? 'undefined' : 'present'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-800">
      {/* Header */}
      <div className="flex-shrink-0 p-4 border-b border-slate-700">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-200">PDF Preview</h2>
            <p className="text-sm text-slate-400">Live preview of your resume</p>
          </div>
          {pdfError && (
            <button
              onClick={retryPdfLoad}
              className="px-3 py-1 text-xs rounded bg-blue-600 text-white hover:bg-blue-700"
            >
              Retry PDF Generation
            </button>
          )}
        </div>
      </div>

      {/* PDF Content */}
      <div className="flex-1 min-h-0">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className="text-slate-400">Generating PDF...</p>
            </div>
          </div>
        ) : pdfError ? (
          <div className="text-center py-20">
            <div className="text-red-600 mb-4">
              <h3 className="text-lg font-semibold">PDF Preview Error</h3>
              <p className="text-sm mb-2">Unable to load PDF preview.</p>
              {errorMessage && (
                <div className="bg-red-50 border border-red-200 rounded p-3 mb-4 max-w-md mx-auto">
                  <p className="text-xs text-red-700 font-mono break-all">
                    Error: {errorMessage}
                  </p>
                </div>
              )}
              <button
                onClick={retryPdfLoad}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Retry PDF Generation
              </button>
            </div>
          </div>
        ) : pdfUrl ? (
          <div className="h-full bg-slate-100">
            {/* Page indicators */}
            <div className="absolute top-4 right-4 z-10 bg-slate-800/90 text-white px-3 py-1 rounded-full text-xs">
              <span className="text-slate-300">PDF Preview</span>
            </div>
            
            {/* PDF Container with page-like styling */}
            <div className="w-full h-full overflow-auto p-4">
              <div className="max-w-4xl mx-auto">
                <div className="bg-white shadow-2xl rounded-lg overflow-hidden">
                  <iframe
                    src={pdfUrl}
                    className="w-full h-[800px] border-0"
                    onLoad={handlePdfLoad}
                    onError={handlePdfError}
                    title="Resume PDF"
                  />
                </div>
                
                {/* Page break indicator */}
                <div className="mt-4 text-center">
                  <div className="inline-flex items-center gap-2 text-slate-500 text-sm">
                    <div className="w-8 h-px bg-slate-400"></div>
                    <span>Page 1</span>
                    <div className="w-8 h-px bg-slate-400"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="text-slate-400 mb-4">
                <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-slate-200 mb-2">PDF Not Available</h3>
              <p className="text-slate-400">PDF generation failed or is not ready</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};