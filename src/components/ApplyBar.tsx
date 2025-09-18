import { Button } from '@/components/ui/button';
import { Check, X, RotateCcw } from 'lucide-react';

interface ApplyBarProps {
  hasChanges: boolean;
  acceptedCount: number;
  isCompiling: boolean;
  onApply: () => void;
  onDiscard: () => void;
}

export const ApplyBar = ({ hasChanges, acceptedCount, isCompiling, onApply, onDiscard }: ApplyBarProps) => {
  if (!hasChanges) return null;

  return (
    <div className="border-t border-border bg-card px-4 py-3">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        {/* Left side - Apply */}
        <div className="flex items-center gap-3">
          <Button 
            onClick={onApply}
            disabled={acceptedCount === 0 || isCompiling}
            className="bg-success hover:bg-success/90 text-white"
          >
            <Check className="w-4 h-4 mr-2" />
            Apply accepted ({acceptedCount})
          </Button>
          
          <Button 
            variant="outline"
            onClick={onDiscard}
            disabled={isCompiling}
          >
            <X className="w-4 h-4 mr-2" />
            Discard all
          </Button>
        </div>

        {/* Center - Status */}
        <div className="flex items-center gap-2">
          {isCompiling && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="w-2 h-2 bg-compiling rounded-full animate-pulse" />
              Compiling...
            </div>
          )}
        </div>

        {/* Right side - Optional undo */}
        <div className="flex items-center gap-2">
          <Button 
            variant="ghost" 
            size="sm"
            className="text-xs text-muted-foreground"
            disabled
          >
            <RotateCcw className="w-3 h-3 mr-1" />
            Undo last apply
          </Button>
        </div>
      </div>
    </div>
  );
};