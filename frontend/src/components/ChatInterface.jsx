import React, { useState } from 'react';

const ChatInterface = ({ pdfId }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);

  const handleSendMessage = async () => {
    if (!input || !pdfId || isThinking) return;

    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsThinking(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: input, pdf_id: pdfId }),
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
            {msg.sources && (
              <div className="sources-row">
                {msg.sources.map((src, j) => (
                  <div key={j} className="source-card">
                    <span className="page-tag">ص : {src.page}</span>
                    <p className="source-snippet">{src.text.substring(0, 80)}...</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {isThinking && (
          <div className="message ai-msg thinking-msg">
            <div className="msg-text">...يفكّر</div>
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
          {isThinking ? '...' : '←'}
        </button>
      </div>
    </div>
  );
};

export default ChatInterface;