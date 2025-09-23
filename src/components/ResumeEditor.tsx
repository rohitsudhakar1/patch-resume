import { useState, useEffect } from 'react';
import { ChatPanel } from './ChatPanel';
import { Workspace } from './Workspace';
import { UploadModal } from './UploadModal';
import { apiClient } from '../lib/api';

export interface Change {
  id: string;
  type: 'addition' | 'removal' | 'replacement';
  startLine: number;
  endLine: number;
  content: string;
  accepted?: boolean | null; // null = pending, true = accepted, false = rejected
  pdfRegions?: Array<{x: number, y: number, width: number, height: number}>;
}

export const ResumeEditor = () => {
  const [showUploadModal, setShowUploadModal] = useState(true);
  const [activeTab, setActiveTab] = useState<'pdf' | 'latex'>('pdf');
  const [isCompiling, setIsCompiling] = useState(false);
  const [changes, setChanges] = useState<Change[]>([]);
  const [currentProject, setCurrentProject] = useState<any>(null);

  // Load project data on mount
  useEffect(() => {
    const projectData = sessionStorage.getItem('currentProject');
    if (projectData) {
      setCurrentProject(JSON.parse(projectData));
      setShowUploadModal(false);
    }
  }, []);

  // Listen for project updates from LaTeX editor and upload modal
  useEffect(() => {
    const handleProjectUpdate = (event?: CustomEvent) => {
      let projectData;
      
      if (event && event.detail) {
        // Handle custom event from upload modal
        projectData = event.detail;
        console.log('🔄 DEBUG: ResumeEditor received project from upload modal:', projectData);
      } else {
        // Handle storage change event
        const storedData = sessionStorage.getItem('currentProject');
        if (storedData) {
          projectData = JSON.parse(storedData);
          console.log('🔄 DEBUG: ResumeEditor updated project from storage:', projectData);
        }
      }
      
      if (projectData) {
        setCurrentProject(projectData);
        setShowUploadModal(false); // Hide upload modal when project is loaded
      }
    };

    // Listen for storage changes (when LaTeX editor creates a project)
    window.addEventListener('storage', handleProjectUpdate);
    
    // Also listen for custom project update events
    window.addEventListener('projectUpdated', handleProjectUpdate as EventListener);
    
    return () => {
      window.removeEventListener('storage', handleProjectUpdate);
      window.removeEventListener('projectUpdated', handleProjectUpdate as EventListener);
    };
  }, []);

  // Listen for patch generation events
  useEffect(() => {
    const handlePatchGenerated = (event: CustomEvent) => {
      const patchResult = event.detail;
      console.log('📥 DEBUG: ResumeEditor received patch result:', patchResult);
      console.log('📝 DEBUG: Setting changes:', patchResult.changes);
      
      // Update current project ID to match the patch result
      if (patchResult.project_id && patchResult.project_id !== currentProject?.id) {
        console.log('🔄 DEBUG: Updating project ID from', currentProject?.id, 'to', patchResult.project_id);
        setCurrentProject(prev => prev ? { ...prev, id: patchResult.project_id } : { id: patchResult.project_id });
      }
      
      // Map backend field names to frontend field names
      const newChanges = patchResult.changes.map((change: any) => ({
        ...change,
        startLine: change.start_line || change.startLine,
        endLine: change.end_line || change.endLine,
        pdfRegions: change.pdf_regions || change.pdfRegions
      }));
      
      // Simply set the new changes
      setChanges(newChanges);
      console.log('📊 DEBUG: Set new changes:', newChanges.length);
      
      // Automatically switch to LaTeX tab when changes are received
      console.log('🔄 DEBUG: Switching to LaTeX tab to show changes');
      setActiveTab('latex');
    };

    window.addEventListener('patchGenerated', handlePatchGenerated as EventListener);
    return () => window.removeEventListener('patchGenerated', handlePatchGenerated as EventListener);
  }, []);

  // Listen for individual change acceptance events from LaTeXEditor
  useEffect(() => {
    const handleChangeAccepted = (event: CustomEvent) => {
      const { changeId, accepted } = event.detail;
      console.log('🔧 DEBUG: ResumeEditor received change acceptance:', changeId, accepted);
      handleChangeAccept(changeId, accepted);
    };

    window.addEventListener('changeAccepted', handleChangeAccepted as EventListener);
    return () => window.removeEventListener('changeAccepted', handleChangeAccepted as EventListener);
  }, []);

  // Persist changes to sessionStorage
  useEffect(() => {
    if (changes.length > 0) {
      console.log('💾 DEBUG: Persisting changes to sessionStorage');
      sessionStorage.setItem('currentChanges', JSON.stringify(changes));
    } else {
      // Clear sessionStorage when no changes remain
      console.log('🧹 DEBUG: No changes remaining, clearing sessionStorage');
      sessionStorage.removeItem('currentChanges');
    }
  }, [changes]);

  // Load changes from sessionStorage on mount
  useEffect(() => {
    // Clear any old changes from sessionStorage to prevent them from interfering
    const storedChanges = sessionStorage.getItem('currentChanges');
    if (storedChanges) {
      console.log('🧹 DEBUG: Clearing old changes from sessionStorage to prevent interference');
      sessionStorage.removeItem('currentChanges');
    }
  }, []);

  const handleChangeAccept = (changeId: string, accepted: boolean) => {
    console.log('🔧 DEBUG: handleChangeAccept called:', changeId, accepted);
    
    // Simply remove the change from the list - LaTeXEditor handles the actual application
    setChanges(prev => {
      const newChanges = prev.filter(c => c.id !== changeId);
      console.log(`🔄 DEBUG: Removed change ${changeId}, ${prev.length} -> ${newChanges.length} changes`);
      return newChanges;
    });
    
    // If a change was accepted, update the project state
    if (accepted) {
      console.log('🔄 DEBUG: Change accepted, updating project state...');
      updateProjectState();
    }
  };

  const updateProjectState = async () => {
    try {
      // Get the current LaTeX content from the editor
      const currentContent = (window as any).latexEditorContent;
      if (currentContent && currentProject) {
        console.log('🔄 DEBUG: Updating project with new LaTeX content...');
        
        // Update the project in sessionStorage
        const updatedProject = {
          ...currentProject,
          resume_tex: currentContent,
          last_updated: new Date().toISOString()
        };
        
        sessionStorage.setItem('currentProject', JSON.stringify(updatedProject));
        setCurrentProject(updatedProject);
        
        // Update the project in the backend
        try {
          const response = await fetch('http://localhost:8000/project/recreate', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(updatedProject),
          });
          
          if (response.ok) {
            console.log('✅ DEBUG: Project updated in backend');
          } else {
            console.log('⚠️ DEBUG: Failed to update project in backend');
          }
        } catch (error) {
          console.log('⚠️ DEBUG: Error updating project in backend:', error);
        }
        
        // Trigger a custom event to notify other components
        window.dispatchEvent(new CustomEvent('projectUpdated', { detail: updatedProject }));
        
        // Also trigger a PDF regeneration event
        window.dispatchEvent(new CustomEvent('pdfRegenerate', { detail: { projectId: updatedProject.id } }));
      }
    } catch (error) {
      console.log('❌ DEBUG: Error updating project state:', error);
    }
  };


  const handleTabChange = (tab: 'pdf' | 'latex') => {
    console.log('🔄 DEBUG: Tab changed to:', tab);
    setActiveTab(tab);
    
    // If switching to PDF view, trigger PDF regeneration
    if (tab === 'pdf' && currentProject?.id) {
      console.log('🔄 DEBUG: Switching to PDF view, triggering regeneration...');
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
        <div className="flex-1 min-h-0 overflow-hidden">
          <Workspace 
            activeTab={activeTab}
            onTabChange={handleTabChange}
            changes={changes}
            onChangeAccept={handleChangeAccept}
            project={currentProject}
          />
        </div>
        
      </div>
    </div>
  );
};