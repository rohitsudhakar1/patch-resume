import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Check, X } from 'lucide-react';

interface Change {
  id: string;
  type: 'addition' | 'removal' | 'replacement';
  startLine: number;
  endLine: number;
  content: string;
  accepted?: boolean | null;
  // Backend field names for compatibility
  start_line?: number;
  end_line?: number;
  pdf_regions?: Array<{x: number, y: number, width: number, height: number}>;
}

interface LaTeXEditorProps {
  changes: Change[];
  onContentChange?: (content: string) => void;
}

export default function LaTeXEditor({ changes, onContentChange }: LaTeXEditorProps) {
  const [content, setContent] = useState<string>('');
  const [contentVersion, setContentVersion] = useState<number>(0);
  const [rejectedChanges, setRejectedChanges] = useState<Set<string>>(new Set());
  const [appliedChanges, setAppliedChanges] = useState<Set<string>>(new Set());

  // Load content from sessionStorage
  useEffect(() => {
    const projectData = sessionStorage.getItem('currentProject');
    if (projectData) {
      const project = JSON.parse(projectData);
      if (project.resume_tex) {
        setContent(project.resume_tex);
        console.log('📄 DEBUG: LaTeXEditor loaded project:', project);
      }
    }
  }, []);

  // Listen for project updates
  useEffect(() => {
    const handleProjectUpdate = () => {
      const projectData = sessionStorage.getItem('currentProject');
      if (projectData) {
        const project = JSON.parse(projectData);
        if (project.resume_tex) {
          console.log('🔄 DEBUG: LaTeXEditor updating content from project');
          console.log('📝 DEBUG: New content length:', project.resume_tex.length);
          setContent(project.resume_tex);
          console.log('🔄 DEBUG: LaTeXEditor updated content from project');
        }
      }
    };

    window.addEventListener('projectUpdated', handleProjectUpdate);
    return () => window.removeEventListener('projectUpdated', handleProjectUpdate);
  }, []); // Remove content dependency to prevent infinite loop

  // Clear previous changes when new ones come in (only if changes actually changed)
  useEffect(() => {
    if (changes.length > 0) {
      console.log('🔄 DEBUG: New changes received, clearing previous state');
      console.log('📊 DEBUG: Changes IDs:', changes.map(c => c.id));
      setRejectedChanges(new Set());
      setAppliedChanges(new Set());
    }
  }, [changes.map(c => c.id).join(',')]); // Only trigger when change IDs change

  // Listen for change acceptance events and update content accordingly
  useEffect(() => {
    const handleChangeAccepted = (event: CustomEvent) => {
      const { changeId, accepted } = event.detail;
      console.log('🔧 DEBUG: LaTeXEditor received change acceptance:', changeId, accepted);
      
      if (accepted) {
        // The change has already been applied in handleApplyChange
        // Just ensure the UI reflects the current state
        setAppliedChanges(prev => new Set(prev).add(changeId));
        setRejectedChanges(prev => {
          const newSet = new Set(prev);
          newSet.delete(changeId);
          return newSet;
        });
      } else {
        // Mark as rejected
        setRejectedChanges(prev => new Set(prev).add(changeId));
        setAppliedChanges(prev => {
          const newSet = new Set(prev);
          newSet.delete(changeId);
          return newSet;
        });
      }
    };

    window.addEventListener('changeAccepted', handleChangeAccepted as EventListener);
    return () => window.removeEventListener('changeAccepted', handleChangeAccepted as EventListener);
  }, []);

  const handleContentChange = async (newContent: string) => {
    console.log('📝 DEBUG: Content changed, length:', newContent.length);
    setContent(newContent);
    setContentVersion(prev => prev + 1);

    // Update sessionStorage
    const projectData = sessionStorage.getItem('currentProject');
    if (projectData) {
      try {
        const project = JSON.parse(projectData);
        project.resume_tex = newContent;
        sessionStorage.setItem('currentProject', JSON.stringify(project));
        console.log('💾 DEBUG: Updated sessionStorage with new content');

        // Create project in backend if it doesn't exist
        const response = await fetch('http://localhost:8000/project/recreate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(project),
        });

        if (response.ok) {
          console.log('✅ DEBUG: Project created/updated in backend');
        } else {
          console.log('❌ DEBUG: Failed to create project in backend');
        }
      } catch (error) {
        console.log('❌ DEBUG: Error creating project:', error);
      }
    }
    
    // Also expose content globally for PDF viewer
    (window as any).latexEditorContent = newContent;
    
    onContentChange?.(newContent);
  };

  const handleApplyChange = (changeId: string, accepted: boolean) => {
    console.log(`🔧 DEBUG: Applying change ${changeId}: ${accepted ? 'accepted' : 'rejected'}`);
    
    if (accepted) {
      // Find the change and apply it to content
      const change = changes.find(c => c.id === changeId);
      if (change) {
        console.log(`✅ DEBUG: Applying change ${changeId} of type ${change.type}`);
        
        // Check if this change is already applied
        if (appliedChanges.has(changeId)) {
          console.log(`⏭️ DEBUG: Change ${changeId} already applied, skipping`);
          return;
        }
        
        // Apply the change to the content
        const lines = content.split('\n');
        let newContent = content;
        
        // Get the correct line number (handle both frontend and backend field names)
        const lineNumber = change.startLine || change.start_line || 1;
        const lineIndex = lineNumber - 1;
        
        console.log(`🔍 DEBUG: Line number: ${lineNumber}, Line index: ${lineIndex}, Content length: ${lines.length}`);
        console.log(`🔍 DEBUG: Change type: ${change.type}`);
        console.log(`🔍 DEBUG: Change content: "${change.content}"`);
        console.log(`🔍 DEBUG: Current lines around target:`, lines.slice(Math.max(0, lineIndex - 2), lineIndex + 3));
        console.log(`🔍 DEBUG: Target line content: "${lines[lineIndex] || 'UNDEFINED'}"`);
        console.log(`🔍 DEBUG: All lines:`, lines.map((line, idx) => `${idx + 1}: ${line}`).slice(Math.max(0, lineIndex - 2), lineIndex + 3));
        
        if (change.type === 'removal') {
          // Remove the line
          console.log(`🗑️ DEBUG: Removing line ${lineNumber}: "${lines[lineIndex]}"`);
          if (lineIndex >= 0 && lineIndex < lines.length) {
            lines.splice(lineIndex, 1);
            newContent = lines.join('\n');
            console.log(`✅ DEBUG: Line removed successfully`);
          }
        } else if (change.type === 'addition') {
          // Add the line
          console.log(`➕ DEBUG: Adding line at position ${lineNumber}: "${change.content}"`);
          if (lineIndex >= 0 && lineIndex <= lines.length) {
            lines.splice(lineIndex, 0, change.content);
            newContent = lines.join('\n');
            console.log(`✅ DEBUG: Line added successfully`);
          }
        } else if (change.type === 'replacement') {
          // Replace the line
          console.log(`🔄 DEBUG: Replacing line ${lineNumber}: "${lines[lineIndex]}" -> "${change.content}"`);
          if (lineIndex >= 0 && lineIndex < lines.length) {
            console.log(`🔄 DEBUG: Before replacement - line ${lineIndex}: "${lines[lineIndex]}"`);
            const originalLine = lines[lineIndex];
            lines[lineIndex] = change.content;
            newContent = lines.join('\n');
            console.log(`🔄 DEBUG: After replacement - line ${lineIndex}: "${lines[lineIndex]}"`);
            console.log(`🔄 DEBUG: Original line was: "${originalLine}"`);
            console.log(`🔄 DEBUG: New line is: "${lines[lineIndex]}"`);
            console.log(`✅ DEBUG: Line replaced successfully`);
          }
        }
        
        // Update content if it changed
        if (newContent !== content) {
          console.log(`📝 DEBUG: Content before change: ${content.substring(0, 100)}...`);
          console.log(`📝 DEBUG: Content after change: ${newContent.substring(0, 100)}...`);
          console.log(`📝 DEBUG: Content length before: ${content.length}, after: ${newContent.length}`);
          
          // Update content immediately
          setContent(newContent);
          setContentVersion(prev => prev + 1);
          handleContentChange(newContent);
          
          // Update sessionStorage with the new content
          const projectData = sessionStorage.getItem('currentProject');
          if (projectData) {
            const project = JSON.parse(projectData);
            project.resume_tex = newContent;
            sessionStorage.setItem('currentProject', JSON.stringify(project));
            console.log(`💾 DEBUG: Updated sessionStorage with new content`);
            
            // Dispatch project updated event
            window.dispatchEvent(new CustomEvent('projectUpdated', { 
              detail: { project } 
            }));
          }
          
          // Mark change as applied
          setAppliedChanges(prev => new Set(prev).add(changeId));
          setRejectedChanges(prev => {
            const newSet = new Set(prev);
            newSet.delete(changeId);
            return newSet;
          });
          
          console.log(`✅ DEBUG: Change ${changeId} applied and marked as applied`);
        } else {
          console.log(`⚠️ DEBUG: No content change detected for change ${changeId}`);
        }
      } else {
        console.log(`❌ DEBUG: Change ${changeId} not found`);
      }
    } else {
      // Mark as rejected
      setRejectedChanges(prev => new Set(prev).add(changeId));
      setAppliedChanges(prev => {
        const newSet = new Set(prev);
        newSet.delete(changeId);
        return newSet;
      });
      console.log(`❌ DEBUG: Change ${changeId} marked as rejected`);
    }
    
    // Dispatch change acceptance event for parent components
    const event = new CustomEvent('changeAccepted', {
      detail: { changeId, accepted }
    });
    window.dispatchEvent(event);
  };

  const handleAcceptAll = () => {
    console.log(`🎯 DEBUG: Accepting all changes`);
    
    // Get all active changes (not rejected, not applied)
    const activeChanges = changes.filter(change => 
      !rejectedChanges.has(change.id) && !appliedChanges.has(change.id)
    );
    
    console.log(`📋 DEBUG: Found ${activeChanges.length} active changes to accept`);
    
    if (activeChanges.length === 0) {
      console.log(`⚠️ DEBUG: No active changes to accept`);
      return;
    }
    
    // Apply all changes to content
    let newContent = content;
    const lines = newContent.split('\n');
    
    // Sort changes by line number (descending) to avoid index issues
    const sortedChanges = [...activeChanges].sort((a, b) => {
      const aLine = a.startLine || a.start_line || 0;
      const bLine = b.startLine || b.start_line || 0;
      return bLine - aLine;
    });
    
    console.log(`📊 DEBUG: Processing ${sortedChanges.length} changes in order`);
    console.log(`📊 DEBUG: Initial content length: ${newContent.length}`);
    
    // Apply each change
    for (const change of sortedChanges) {
      console.log(`🔄 DEBUG: Applying change ${change.id} of type ${change.type}`);
      console.log(`🔄 DEBUG: Change content: "${change.content}"`);
      
      const lineNumber = change.startLine || change.start_line || 1;
      const lineIndex = lineNumber - 1;
      
      console.log(`🔍 DEBUG: Line number: ${lineNumber}, Line index: ${lineIndex}, Content length: ${lines.length}`);
      console.log(`🔍 DEBUG: Change type: ${change.type}`);
      console.log(`🔍 DEBUG: Change content: "${change.content}"`);
      console.log(`🔍 DEBUG: Current lines around target:`, lines.slice(Math.max(0, lineIndex - 2), lineIndex + 3));
      console.log(`🔍 DEBUG: Target line content: "${lines[lineIndex] || 'UNDEFINED'}"`);
      
      if (change.type === 'removal') {
        // Remove the line
        console.log(`🗑️ DEBUG: Removing line ${lineNumber}: "${lines[lineIndex]}"`);
        if (lineIndex >= 0 && lineIndex < lines.length) {
          lines.splice(lineIndex, 1);
          console.log(`✅ DEBUG: Line removed successfully`);
        }
      } else if (change.type === 'addition') {
        // Add the line
        console.log(`➕ DEBUG: Adding line at position ${lineNumber}: "${change.content}"`);
        if (lineIndex >= 0 && lineIndex <= lines.length) {
          lines.splice(lineIndex, 0, change.content);
          console.log(`✅ DEBUG: Line added successfully`);
        }
      } else if (change.type === 'replacement') {
        // Replace the line
        console.log(`🔄 DEBUG: Replacing line ${lineNumber}: "${lines[lineIndex]}" -> "${change.content}"`);
        if (lineIndex >= 0 && lineIndex < lines.length) {
          console.log(`🔄 DEBUG: Before replacement - line ${lineIndex}: "${lines[lineIndex]}"`);
          const originalLine = lines[lineIndex];
          lines[lineIndex] = change.content;
          console.log(`🔄 DEBUG: After replacement - line ${lineIndex}: "${lines[lineIndex]}"`);
          console.log(`🔄 DEBUG: Original line was: "${originalLine}"`);
          console.log(`🔄 DEBUG: New line is: "${lines[lineIndex]}"`);
          console.log(`✅ DEBUG: Line replaced successfully`);
        }
      }
    }
    
    // Update content with all changes
    newContent = lines.join('\n');
    console.log(`📝 DEBUG: Content before all changes: ${content.substring(0, 100)}...`);
    console.log(`📝 DEBUG: Content after all changes: ${newContent.substring(0, 100)}...`);
    console.log(`📝 DEBUG: Content length before: ${content.length}, after: ${newContent.length}`);
    
    // Update content
    setContent(newContent);
    setContentVersion(prev => prev + 1);
    handleContentChange(newContent);
    
    // Mark all changes as applied
    const newAppliedChanges = new Set(appliedChanges);
    activeChanges.forEach(change => newAppliedChanges.add(change.id));
    setAppliedChanges(newAppliedChanges);
    
    // Remove from rejected changes
    setRejectedChanges(prev => {
      const newSet = new Set(prev);
      activeChanges.forEach(change => newSet.delete(change.id));
      return newSet;
    });
    
    console.log(`💾 DEBUG: Updated sessionStorage with all changes`);
    console.log(`🎉 DEBUG: All changes applied successfully`);
  };

  // Expose accept all function globally
  useEffect(() => {
    (window as any).latexEditorAcceptAll = handleAcceptAll;
    return () => {
      delete (window as any).latexEditorAcceptAll;
    };
  }, []);

  // Get active changes (not applied, not rejected)
  const activeChanges = changes.filter(change => 
    !rejectedChanges.has(change.id) && !appliedChanges.has(change.id)
  );

  // Group changes by line number
  const changesByLine = new Map<number, Change[]>();
  activeChanges.forEach(change => {
    const lineNumber = change.startLine || change.start_line || 1;
    if (!changesByLine.has(lineNumber)) {
      changesByLine.set(lineNumber, []);
    }
    changesByLine.get(lineNumber)!.push(change);
  });

  console.log(`🔍 DEBUG: Active changes: ${activeChanges.length}, Total changes: ${changes.length}`);
  console.log(`🔍 DEBUG: Applied changes: ${Array.from(appliedChanges)}`);
  console.log(`🔍 DEBUG: Rejected changes: ${Array.from(rejectedChanges)}`);

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700">
        <h2 className="text-lg font-semibold text-slate-200">LaTeX Editor</h2>
        <div className="text-sm text-slate-400">
          {activeChanges.length} changes pending
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {activeChanges.length === 0 ? (
          <div className="text-center text-slate-400 py-8">
            <div className="text-4xl mb-4">✅</div>
            <div className="text-lg font-semibold mb-2">No Changes Pending</div>
            <div className="text-sm">All changes have been processed</div>
          </div>
        ) : (
          <div className="space-y-4">
            {Array.from(changesByLine.entries()).map(([lineNumber, lineChanges]) => (
              <div key={lineNumber} className="border border-slate-700 rounded-lg p-4 bg-slate-800">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-slate-200">Line {lineNumber}</h3>
                  <div className="text-sm text-slate-400">
                    {lineChanges.length} change{lineChanges.length > 1 ? 's' : ''}
                  </div>
                </div>
                
                <div className="space-y-3">
                  {lineChanges.map((change) => (
                    <div key={change.id} className="flex items-start space-x-3 p-3 bg-slate-700 rounded border border-slate-600">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <span className={`px-2 py-1 text-xs font-semibold rounded ${
                            change.type === 'addition' ? 'bg-green-900 text-green-200' :
                            change.type === 'removal' ? 'bg-red-900 text-red-200' :
                            'bg-blue-900 text-blue-200'
                          }`}>
                            {change.type.toUpperCase()}
                          </span>
                        </div>
                        <div className="text-slate-200 font-mono text-sm whitespace-pre-wrap">
                          {change.content}
                        </div>
                      </div>
                      
                      <div className="flex space-x-2">
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-green-600 border-green-600 hover:bg-green-600 hover:text-white"
                          onClick={() => handleApplyChange(change.id, true)}
                        >
                          <Check className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-red-600 border-red-600 hover:bg-red-600 hover:text-white"
                          onClick={() => handleApplyChange(change.id, false)}
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
