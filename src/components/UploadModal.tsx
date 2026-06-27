import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Upload, FileText, File, Image } from 'lucide-react';

interface UploadModalProps {
  onClose: () => void;
}

export const UploadModal = ({ onClose }: UploadModalProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      handleFiles(files);
    }
  };

  const handleFiles = async (files: File[]) => {
    if (files.length > 0) {
      setIsProcessing(true);
      try {
        console.log('📤 DEBUG: Starting file upload...', files[0].name);
        
        // Upload file to backend
        const { apiClient } = await import('../lib/api');
        const result = await apiClient.uploadResume(files[0]);
        
        console.log('✅ DEBUG: Upload successful:', result);
        
        // Store project info for the session
        const projectData = {
          id: result.project_id,
          resume_tex: result.resume_tex,
          pdf_url: result.pdf_url,
          reconstruction_note: result.reconstruction_note
        };
        
        sessionStorage.setItem('currentProject', JSON.stringify(projectData));
        
        // Notify ResumeEditor about the new project
        window.dispatchEvent(new CustomEvent('projectUpdated', { detail: projectData }));
        
        console.log('✅ DEBUG: Project uploaded and stored:', projectData);
        
        setIsProcessing(false);
        onClose();
      } catch (error) {
        console.error('❌ ERROR: Upload failed:', error);
        setIsProcessing(false);
        
        // Show detailed error to user
        const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
        alert(`Upload failed: ${errorMessage}\n\nPlease check the console for more details and try again.`);
        
        // Clear any existing project data
        sessionStorage.removeItem('currentProject');
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-background p-4">
      {/* ambient accent glow */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 h-80 w-[36rem] -translate-x-1/2 rounded-full bg-accent/10 blur-3xl" />
      </div>

      <Card className="relative w-full max-w-xl border-border bg-card/90 p-8 shadow-2xl backdrop-blur-sm">
        {/* Brand */}
        <div className="mb-7 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent font-display text-base font-bold text-accent-foreground shadow-sm">P</div>
          <div className="leading-tight">
            <h1 className="font-display text-lg font-semibold tracking-tight text-foreground">Patch Resume</h1>
            <p className="text-xs text-muted-foreground">AI-proposed edits · live LaTeX · clean PDF</p>
          </div>
        </div>

        <h2 className="font-display text-2xl font-semibold tracking-tight text-foreground">
          Turn your resume into reviewable, AI-polished LaTeX
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Drop in your current resume. We extract it, convert it to clean ATS-friendly LaTeX,
          and let you chat to improve it — every change is yours to accept or reject.
        </p>

        {isProcessing ? (
          <div className="mt-7 flex flex-col items-center justify-center rounded-xl border border-border bg-secondary/40 py-14">
            <div className="h-10 w-10 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
            <h3 className="mt-4 text-sm font-semibold text-foreground">Reading your resume…</h3>
            <p className="mt-1 text-xs text-muted-foreground">Extracting content and generating LaTeX with Claude</p>
          </div>
        ) : (
          <div
            className={`group mt-7 cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-all duration-200 ${
              isDragging
                ? 'border-accent bg-accent/10'
                : 'border-border hover:border-accent/60 hover:bg-secondary/40'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById('file-input')?.click()}
          >
            <input id="file-input" type="file" accept=".pdf,.docx,.txt" onChange={handleFileInput} className="hidden" />
            <div className={`mx-auto flex h-12 w-12 items-center justify-center rounded-xl transition-colors ${isDragging ? 'bg-accent text-accent-foreground' : 'bg-secondary text-muted-foreground group-hover:text-foreground'}`}>
              <Upload className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-base font-semibold text-foreground">Drop your resume here</h3>
            <p className="mt-0.5 text-sm text-muted-foreground">or click to browse</p>
            <div className="mt-5 flex items-center justify-center gap-2 text-xs text-muted-foreground">
              {[{ icon: File, label: 'PDF' }, { icon: FileText, label: 'DOCX' }, { icon: Image, label: 'TXT' }].map(({ icon: Icon, label }) => (
                <span key={label} className="inline-flex items-center gap-1.5 rounded-full border border-border bg-secondary/50 px-2.5 py-1">
                  <Icon className="h-3.5 w-3.5" /> {label}
                </span>
              ))}
            </div>
          </div>
        )}

        {!isProcessing && (
          <button
            onClick={onClose}
            className="mt-5 w-full rounded-lg border border-border py-2.5 text-sm font-medium text-muted-foreground transition hover:bg-secondary hover:text-foreground"
          >
            Skip — start with a blank resume
          </button>
        )}
      </Card>
    </div>
  );
};