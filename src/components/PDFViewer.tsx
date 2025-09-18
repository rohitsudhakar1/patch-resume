import { Button } from '@/components/ui/button';
import { Check, X, Code } from 'lucide-react';
import { Change } from './ResumeEditor';

interface PDFViewerProps {
  changes: Change[];
  onChangeAccept: (changeId: string, accepted: boolean) => void;
}

export const PDFViewer = ({ changes, onChangeAccept }: PDFViewerProps) => {
  const handleChangeClick = (changeId: string) => {
    // In a real implementation, this would jump to the LaTeX source
    console.log(`Jump to change ${changeId} in LaTeX`);
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* PDF Container with overlaid changes */}
      <div className="flex-1 relative overflow-auto p-8">
        {/* Simulated PDF content */}
        <div className="max-w-2xl mx-auto bg-white shadow-lg" style={{aspectRatio: '8.5/11'}}>
          <div className="p-12 space-y-6">
            {/* Header */}
            <div className="text-center">
              <h1 className="text-2xl font-bold">John Smith</h1>
              <div className="text-sm text-gray-600 mt-1">
                Email: john.smith@email.com • Phone: (555) 123-4567<br />
                LinkedIn: linkedin.com/in/johnsmith • GitHub: github.com/johnsmith
              </div>
            </div>

            {/* Professional Summary */}
            <div>
              <h2 className="font-bold text-lg border-b border-gray-300 pb-1">Professional Summary</h2>
              <p className="text-sm mt-2">
                Experienced software engineer with 5+ years building scalable web applications and leading technical teams. 
                Proven track record of delivering high-impact solutions and mentoring junior developers.
              </p>
            </div>

            {/* Experience Section with Changes */}
            <div className="relative">
              <h2 className="font-bold text-lg border-b border-gray-300 pb-1">Experience</h2>
              
              <div className="mt-3">
                <div className="flex justify-between items-start">
                  <div>
                    <strong>Senior Software Engineer</strong><br />
                    <em>TechCorp Inc.</em>
                  </div>
                  <div className="text-right text-sm">
                    <em>2022 - Present</em><br />
                    <em>San Francisco, CA</em>
                  </div>
                </div>

                <ul className="list-disc list-inside mt-2 space-y-1 text-sm relative">
                  {/* Addition Change Overlay */}
                  {changes.find(c => c.id === '1') && (
                    <div className="relative">
                      <div 
                        className="absolute inset-0 bg-addition-bg border border-addition rounded cursor-pointer group"
                        style={{
                          top: '-2px',
                          left: '-8px',
                          right: '-8px',
                          height: '66px'
                        }}
                        onClick={() => handleChangeClick('1')}
                      >
                        {/* Change popover */}
                        <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity bg-white border border-border rounded shadow-lg p-2 z-10 min-w-48">
                          <div className="text-xs text-muted-foreground mb-2">
                            Added leadership and impact metrics
                          </div>
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 px-2 text-xs bg-success text-white hover:bg-success/80"
                              onClick={(e) => {
                                e.stopPropagation();
                                onChangeAccept('1', true);
                              }}
                            >
                              <Check className="w-3 h-3 mr-1" />
                              Accept
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 px-2 text-xs bg-destructive text-white hover:bg-destructive/80"
                              onClick={(e) => {
                                e.stopPropagation();
                                onChangeAccept('1', false);
                              }}
                            >
                              <X className="w-3 h-3 mr-1" />
                              Reject
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 px-2 text-xs hover:bg-secondary"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleChangeClick('1');
                              }}
                            >
                              <Code className="w-3 h-3" />
                            </Button>
                          </div>
                        </div>
                      </div>
                      
                      <li>Led cross-functional team of 8 engineers to deliver customer analytics platform</li>
                      <li>Implemented microservices architecture reducing system latency by 40%</li>
                      <li>Established CI/CD pipeline improving deployment frequency by 300%</li>
                    </div>
                  )}
                  
                  <li>Collaborated with product managers to define technical requirements</li>
                  
                  {/* Removal Change Overlay */}
                  {changes.find(c => c.id === '2') && (
                    <div className="relative">
                      <div 
                        className="absolute inset-0 bg-removal-bg border border-removal rounded cursor-pointer group opacity-60"
                        style={{
                          top: '-2px',
                          left: '-8px',
                          right: '-8px',
                          height: '44px'
                        }}
                        onClick={() => handleChangeClick('2')}
                      >
                        {/* Diagonal stripes for removal */}
                        <div className="absolute inset-0 opacity-30" style={{
                          backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 4px, rgba(239, 68, 68, 0.3) 4px, rgba(239, 68, 68, 0.3) 8px)'
                        }}></div>
                        
                        {/* Change popover */}
                        <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity bg-white border border-border rounded shadow-lg p-2 z-10 min-w-48">
                          <div className="text-xs text-muted-foreground mb-2">
                            Remove weak bullet points
                          </div>
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 px-2 text-xs bg-success text-white hover:bg-success/80"
                              onClick={(e) => {
                                e.stopPropagation();
                                onChangeAccept('2', true);
                              }}
                            >
                              <Check className="w-3 h-3 mr-1" />
                              Accept
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 px-2 text-xs bg-destructive text-white hover:bg-destructive/80"
                              onClick={(e) => {
                                e.stopPropagation();
                                onChangeAccept('2', false);
                              }}
                            >
                              <X className="w-3 h-3 mr-1" />
                              Reject
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 px-2 text-xs hover:bg-secondary"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleChangeClick('2');
                              }}
                            >
                              <Code className="w-3 h-3" />
                            </Button>
                          </div>
                        </div>
                      </div>
                      
                      <li className="line-through text-gray-400">Basic project management tasks</li>
                      <li className="line-through text-gray-400">Routine maintenance work</li>
                    </div>
                  )}
                </ul>
              </div>
            </div>

            {/* Education */}
            <div>
              <h2 className="font-bold text-lg border-b border-gray-300 pb-1">Education</h2>
              <div className="mt-2 text-sm">
                <strong>Bachelor of Science in Computer Science</strong><br />
                <em>University of California, Berkeley</em> • <em>2018</em>
              </div>
            </div>

            {/* Skills */}
            <div>
              <h2 className="font-bold text-lg border-b border-gray-300 pb-1">Skills</h2>
              <p className="text-sm mt-2">
                JavaScript, TypeScript, React, Node.js, Python, PostgreSQL, AWS, Docker, Kubernetes
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Status bar */}
      <div className="border-t border-border px-4 py-2 text-xs text-muted-foreground bg-card">
        <div className="flex justify-between items-center">
          <span>resume.pdf</span>
          <span>Click highlighted regions to review changes</span>
        </div>
      </div>
    </div>
  );
};