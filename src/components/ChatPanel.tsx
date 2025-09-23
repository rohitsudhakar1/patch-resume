import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send, Sparkles } from 'lucide-react';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export const ChatPanel = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    console.log('🔍 DEBUG: ChatPanel - Starting AI chat');
    console.log('📝 DEBUG: Message:', input.trim());

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const message = input.trim();
    setInput('');
    setIsLoading(true);

    try {
      // Get current project
      const projectData = sessionStorage.getItem('currentProject');
      const currentProject = projectData ? JSON.parse(projectData) : null;
      
      console.log('📁 DEBUG: Project data from sessionStorage:', currentProject ? 'Found' : 'Not found');
      
      // Prepare chat history
      const chatHistory = messages.map(m => ({
        role: m.type === 'user' ? 'user' : 'assistant',
        content: m.content
      }));
      
      // Call the AI chat endpoint
      const response = await fetch('http://localhost:8000/llm/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          chat_history: chatHistory,
          current_resume: currentProject?.resume_tex,
          context: {
            has_resume: !!currentProject,
            resume_length: currentProject?.resume_tex?.length || 0
          }
        })
      });

      if (!response.ok) {
        throw new Error('Failed to get response from AI agent');
      }

      const data = await response.json();
      console.log('📥 DEBUG: Received AI response:', data);
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: data.response,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, aiMessage]);
      
      // If this is a resume update, handle it
      if (data.is_resume_update && data.resume_data && currentProject) {
        console.log('🔄 DEBUG: Resume updated by AI agent');
        const updatedProject = { ...currentProject, resume_tex: data.resume_data };
        sessionStorage.setItem('currentProject', JSON.stringify(updatedProject));
        window.dispatchEvent(new CustomEvent('projectUpdated', { detail: updatedProject }));
      }
      
      // Check if this is a patch generation request (for backward compatibility)
      const patchKeywords = ['change', 'modify', 'add', 'remove', 'delete', 'improve', 'fix', 'update'];
      const isPatchRequest = patchKeywords.some(keyword => message.toLowerCase().includes(keyword));
      
      if (isPatchRequest && currentProject) {
        console.log('🔧 DEBUG: Detected patch request, generating changes...');
        try {
          const { apiClient } = await import('../lib/api');
          const patchResult = await apiClient.generatePatch(message, undefined, false, currentProject.id, currentProject);
          console.log('📥 DEBUG: Generated patch result:', patchResult);
          
          // Store patch result for the workspace
          sessionStorage.setItem('currentPatch', JSON.stringify(patchResult));
          
          // Trigger workspace update
          window.dispatchEvent(new CustomEvent('patchGenerated', { detail: patchResult }));
        } catch (patchError) {
          console.log('⚠️ DEBUG: Patch generation failed, but chat response was successful:', patchError);
        }
      }
      
    } catch (error) {
      console.error('❌ ERROR: AI chat failed:', error);
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
      <div className="p-4 border-b border-slate-700 bg-slate-800">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-cyan-400" />
          <h2 className="font-semibold text-white">Resume Assistant</h2>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-900">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                message.type === 'user'
                  ? 'bg-cyan-600 text-white ml-4'
                  : 'bg-slate-800 border border-slate-600 text-slate-100 mr-4'
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
            </div>
          </div>
        ))}
        
         {isLoading && (
           <div className="flex justify-start">
             <div className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-3 py-2 text-sm mr-4">
               <div className="flex items-center gap-2">
                 <div className="flex space-x-1">
                   <div className="w-1 h-1 bg-cyan-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                   <div className="w-1 h-1 bg-cyan-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                   <div className="w-1 h-1 bg-cyan-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                 </div>
                 <span className="text-slate-400">Analyzing...</span>
               </div>
             </div>
           </div>
         )}
         <div ref={messagesEndRef} />
       </div>

       {/* Input */}
       <div className="p-4 border-t border-slate-700 bg-slate-800">
         <form onSubmit={handleSubmit} className="flex gap-2">
           <Textarea
             ref={textareaRef}
             value={input}
             onChange={(e) => setInput(e.target.value)}
             placeholder="Ask me to improve your resume..."
             className="flex-1 bg-slate-700 border-slate-600 text-white placeholder-slate-400 resize-none min-h-[40px] max-h-[120px]"
             disabled={isLoading}
             rows={1}
           />
           <Button 
             type="submit" 
             size="icon" 
             disabled={!input.trim() || isLoading}
             className="shrink-0 bg-cyan-600 hover:bg-cyan-700"
           >
             <Send className="w-4 h-4" />
           </Button>
         </form>
       </div>
    </div>
  );
};