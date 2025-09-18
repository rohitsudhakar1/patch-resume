import { Button } from '@/components/ui/button';
import { FileText, Eye } from 'lucide-react';
import { Change } from './ResumeEditor';
import { LaTeXEditor } from './LaTeXEditor';
import { PDFViewer } from './PDFViewer';

interface WorkspaceProps {
  activeTab: 'pdf' | 'latex';
  onTabChange: (tab: 'pdf' | 'latex') => void;
  changes: Change[];
  onChangeAccept: (changeId: string, accepted: boolean) => void;
}

export const Workspace = ({ activeTab, onTabChange, changes, onChangeAccept }: WorkspaceProps) => {
  return (
    <div className="flex-1 flex flex-col">
      {/* Tab Bar */}
      <div className="flex items-center border-b border-border bg-card">
        <div className="flex">
          <Button
            variant={activeTab === 'pdf' ? 'secondary' : 'ghost'}
            onClick={() => onTabChange('pdf')}
            className="rounded-none border-r border-border h-10"
          >
            <Eye className="w-4 h-4 mr-2" />
            PDF Preview
          </Button>
          <Button
            variant={activeTab === 'latex' ? 'secondary' : 'ghost'}
            onClick={() => onTabChange('latex')}
            className="rounded-none h-10"
          >
            <FileText className="w-4 h-4 mr-2" />
            LaTeX Source
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'pdf' ? (
          <PDFViewer changes={changes} onChangeAccept={onChangeAccept} />
        ) : (
          <LaTeXEditor changes={changes} onChangeAccept={onChangeAccept} />
        )}
      </div>
    </div>
  );
};