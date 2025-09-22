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
    <div className="border-t border-slate-700 bg-slate-800 px-4 py-3 shadow-sm flex-shrink-0">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        {/* Left side - Apply */}
        <div className="flex items-center gap-3">
          <Button 
            onClick={() => {
              console.log('🔧 DEBUG: Accept all button clicked');
              console.log('📊 DEBUG: acceptedCount:', acceptedCount);
              console.log('📊 DEBUG: isCompiling:', isCompiling);
              onApply();
            }}
            disabled={isCompiling}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            <Check className="w-4 h-4 mr-2" />
            Accept all
          </Button>
          
          <Button 
            variant="outline"
            onClick={onDiscard}
            disabled={isCompiling}
            className="border-slate-600 text-slate-300 hover:bg-slate-700"
          >
            <X className="w-4 h-4 mr-2" />
            Discard all
          </Button>
        </div>

        {/* Center - Status */}
        <div className="flex items-center gap-2">
          {isCompiling && (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <div className="w-2 h-2 bg-cyan-500 rounded-full animate-pulse" />
              Compiling...
            </div>
          )}
        </div>

        {/* Right side - Optional undo */}
        <div className="flex items-center gap-2">
          <Button 
            variant="ghost" 
            size="sm"
            className="text-xs text-slate-500"
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