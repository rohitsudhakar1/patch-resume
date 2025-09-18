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

  const handleFiles = (files: File[]) => {
    if (files.length > 0) {
      setIsProcessing(true);
      // Simulate processing
      setTimeout(() => {
        setIsProcessing(false);
        onClose();
      }, 3000);
    }
  };

  return (
    <div className="fixed inset-0 bg-background flex items-center justify-center z-50">
      <Card className="w-full max-w-2xl mx-4 p-8">
        <div className="text-center space-y-6">
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">Resume Builder</h1>
            <p className="text-muted-foreground">
              Upload your existing resume to get started. We'll convert it to clean, ATS-friendly LaTeX format.
            </p>
          </div>

          {isProcessing ? (
            <div className="space-y-4">
              <div className="w-16 h-16 mx-auto border-4 border-primary border-t-transparent rounded-full animate-spin" />
              <div>
                <h3 className="font-semibold">Processing your resume...</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Extracting content and converting to LaTeX format
                </p>
              </div>
            </div>
          ) : (
            <div
              className={`border-2 border-dashed rounded-lg p-12 transition-colors cursor-pointer ${
                isDragging
                  ? 'border-primary bg-primary/5'
                  : 'border-muted-foreground/25 hover:border-primary/50 hover:bg-primary/5'
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
                <Upload className="w-12 h-12 text-muted-foreground mx-auto" />
                <div>
                  <h3 className="font-semibold text-lg">Drop your resume here</h3>
                  <p className="text-muted-foreground">or click to browse</p>
                </div>
                
                <div className="flex justify-center gap-6 text-sm text-muted-foreground">
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
              <div className="text-sm text-muted-foreground">
                <strong>What happens next:</strong>
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
                className="w-full"
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