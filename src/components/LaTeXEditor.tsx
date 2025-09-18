import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Check, X } from 'lucide-react';
import { Change } from './ResumeEditor';

interface LaTeXEditorProps {
  changes: Change[];
  onChangeAccept: (changeId: string, accepted: boolean) => void;
}

const sampleLatexContent = `\\documentclass{article}
\\usepackage[letterpaper,margin=0.75in]{geometry}
\\usepackage{enumitem}
\\usepackage{hyperref}

\\begin{document}

\\begin{center}
{\\Large \\textbf{John Smith}}\\\\
Email: john.smith@email.com $\\bullet$ Phone: (555) 123-4567\\\\
LinkedIn: linkedin.com/in/johnsmith $\\bullet$ GitHub: github.com/johnsmith
\\end{center}

\\section*{Professional Summary}
Experienced software engineer with 5+ years building scalable web applications and leading technical teams. Proven track record of delivering high-impact solutions and mentoring junior developers.

\\section*{Experience}
\\textbf{Senior Software Engineer} \\hfill \\textit{2022 - Present}\\\\
\\textit{TechCorp Inc.} \\hfill \\textit{San Francisco, CA}
\\begin{itemize}[leftmargin=0.5in]
%CHANGE_1_START%
\\item Led cross-functional team of 8 engineers to deliver customer analytics platform
\\item Implemented microservices architecture reducing system latency by 40\\%
\\item Established CI/CD pipeline improving deployment frequency by 300\\%
%CHANGE_1_END%
\\item Collaborated with product managers to define technical requirements
%CHANGE_2_START%
\\item Basic project management tasks
\\item Routine maintenance work
%CHANGE_2_END%
\\end{itemize}

\\section*{Education}
\\textbf{Bachelor of Science in Computer Science}\\\\
\\textit{University of California, Berkeley} \\hfill \\textit{2018}

\\section*{Skills}
JavaScript, TypeScript, React, Node.js, Python, PostgreSQL, AWS, Docker, Kubernetes

\\end{document}`;

export const LaTeXEditor = ({ changes, onChangeAccept }: LaTeXEditorProps) => {
  const [content, setContent] = useState(sampleLatexContent);

  const renderContentWithChanges = () => {
    const lines = content.split('\n');
    const result: JSX.Element[] = [];
    let i = 0;

    while (i < lines.length) {
      const currentLine = i + 1; // 1-indexed
      const change = changes.find(c => 
        currentLine >= c.startLine && currentLine <= c.endLine
      );

      if (change) {
        const changeLines = lines.slice(change.startLine - 1, change.endLine);
        
        result.push(
          <div
            key={`change-${change.id}`}
            className={`relative group ${
              change.type === 'addition' 
                ? 'bg-addition-bg border-l-2 border-addition' 
                : 'bg-removal-bg border-l-2 border-removal opacity-60'
            }`}
          >
            {/* Change content */}
            <div className="py-1 px-3 font-mono text-sm whitespace-pre">
              {changeLines.map((line, idx) => (
                <div key={idx}>{line}</div>
              ))}
            </div>

            {/* Action buttons */}
            <div className="absolute right-2 top-1 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
              <Button
                size="sm"
                variant="ghost"
                className={`h-6 w-6 p-0 ${
                  change.accepted === true 
                    ? 'bg-success text-white' 
                    : 'hover:bg-success hover:text-white'
                }`}
                onClick={() => onChangeAccept(change.id, true)}
              >
                <Check className="w-3 h-3" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className={`h-6 w-6 p-0 ${
                  change.accepted === false 
                    ? 'bg-destructive text-white' 
                    : 'hover:bg-destructive hover:text-white'
                }`}
                onClick={() => onChangeAccept(change.id, false)}
              >
                <X className="w-3 h-3" />
              </Button>
            </div>

            {/* Keyboard shortcuts hint */}
            <div className="absolute left-2 top-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="text-xs text-muted-foreground bg-background px-1 rounded">
                A: Accept | R: Reject
              </span>
            </div>
          </div>
        );

        i = change.endLine; // Skip to end of change
      } else {
        result.push(
          <div key={`line-${i}`} className="py-1 px-3 font-mono text-sm">
            {lines[i]}
          </div>
        );
        i++;
      }
    }

    return result;
  };

  return (
    <div className="h-full flex flex-col bg-workspace-background">
      <div className="flex-1 overflow-auto">
        <div className="p-0">
          {renderContentWithChanges()}
        </div>
      </div>
      
      {/* Status bar */}
      <div className="border-t border-border px-4 py-2 text-xs text-muted-foreground bg-card">
        <div className="flex justify-between items-center">
          <span>resume.tex</span>
          <div className="flex gap-4">
            <span>{changes.filter(c => c.type === 'addition').length} additions</span>
            <span>{changes.filter(c => c.type === 'removal').length} removals</span>
          </div>
        </div>
      </div>
    </div>
  );
};