import { useState } from 'react';
import { ChatPanel } from './ChatPanel';
import { Workspace } from './Workspace';
import { ApplyBar } from './ApplyBar';
import { UploadModal } from './UploadModal';

export interface Change {
  id: string;
  type: 'addition' | 'removal';
  startLine: number;
  endLine: number;
  content: string;
  accepted: boolean | null; // null = pending, true = accepted, false = rejected
  pdfRegions?: Array<{x: number, y: number, width: number, height: number}>;
}

export const ResumeEditor = () => {
  const [showUploadModal, setShowUploadModal] = useState(true);
  const [activeTab, setActiveTab] = useState<'pdf' | 'latex'>('pdf');
  const [isCompiling, setIsCompiling] = useState(false);
  const [changes, setChanges] = useState<Change[]>([
    {
      id: '1',
      type: 'addition',
      startLine: 12,
      endLine: 14,
      content: '\\item Led cross-functional team of 8 engineers to deliver customer analytics platform\n\\item Implemented microservices architecture reducing system latency by 40\\%\n\\item Established CI/CD pipeline improving deployment frequency by 300\\%',
      accepted: null,
      pdfRegions: [{x: 50, y: 200, width: 400, height: 60}]
    },
    {
      id: '2',
      type: 'removal',
      startLine: 18,
      endLine: 19,
      content: '\\item Basic project management tasks\n\\item Routine maintenance work',
      accepted: null,
      pdfRegions: [{x: 50, y: 280, width: 300, height: 40}]
    }
  ]);

  const handleChangeAccept = (changeId: string, accepted: boolean) => {
    setChanges(prev => prev.map(change => 
      change.id === changeId ? {...change, accepted} : change
    ));
  };

  const handleApplyChanges = () => {
    setIsCompiling(true);
    // Simulate compilation
    setTimeout(() => {
      setChanges(prev => prev.filter(change => change.accepted !== true));
      setIsCompiling(false);
    }, 2000);
  };

  const handleDiscardAll = () => {
    setChanges([]);
  };

  if (showUploadModal) {
    return <UploadModal onClose={() => setShowUploadModal(false)} />;
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Chat Panel */}
      <div className="w-96 border-r border-chat-border bg-chat-background">
        <ChatPanel />
      </div>

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col bg-workspace-background">
        <Workspace 
          activeTab={activeTab}
          onTabChange={setActiveTab}
          changes={changes}
          onChangeAccept={handleChangeAccept}
        />
        
        <ApplyBar
          hasChanges={changes.length > 0}
          acceptedCount={changes.filter(c => c.accepted === true).length}
          isCompiling={isCompiling}
          onApply={handleApplyChanges}
          onDiscard={handleDiscardAll}
        />
      </div>
    </div>
  );
};