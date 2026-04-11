import React, { useState, useEffect } from 'react';
import './App.css';
import ChatInterface from './components/ChatInterface';
import PDFUpload from './components/PDFUpload';
const API_URL = import.meta.env.VITE_API_URL; 
function App() {
  const [currentPdfId, setCurrentPdfId] = useState(null);
  const [isIndexing, setIsIndexing] = useState(false);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await fetch(`${API_URL}/status`);
        const data = await response.json();
        if (data.has_index) {
          setCurrentPdfId("loaded");
        }
      } catch (e) {
        console.warn("Backend not reachable on startup");
      }
    };
    checkStatus();
  }, []);

  return (
    <div className="virela-app" dir="rtl">
      {/* SIDEBAR - RIGHT SIDE */}
      <aside className="sidebar">
        <div className="logo-area">
          <div className="logo-dot"></div>
          <span>QalbAI</span>
        </div>

        <PDFUpload 
          onUploadSuccess={(id) => setCurrentPdfId(id)} 
          setIsIndexing={setIsIndexing} 
        />

        <div className="status-panel">
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
