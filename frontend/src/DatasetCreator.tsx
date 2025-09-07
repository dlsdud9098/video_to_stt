import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LinkIcon, BeakerIcon, EyeIcon, CpuChipIcon } from '@heroicons/react/24/outline';
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/solid';

const API_URL = 'http://localhost:8000';

interface DatasetTask {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  result?: {
    dataset_file?: string;
    items_count?: number;
    video_title?: string;
    video_duration?: number;
  };
  error?: string;
}

function DatasetCreator() {
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [useOcr, setUseOcr] = useState(false);
  const [modelSize, setModelSize] = useState('large-v3');
  const [taskId, setTaskId] = useState<string | null>(null);
  const [task, setTask] = useState<DatasetTask | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    if (taskId) {
      const websocket = new WebSocket(`ws://localhost:8000/ws/${taskId}`);
      
      websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setTask(data);
        if (data.status === 'completed' || data.status === 'failed') {
          setIsProcessing(false);
        }
      };

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsProcessing(false);
      };

      setWs(websocket);

      return () => {
        websocket.close();
      };
    }
  }, [taskId]);

  const handleCreateDataset = async () => {
    if (!youtubeUrl) {
      alert('Please enter a YouTube URL');
      return;
    }

    setIsProcessing(true);

    try {
      const response = await axios.post(`${API_URL}/api/dataset/create`, {
        youtube_url: youtubeUrl,
        youtube_api_key: apiKey || null,
        use_ocr: useOcr,
        model_size: modelSize,
      });

      setTaskId(response.data.task_id);
    } catch (error) {
      console.error('Error creating dataset:', error);
      alert('Failed to start dataset creation');
      setIsProcessing(false);
    }
  };

  const handleDownload = (filename: string) => {
    window.open(`${API_URL}/api/dataset/download/${filename}`, '_blank');
  };

  const resetState = () => {
    setYoutubeUrl('');
    setTaskId(null);
    setTask(null);
    setIsProcessing(false);
    if (ws) {
      ws.close();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-100">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold text-gray-800 mb-2 text-center">
            YouTube Dataset Creator
          </h1>
          <p className="text-gray-600 text-center mb-8">
            Create AI training datasets from YouTube videos with comments
          </p>

          {!taskId ? (
            <div className="bg-white rounded-lg shadow-xl p-8">
              <div className="space-y-6">
                <div>
                  <label className="flex items-center text-sm font-medium text-gray-700 mb-2">
                    <LinkIcon className="w-4 h-4 mr-1" />
                    YouTube URL
                  </label>
                  <input
                    type="text"
                    value={youtubeUrl}
                    onChange={(e) => setYoutubeUrl(e.target.value)}
                    placeholder="https://youtube.com/watch?v=... or https://youtube.com/shorts/..."
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>

                <div>
                  <label className="flex items-center text-sm font-medium text-gray-700 mb-2">
                    <BeakerIcon className="w-4 h-4 mr-1" />
                    YouTube API Key (Optional for comments)
                  </label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="Your YouTube Data API v3 key"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Get your API key from{' '}
                    <a
                      href="https://console.cloud.google.com/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-purple-600 hover:underline"
                    >
                      Google Cloud Console
                    </a>
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="flex items-center text-sm font-medium text-gray-700 mb-2">
                      <CpuChipIcon className="w-4 h-4 mr-1" />
                      Whisper Model Size
                    </label>
                    <select
                      value={modelSize}
                      onChange={(e) => setModelSize(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    >
                      <option value="tiny">Tiny (Fastest)</option>
                      <option value="base">Base</option>
                      <option value="small">Small</option>
                      <option value="medium">Medium</option>
                      <option value="large">Large</option>
                      <option value="large-v2">Large-v2</option>
                      <option value="large-v3">Large-v3 (Best)</option>
                    </select>
                  </div>

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="useOcr"
                      checked={useOcr}
                      onChange={(e) => setUseOcr(e.target.checked)}
                      className="mr-2"
                    />
                    <label htmlFor="useOcr" className="flex items-center text-sm font-medium text-gray-700">
                      <EyeIcon className="w-4 h-4 mr-1" />
                      Enable OCR Analysis
                    </label>
                  </div>
                </div>

                <button
                  onClick={handleCreateDataset}
                  disabled={isProcessing || !youtubeUrl}
                  className="w-full py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isProcessing ? 'Processing...' : 'Create Dataset'}
                </button>
              </div>
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
                            className="bg-gradient-to-r from-purple-500 to-pink-500 h-3 rounded-full transition-all duration-500"
                            style={{ width: `${task.progress}%` }}
                          />
                        </div>
                      </div>

                      <div className="bg-gray-50 rounded-lg p-4">
                        <p className="text-gray-700">{task.message}</p>
                      </div>

                      {task.status === 'completed' && task.result && (
                        <div className="space-y-3">
                          <h3 className="text-lg font-semibold text-gray-800">Dataset Created!</h3>
                          
                          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                            <p className="text-sm text-gray-700">
                              <strong>Video:</strong> {task.result.video_title}
                            </p>
                            <p className="text-sm text-gray-700">
                              <strong>Duration:</strong> {task.result.video_duration} seconds
                            </p>
                            <p className="text-sm text-gray-700">
                              <strong>Dataset Items:</strong> {task.result.items_count}
                            </p>
                          </div>

                          {task.result.dataset_file && (
                            <button
                              onClick={() => handleDownload(task.result.dataset_file!)}
                              className="w-full py-2 px-4 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                            >
                              Download Dataset (JSONL)
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
                          Create Another Dataset
                        </button>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          <div className="mt-8 bg-white rounded-lg shadow-xl p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">How it works</h3>
            <ol className="list-decimal list-inside space-y-2 text-gray-600">
              <li>Enter a YouTube video URL (regular or shorts)</li>
              <li>Optionally add YouTube API key for comment collection</li>
              <li>Choose Whisper model size (larger = more accurate)</li>
              <li>Enable OCR for text extraction from video frames</li>
              <li>Click "Create Dataset" and wait for processing</li>
              <li>Download the generated JSONL dataset file</li>
            </ol>
            <div className="mt-4 p-4 bg-purple-50 rounded-lg">
              <p className="text-sm text-gray-700">
                <strong>Dataset Format:</strong> Each item contains video analysis (transcription, metadata) as input 
                and top comments as output, perfect for training AI models.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DatasetCreator;