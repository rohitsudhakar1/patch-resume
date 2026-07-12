import { useState, useEffect } from 'react';
import { ChatPanel } from './ChatPanel';
import { Workspace } from './Workspace';
import { UploadModal } from './UploadModal';
import { VersionHistory } from './VersionHistory';
import { useVersionHistory } from '@/hooks/useVersionHistory';
import { Button } from './ui/button';
import { PanelRightClose, PanelRightOpen, Minimize2 } from 'lucide-react';

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
  const [fitting, setFitting] = useState(false);

  // Initialize version history
  const {
    currentVersion,
    currentIndex,
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

        // Save to version history when content changes — but NOT for
        // undo/redo/history restores: re-saving a restored version would
        // truncate the redo stack and break Redo entirely.
        if (!projectData.__restored && projectData.resume_tex && projectData.resume_tex !== currentVersion) {
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

  // Shared restore path for undo/redo/history: sync the BACKEND first (the
  // PDF endpoint compiles from backend state — without this the preview
  // silently keeps showing the newer version), then notify with a marker so
  // the update listener doesn't re-save the restore as a new version.
  const restoreVersion = async (content: string) => {
    if (!content || !currentProject) return;
    const updatedProject = {
      ...currentProject,
      resume_tex: content,
      last_updated: new Date().toISOString()
    };
    sessionStorage.setItem('currentProject', JSON.stringify(updatedProject));
    setCurrentProject(updatedProject);
    try {
      await fetch('http://localhost:8000/project/recreate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedProject),
      });
    } catch (e) {
      console.error('❌ Failed to sync restored version to backend:', e);
    }
    window.dispatchEvent(new CustomEvent('projectUpdated', { detail: { ...updatedProject, __restored: true } }));
  };

  const handleUndo = () => restoreVersion(undo() || '');
  const handleRedo = () => restoreVersion(redo() || '');
  const handleGoToVersion = (versionId: string) => restoreVersion(goToVersion(versionId) || '');

  const handleTabChange = (tab: 'pdf' | 'latex') => {
    setActiveTab(tab);

    if (tab === 'pdf' && currentProject?.id) {
      window.dispatchEvent(new CustomEvent('pdfRegenerate', { detail: { projectId: currentProject.id } }));
    }
  };

  // Loop-condense the resume until its compiled PDF is a single page.
  const handleFitOnePage = async () => {
    if (!currentProject?.id || fitting) return;
    setFitting(true);
    try {
      const res = await fetch('http://localhost:8000/llm/fit-one-page', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: currentProject.id, resume: currentProject.resume_tex }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      if (data.resume_tex && data.changed) {
        // Route through the approval flow: ChatPanel renders the condensed
        // draft as a proposal with Apply/Discard + highlighted preview.
        window.dispatchEvent(new CustomEvent('fitProposal', {
          detail: {
            latex: data.resume_tex,
            pages: data.pages,
            fit: data.fit,
            iterations: data.iterations,
            previewAvailable: data.preview_available,
            projectId: currentProject.id,
          },
        }));
      } else {
        window.dispatchEvent(new CustomEvent('fitNoChange', { detail: { pages: data.pages } }));
      }
    } catch (e) {
      console.error('❌ Fit-to-one-page failed:', e);
    } finally {
      setFitting(false);
    }
  };

  if (showUploadModal) {
    return <UploadModal onClose={() => setShowUploadModal(false)} />;
  }

  return (
    <div className="flex h-screen bg-background text-foreground min-w-0 overflow-hidden">
      {/* Chat Panel */}
      <div className="w-96 border-r border-border bg-card flex-shrink-0 min-w-96 overflow-y-auto">
        <ChatPanel />
      </div>

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col bg-background min-w-0 overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 h-12 bg-card/60 border-b border-border backdrop-blur-sm">
          <div className="flex items-center gap-3">
            {/* Brand */}
            <div className="flex items-center gap-2 pr-3 mr-1 border-r border-border">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent text-accent-foreground font-display text-[13px] font-bold shadow-sm">P</div>
              <span className="font-display text-sm font-semibold tracking-tight">Patch Resume</span>
            </div>
            <button
              onClick={handleUndo}
              disabled={!canUndo}
              className="rounded-md px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition hover:bg-secondary hover:text-foreground disabled:opacity-40 disabled:hover:bg-transparent"
            >
              Undo
            </button>
            <button
              onClick={handleRedo}
              disabled={!canRedo}
              className="rounded-md px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition hover:bg-secondary hover:text-foreground disabled:opacity-40 disabled:hover:bg-transparent"
            >
              Redo
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleFitOnePage}
              disabled={fitting || !currentProject}
              title="Condense the resume until it fits on a single page"
              className="inline-flex items-center gap-1.5 rounded-md bg-accent px-2.5 py-1.5 text-xs font-medium text-accent-foreground transition hover:opacity-90 disabled:opacity-50"
            >
              {fitting ? (
                <>
                  <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  Fitting…
                </>
              ) : (
                <>
                  <Minimize2 className="w-3.5 h-3.5" />
                  Fit to 1 page
                </>
              )}
            </button>
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition hover:bg-secondary hover:text-foreground"
            >
              {showHistory ? <PanelRightClose className="w-3.5 h-3.5" /> : <PanelRightOpen className="w-3.5 h-3.5" />}
              {showHistory ? 'Hide' : 'Show'} History
            </button>
          </div>
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
                currentIndex={currentIndex}
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