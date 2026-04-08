import React from 'react';
const API_URL = import.meta.env.VITE_API_URL;
const PDFUpload = ({ onUploadSuccess, setIsIndexing }) => {
  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsIndexing(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail || data?.error || 'Upload failed');
      }

      if (!data.pdf_id){
        throw new Error('Upload failed');
      }

      onUploadSuccess(data.pdf_id);
      
    } catch (error) {
      console.error('Upload failed', error);
    } finally {
      setIsIndexing(false);
    }
  };

  return (
    <div className="upload-zone">
      <input type="file" id="pdf-input" hidden onChange={handleFileChange} accept=".pdf" />
      <label htmlFor="pdf-input" className="upload-label">
        <div className="upload-icon">PDF</div>
        <p>اسحب ملف الـ PDF هنا</p>
        <span className="upload-subtext">Cardiology Guides Only</span>
      </label>
    </div>
  );
};

export default PDFUpload;