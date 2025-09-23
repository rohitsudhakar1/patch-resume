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
      <div className="flex items-center border-b border-slate-600/50 bg-slate-800/80 backdrop-blur-sm shadow-lg flex-shrink-0">
        <div className="flex">
          <Button
            variant="ghost"
            onClick={() => onTabChange('pdf')}
            className={`rounded-none border-r border-slate-600/50 h-14 px-8 transition-all duration-300 ${
              activeTab === 'pdf' 
                ? 'bg-gradient-to-r from-slate-700 to-slate-600 text-white shadow-lg border-b-2 border-b-cyan-500' 
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50 hover:shadow-md'
            }`}
          >
            <Eye className={`w-5 h-5 mr-3 ${activeTab === 'pdf' ? 'text-cyan-400' : 'text-slate-500'}`} />
            <span className="font-medium">PDF Preview</span>
          </Button>
          <Button
            variant="ghost"
            onClick={() => onTabChange('latex')}
            className={`rounded-none h-14 px-8 transition-all duration-300 ${
              activeTab === 'latex' 
                ? 'bg-gradient-to-r from-slate-700 to-slate-600 text-white shadow-lg border-b-2 border-b-cyan-500' 
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50 hover:shadow-md'
            }`}
          >
            <FileText className={`w-5 h-5 mr-3 ${activeTab === 'latex' ? 'text-cyan-400' : 'text-slate-500'}`} />
            <span className="font-medium">LaTeX Source</span>
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