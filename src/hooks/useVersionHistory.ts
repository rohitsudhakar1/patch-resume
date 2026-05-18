import { useState, useCallback, useEffect } from 'react';

export interface Version {
  id: string;
  content: string;
  timestamp: Date;
  description: string;
}

interface UseVersionHistoryReturn {
  currentVersion: string;
  versions: Version[];
  canUndo: boolean;
  canRedo: boolean;
  saveVersion: (content: string, description?: string) => void;
  undo: () => string | null;
  redo: () => string | null;
  goToVersion: (versionId: string) => string | null;
  clearHistory: () => void;
}

const MAX_VERSIONS = 50; // Keep last 50 versions

export const useVersionHistory = (initialContent: string = ''): UseVersionHistoryReturn => {
  const [versions, setVersions] = useState<Version[]>([]);
  const [currentIndex, setCurrentIndex] = useState(-1);

  // Initialize with first version
  useEffect(() => {
    if (initialContent && versions.length === 0) {
      const initialVersion: Version = {
        id: Date.now().toString(),
        content: initialContent,
        timestamp: new Date(),
        description: 'Initial version'
      };
      setVersions([initialVersion]);
      setCurrentIndex(0);
    }
  }, [initialContent, versions.length]);

  const saveVersion = useCallback((content: string, description: string = 'Update') => {
    setVersions(prev => {
      // Remove any versions after current index (redo stack)
      const newVersions = prev.slice(0, currentIndex + 1);

      // Add new version
      const newVersion: Version = {
        id: Date.now().toString(),
        content,
        timestamp: new Date(),
        description
      };

      newVersions.push(newVersion);

      // Keep only last MAX_VERSIONS
      const trimmed = newVersions.slice(-MAX_VERSIONS);

      return trimmed;
    });

    setCurrentIndex(prev => {
      const newIndex = Math.min(prev + 1, MAX_VERSIONS - 1);
      return newIndex;
    });
  }, [currentIndex]);

  const undo = useCallback((): string | null => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1);
      return versions[currentIndex - 1]?.content || null;
    }
    return null;
  }, [currentIndex, versions]);

  const redo = useCallback((): string | null => {
    if (currentIndex < versions.length - 1) {
      setCurrentIndex(prev => prev + 1);
      return versions[currentIndex + 1]?.content || null;
    }
    return null;
  }, [currentIndex, versions]);

  const goToVersion = useCallback((versionId: string): string | null => {
    const index = versions.findIndex(v => v.id === versionId);
    if (index !== -1) {
      setCurrentIndex(index);
      return versions[index].content;
    }
    return null;
  }, [versions]);

  const clearHistory = useCallback(() => {
    setVersions([]);
    setCurrentIndex(-1);
  }, []);

  const currentVersion = versions[currentIndex]?.content || '';
  const canUndo = currentIndex > 0;
  const canRedo = currentIndex < versions.length - 1;

  return {
    currentVersion,
    versions,
    canUndo,
    canRedo,
    saveVersion,
    undo,
    redo,
    goToVersion,
    clearHistory
  };
};
