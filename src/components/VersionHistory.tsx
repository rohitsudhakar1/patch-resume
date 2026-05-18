import { History, Undo2, Redo2, Clock } from 'lucide-react';
import { Button } from './ui/button';
import { Version } from '@/hooks/useVersionHistory';

interface VersionHistoryProps {
  versions: Version[];
  currentIndex: number;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onGoToVersion: (versionId: string) => void;
}

export const VersionHistory = ({
  versions,
  currentIndex,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onGoToVersion
}: VersionHistoryProps) => {
  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - new Date(date).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  return (
    <div className="flex flex-col h-full bg-slate-800 border-l border-slate-700">
      {/* Header with Undo/Redo */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-cyan-400" />
            <h3 className="font-semibold text-slate-200">Version History</h3>
          </div>
          <span className="text-xs text-slate-400">{versions.length} versions</span>
        </div>

        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={onUndo}
            disabled={!canUndo}
            className="flex-1 bg-slate-700 border-slate-600 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Undo2 className="w-4 h-4 mr-2" />
            Undo
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onRedo}
            disabled={!canRedo}
            className="flex-1 bg-slate-700 border-slate-600 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Redo2 className="w-4 h-4 mr-2" />
            Redo
          </Button>
        </div>
      </div>

      {/* Version List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {versions.length === 0 ? (
          <div className="text-center py-8">
            <Clock className="w-12 h-12 mx-auto mb-3 text-slate-600" />
            <p className="text-sm text-slate-400">No version history yet</p>
          </div>
        ) : (
          [...versions].reverse().map((version, idx) => {
            const actualIndex = versions.length - 1 - idx;
            const isCurrent = actualIndex === currentIndex;

            return (
              <button
                key={version.id}
                onClick={() => onGoToVersion(version.id)}
                className={`w-full text-left p-3 rounded-lg border transition-all ${
                  isCurrent
                    ? 'bg-cyan-900/30 border-cyan-500/50 shadow-lg'
                    : 'bg-slate-700/50 border-slate-600 hover:bg-slate-700 hover:border-slate-500'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium truncate ${
                      isCurrent ? 'text-cyan-300' : 'text-slate-200'
                    }`}>
                      {version.description}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      {formatTime(version.timestamp)}
                    </p>
                  </div>
                  {isCurrent && (
                    <span className="text-xs bg-cyan-500 text-white px-2 py-1 rounded-full">
                      Current
                    </span>
                  )}
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
};
