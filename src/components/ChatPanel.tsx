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

    console.log('🔍 DEBUG: ChatPanel - Starting patch generation');
    console.log('📝 DEBUG: Instruction:', input.trim());

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const instruction = input.trim();
    setInput('');
    setIsLoading(true);

    try {
      // Get current project
      const projectData = sessionStorage.getItem('currentProject');
      console.log('📁 DEBUG: Project data from sessionStorage:', projectData ? 'Found' : 'Not found');
      
      if (!projectData) {
        throw new Error('No project found. Please upload a resume first.');
      }

      // Test API connection first
      console.log('🔗 DEBUG: Testing API connection...');
      const { apiClient } = await import('../lib/api');
      
      try {
        const healthCheck = await apiClient.healthCheck();
        console.log('✅ DEBUG: API health check successful:', healthCheck);
      } catch (healthError) {
        console.log('⚠️ DEBUG: API health check failed:', healthError);
      }

      // Get current project ID and data
      const currentProject = projectData ? JSON.parse(projectData) : null;
      const projectId = currentProject?.id;
      
      // Generate patch using backend
      console.log('🤖 DEBUG: Calling generatePatch API...');
      console.log('📁 DEBUG: Using project ID:', projectId);
      console.log('📁 DEBUG: Project data available:', !!currentProject);
      const patchResult = await apiClient.generatePatch(instruction, undefined, false, projectId, currentProject);
      console.log('📥 DEBUG: Received patch result:', patchResult);
      
      // Store patch result for the workspace
      sessionStorage.setItem('currentPatch', JSON.stringify(patchResult));
      console.log('💾 DEBUG: Stored patch in sessionStorage');
      
      // Generate a detailed response based on the instruction and changes
      let aiResponse = `I've analyzed your request: "${instruction}"\n\n`;
      
      // Check if we need more information for complex additions
      if (instruction.toLowerCase().includes('add') && (instruction.toLowerCase().includes('internship') || instruction.toLowerCase().includes('experience') || instruction.toLowerCase().includes('project'))) {
        aiResponse += `**I need more details to create a proper entry:**\n\n`;
        aiResponse += `To add this properly, I need:\n`;
        aiResponse += `• **Company/Organization name**\n`;
        aiResponse += `• **Your position/title**\n`;
        aiResponse += `• **Location** (city, state/country)\n`;
        aiResponse += `• **Start and end dates**\n`;
        aiResponse += `• **Key achievements** (with numbers/metrics if possible)\n`;
        aiResponse += `• **Technologies used** (for technical roles)\n\n`;
        aiResponse += `Please provide these details so I can format it exactly like your existing entries.\n\n`;
        aiResponse += `**Current changes prepared:**\n`;
      } else {
        aiResponse += `**What I found:**\n`;
      }
      
      // Analyze the changes and provide detailed explanation
      const additions = patchResult.changes.filter(c => c.type === 'addition');
      const removals = patchResult.changes.filter(c => c.type === 'removal');
      
      aiResponse += `• ${additions.length} additions to make\n`;
      aiResponse += `• ${removals.length} removals to make\n\n`;
      
      // Explain each change in detail
      if (additions.length > 0) {
        aiResponse += `**Additions I'm suggesting:**\n`;
        additions.forEach((change, index) => {
          aiResponse += `${index + 1}. ${change.content.replace(/\\textbf\{([^}]+)\}/g, '$1').replace(/\\/g, '')}\n`;
        });
        aiResponse += `\n`;
      }
      
      if (removals.length > 0) {
        aiResponse += `**Content I'm suggesting to remove:**\n`;
        removals.forEach((change, index) => {
          aiResponse += `${index + 1}. ${change.content.replace(/\\textbf\{([^}]+)\}/g, '$1').replace(/\\/g, '')}\n`;
        });
        aiResponse += `\n`;
      }
      
      // Provide context about the changes
      if (instruction.toLowerCase().includes('name') || instruction.toLowerCase().includes('change name')) {
        aiResponse += `**Why this change:** I'm updating your name as requested. This will appear in the header section of your resume.\n\n`;
      } else if (instruction.toLowerCase().includes('improve') || instruction.toLowerCase().includes('better')) {
        aiResponse += `**Why these changes:** I've identified areas where your resume can be strengthened with more specific achievements, quantified results, and stronger action verbs.\n\n`;
      } else if (instruction.toLowerCase().includes('add') || instruction.toLowerCase().includes('include')) {
        aiResponse += `**Why these additions:** I'm adding relevant content to make your resume more comprehensive and competitive.\n\n`;
      } else if (instruction.toLowerCase().includes('remove') || instruction.toLowerCase().includes('delete')) {
        aiResponse += `**Why these removals:** I'm removing redundant or less impactful content to make your resume more concise and focused.\n\n`;
      } else if (instruction.toLowerCase().includes('format') || instruction.toLowerCase().includes('structure')) {
        aiResponse += `**Why these formatting changes:** I'm improving the structure and presentation to make your resume more professional and easier to read.\n\n`;
      } else {
        aiResponse += `**Why these changes:** I've analyzed your resume and identified specific improvements based on your request.\n\n`;
      }
      
      aiResponse += `**Next steps:** Review each change in the workspace below. You can accept or reject individual changes. When you're ready, click 'Apply accepted' to compile the changes into your resume.`;
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: aiResponse,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, aiMessage]);
      
      // Trigger workspace update
      console.log('📡 DEBUG: Dispatching patchGenerated event');
      window.dispatchEvent(new CustomEvent('patchGenerated', { detail: patchResult }));
      
    } catch (error) {
      console.error('❌ ERROR: Patch generation failed:', error);
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