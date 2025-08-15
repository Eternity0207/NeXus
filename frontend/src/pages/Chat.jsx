import { useState, useRef, useEffect } from 'react';
import { api } from '../api';

export default function Chat() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I\'m **NEXUS AI** — your codebase intelligence assistant.\n\nI can help you understand your code, find functions, explain architecture, and suggest improvements.\n\nIngest a repository first, then ask me anything about it.' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [repoId, setRepoId] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const data = await api.chat(userMsg, repoId || 'default');
      const reply = data?.reply || 'Sorry, I couldn\'t process that request. Make sure the backend services are running.';
      setMessages(prev => [...prev, { role: 'assistant', content: reply }]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Unable to connect to the AI service. Please ensure all backend services are running.' }]);
    }

    setLoading(false);
  };

  const formatContent = (text) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code style="background:rgba(99,102,241,0.15);padding:0.125rem 0.375rem;border-radius:4px;font-family:var(--font-mono);font-size:0.8rem">$1</code>')
      .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre style="background:rgba(0,0,0,0.4);border:1px solid var(--border-subtle);border-radius:8px;padding:0.75rem;margin:0.5rem 0;font-size:0.8rem;overflow-x:auto">$2</pre>')
      .replace(/\n/g, '<br/>');
  };

  const suggestions = [
    'How does authentication work?',
    'Show me the database models',
    'What are the main API endpoints?',
    'Explain the project architecture',
  ];

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">AI Chat</h1>
        <p className="page-subtitle">Ask questions about your codebase — powered by RAG + LLM</p>
      </div>

      <div className="card chat-container">
        {/* Messages */}
        <div className="chat-messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`chat-bubble ${msg.role}`}>
              <div dangerouslySetInnerHTML={{ __html: formatContent(msg.content) }} />
            </div>
          ))}

          {loading && (
            <div className="chat-bubble assistant" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="spinner" style={{ width: 14, height: 14 }} />
              <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Analyzing codebase...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggestions */}
        {messages.length <= 1 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', paddingBottom: '0.75rem' }}>
            {suggestions.map((s) => (
              <button
                key={s}
                className="btn btn-secondary"
                style={{ fontSize: '0.8rem', padding: '0.375rem 0.75rem' }}
                onClick={() => { setInput(s); }}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="chat-input-area">
          <form onSubmit={handleSend}>
            <div className="input-group">
              <input
                className="input"
                type="text"
                placeholder="Ask about your codebase..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
              />
              <button className="btn btn-primary" type="submit" disabled={loading || !input.trim()}>
                Send
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
