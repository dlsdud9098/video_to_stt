import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { CloudArrowUpIcon, DocumentTextIcon, LanguageIcon, CogIcon } from '@heroicons/react/24/outline';
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/solid';

const API_URL = 'http://localhost:8000';

interface ProcessingTask {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  result?: {
    subtitle?: string;
    english_subtitle?: string;
  };
  error?: string;
}

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [task, setTask] = useState<ProcessingTask | null>(null);
  const [modelSize, setModelSize] = useState('base');
  const [language, setLanguage] = useState('');
  const [subtitleFormat, setSubtitleFormat] = useState('srt');
  const [translateEnglish, setTranslateEnglish] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    if (taskId) {
      const websocket = new WebSocket(`ws://localhost:8000/ws/${taskId}`);
      
      websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setTask(data);
      };

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      setWs(websocket);

      return () => {
        websocket.close();
      };
    }
  }, [taskId]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      if (file.type.startsWith('video/')) {
        setSelectedFile(file);
      }
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setSelectedFile(files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const uploadResponse = await axios.post(`${API_URL}/api/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const { task_id } = uploadResponse.data;
      setTaskId(task_id);

      await axios.post(`${API_URL}/api/process/${task_id}`, {
        model_size: modelSize,
        language: language || null,
        subtitle_format: subtitleFormat,
        translate_english: translateEnglish,
      });
    } catch (error) {
      console.error('Error uploading file:', error);
      alert('Failed to upload file');
    }
  };

  const handleDownload = (filename: string) => {
    window.open(`${API_URL}/api/download/${filename}`, '_blank');
  };

  const resetState = () => {
    setSelectedFile(null);
    setTaskId(null);
    setTask(null);
    if (ws) {
      ws.close();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold text-gray-800 mb-2 text-center">
            Video to Subtitle Converter
          </h1>
          <p className="text-gray-600 text-center mb-8">
            Upload a video and get subtitles using AI-powered speech recognition
          </p>

          {!taskId ? (
            <div className="bg-white rounded-lg shadow-xl p-8">
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  isDragging
                    ? 'border-indigo-500 bg-indigo-50'
                    : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <CloudArrowUpIcon className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                <p className="text-lg mb-2 text-gray-700">
                  {selectedFile ? selectedFile.name : 'Drag and drop your video here'}
                </p>
                <p className="text-sm text-gray-500 mb-4">or</p>
                <label className="inline-block">
                  <input
                    type="file"
                    accept="video/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <span className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 cursor-pointer transition-colors">
                    Choose File
                  </span>
                </label>
              </div>

              {selectedFile && (
                <div className="mt-8 space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="flex items-center text-sm font-medium text-gray-700 mb-2">
                        <CogIcon className="w-4 h-4 mr-1" />
                        Model Size
                      </label>
                      <select
                        value={modelSize}
                        onChange={(e) => setModelSize(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="tiny">Tiny (Fastest)</option>
                        <option value="base">Base (Balanced)</option>
                        <option value="small">Small</option>
                        <option value="medium">Medium</option>
                        <option value="large">Large (Most Accurate)</option>
                      </select>
                    </div>

                    <div>
                      <label className="flex items-center text-sm font-medium text-gray-700 mb-2">
                        <LanguageIcon className="w-4 h-4 mr-1" />
                        Language (Optional)
                      </label>
                      <input
                        type="text"
                        value={language}
                        onChange={(e) => setLanguage(e.target.value)}
                        placeholder="Auto-detect"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="flex items-center text-sm font-medium text-gray-700 mb-2">
                        <DocumentTextIcon className="w-4 h-4 mr-1" />
                        Subtitle Format
                      </label>
                      <select
                        value={subtitleFormat}
                        onChange={(e) => setSubtitleFormat(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="srt">SRT</option>
                        <option value="json">JSON</option>
                        <option value="txt">Text</option>
                      </select>
                    </div>

                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        id="translate"
                        checked={translateEnglish}
                        onChange={(e) => setTranslateEnglish(e.target.checked)}
                        className="mr-2"
                      />
                      <label htmlFor="translate" className="text-sm font-medium text-gray-700">
                        Also translate to English
                      </label>
                    </div>
                  </div>

                  <button
                    onClick={handleUpload}
                    className="w-full py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold rounded-lg hover:from-indigo-700 hover:to-purple-700 transition-all transform hover:scale-[1.02]"
                  >
                    Process Video
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow-xl p-8">
              <div className="space-y-6">
                {task && (
                  <>
                    <div className="flex items-center justify-between">
                      <h2 className="text-2xl font-semibold text-gray-800">Processing Status</h2>
                      {task.status === 'completed' && (
                        <CheckCircleIcon className="w-8 h-8 text-green-500" />
                      )}
                      {task.status === 'failed' && (
                        <XCircleIcon className="w-8 h-8 text-red-500" />
                      )}
                    </div>

                    <div className="space-y-4">
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-600">Progress</span>
                          <span className="text-gray-800 font-medium">{task.progress}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-3">
                          <div
                            className="bg-gradient-to-r from-indigo-500 to-purple-500 h-3 rounded-full transition-all duration-500"
                            style={{ width: `${task.progress}%` }}
                          />
                        </div>
                      </div>

                      <div className="bg-gray-50 rounded-lg p-4">
                        <p className="text-gray-700">{task.message}</p>
                      </div>

                      {task.status === 'completed' && task.result && (
                        <div className="space-y-3">
                          <h3 className="text-lg font-semibold text-gray-800">Download Files</h3>
                          {task.result.subtitle && (
                            <button
                              onClick={() => handleDownload(task.result.subtitle!)}
                              className="w-full py-2 px-4 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                            >
                              Download Subtitles
                            </button>
                          )}
                          {task.result.english_subtitle && (
                            <button
                              onClick={() => handleDownload(task.result.english_subtitle!)}
                              className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                            >
                              Download English Subtitles
                            </button>
                          )}
                        </div>
                      )}

                      {task.status === 'failed' && task.error && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                          <p className="text-red-700">Error: {task.error}</p>
                        </div>
                      )}

                      {(task.status === 'completed' || task.status === 'failed') && (
                        <button
                          onClick={resetState}
                          className="w-full py-2 px-4 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                        >
                          Process Another Video
                        </button>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;