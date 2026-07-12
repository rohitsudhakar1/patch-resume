import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send, Sparkles, Briefcase, X, Check, CheckCircle2, FileCheck2 } from 'lucide-react';

interface Proposal {
  latex: string;
  status: 'pending' | 'applied' | 'discarded';
  // Human-readable label for version history, e.g. 'Chat: "Change my name…"'
  description: string;
}

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  // A validated resume update awaiting the user's explicit approval.
  proposal?: Proposal;
}

export const ChatPanel = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [jdOpen, setJdOpen] = useState(false);
  const [jdText, setJdText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Auto-expand textarea
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [input]);

  useEffect(scrollToBottom, [messages]);

  // Add initial message when component mounts
  useEffect(() => {
    if (messages.length === 0) {
      const initialMessage: Message = {
        id: '1',
        type: 'assistant',
        content: "Hi! I'm your AI resume assistant. I can help you improve your resume by suggesting specific changes, restructuring content, or optimizing for specific roles. What would you like to work on?",
        timestamp: new Date()
      };
      setMessages([initialMessage]);
    }
  }, [messages.length]);

  // Fit-to-one-page results arrive as proposals too (same approval flow).
  useEffect(() => {
    const onFitProposal = (e: Event) => {
      const d = (e as CustomEvent).detail || {};
      if (!d.latex) return;
      const passes = `${d.iterations} pass${d.iterations === 1 ? '' : 'es'}`;
      const msg: Message = {
        id: Date.now().toString(),
        type: 'assistant',
        content: d.fit
          ? `Condensed your resume to one page in ${passes}. Review the highlighted preview and apply if it looks right.`
          : `Best effort: reached ${d.pages ?? '?'} pages after ${passes}. Review the preview and decide.`,
        timestamp: new Date(),
        proposal: { latex: d.latex, status: 'pending', description: d.fit ? 'Fit to one page' : 'Condensed (best effort)' }
      };
      setMessages(prev => [...prev, msg]);
      if (d.previewAvailable && d.projectId) {
        window.dispatchEvent(new CustomEvent('proposalPreview', { detail: { projectId: d.projectId } }));
      }
    };
    const onFitNoChange = () => {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        type: 'assistant',
        content: 'Your resume already fits on one page — nothing to change.',
        timestamp: new Date()
      }]);
    };
    window.addEventListener('fitProposal', onFitProposal);
    window.addEventListener('fitNoChange', onFitNoChange);
    return () => {
      window.removeEventListener('fitProposal', onFitProposal);
      window.removeEventListener('fitNoChange', onFitNoChange);
    };
  }, []);

  // Handle Enter key press
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const message = input.trim();
    if (!message || isLoading) return;
    setInput('');
    sendMessage(message);
  };

  // Tailor the resume to a pasted job description.
  const handleTailor = () => {
    const jd = jdText.trim();
    if (!jd || isLoading) return;
    const instruction =
      'Tailor my resume to the following job description. Reorder and rewrite the ' +
      'summary, bullet points, and skills to emphasize the most relevant experience ' +
      'and naturally weave in the key skills, tools, and keywords from the posting. ' +
      'Stay truthful — do not invent experience, employers, or credentials. Keep it ' +
      'concise (ideally one page) and keep the existing LaTeX document structure and ' +
      'formatting exactly as it is. Return the full updated LaTeX.\n\n' +
      'JOB DESCRIPTION:\n' + jd;
    sendMessage(instruction, '✦ Tailor my resume to this job description');
    setJdText('');
    setJdOpen(false);
  };

  // Apply a validated proposal: sync the backend first (the PDF endpoint
  // compiles from backend state), then update local state and notify.
  const applyProposal = async (messageId: string) => {
    const msg = messages.find(m => m.id === messageId);
    if (!msg?.proposal || msg.proposal.status !== 'pending') return;

    const projectData = sessionStorage.getItem('currentProject');
    const currentProject = projectData ? JSON.parse(projectData) : null;
    if (!currentProject) return;

    const updatedProject = {
      ...currentProject,
      resume_tex: msg.proposal.latex,
      last_updated: new Date().toISOString(),
      last_description: msg.proposal.description || 'Applied chat edit'
    };

    try {
      await fetch('http://localhost:8000/project/recreate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedProject),
      });
      sessionStorage.setItem('currentProject', JSON.stringify(updatedProject));
      window.dispatchEvent(new CustomEvent('projectUpdated', { detail: updatedProject }));
      setMessages(prev => prev.map(m =>
        m.id === messageId && m.proposal ? { ...m, proposal: { ...m.proposal, status: 'applied' } } : m
      ));
      console.log('✅ Proposal applied by user');
    } catch (error) {
      console.error('❌ Failed to apply proposal:', error);
    }
  };

  const discardProposal = (messageId: string) => {
    setMessages(prev => prev.map(m =>
      m.id === messageId && m.proposal?.status === 'pending'
        ? { ...m, proposal: { ...m.proposal, status: 'discarded' } } : m
    ));
    // Snap the PDF pane back to the current (unchanged) document.
    const projectData = sessionStorage.getItem('currentProject');
    const pid = projectData ? JSON.parse(projectData).id : undefined;
    window.dispatchEvent(new CustomEvent('proposalPreviewEnd', { detail: { projectId: pid } }));
    console.log('🗑️ Proposal discarded — resume unchanged');
  };

  // Core send routine. `message` is what's sent to the model; `displayText`
  // (optional) is what's shown in the chat bubble (used for long JD pastes).
  const sendMessage = async (message: string, displayText?: string) => {
    if (!message.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: displayText || message,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Get current project
      const projectData = sessionStorage.getItem('currentProject');
      const currentProject = projectData ? JSON.parse(projectData) : null;

      console.log('💬 Chat request:', message.substring(0, 50) + '...');

      // Prepare chat history
      const chatHistory = messages.map(m => ({
        role: m.type === 'user' ? 'user' : 'assistant',
        content: m.content
      }));

      // Call improved chat endpoint with direct LaTeX updates
      const response = await fetch('http://localhost:8000/llm/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          chat_history: chatHistory,
          current_resume: currentProject?.resume_tex || '',
          context: {
            has_resume: !!currentProject,
            resume_length: currentProject?.resume_tex?.length || 0,
            project_id: currentProject?.id || 'default'
          }
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`AI service error: ${errorText}`);
      }

      const data = await response.json();

      // Display AI response. A validated resume update arrives as a PROPOSAL —
      // nothing is applied until the user clicks Apply (human approval layer).
      const hasProposal = data.is_resume_update && data.resume_data;
      const isTailor = (displayText || '').startsWith('✦');
      const shortAsk = message.length > 42 ? message.slice(0, 42) + '…' : message;
      const description = isTailor ? 'Tailored to job description' : `Chat: "${shortAsk}"`;
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: (data.response && data.response.trim()) || data.explanation || 'Done.',
        timestamp: new Date(),
        ...(hasProposal ? { proposal: { latex: data.resume_data, status: 'pending' as const, description } } : {})
      };
      setMessages(prev => [...prev, aiMessage]);

      if (hasProposal) {
        console.log('📋 Validated proposal received (' + data.resume_data.length + ' chars) — awaiting approval');
        // Switch the PDF pane to the highlighted preview of this proposal.
        if (data.preview_available && currentProject?.id) {
          window.dispatchEvent(new CustomEvent('proposalPreview', { detail: { projectId: currentProject.id } }));
        }
      }

    } catch (error) {
      console.error('❌ Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-border bg-card px-4 h-12 flex-shrink-0">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent/15 text-accent ring-1 ring-accent/25">
          <Sparkles className="h-4 w-4" />
        </div>
        <div className="leading-tight">
          <h2 className="font-display text-sm font-semibold text-foreground">AI Editor</h2>
          <p className="text-[11px] text-muted-foreground">Powered by Claude</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-background scrollbar-thin scrollbar-thumb-slate-600 scrollbar-track-slate-800 hover:scrollbar-thumb-slate-500" style={{
        scrollbarWidth: 'thin',
        scrollbarColor: '#475569 #1e293b'
      }}>
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} group`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-lg transition-all duration-200 ${
                message.type === 'user'
                  ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white ml-4 hover:shadow-xl'
                  : 'bg-slate-800/80 border border-slate-600/50 text-slate-100 mr-4 hover:bg-slate-800/90 backdrop-blur-sm'
              }`}
            >
               {message.type === 'assistant' ? (
                 <div className="whitespace-pre-wrap">
                   {message.content.split('\n').map((line, index) => {
                     // Handle bold text with **
                     if (line.includes('**')) {
                       const parts = line.split(/(\*\*[^*]+\*\*)/g);
                       return (
                         <div key={index} className="text-slate-300">
                           {parts.map((part, partIndex) => {
                             if (part.startsWith('**') && part.endsWith('**')) {
                               return <span key={partIndex} className="font-bold text-cyan-300">{part.replace(/\*\*/g, '')}</span>;
                             }
                             return part;
                           })}
                         </div>
                       );
                     } else if (line.startsWith('• ')) {
                       return <div key={index} className="ml-4 text-slate-300">• {line.substring(2)}</div>;
                     } else if (line.match(/^\d+\./)) {
                       return <div key={index} className="ml-4 text-slate-300">{line}</div>;
                     } else if (line.trim() === '') {
                       return <div key={index} className="h-2"></div>;
                     } else {
                       return <div key={index} className="text-slate-300">{line}</div>;
                     }
                   })}
                 </div>
               ) : (
                 message.content
               )}
               {message.proposal && (
                 <div className="mt-3" data-testid="proposal-controls">
                   {message.proposal.status === 'pending' && (
                     <div className="overflow-hidden rounded-lg border border-amber-400/30 bg-amber-400/[0.06]">
                       {/* Status header: what stage of the pipeline this is at */}
                       <div className="flex items-center justify-between gap-2 border-b border-amber-400/20 px-3 py-2">
                         <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-amber-300/90">
                           Proposed change
                         </span>
                         <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2 py-0.5 text-[10px] font-medium text-emerald-300">
                           <FileCheck2 className="h-3 w-3" /> Compiles
                         </span>
                       </div>
                       <div className="space-y-2.5 px-3 py-2.5">
                         <p className="text-[11px] leading-relaxed text-slate-400">
                           Previewing in the PDF pane — blue text is what changes. Your resume stays untouched until you apply.
                         </p>
                         <div className="flex items-center gap-2">
                           <Button
                             size="sm"
                             onClick={() => applyProposal(message.id)}
                             className="h-8 flex-1 rounded-md bg-gradient-to-r from-cyan-600 to-blue-600 px-3 text-xs font-semibold text-white shadow-sm transition hover:opacity-90"
                             data-testid="apply-proposal"
                           >
                             <Check className="mr-1.5 h-3.5 w-3.5" /> Apply change
                           </Button>
                           <Button
                             size="sm"
                             variant="outline"
                             onClick={() => discardProposal(message.id)}
                             className="h-8 rounded-md border-slate-500/50 bg-transparent px-3 text-xs font-medium text-slate-400 transition hover:border-slate-400/60 hover:bg-slate-700/50 hover:text-slate-200"
                             data-testid="discard-proposal"
                           >
                             <X className="mr-1.5 h-3.5 w-3.5" /> Discard
                           </Button>
                         </div>
                       </div>
                     </div>
                   )}
                   {message.proposal.status === 'applied' && (
                     <div
                       className="flex items-center gap-2 rounded-lg border border-emerald-400/25 bg-emerald-400/[0.07] px-3 py-2"
                       data-testid="proposal-applied"
                     >
                       <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                       <div className="leading-tight">
                         <p className="text-xs font-medium text-emerald-300">Applied to your resume</p>
                         <p className="text-[10px] text-slate-500">Saved to version history — undo anytime</p>
                       </div>
                     </div>
                   )}
                   {message.proposal.status === 'discarded' && (
                     <div
                       className="flex items-center gap-2 rounded-lg border border-slate-600/40 bg-slate-700/20 px-3 py-2"
                       data-testid="proposal-discarded"
                     >
                       <X className="h-4 w-4 shrink-0 text-slate-500" />
                       <p className="text-xs font-medium text-slate-400">Discarded — resume unchanged</p>
                     </div>
                   )}
                 </div>
               )}
            </div>
          </div>
        ))}
        
         {isLoading && (
           <div className="flex justify-start">
             <div className="bg-slate-800/80 border border-slate-600/50 text-slate-100 rounded-2xl px-4 py-3 text-sm mr-4 shadow-lg backdrop-blur-sm">
               <div className="flex items-center gap-3">
                 <div className="flex space-x-1">
                   <div className="w-2 h-2 bg-gradient-to-r from-cyan-400 to-blue-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                   <div className="w-2 h-2 bg-gradient-to-r from-cyan-400 to-blue-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                   <div className="w-2 h-2 bg-gradient-to-r from-cyan-400 to-blue-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                 </div>
                 <span className="text-slate-300 font-medium">AI is thinking...</span>
               </div>
             </div>
           </div>
         )}
         <div ref={messagesEndRef} />
       </div>

       {/* Input */}
       <div className="p-3 border-t border-border bg-card space-y-2">
         {/* Tailor to a job description */}
         {jdOpen ? (
           <div className="rounded-lg border border-accent/40 bg-secondary/40 p-2.5">
             <div className="mb-1.5 flex items-center justify-between">
               <span className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                 <Briefcase className="h-3.5 w-3.5 text-accent" /> Tailor to a job description
               </span>
               <button onClick={() => setJdOpen(false)} className="text-muted-foreground transition hover:text-foreground">
                 <X className="h-3.5 w-3.5" />
               </button>
             </div>
             <Textarea
               value={jdText}
               onChange={(e) => setJdText(e.target.value)}
               placeholder="Paste the full job description here — Claude will rewrite your resume to match it."
               className="min-h-[92px] max-h-[200px] resize-none rounded-md border-border bg-background text-foreground placeholder:text-muted-foreground text-sm scrollbar-thin"
               disabled={isLoading}
             />
             <Button
               onClick={handleTailor}
               disabled={!jdText.trim() || isLoading}
               className="mt-2 w-full rounded-md bg-accent text-accent-foreground transition hover:opacity-90 disabled:opacity-40"
             >
               {isLoading ? 'Tailoring…' : 'Tailor my resume'}
             </Button>
           </div>
         ) : (
           <button
             onClick={() => setJdOpen(true)}
             disabled={isLoading}
             className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-border py-2 text-xs font-medium text-muted-foreground transition hover:border-accent/60 hover:text-foreground disabled:opacity-40"
           >
             <Briefcase className="h-3.5 w-3.5" /> Tailor to a job description
           </button>
         )}

         <form onSubmit={handleSubmit} className="flex items-end gap-2">
           <Textarea
             ref={textareaRef}
             value={input}
             onChange={(e) => setInput(e.target.value)}
             onKeyPress={handleKeyPress}
             placeholder="Ask Claude to improve your resume…"
             className="flex-1 resize-none rounded-lg border-border bg-secondary/50 text-foreground placeholder:text-muted-foreground min-h-[44px] max-h-[140px] py-2.5 px-3 focus-visible:ring-2 focus-visible:ring-accent focus-visible:border-accent transition scrollbar-thin"
             disabled={isLoading}
             rows={1}
           />
           <Button
             type="submit"
             size="icon"
             disabled={!input.trim() || isLoading}
             className="h-11 w-11 shrink-0 rounded-lg bg-accent text-accent-foreground transition hover:opacity-90 disabled:opacity-40"
           >
             {isLoading ? (
               <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
             ) : (
               <Send className="h-4 w-4" />
             )}
           </Button>
         </form>
         <p className="mt-1.5 px-1 text-[11px] text-muted-foreground">Enter to send · Shift+Enter for a new line</p>
       </div>
    </div>
  );
};