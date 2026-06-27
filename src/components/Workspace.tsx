import { Button } from '@/components/ui/button';
import { FileText, Eye } from 'lucide-react';
import LaTeXEditor from './LaTeXEditor';
import { PDFViewer } from './PDFViewer';

interface WorkspaceProps {
  activeTab: 'pdf' | 'latex';
  onTabChange: (tab: 'pdf' | 'latex') => void;
  project?: any;
  onLatexChange?: (content: string) => void;
  changes?: any[];
}

export const Workspace = ({ activeTab, onTabChange, project, onLatexChange, changes = [] }: WorkspaceProps) => {
  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      {/* Tab Bar */}
      <div className="flex items-center gap-1 border-b border-border bg-card/60 px-2 backdrop-blur-sm flex-shrink-0">
        <button
          onClick={() => onTabChange('pdf')}
          className={`group relative flex h-12 items-center gap-2 px-4 text-sm font-medium transition-colors ${
            activeTab === 'pdf' ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Eye className={`h-4 w-4 ${activeTab === 'pdf' ? 'text-accent' : 'text-muted-foreground group-hover:text-foreground'}`} />
          PDF Preview
          {activeTab === 'pdf' && <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-accent" />}
        </button>
        <button
          onClick={() => onTabChange('latex')}
          className={`group relative flex h-12 items-center gap-2 px-4 text-sm font-medium transition-colors ${
            activeTab === 'latex' ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <FileText className={`h-4 w-4 ${activeTab === 'latex' ? 'text-accent' : 'text-muted-foreground group-hover:text-foreground'}`} />
          LaTeX Source
          {activeTab === 'latex' && <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-accent" />}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {/* Keep both views mounted to maintain event listeners */}
        <div className={`h-full ${activeTab === 'pdf' ? 'block' : 'hidden'}`}>
          <PDFViewer project={project} />
        </div>
        <div className={`h-full ${activeTab === 'latex' ? 'block' : 'hidden'}`}>
          <LaTeXEditor
            content={project?.resume_tex || ''}
            onContentChange={onLatexChange}
            changes={changes}
          />
        </div>
      </div>
    </div>
  );
};