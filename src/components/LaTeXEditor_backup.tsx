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
    setContent(newContent);
    
    // Update sessionStorage
    const projectData = sessionStorage.getItem('currentProject');
    if (projectData) {
      const project = JSON.parse(projectData);
      project.resume_tex = newContent;
      sessionStorage.setItem('currentProject', JSON.stringify(project));
    } else if (newContent.trim().length > 0) {
      // Create a new project if none exists and content is added
      console.log('🔄 DEBUG: Creating new project for LaTeX content');
      const newProject = {
        id: `latex-${Date.now()}`,
        resume_tex: newContent,
        pdf_url: null,
        reconstruction_note: 'Created from LaTeX editor'
      };
      sessionStorage.setItem('currentProject', JSON.stringify(newProject));
      
      // Create project in backend
      try {
        const response = await fetch('http://localhost:8000/project/recreate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(newProject),
        });
        
      if (response.ok) {
        console.log('✅ DEBUG: Project created in backend for LaTeX content');
        // Dispatch project update event
        window.dispatchEvent(new CustomEvent('projectUpdated', { detail: newProject }));
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
            
            console.log(`🔍 DEBUG: Line number: ${lineNumber}, Line index: ${lineIndex}, Content length: ${lines.length}`);
            console.log(`🔍 DEBUG: Change type: replacement (converted from removal+addition)`);
            console.log(`🔍 DEBUG: Change content: "${additionChange.content}"`);
            console.log(`🔍 DEBUG: Current lines around target:`, lines.slice(Math.max(0, lineIndex - 2), lineIndex + 3));
            console.log(`🔍 DEBUG: Target line content: "${lines[lineIndex] || 'UNDEFINED'}"`);
            
            // Replace the line
            console.log(`🔄 DEBUG: Replacing line ${lineNumber}: "${lines[lineIndex]}" -> "${additionChange.content}"`);
            if (lineIndex >= 0 && lineIndex < lines.length) {
              console.log(`🔄 DEBUG: Before replacement - line ${lineIndex}: "${lines[lineIndex]}"`);
              const originalLine = lines[lineIndex];
              lines[lineIndex] = additionChange.content;
              newContent = lines.join('\n');
              console.log(`🔄 DEBUG: After replacement - line ${lineIndex}: "${lines[lineIndex]}"`);
              console.log(`🔄 DEBUG: Original line was: "${originalLine}"`);
              console.log(`🔄 DEBUG: New line is: "${lines[lineIndex]}"`);
              console.log(`✅ DEBUG: Line replaced successfully`);
              console.log(`✅ DEBUG: New content around replacement:`, newContent.split('\n').slice(Math.max(0, lineIndex - 2), lineIndex + 3));
              
              // Verify the replacement actually happened
              if (lines[lineIndex] === additionChange.content) {
                console.log(`✅ DEBUG: Replacement verified - content matches expected`);
              } else {
                console.log(`❌ DEBUG: Replacement failed - content does not match expected`);
              }
              
              // Update content immediately
              console.log(`📝 DEBUG: Content before change: ${content.substring(0, 100)}...`);
              console.log(`📝 DEBUG: Content after change: ${newContent.substring(0, 100)}...`);
              console.log(`📝 DEBUG: Content length before: ${content.length}, after: ${newContent.length}`);
              console.log(`📝 DEBUG: New content lines:`, newContent.split('\n').slice(Math.max(0, lineIndex - 2), lineIndex + 3));
              
              // Update content immediately
              setContent(newContent);
              setContentVersion(prev => prev + 1);
              handleContentChange(newContent);
              
              // Force a state update to ensure React re-renders
              setTimeout(() => {
                setContent(prevContent => {
                  if (prevContent !== newContent) {
                    console.log('🔄 DEBUG: Force updating content to match newContent');
                    console.log('🔄 DEBUG: Previous content length:', prevContent.length);
                    console.log('🔄 DEBUG: New content length:', newContent.length);
                    setContentVersion(prev => prev + 1);
                    return newContent;
                  }
                  return prevContent;
                });
              }, 0);
              
              // Additional force update after a longer delay
              setTimeout(() => {
                console.log('🔄 DEBUG: Second force update check');
                setContent(currentContent => {
                  if (currentContent !== newContent) {
                    console.log('🔄 DEBUG: Second force update applied');
                    setContentVersion(prev => prev + 1);
                    return newContent;
                  }
                  return currentContent;
                });
              }, 100);
              
              // Log the content state after update
              console.log(`✅ DEBUG: Content updated successfully, new length: ${newContent.length}`);
              
              // Update sessionStorage with the new content
              const projectData = sessionStorage.getItem('currentProject');
              if (projectData) {
                const project = JSON.parse(projectData);
                project.resume_tex = newContent;
                sessionStorage.setItem('currentProject', JSON.stringify(project));
                console.log(`💾 DEBUG: Updated sessionStorage with new content`);
                console.log(`💾 DEBUG: SessionStorage content length: ${project.resume_tex.length}`);
                
                // Dispatch project updated event
                window.dispatchEvent(new CustomEvent('projectUpdated', { 
                  detail: { project } 
                }));
              }
              
              // Mark only the current change as applied (not both)
              setAppliedChanges(prev => new Set(prev).add(changeId));
              setRejectedChanges(prev => {
                const newSet = new Set(prev);
                newSet.delete(changeId);
                return newSet;
              });
              
              console.log(`🎯 DEBUG: Change ${changeId} applied and marked as applied`);
              
              // Dispatch change acceptance event for parent components (only for the current change)
              const event = new CustomEvent('changeAccepted', {
                detail: { changeId, accepted }
              });
              window.dispatchEvent(event);
              
              return;
            }
          }
        }
        
        // If this is an addition and there's a removal on the same line, skip it (already handled by smart replacement)
        // But only if the removal change has been applied
        if (change.type === 'addition' && otherChangesOnSameLine.some(c => c.type === 'removal' && appliedChanges.has(c.id))) {
          console.log(`⏭️ DEBUG: Addition change ${changeId} is part of a smart replacement pattern, skipping`);
          return;
        }
        
        // Apply the change to the content
        const lines = content.split('\n');
        let newContent = content;
        
        // Get the correct line number (handle both frontend and backend field names)
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
            console.log(`✅ DEBUG: New content around replacement:`, newContent.split('\n').slice(Math.max(0, lineIndex - 2), lineIndex + 3));
            
            // Verify the replacement actually happened
            if (lines[lineIndex] === change.content) {
              console.log(`✅ DEBUG: Replacement verified - content matches expected`);
            } else {
              console.log(`❌ DEBUG: Replacement failed - content does not match expected`);
            }
          } else {
            console.log(`❌ DEBUG: Replacement failed - lineIndex ${lineIndex} out of bounds (0-${lines.length - 1})`);
          }
        }
        
        // Update content immediately
        console.log(`📝 DEBUG: Content before change: ${content.substring(0, 100)}...`);
        console.log(`📝 DEBUG: Content after change: ${newContent.substring(0, 100)}...`);
        console.log(`📝 DEBUG: Content length before: ${content.length}, after: ${newContent.length}`);
        console.log(`📝 DEBUG: New content lines:`, newContent.split('\n').slice(Math.max(0, lineIndex - 2), lineIndex + 3));
        
        // Update content immediately
        setContent(newContent);
        setContentVersion(prev => prev + 1);
        handleContentChange(newContent);
        
        // Force a state update to ensure React re-renders
        setTimeout(() => {
          setContent(prevContent => {
            if (prevContent !== newContent) {
              console.log('🔄 DEBUG: Force updating content to match newContent');
              console.log('🔄 DEBUG: Previous content length:', prevContent.length);
              console.log('🔄 DEBUG: New content length:', newContent.length);
              setContentVersion(prev => prev + 1);
              return newContent;
            }
            return prevContent;
          });
        }, 0);
        
        // Additional force update after a longer delay
        setTimeout(() => {
          console.log('🔄 DEBUG: Second force update check');
          setContent(currentContent => {
            if (currentContent !== newContent) {
              console.log('🔄 DEBUG: Second force update applied');
              setContentVersion(prev => prev + 1);
              return newContent;
            }
            return currentContent;
          });
        }, 100);
        
        // Log the content state after update
        console.log(`✅ DEBUG: Content updated successfully, new length: ${newContent.length}`);
        
        // Update sessionStorage with the new content
        const projectData = sessionStorage.getItem('currentProject');
        if (projectData) {
          const project = JSON.parse(projectData);
          project.resume_tex = newContent;
          sessionStorage.setItem('currentProject', JSON.stringify(project));
          console.log(`💾 DEBUG: Updated sessionStorage with new content`);
          console.log(`💾 DEBUG: SessionStorage content length: ${project.resume_tex.length}`);
          
          // Dispatch project updated event
          window.dispatchEvent(new CustomEvent('projectUpdated', { 
            detail: { project } 
          }));
        }
        
        // Mark as applied immediately
        setAppliedChanges(prev => new Set(prev).add(changeId));
        setRejectedChanges(prev => {
          const newSet = new Set(prev);
          newSet.delete(changeId);
          return newSet;
        });
        
        console.log(`🎯 DEBUG: Change ${changeId} applied and marked as applied`);
      }
    } else {
      // Add to rejected changes
      console.log(`❌ DEBUG: Rejecting change ${changeId}`);
      setRejectedChanges(prev => new Set(prev).add(changeId));
      setAppliedChanges(prev => {
        const newSet = new Set(prev);
        newSet.delete(changeId);
        return newSet;
      });
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
    console.log(`📊 DEBUG: Initial content length: ${lines.length}`);
    
    for (const change of sortedChanges) {
      console.log(`🔄 DEBUG: Applying change ${change.id} of type ${change.type}`);
      console.log(`🔄 DEBUG: Change content: "${change.content}"`);
      
      // Get the correct line number (handle both frontend and backend field names)
      const lineNumber = change.startLine || change.start_line || 1;
      const lineIndex = lineNumber - 1;
      
      console.log(`🔍 DEBUG: Line number: ${lineNumber}, Line index: ${lineIndex}, Content length: ${lines.length}`);
      console.log(`🔍 DEBUG: Change type: ${change.type}`);
      console.log(`🔍 DEBUG: Change content: "${change.content}"`);
      console.log(`🔍 DEBUG: Current lines around target:`, lines.slice(Math.max(0, lineIndex - 2), lineIndex + 3));
      console.log(`🔍 DEBUG: Target line content: "${lines[lineIndex] || 'UNDEFINED'}"`);
      
      if (change.type === 'removal') {
        if (lineIndex >= 0 && lineIndex < lines.length) {
          lines.splice(lineIndex, 1);
          console.log(`✅ DEBUG: Removed line ${lineNumber}`);
          console.log(`✅ DEBUG: Lines after removal:`, lines.slice(Math.max(0, lineIndex - 2), lineIndex + 3));
        }
      } else if (change.type === 'addition') {
        if (lineIndex >= 0 && lineIndex <= lines.length) {
          lines.splice(lineIndex, 0, change.content);
          console.log(`✅ DEBUG: Added line at ${lineNumber}`);
          console.log(`✅ DEBUG: Lines after addition:`, lines.slice(Math.max(0, lineIndex - 2), lineIndex + 3));
        }
      } else if (change.type === 'replacement') {
        if (lineIndex >= 0 && lineIndex < lines.length) {
          console.log(`🔄 DEBUG: Before replacement - line ${lineIndex}: "${lines[lineIndex]}"`);
          const originalLine = lines[lineIndex];
          lines[lineIndex] = change.content;
          console.log(`🔄 DEBUG: After replacement - line ${lineIndex}: "${lines[lineIndex]}"`);
          console.log(`🔄 DEBUG: Original line was: "${originalLine}"`);
          console.log(`🔄 DEBUG: New line is: "${lines[lineIndex]}"`);
          console.log(`✅ DEBUG: Replaced line ${lineNumber}`);
          console.log(`✅ DEBUG: Lines after replacement:`, lines.slice(Math.max(0, lineIndex - 2), lineIndex + 3));
          
          // Verify the replacement actually happened
          if (lines[lineIndex] === change.content) {
            console.log(`✅ DEBUG: Replacement verified in acceptAll - content matches expected`);
          } else {
            console.log(`❌ DEBUG: Replacement failed in acceptAll - content does not match expected`);
          }
        } else {
          console.log(`❌ DEBUG: Replacement failed in acceptAll - lineIndex ${lineIndex} out of bounds (0-${lines.length - 1})`);
        }
      }
    }
    
    newContent = lines.join('\n');
    
    console.log(`📝 DEBUG: Content before all changes: ${content.substring(0, 100)}...`);
    console.log(`📝 DEBUG: Content after all changes: ${newContent.substring(0, 100)}...`);
    console.log(`📝 DEBUG: Content length before: ${content.length}, after: ${newContent.length}`);
    
    // Update content
    setContent(newContent);
    setContentVersion(prev => prev + 1);
    handleContentChange(newContent);
    
    // Force a state update to ensure React re-renders
    setTimeout(() => {
      setContent(prevContent => {
        if (prevContent !== newContent) {
          console.log('🔄 DEBUG: Force updating content in acceptAll to match newContent');
          setContentVersion(prev => prev + 1);
          return newContent;
        }
        return prevContent;
      });
    }, 0);
    
    // Update sessionStorage with the new content
    const projectData = sessionStorage.getItem('currentProject');
    if (projectData) {
      const project = JSON.parse(projectData);
      project.resume_tex = newContent;
      sessionStorage.setItem('currentProject', JSON.stringify(project));
      console.log(`💾 DEBUG: Updated sessionStorage with all changes`);
      
      // Dispatch project updated event
      window.dispatchEvent(new CustomEvent('projectUpdated', { 
        detail: { project } 
      }));
    }
    
    // Mark all changes as applied
    const allChangeIds = activeChanges.map(c => c.id);
    setAppliedChanges(prev => {
      const newSet = new Set(prev);
      allChangeIds.forEach(id => newSet.add(id));
      return newSet;
    });
    
    console.log(`🎉 DEBUG: All changes applied successfully`);
  };

  // Expose handleAcceptAll to parent component
  useEffect(() => {
    (window as any).latexEditorAcceptAll = handleAcceptAll;
    return () => {
      delete (window as any).latexEditorAcceptAll;
    };
  }, [handleAcceptAll]);

  const renderContentWithChanges = () => {
    if (!content) {
      return (
        <div className="flex items-center justify-center h-64 text-slate-500">
          <div className="text-sm">Upload a resume to see the LaTeX source code</div>
        </div>
      );
    }

    // Filter out rejected and applied changes to get active changes
    const activeChanges = changes.filter(change => 
      !rejectedChanges.has(change.id) && !appliedChanges.has(change.id)
    );
    
    console.log(`🔍 DEBUG: Rendering ${activeChanges.length} active changes`);
    console.log(`🔍 DEBUG: Applied changes:`, Array.from(appliedChanges));
    console.log(`🔍 DEBUG: Rejected changes:`, Array.from(rejectedChanges));
    
    if (activeChanges.length === 0) {
      // No active changes, show regular content
      const lines = content.split('\n');
      return (
        <div className="space-y-0">
          {lines.map((line, index) => (
            <div key={`line-${index + 1}`} className="flex items-start py-1 px-4 hover:bg-slate-800/50">
              <div className="flex-shrink-0 w-8 text-xs text-slate-500 mr-3 mt-0.5">
                {index + 1}
              </div>
              <div className="flex-1 font-mono text-sm text-slate-300">
                {line}
              </div>
            </div>
          ))}
        </div>
      );
    }
    
    // Group changes by their target line for inline display
    const changesByLine = new Map<number, any[]>();
    
    activeChanges.forEach((change) => {
      const targetLine = change.startLine || change.start_line || 1;
      if (!changesByLine.has(targetLine)) {
        changesByLine.set(targetLine, []);
      }
      changesByLine.get(targetLine)!.push(change);
    });

    console.log(`📊 DEBUG: Changes by line:`, changesByLine);

    // Render content with inline changes like Cursor
    const lines = content.split('\n');
    const result: JSX.Element[] = [];

    for (let i = 0; i < lines.length; i++) {
      const lineNumber = i + 1;
      const lineChanges = changesByLine.get(lineNumber) || [];
      
      if (lineChanges.length > 0) {
        console.log(`🔍 DEBUG: Line ${lineNumber} has ${lineChanges.length} changes:`, lineChanges);
        // Group changes by type for this line
        const removals = lineChanges.filter(c => c.type === 'removal');
        const additions = lineChanges.filter(c => c.type === 'addition');
        
        // Check if this is a replacement (both removal and addition on same line)
        const isReplacement = removals.length > 0 && additions.length > 0;
        
        if (isReplacement) {
          // Check if any changes in this replacement are applied
          const hasAppliedChanges = lineChanges.some(change => appliedChanges.has(change.id));
          
          // Show replacement inline - old line with strikethrough, new line below
          result.push(
            <div key={`replacement-${lineNumber}`} className="relative group mb-2">
              {/* Original line with strikethrough */}
              <div className={`flex items-start py-1 px-4 border-l-4 ${
                hasAppliedChanges 
                  ? 'bg-green-900/20 border-green-500' 
                  : 'bg-red-900/10 border-red-500'
              }`}>
                <span className="text-slate-500 text-xs mr-4 w-8 inline-block">{lineNumber}</span>
                <span className={`whitespace-pre font-mono text-sm line-through ${
                  hasAppliedChanges ? 'text-green-300' : 'text-red-300'
                }`}>{lines[i]}</span>
                {!hasAppliedChanges && (
                  <div className="absolute right-2 top-1 flex gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0 hover:bg-green-500 hover:text-white bg-slate-700"
                      onClick={() => {
                        // Accept all changes in this replacement
                        lineChanges.forEach(change => handleApplyChange(change.id, true));
                      }}
                    >
                      <Check className="w-3 h-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0 hover:bg-red-500 hover:text-white bg-slate-700"
                      onClick={() => {
                        // Reject all changes in this replacement
                        lineChanges.forEach(change => handleApplyChange(change.id, false));
                      }}
                    >
                      <X className="w-3 h-3" />
                    </Button>
                  </div>
                )}
                {hasAppliedChanges && (
                  <div className="absolute right-2 top-1">
                    <div className="h-6 w-6 bg-green-500 text-white rounded flex items-center justify-center">
                      <Check className="w-3 h-3" />
                    </div>
                  </div>
                )}
              </div>
              
              {/* New line */}
              {additions.map((change, idx) => {
                const isApplied = appliedChanges.has(change.id);
                return (
                  <div key={`addition-${change.id}`} className={`flex items-start py-1 px-4 border-l-4 ${
                    isApplied 
                      ? 'bg-green-900/20 border-green-500' 
                      : 'bg-green-900/10 border-green-500'
                  }`}>
                    <span className="text-slate-500 text-xs mr-4 w-8 inline-block">+</span>
                    <span className={`whitespace-pre font-mono text-sm ${
                      isApplied ? 'text-green-200' : 'text-green-300'
                    }`}>{change.content}</span>
                    {isApplied && (
                      <div className="absolute right-2 top-1">
                        <div className="h-6 w-6 bg-green-500 text-white rounded flex items-center justify-center">
                          <Check className="w-3 h-3" />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          );
        } else if (removals.length > 0) {
          // Pure deletion - show with strikethrough
          const isApplied = appliedChanges.has(removals[0].id);
          result.push(
            <div key={`deletion-${lineNumber}`} className="relative group mb-1">
              <div className={`flex items-start py-1 px-4 border-l-4 ${
                isApplied 
                  ? 'bg-green-900/20 border-green-500' 
                  : 'bg-red-900/10 border-red-500'
              }`}>
                <span className="text-slate-500 text-xs mr-4 w-8 inline-block">{lineNumber}</span>
                <span className={`whitespace-pre font-mono text-sm line-through ${
                  isApplied ? 'text-green-300' : 'text-red-300'
                }`}>{lines[i]}</span>
                {!isApplied && (
                  <div className="absolute right-2 top-1 flex gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0 hover:bg-green-500 hover:text-white bg-slate-700"
                      onClick={() => handleApplyChange(removals[0].id, true)}
                    >
                      <Check className="w-3 h-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0 hover:bg-red-500 hover:text-white bg-slate-700"
                      onClick={() => handleApplyChange(removals[0].id, false)}
                    >
                      <X className="w-3 h-3" />
                    </Button>
                  </div>
                )}
                {isApplied && (
                  <div className="absolute right-2 top-1">
                    <div className="h-6 w-6 bg-green-500 text-white rounded flex items-center justify-center">
                      <Check className="w-3 h-3" />
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        } else if (additions.length > 0) {
          // Pure addition - show new line
          additions.forEach((change, idx) => {
            const isApplied = appliedChanges.has(change.id);
            result.push(
              <div key={`addition-${change.id}`} className="relative group mb-1">
                <div className={`flex items-start py-1 px-4 border-l-4 ${
                  isApplied 
                    ? 'bg-green-900/20 border-green-500' 
                    : 'bg-green-900/10 border-green-500'
                }`}>
                  <span className="text-slate-500 text-xs mr-4 w-8 inline-block">+</span>
                  <span className={`whitespace-pre font-mono text-sm ${
                    isApplied ? 'text-green-200' : 'text-green-300'
                  }`}>{change.content}</span>
                  {!isApplied && (
                    <div className="absolute right-2 top-1 flex gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 w-6 p-0 hover:bg-green-500 hover:text-white bg-slate-700"
                        onClick={() => handleApplyChange(change.id, true)}
                      >
                        <Check className="w-3 h-3" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 w-6 p-0 hover:bg-red-500 hover:text-white bg-slate-700"
                        onClick={() => handleApplyChange(change.id, false)}
                      >
                        <X className="w-3 h-3" />
                      </Button>
                    </div>
                  )}
                  {isApplied && (
                    <div className="absolute right-2 top-1">
                      <div className="h-6 w-6 bg-green-500 text-white rounded flex items-center justify-center">
                        <Check className="w-3 h-3" />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          });
        }
      } else {
        // No changes for this line - show normal line
        result.push(
          <div key={`line-${i}`} className="flex items-start py-1 px-4 hover:bg-slate-800/50">
            <span className="text-slate-500 text-xs mr-4 w-8 inline-block">{lineNumber}</span>
            <span className="whitespace-pre font-mono text-sm text-slate-300">{lines[i]}</span>
          </div>
        );
      }
    }

    return result;
  };

  return (
    <div className="h-full flex flex-col bg-slate-900 min-h-96">
      {/* Header */}
      <div className="flex-shrink-0 px-4 py-3 border-b border-slate-700 bg-slate-800">
        <h3 className="text-sm font-medium text-slate-200">LaTeX Source</h3>
      </div>
      
      {/* Content Area - Show changes directly instead of overlay */}
      <div className="flex-1 min-h-0 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-600 scrollbar-track-slate-800">
        {(() => {
          // Filter out rejected and applied changes to get active changes
          const activeChanges = changes.filter(change => 
            !rejectedChanges.has(change.id) && !appliedChanges.has(change.id)
          );
          
          console.log(`🔍 DEBUG: Active changes: ${activeChanges.length}, Total changes: ${changes.length}`);
          console.log(`🔍 DEBUG: Applied changes: ${Array.from(appliedChanges).length}, Rejected changes: ${Array.from(rejectedChanges).length}`);
          
          return activeChanges.length > 0 ? (
            // Show changes view only if there are active changes
            <div className="p-4">
              {renderContentWithChanges()}
            </div>
          ) : (
            // Show editable textarea when no active changes
            <div>
              <div className="text-xs text-slate-500 p-2 bg-slate-800">
                Content length: {content.length} characters
              </div>
              <textarea
                key={`content-${contentVersion}`} // Force re-render when content changes
                value={content}
                onChange={(e) => handleContentChange(e.target.value)}
                className="w-full h-full min-h-96 p-4 bg-slate-900 text-slate-300 font-mono text-sm resize-none border-none outline-none"
                placeholder="LaTeX content will appear here..."
              />
            </div>
          );
        })()}
      </div>
    </div>
  );
}