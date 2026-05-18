import { useState, useEffect } from 'react';
import { ChatPanel } from './ChatPanel';
import { Workspace } from './Workspace';
import { UploadModal } from './UploadModal';
import { VersionHistory } from './VersionHistory';
import { useVersionHistory } from '@/hooks/useVersionHistory';
import { Button } from './ui/button';
import { PanelRightClose, PanelRightOpen } from 'lucide-react';

export interface Change {
  id: string;
  type: 'addition' | 'removal' | 'replacement';
  startLine: number;
  endLine: number;
  content: string;
  accepted?: boolean | null;
  pdfRegions?: Array<{x: number, y: number, width: number, height: number}>;
}

export const ResumeEditor = () => {
  const [showUploadModal, setShowUploadModal] = useState(true);
  const [activeTab, setActiveTab] = useState<'pdf' | 'latex'>('pdf');
  const [currentProject, setCurrentProject] = useState<any>(null);
  const [pendingChanges, setPendingChanges] = useState<any[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  // Initialize version history
  const {
    currentVersion,
    versions,
    canUndo,
    canRedo,
    saveVersion,
    undo,
    redo,
    goToVersion
  } = useVersionHistory(currentProject?.resume_tex || '');

  // Load project data on mount
  useEffect(() => {
    const projectData = sessionStorage.getItem('currentProject');
    if (projectData) {
      const project = JSON.parse(projectData);
      setCurrentProject(project);
      setShowUploadModal(false);

      // Initialize version history with uploaded resume
      if (project.resume_tex) {
        saveVersion(project.resume_tex, 'Resume uploaded');
      }
    }
  }, []);

  // Listen for project updates
  useEffect(() => {
    const handleProjectUpdate = (event?: CustomEvent) => {
      let projectData;

      if (event && event.detail) {
        projectData = event.detail;
        console.log('🔄 Project update received');
      } else {
        const storedData = sessionStorage.getItem('currentProject');
        if (storedData) {
          projectData = JSON.parse(storedData);
        }
      }

      if (projectData) {
        setCurrentProject(projectData);
        setShowUploadModal(false);

        // Save to version history when content changes
        if (projectData.resume_tex && projectData.resume_tex !== currentVersion) {
          const description = projectData.last_description || 'AI update';
          saveVersion(projectData.resume_tex, description);
        }
      }
    };

    window.addEventListener('storage', handleProjectUpdate);
    window.addEventListener('projectUpdated', handleProjectUpdate as EventListener);

    return () => {
      window.removeEventListener('storage', handleProjectUpdate);
      window.removeEventListener('projectUpdated', handleProjectUpdate as EventListener);
    };
  }, [currentVersion, saveVersion]);

  // Handle LaTeX content changes
  const handleLatexChange = (newContent: string, description: string = 'Manual edit') => {
    if (currentProject && newContent !== currentProject.resume_tex) {
      const updatedProject = {
        ...currentProject,
        resume_tex: newContent,
        last_updated: new Date().toISOString(),
        last_description: description
      };

      sessionStorage.setItem('currentProject', JSON.stringify(updatedProject));
      setCurrentProject(updatedProject);
      saveVersion(newContent, description);

      // Update backend
      fetch('http://localhost:8000/project/recreate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedProject),
      }).then(() => {
        window.dispatchEvent(new CustomEvent('projectUpdated', { detail: updatedProject }));
      });
    }
  };

  // Handle undo
  const handleUndo = () => {
    const previousContent = undo();
    if (previousContent && currentProject) {
      const updatedProject = {
        ...currentProject,
        resume_tex: previousContent,
        last_updated: new Date().toISOString()
      };
      sessionStorage.setItem('currentProject', JSON.stringify(updatedProject));
      setCurrentProject(updatedProject);
      window.dispatchEvent(new CustomEvent('projectUpdated', { detail: updatedProject }));
    }
  };

  // Handle redo
  const handleRedo = () => {
    const nextContent = redo();
    if (nextContent && currentProject) {
      const updatedProject = {
        ...currentProject,
        resume_tex: nextContent,
        last_updated: new Date().toISOString()
      };
      sessionStorage.setItem('currentProject', JSON.stringify(updatedProject));
      setCurrentProject(updatedProject);
      window.dispatchEvent(new CustomEvent('projectUpdated', { detail: updatedProject }));
    }
  };

  // Handle go to version
  const handleGoToVersion = (versionId: string) => {
    const versionContent = goToVersion(versionId);
    if (versionContent && currentProject) {
      const updatedProject = {
        ...currentProject,
        resume_tex: versionContent,
        last_updated: new Date().toISOString()
      };
      sessionStorage.setItem('currentProject', JSON.stringify(updatedProject));
      setCurrentProject(updatedProject);
      window.dispatchEvent(new CustomEvent('projectUpdated', { detail: updatedProject }));
    }
  };

  const handleTabChange = (tab: 'pdf' | 'latex') => {
    setActiveTab(tab);

    if (tab === 'pdf' && currentProject?.id) {
      window.dispatchEvent(new CustomEvent('pdfRegenerate', { detail: { projectId: currentProject.id } }));
    }
  };

  if (showUploadModal) {
    return <UploadModal onClose={() => setShowUploadModal(false)} />;
  }

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 min-w-0 overflow-hidden">
      {/* Chat Panel */}
      <div className="w-96 border-r border-slate-700/50 bg-slate-800/50 backdrop-blur-sm shadow-xl flex-shrink-0 min-w-96 overflow-y-auto">
        <ChatPanel />
      </div>

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col bg-slate-900/50 backdrop-blur-sm min-w-0 overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 bg-slate-800/80 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleUndo}
              disabled={!canUndo}
              className="bg-slate-700 border-slate-600 hover:bg-slate-600"
            >
              Undo
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleRedo}
              disabled={!canRedo}
              className="bg-slate-700 border-slate-600 hover:bg-slate-600"
            >
              Redo
            </Button>
          </div>

          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowHistory(!showHistory)}
            className="bg-slate-700 border-slate-600 hover:bg-slate-600"
          >
            {showHistory ? <PanelRightClose className="w-4 h-4 mr-2" /> : <PanelRightOpen className="w-4 h-4 mr-2" />}
            {showHistory ? 'Hide' : 'Show'} History
          </Button>
        </div>

        <div className="flex-1 flex min-h-0 overflow-hidden">
          {/* Workspace */}
          <div className="flex-1 min-h-0 overflow-hidden">
            <Workspace
              activeTab={activeTab}
              onTabChange={handleTabChange}
              project={currentProject}
              onLatexChange={handleLatexChange}
              changes={pendingChanges}
            />
          </div>

          {/* Version History Panel */}
          {showHistory && (
            <div className="w-80 flex-shrink-0">
              <VersionHistory
                versions={versions}
                currentIndex={versions.findIndex(v => v.content === currentVersion)}
                canUndo={canUndo}
                canRedo={canRedo}
                onUndo={handleUndo}
                onRedo={handleRedo}
                onGoToVersion={handleGoToVersion}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};