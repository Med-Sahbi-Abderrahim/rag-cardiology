import React, { useState } from 'react';
const API_URL = import.meta.env.VITE_API_URL;

const ChatInterface = ({ pdfId }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);

  const handleSendMessage = async () => {
    if (!input || !pdfId || isThinking) return;

    const history = messages.slice(-4).map(msg => ({
      role: msg.role,
      content: msg.content
    }));
    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsThinking(true);

    try {
      const response = await fetch(`${API_URL}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: input, pdf_id: pdfId, history }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || data?.error || 'Chat request failed');
      }
      
      setMessages(prev => [...prev, { 
        role: 'ai', 
        content: data?.answer || 'ما لقيتش جواب حالياً.',
        sources: data?.sources || []
      }]);
    } catch (error) {
      console.error("Chat failed", error);
      setMessages(prev => [...prev, {
        role: 'ai',
        content: 'صار مشكل في الاتصال بالسيرفر. جرّب مرة أخرى.',
        sources: []
      }]);
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <div className="chat-wrapper">
      <div className="chat-history">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}-msg`}>
            <div className="msg-text">{msg.content}</div>
          </div>
        ))}
        {isThinking && (
          <div className="message ai-msg thinking-msg">
              <div className="msg-text">🔄 يعيد صياغة السؤال ويبحث...</div>
          </div>
      )}
      </div>

      <div className="input-area">
        <input 
          value={input} 
          onChange={(e) => setInput(e.target.value)}
          placeholder="اسأل أي سؤال طبي بالدارجة..."
          onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
          disabled={!pdfId || isThinking}
        />
        <button className="send-btn" onClick={handleSendMessage} disabled={!pdfId || isThinking}>
          {isThinking ? (
              <span className="btn-dots">
                  <span className="btn-dot"></span>
                  <span className="btn-dot"></span>
                  <span className="btn-dot"></span>
              </span>
          ) : '←'}
      </button>
      </div>
    </div>
  );
};

export default ChatInterface;
