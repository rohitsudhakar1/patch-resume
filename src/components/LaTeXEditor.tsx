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
  const [processedChanges, setProcessedChanges] = useState<Set<string>>(new Set());
  const [lastChangeIds, setLastChangeIds] = useState<string>('');

  console.log('🔍 DEBUG: LaTeXEditor received changes:', changes?.length || 0);

  // Clean content immediately on mount if it exists
  useEffect(() => {
    if (content) {
      const cleanedContent = cleanDuplicateContent(content);
      if (cleanedContent !== content) {
        console.log('🧹 DEBUG: Cleaning existing content on mount');
        setContent(cleanedContent);
        handleContentChange(cleanedContent);
      }
    }
  }, []); // Run only once on mount

  // Load content from sessionStorage
  useEffect(() => {
    const projectData = sessionStorage.getItem('currentProject');
    if (projectData) {
      const project = JSON.parse(projectData);
      if (project.resume_tex) {
        // Clean the content when loading
        const cleanedContent = cleanDuplicateContent(project.resume_tex);
        setContent(cleanedContent);
        console.log('📄 DEBUG: LaTeXEditor loaded and cleaned content');
        
        // Update the project with cleaned content
        project.resume_tex = cleanedContent;
        sessionStorage.setItem('currentProject', JSON.stringify(project));
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
          // Clean the content when updating
          const cleanedContent = cleanDuplicateContent(project.resume_tex);
          setContent(cleanedContent);
          console.log('🔄 DEBUG: LaTeXEditor updated and cleaned content');
          
          // Update the project with cleaned content
          project.resume_tex = cleanedContent;
          sessionStorage.setItem('currentProject', JSON.stringify(project));
        }
      }
    };

    window.addEventListener('projectUpdated', handleProjectUpdate);
    return () => window.removeEventListener('projectUpdated', handleProjectUpdate);
  }, []);

  // Clear processed changes when new changes come in
  useEffect(() => {
    if (changes && changes.length > 0) {
      const currentChangeIds = changes.map(c => c.id).join(',');
      
      // Only clear processed changes if these are truly new changes
      if (currentChangeIds !== lastChangeIds) {
        console.log('🔄 DEBUG: New changes received, clearing processed changes');
        console.log('🔄 DEBUG: Change IDs:', changes.map(c => c.id));
        console.log('🔄 DEBUG: Current processed changes before clearing:', Array.from(processedChanges));
        
        // Force clear processed changes and ensure they stay clear
        setProcessedChanges(new Set());
        setLastChangeIds(currentChangeIds);
        
        console.log('✅ DEBUG: Processed changes cleared for new changes');
      } else {
        console.log('🔄 DEBUG: Same changes received, not clearing processed changes');
      }
    }
  }, [changes?.map(c => c.id).join(',')]);

  const cleanDuplicateContent = (content: string) => {
    const lines = content.split('\n');
    const cleanedLines: string[] = [];
    let hasUniversity = false;
    let hasArdentCapital = false;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmedLine = line.trim();
      
      // Handle university entries - keep only one
      if (trimmedLine.includes('\\textbf{') && trimmedLine.includes('Expected May 2026')) {
        if (!hasUniversity) {
          hasUniversity = true;
          cleanedLines.push(line);
        }
        // Skip duplicate university entries
        continue;
      }
      
      // Handle duplicate Ardent Capital entries
      if (trimmedLine.includes('Ardent Capital') || trimmedLine.includes('ardent')) {
        if (!hasArdentCapital) {
          hasArdentCapital = true;
          cleanedLines.push(line);
        }
        // Skip duplicate Ardent entries
        continue;
      }
      
      // Handle malformed Personal Project entries
      if (trimmedLine.includes('\\\\textbf{Personal Project}') || 
          trimmedLine.includes('\\n\\\\textbf{Personal Project}')) {
        // Skip malformed entries
        continue;
      }
      
      // Handle malformed itemize blocks
      if (trimmedLine.includes('\\\\begin{itemize}') || 
          trimmedLine.includes('\\\\item') ||
          trimmedLine.includes('\\\\end{itemize}')) {
        // Skip malformed LaTeX
        continue;
      }
      
      // Handle orphaned \item entries (not inside itemize blocks)
      if (trimmedLine.includes('\\item') && !trimmedLine.includes('\\begin{itemize}')) {
        // Check if previous line has \begin{itemize}
        const prevLine = i > 0 ? lines[i-1].trim() : '';
        if (!prevLine.includes('\\begin{itemize}')) {
          // This is an orphaned \item, skip it
          continue;
        }
      }
      
      // Handle template placeholders
      if (trimmedLine.includes('New Company Name') || 
          trimmedLine.includes('Internship Role') ||
          trimmedLine.includes('Brief description of your responsibilities')) {
        // Skip template content
        continue;
      }
      
      cleanedLines.push(line);
    }
    
    let cleanedContent = cleanedLines.join('\n');
    
    // Fix document structure
    if (!cleanedContent.includes('\\begin{document}')) {
      const parts = cleanedContent.split('\\usepackage{hyperref}');
      if (parts.length > 1) {
        cleanedContent = parts[0] + '\\usepackage{hyperref}\n\n\\begin{document}\n\n' + parts[1];
      }
    }
    
    return cleanedContent;
  };

  const handleContentChange = async (newContent: string) => {
    console.log('📝 DEBUG: Content changed');
    
    // Clean up duplicate content
    const cleanedContent = cleanDuplicateContent(newContent);
    setContent(cleanedContent);
    
    // Update sessionStorage
    const projectData = sessionStorage.getItem('currentProject');
    if (projectData) {
      try {
        const project = JSON.parse(projectData);
        project.resume_tex = cleanedContent;
        sessionStorage.setItem('currentProject', JSON.stringify(project));
        
        // Create project in backend
        const response = await fetch('http://localhost:8000/project/recreate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(project),
        });
        
        if (response.ok) {
          console.log('✅ DEBUG: Project updated in backend');
        }
      } catch (error) {
        console.log('❌ DEBUG: Error updating project:', error);
      }
    }
    
    onContentChange?.(cleanedContent);
  };

  const handleApplyChange = (changeId: string, accepted: boolean) => {
    console.log(`🔧 DEBUG: Applying change ${changeId}: ${accepted ? 'accepted' : 'rejected'}`);
    
    const change = changes?.find(c => c.id === changeId);
    if (!change) {
      console.log(`❌ DEBUG: Change ${changeId} not found`);
      return;
    }
    
    // Check if change is already processed
    if (processedChanges.has(changeId)) {
      console.log(`⚠️ DEBUG: Change ${changeId} already processed, ignoring`);
      return;
    }
    
    console.log(`🔍 DEBUG: Found change:`, {
      id: change.id,
      type: change.type,
      startLine: change.startLine || change.start_line,
      content: change.content
    });
        
    const lineNumber = change.startLine || change.start_line || 1;
    const otherChangesOnSameLine = changes?.filter(c => 
      c.id !== changeId && 
      (c.startLine || c.start_line) === lineNumber &&
      !processedChanges.has(c.id)
    ) || [];
    
    console.log(`🔍 DEBUG: Line ${lineNumber} analysis:`);
    console.log(`  Current change line: ${lineNumber}`);
    console.log(`  Other changes on same line: ${otherChangesOnSameLine.length}`);
    console.log(`  All changes:`, changes?.map(c => ({
      id: c.id,
      type: c.type,
      line: c.startLine || c.start_line,
      content: c.content.substring(0, 50) + '...'
    })));
    otherChangesOnSameLine.forEach(c => {
      console.log(`    - ${c.id}: ${c.type} - Line ${c.startLine || c.start_line} - "${c.content}"`);
    });
        
    // Check if this is part of a smart replacement (removal + addition on same line)
    const isSmartReplacement = change.type === 'removal' && 
      otherChangesOnSameLine.some(c => c.type === 'addition');
    
    // Also check if this is an addition with a removal on the same line
    const isSmartReplacementFromAddition = change.type === 'addition' && 
      otherChangesOnSameLine.some(c => c.type === 'removal');
    
    const isAnySmartReplacement = isSmartReplacement || isSmartReplacementFromAddition;
    
    console.log(`🔍 DEBUG: Is smart replacement (removal): ${isSmartReplacement}`);
    console.log(`🔍 DEBUG: Is smart replacement (addition): ${isSmartReplacementFromAddition}`);
    console.log(`🔍 DEBUG: Is any smart replacement: ${isAnySmartReplacement}`);
    
    // Additional debugging for line matching
    if (otherChangesOnSameLine.length > 0) {
      console.log(`🔍 DEBUG: Found changes on same line, checking content matching:`);
      const lines = content.split('\n');
      otherChangesOnSameLine.forEach(otherChange => {
        console.log(`  - ${otherChange.id}: "${otherChange.content}" vs current line: "${lines[lineNumber - 1] || 'undefined'}"`);
      });
    }
        
    if (accepted && isAnySmartReplacement) {
      // Handle smart replacement - apply both removal and addition as one replacement
      const additionChanges = otherChangesOnSameLine.filter(c => c.type === 'addition');
      const removalChanges = otherChangesOnSameLine.filter(c => c.type === 'removal');
      
      // Determine which change to use for the replacement
      let replacementChange;
      if (change.type === 'addition') {
        replacementChange = change;
      } else if (additionChanges.length > 0) {
        replacementChange = additionChanges[0];
      }
      
      if (replacementChange) {
        const lines = content.split('\n');
        const lineIndex = lineNumber - 1;
        
        console.log(`🔍 DEBUG: Smart replacement - Line ${lineNumber}:`);
        console.log(`  Original: "${lines[lineIndex]}"`);
        console.log(`  New: "${replacementChange.content.replace(/\\n/g, '\n')}"`);
        
        if (lineIndex >= 0 && lineIndex < lines.length) {
          // Replace the entire line (removal + addition = replacement)
          lines[lineIndex] = replacementChange.content.replace(/\\n/g, '\n');
          console.log(`✅ DEBUG: Smart replacement completed on line ${lineNumber}`);
        }

        // Update content
        const newContent = lines.join('\n');
        setContent(newContent);
        handleContentChange(newContent);
        
        // Mark all changes on this line as processed
        const allChangesOnLine = changes?.filter(c => 
          (c.startLine || c.start_line) === lineNumber
        ) || [];
        
        setProcessedChanges(prev => {
          const newSet = new Set(prev);
          allChangesOnLine.forEach(c => newSet.add(c.id));
          return newSet;
        });
        
        // Only dispatch one event for the smart replacement
        window.dispatchEvent(new CustomEvent('changeAccepted', { detail: { changeId, accepted } }));
        
        return;
      }
    }

    if (accepted) {
      // Apply individual change
      const lines = content.split('\n');
      const lineIndex = lineNumber - 1;
      
      console.log(`🔍 DEBUG: Line ${lineNumber}, Type: ${change.type}`);
      console.log(`🔍 DEBUG: Current line content: "${lines[lineIndex]}"`);
      
      if (change.type === 'removal') {
        // Remove the line
        if (lineIndex >= 0 && lineIndex < lines.length) {
          console.log(`🔍 DEBUG: Removing line ${lineNumber}: "${lines[lineIndex]}"`);
          lines.splice(lineIndex, 1);
          console.log(`✅ DEBUG: Removed line ${lineNumber}`);
        }
      } else if (change.type === 'addition') {
        // For additions, check if this is part of a replacement by looking for removal on same line
        const hasRemovalOnSameLine = changes?.some(c => 
          c.id !== changeId && 
          (c.startLine || c.start_line) === lineNumber && 
          c.type === 'removal' &&
          !processedChanges.has(c.id)
        );
        
        if (hasRemovalOnSameLine) {
          // This is part of a replacement, replace the line instead of adding
          if (lineIndex >= 0 && lineIndex < lines.length) {
            console.log(`🔍 DEBUG: Replacing line ${lineNumber} (addition with removal on same line)`);
            console.log(`🔍 DEBUG: Old: "${lines[lineIndex]}"`);
            console.log(`🔍 DEBUG: New: "${change.content.replace(/\\n/g, '\n')}"`);
            lines[lineIndex] = change.content.replace(/\\n/g, '\n');
            console.log(`✅ DEBUG: Replaced line ${lineNumber}`);
          }
        } else {
          // Regular addition
          if (lineIndex >= 0 && lineIndex <= lines.length) {
            lines.splice(lineIndex, 0, change.content.replace(/\\n/g, '\n'));
            console.log(`✅ DEBUG: Added line at ${lineNumber}`);
          }
        }
      } else if (change.type === 'replacement') {
        // Replace the line
        if (lineIndex >= 0 && lineIndex < lines.length) {
          lines[lineIndex] = change.content.replace(/\\n/g, '\n');
          console.log(`✅ DEBUG: Replaced line ${lineNumber}`);
        }
      }
    
      // Update content
      const newContent = lines.join('\n');
      setContent(newContent);
      handleContentChange(newContent);
    }

    // Mark change as processed
    setProcessedChanges(prev => new Set(prev).add(changeId));
    
    // Dispatch event to parent
    const event = new CustomEvent('changeAccepted', {
      detail: { changeId, accepted }
    });
    window.dispatchEvent(event);
  };

  // Get active changes (not processed yet)
  const activeChanges = (changes || []).filter(change => {
    const isProcessed = processedChanges.has(change.id);
    console.log(`🔍 DEBUG: Change ${change.id} processed: ${isProcessed}`);
    return !isProcessed;
  });

  // Group changes by line number
  const changesByLine = new Map<number, Change[]>();
  activeChanges.forEach(change => {
    const lineNumber = change.startLine || change.start_line || 1;
    if (!changesByLine.has(lineNumber)) {
      changesByLine.set(lineNumber, []);
    }
    changesByLine.get(lineNumber)!.push(change);
  });
  
  console.log(`🔍 DEBUG: Changes by line:`, Array.from(changesByLine.entries()).map(([line, changes]) => ({
    line,
    changes: changes.map(c => ({ id: c.id, type: c.type, content: c.content.substring(0, 50) + '...' }))
  })));

  console.log(`🔍 DEBUG: Active changes: ${activeChanges.length}, Total: ${changes?.length || 0}, Processed: ${processedChanges.size}`);
  console.log(`🔍 DEBUG: Processed change IDs:`, Array.from(processedChanges));
  console.log(`🔍 DEBUG: All change IDs:`, changes?.map(c => c.id) || []);

      return (
    <div className="flex h-full bg-slate-900">
      {/* Left Panel - LaTeX Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-slate-200">LaTeX Editor</h2>
          <div className="text-sm text-slate-400">
            {activeChanges.length} changes pending
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          <div className="max-w-none">
            <textarea
              value={content}
              onChange={(e) => handleContentChange(e.target.value)}
              className="w-full h-full bg-slate-800 text-slate-300 font-mono text-sm p-4 border border-slate-600 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="LaTeX content will appear here..."
              style={{ minHeight: '500px' }}
            />
              </div>
              </div>
            </div>

      {/* Right Panel - Changes */}
      <div className="w-80 border-l border-slate-700 flex flex-col">
        {/* Changes Header */}
        <div className="p-4 border-b border-slate-700">
          <h3 className="text-lg font-semibold text-slate-200">Changes</h3>
          <div className="text-sm text-slate-400">
            {activeChanges.length} pending
          </div>
        </div>

        {/* Changes List */}
        <div className="flex-1 overflow-auto p-4">
          {/* Debug info */}
          <div className="mb-4 p-2 bg-slate-800 rounded text-xs text-slate-400">
            <div>Total changes: {changes?.length || 0}</div>
            <div>Active changes: {activeChanges.length}</div>
            <div>Processed: {processedChanges.size}</div>
          </div>
          
          {activeChanges.length > 0 ? (
            <div className="space-y-4">
              {console.log(`🔍 DEBUG: Rendering ${Array.from(changesByLine.entries()).length} line groups`)}
              {Array.from(changesByLine.entries()).map(([lineNumber, lineChanges]) => (
                <div key={lineNumber} className="border border-slate-600 rounded-lg p-4">
                  <div className="text-sm font-semibold text-slate-300 mb-2">
                    Line {lineNumber}
                  </div>
                  
                  {/* Check if this is a smart replacement */}
                  {lineChanges.some(c => c.type === 'removal') && 
                   lineChanges.some(c => c.type === 'addition') && 
                   !lineChanges.some(c => processedChanges.has(c.id)) ? (
                    <div className="space-y-2">
                      <div className="bg-red-900/20 border border-red-500 rounded p-2">
                        <div className="text-red-300 text-sm font-mono line-through">
                          {lineChanges.find(c => c.type === 'removal')?.content.replace(/\\n/g, '\n')}
                    </div>
                        <div className="text-green-300 text-sm font-mono mt-1 whitespace-pre-wrap">
                          {lineChanges.find(c => c.type === 'addition')?.content.replace(/\\n/g, '\n')}
                        </div>
                      </div>
                      <div className="flex space-x-2">
                    <Button
                      size="sm"
                          variant="outline"
                          className="text-green-600 border-green-600 hover:bg-green-600 hover:text-white"
                          onClick={() => handleApplyChange(lineChanges.find(c => c.type === 'removal')!.id, true)}
                        >
                          <Check className="w-4 h-4 mr-1" />
                          Accept
                    </Button>
                    <Button
                      size="sm"
                          variant="outline"
                          className="text-red-600 border-red-600 hover:bg-red-600 hover:text-white"
                          onClick={() => handleApplyChange(lineChanges.find(c => c.type === 'removal')!.id, false)}
                        >
                          <X className="w-4 h-4 mr-1" />
                          Reject
                    </Button>
                  </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {lineChanges.filter(change => !processedChanges.has(change.id)).map((change) => (
                        <div key={change.id} className={`p-2 rounded border ${
                          change.type === 'addition' ? 'bg-green-900/20 border-green-500' :
                          change.type === 'removal' ? 'bg-red-900/20 border-red-500' :
                          'bg-blue-900/20 border-blue-500'
                        }`}>
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <span className={`px-2 py-1 text-xs font-semibold rounded ${
                                change.type === 'addition' ? 'bg-green-900 text-green-200' :
                                change.type === 'removal' ? 'bg-red-900 text-red-200' :
                                'bg-blue-900 text-blue-200'
                              }`}>
                                {change.type.toUpperCase()}
                              </span>
                              <span className="text-slate-300 font-mono text-sm whitespace-pre-wrap">{change.content.replace(/\\n/g, '\n')}</span>
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
                      </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center text-slate-400 py-8">
              <div className="text-lg font-semibold mb-2">No Active Changes</div>
              <div className="text-sm">All changes have been processed</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}