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
  // True while the pane is showing a pending proposal (highlighted changes).
  const [isProposalPreview, setIsProposalPreview] = useState(false);

  // Listen for project updates to force PDF regeneration
  useEffect(() => {
    const handleProjectUpdate = (event: CustomEvent) => {
      console.log('📥 DEBUG: PDFViewer received project update event');

      setIsProposalPreview(false); // an applied update always exits preview mode

      if (event.detail && event.detail.id) {
        // Update the project state with the new data
        const updatedProject = event.detail;
        console.log('🔄 DEBUG: PDF regeneration triggered for project:', updatedProject.id);

        // Force PDF regeneration by updating the URL with timestamp
        const newPdfUrl = `http://localhost:8000/artifact/pdf/${updatedProject.id}?t=${Date.now()}`;
        console.log('🔄 DEBUG: PDF regenerated with URL:', newPdfUrl);
        setPdfUrl(newPdfUrl);
        setIsLoading(true);
        setPdfError(false);

        // Also trigger a full PDF reload after delay to ensure backend compilation completes
        setTimeout(() => {
          const reloadPdfUrl = `http://localhost:8000/artifact/pdf/${updatedProject.id}?t=${Date.now()}`;
          console.log('🔄 DEBUG: Force reloading PDF');
          setPdfUrl(reloadPdfUrl);
        }, 500);
      } else if (project?.id) {
        // Fallback to current project ID
        const newPdfUrl = `http://localhost:8000/artifact/pdf/${project.id}?t=${Date.now()}`;
        console.log('🔄 DEBUG: PDF regeneration (fallback) with URL:', newPdfUrl);
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

    // A pending proposal: show its highlighted preview PDF (compiled by the
    // backend from a deterministic diff). Nothing is applied yet.
    const handleProposalPreview = (event: CustomEvent) => {
      const pid = event.detail?.projectId || project?.id;
      if (!pid) return;
      console.log('🖍️ DEBUG: Showing proposal preview for', pid);
      setPdfUrl(`http://localhost:8000/artifact/pdf-preview/${pid}?t=${Date.now()}`);
      setIsProposalPreview(true);
      setIsLoading(true);
      setPdfError(false);
    };

    // Proposal discarded: snap back to the current document.
    const handleProposalPreviewEnd = (event: CustomEvent) => {
      const pid = event.detail?.projectId || project?.id;
      setIsProposalPreview(false);
      if (pid) {
        console.log('↩️ DEBUG: Proposal dismissed, reverting preview to current document');
        setPdfUrl(`http://localhost:8000/artifact/pdf/${pid}?t=${Date.now()}`);
        setIsLoading(true);
        setPdfError(false);
      }
    };

    window.addEventListener('projectUpdated', handleProjectUpdate as EventListener);
    window.addEventListener('pdfRegenerate', handlePdfRegenerate as EventListener);
    window.addEventListener('proposalPreview', handleProposalPreview as EventListener);
    window.addEventListener('proposalPreviewEnd', handleProposalPreviewEnd as EventListener);
    return () => {
      window.removeEventListener('projectUpdated', handleProjectUpdate as EventListener);
      window.removeEventListener('pdfRegenerate', handlePdfRegenerate as EventListener);
      window.removeEventListener('proposalPreview', handleProposalPreview as EventListener);
      window.removeEventListener('proposalPreviewEnd', handleProposalPreviewEnd as EventListener);
    };
  }, [project?.id]);

  useEffect(() => {
    if (project?.id) {
      console.log('📄 DEBUG: PDFViewer project prop changed:', project.id);

      // Just load the PDF - backend already has the latest content
      // DO NOT recreate project here as it may overwrite fresh changes from chat
      const pdfUrl = `http://localhost:8000/artifact/pdf/${project.id}?t=${Date.now()}`;
      console.log('📄 DEBUG: Loading PDF from:', pdfUrl);
      setPdfUrl(pdfUrl);
      setIsLoading(true);
      setPdfError(false);
      setErrorMessage('');
    }
  }, [project?.id]);

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

      // Just request the PDF again - backend already has the content
      const newPdfUrl = `http://localhost:8000/artifact/pdf/${project.id}?t=${Date.now()}`;
      console.log('🔄 DEBUG: Requesting PDF again:', newPdfUrl);
      setPdfUrl(newPdfUrl);
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
    <div className="flex flex-col h-full bg-card">
      {/* Header */}
      <div className="flex-shrink-0 px-5 py-3 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="flex h-2 w-2 items-center justify-center">
              <span className={`h-2 w-2 rounded-full ${isProposalPreview ? 'animate-pulse bg-amber-400' : isLoading ? 'animate-pulse bg-accent' : pdfError ? 'bg-destructive' : 'bg-emerald-400'}`} />
            </span>
            <div>
              <h2 className="text-sm font-semibold text-foreground leading-tight">
                {isProposalPreview ? 'Proposed change' : 'Live Preview'}
              </h2>
              <p className="text-xs text-muted-foreground">
                {isProposalPreview
                  ? 'Blue text = what changes · not applied yet'
                  : isLoading ? 'Compiling…' : pdfError ? 'Needs attention' : 'Up to date'}
              </p>
            </div>
            {isProposalPreview && (
              <span
                className="ml-2 rounded-full border border-amber-400/40 bg-amber-400/10 px-2.5 py-0.5 text-[11px] font-medium text-amber-300"
                data-testid="preview-banner"
              >
                Awaiting your approval
              </span>
            )}
          </div>
          {pdfError && (
            <button
              onClick={retryPdfLoad}
              className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-accent-foreground transition hover:opacity-90"
            >
              Retry
            </button>
          )}
        </div>
      </div>

      {/* PDF Content */}
      <div className="flex-1 min-h-0 relative">
        {pdfError ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md px-6">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-rose-500/10 text-rose-400">
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" /></svg>
              </div>
              <h3 className="text-base font-semibold text-foreground">Couldn't render the PDF</h3>
              <p className="mt-1 text-sm text-muted-foreground">The compile may still be finishing, or the LaTeX needs a fix.</p>
              {errorMessage && (
                <p className="mt-3 rounded-md bg-rose-500/10 px-3 py-2 text-left font-mono text-xs text-rose-300 break-all">{errorMessage}</p>
              )}
              <button
                onClick={retryPdfLoad}
                className="mt-4 inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition hover:opacity-90"
              >
                Retry
              </button>
            </div>
          </div>
        ) : pdfUrl ? (
          <div className="h-full w-full overflow-auto bg-canvas px-6 py-6">
            {/* Always-mounted iframe so onLoad can clear the loading state */}
            <div className="mx-auto max-w-3xl">
              <div className="overflow-hidden rounded-lg bg-white shadow-2xl ring-1 ring-black/10">
                <iframe
                  src={pdfUrl}
                  className="h-[860px] w-full border-0"
                  onLoad={handlePdfLoad}
                  onError={handlePdfError}
                  title="Resume PDF"
                />
              </div>
            </div>

            {/* Loading overlay (does not unmount the iframe) */}
            {isLoading && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-canvas/80 backdrop-blur-sm transition-opacity">
                <div className="text-center">
                  <div className="mx-auto mb-3 h-7 w-7 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
                  <p className="text-sm text-muted-foreground">Compiling your resume…</p>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
                <svg className="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
              </div>
              <h3 className="text-base font-semibold text-foreground">No preview yet</h3>
              <p className="mt-1 text-sm text-muted-foreground">Upload a resume to see the live PDF.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};