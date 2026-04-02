import React, { useState } from 'react';
import './App.css';
import ChatInterface from './components/ChatInterface';
import PDFUpload from './components/PDFUpload';

function App() {
  const [currentPdfId, setCurrentPdfId] = useState(null);
  const [isIndexing, setIsIndexing] = useState(false);

  return (
    <div className="virela-app" dir="rtl">
      {/* SIDEBAR - RIGHT SIDE */}
      <aside className="sidebar">
        <div className="logo-area">
          <div className="logo-dot"></div>
          <span>نبض RAG</span>
        </div>

        <PDFUpload 
          onUploadSuccess={(id) => setCurrentPdfId(id)} 
          setIsIndexing={setIsIndexing} 
        />

        <div className="status-panel">
          <p className="status-label">حالة النظام:</p>
          <div className={`ekg-line ${isIndexing ? 'active' : ''}`}></div>
          <p className="connection-status">● متصل بـ OpenRouter</p>
          <p className={`upload-status ${currentPdfId ? 'ready' : 'waiting'}`}>
            {currentPdfId ? `● تم تحميل الملف (${currentPdfId})` : '● لم يتم تحميل PDF بعد'}
          </p>
        </div>
      </aside>

      {/* MAIN CHAT - LEFT SIDE */}
      <main className="chat-container">
        <ChatInterface pdfId={currentPdfId} />
      </main>
    </div>
  );
}

export default App;