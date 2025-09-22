import { useState } from 'react';
import { Button } from '@/components/ui/button';
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
    <div className="fixed inset-0 bg-slate-900/95 backdrop-blur-sm flex items-center justify-center z-50">
      <Card className="w-full max-w-2xl mx-4 p-8 bg-slate-800 border-slate-700 shadow-2xl">
        <div className="text-center space-y-6">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Resume Builder</h1>
            <p className="text-slate-300">
              Upload your existing resume to get started. We'll convert it to clean, ATS-friendly LaTeX format.
            </p>
          </div>

          {isProcessing ? (
            <div className="space-y-4">
              <div className="w-16 h-16 mx-auto border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <div>
                <h3 className="font-semibold text-white">Processing your resume...</h3>
                <p className="text-sm text-slate-400 mt-1">
                  Extracting content and converting to LaTeX format
                </p>
              </div>
            </div>
          ) : (
            <div
              className={`border-2 border-dashed rounded-lg p-12 transition-all duration-200 cursor-pointer ${
                isDragging
                  ? 'border-blue-500 bg-blue-500/10 shadow-lg'
                  : 'border-slate-600 hover:border-blue-500/70 hover:bg-slate-700/30 hover:shadow-lg'
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => document.getElementById('file-input')?.click()}
            >
              <input
                id="file-input"
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleFileInput}
                className="hidden"
              />
              
              <div className="space-y-4">
                <Upload className={`w-12 h-12 mx-auto transition-colors ${
                  isDragging ? 'text-blue-400' : 'text-slate-500'
                }`} />
                <div>
                  <h3 className="font-semibold text-lg text-white">Drop your resume here</h3>
                  <p className="text-slate-400">or click to browse</p>
                </div>
                
                <div className="flex justify-center gap-6 text-sm text-slate-500">
                  <div className="flex items-center gap-1">
                    <File className="w-4 h-4" />
                    PDF
                  </div>
                  <div className="flex items-center gap-1">
                    <FileText className="w-4 h-4" />
                    DOCX
                  </div>
                  <div className="flex items-center gap-1">
                    <Image className="w-4 h-4" />
                    TXT
                  </div>
                </div>
              </div>
            </div>
          )}

          {!isProcessing && (
            <div className="space-y-3">
              <div className="text-sm text-slate-400">
                <strong className="text-white">What happens next:</strong>
                <ul className="mt-2 space-y-1 text-left max-w-md mx-auto">
                  <li>• We'll extract and clean up your content</li>
                  <li>• Convert to professional LaTeX format</li>
                  <li>• Generate a clean PDF preview</li>
                  <li>• You can then chat to improve it further</li>
                </ul>
              </div>

              <Button 
                variant="outline" 
                onClick={onClose}
                className="w-full border-slate-500 text-slate-200 hover:bg-slate-600 hover:text-white hover:border-slate-400 bg-slate-700/50"
              >
                Skip - Start with blank resume
              </Button>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};