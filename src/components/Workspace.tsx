import { Button } from '@/components/ui/button';
import { FileText, Eye } from 'lucide-react';
import { Change } from './ResumeEditor';
import LaTeXEditor from './LaTeXEditor';
import { PDFViewer } from './PDFViewer';

interface WorkspaceProps {
  activeTab: 'pdf' | 'latex';
  onTabChange: (tab: 'pdf' | 'latex') => void;
  changes: Change[];
  onChangeAccept: (changeId: string, accepted: boolean) => void;
  project?: any;
}

export const Workspace = ({ activeTab, onTabChange, changes, onChangeAccept, project }: WorkspaceProps) => {
  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      {/* Tab Bar */}
      <div className="flex items-center border-b border-slate-600 bg-slate-800 shadow-sm flex-shrink-0">
        <div className="flex">
          <Button
            variant="ghost"
            onClick={() => onTabChange('pdf')}
            className={`rounded-none border-r border-slate-600 h-12 px-6 transition-all duration-200 ${
              activeTab === 'pdf' 
                ? 'bg-slate-700 text-white shadow-inner border-b-2 border-b-blue-500' 
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            <Eye className={`w-4 h-4 mr-2 ${activeTab === 'pdf' ? 'text-blue-400' : 'text-slate-500'}`} />
            PDF Preview
          </Button>
          <Button
            variant="ghost"
            onClick={() => onTabChange('latex')}
            className={`rounded-none h-12 px-6 transition-all duration-200 ${
              activeTab === 'latex' 
                ? 'bg-slate-700 text-white shadow-inner border-b-2 border-b-blue-500' 
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            <FileText className={`w-4 h-4 mr-2 ${activeTab === 'latex' ? 'text-blue-400' : 'text-slate-500'}`} />
            LaTeX Source
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <div className="h-full transition-all duration-300 ease-in-out">
          {activeTab === 'pdf' ? (
            <PDFViewer project={project} />
          ) : (
            <LaTeXEditor changes={changes} />
          )}
        </div>
      </div>
    </div>
  );
};