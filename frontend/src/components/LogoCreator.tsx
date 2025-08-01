"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Upload, Download, Palette, Type, Sparkles, RefreshCw, Heart, History, Settings, Zap, Image, FileImage, AlertCircle, CheckCircle } from 'lucide-react';

// Updated type definitions to match backend response
interface GeneratedLogo {
  id: string;
  name: string;
  image_url: string;
  local_path?: string;
  style_info: {
    style: string;
    variation: number;
    ai_model: string;
    quality: string;
    industry: string;
    generation_method: string;
  };
  colors_used: string[];
  generation_time: number;
  confidence_score: number;
  prompt_used: string;
  dalle_revised_prompt?: string;
}

interface GenerationResponse {
  success: boolean;
  data: {
    logos: GeneratedLogo[];
    generation_stats: {
      total_time: number;
      logos_generated: number;
      ai_model: string;
      quality: string;
      approximate_cost: string;
      real_ai_generated: boolean;
    };
  };
}

const LogoCreator = () => {
  const [businessName, setBusinessName] = useState('');
  const [businessType, setBusinessType] = useState('');
  const [businessDescription, setBusinessDescription] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [selectedStyle, setSelectedStyle] = useState('modern');
  const [selectedColors, setSelectedColors] = useState(['#3B82F6', '#1E40AF']);
  const [variations] = useState(2);
  const [generatedLogos, setGeneratedLogos] = useState<GeneratedLogo[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState('generate');
  const [favorites, setFavorites] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [downloadingLogo, setDownloadingLogo] = useState<string | null>(null);
  const [generationStats, setGenerationStats] = useState<any>(null);
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);

  // Backend API base URL
  const API_BASE_URL = 'http://localhost:8000';

  const businessTypes = [
    'Technology', 'Healthcare', 'Finance', 'Retail', 'Food & Beverage',
    'Education', 'Real Estate', 'Consulting', 'Creative Services', 'Manufacturing'
  ];

  const logoStyles = [
    { id: 'modern', name: 'Modern', desc: 'Clean, minimalist design' },
    { id: 'vintage', name: 'Vintage', desc: 'Classic, retro aesthetic' },
    { id: 'bold', name: 'Bold', desc: 'Strong, impactful design' },
    { id: 'elegant', name: 'Elegant', desc: 'Sophisticated and refined' },
    { id: 'playful', name: 'Playful', desc: 'Fun and creative' },
    { id: 'professional', name: 'Professional', desc: 'Corporate and trustworthy' }
  ];

  const colorPalettes = [
    ['#3B82F6', '#1E40AF'], // Blue
    ['#EF4444', '#DC2626'], // Red
    ['#10B981', '#059669'], // Green
    ['#F59E0B', '#D97706'], // Orange
    ['#8B5CF6', '#7C3AED'], // Purple
    ['#6B7280', '#374151'], // Gray
    ['#EC4899', '#BE185D'], // Pink
    ['#14B8A6', '#0D9488'], // Teal
  ];

  // Check backend connection on component mount
  useEffect(() => {
    checkBackendConnection();
  }, []);

  const checkBackendConnection = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/`);
      const data = await response.json();
      
      if (data.status === 'healthy') {
        setBackendConnected(true);
        console.log('✅ Backend connected:', data);
      } else {
        setBackendConnected(false);
      }
    } catch (error) {
      console.error('❌ Backend connection failed:', error);
      setBackendConnected(false);
    }
  };

  const generateLogos = async () => {
    if (!businessName.trim()) {
      setError('Please enter a business name');
      return;
    }

    if (!businessType) {
      setError('Please select a business type');
      return;
    }

    if (!backendConnected) {
      setError('Backend is not connected. Please check if the server is running on http://localhost:8000');
      return;
    }

    setIsGenerating(true);
    setError(null);
    setGenerationStats(null);
    
    try {
      // Prepare request payload matching backend schema
      const requestPayload = {
        business_info: {
          name: businessName,
          industry: businessType,
          description: businessDescription || undefined,
          target_audience: targetAudience || undefined
        },
        style: {
          style_type: selectedStyle,
          color_palette: selectedColors,
          font_preference: "sans-serif"
        },
        variations: variations
      };

      console.log('🚀 Sending request to backend:', requestPayload);

      const response = await fetch(`${API_BASE_URL}/api/v1/generate-logos`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestPayload)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data: GenerationResponse = await response.json();
      
      if (data.success) {
        setGeneratedLogos(data.data.logos);
        setGenerationStats(data.data.generation_stats);
        console.log('✅ Logos generated successfully:', data.data.generation_stats);
      } else {
        throw new Error('Generation failed');
      }
      
    } catch (error: any) {
      console.error('❌ Error generating logos:', error);
      
      if (error.message.includes('429')) {
        setError('Rate limit reached. Please wait before generating more logos.');
      } else if (error.message.includes('500')) {
        setError('Server error. Please check if OpenAI API key is configured.');
      } else if (error.message.includes('Failed to fetch')) {
        setError('Cannot connect to backend. Please ensure the server is running on http://localhost:8000');
        setBackendConnected(false);
      } else {
        setError(`Failed to generate logos: ${error.message}`);
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const toggleFavorite = (logoId: string) => {
    setFavorites(prev =>
      prev.includes(logoId)
        ? prev.filter(id => id !== logoId)
        : [...prev, logoId]
    );
  };

  const downloadLogo = async (logo: GeneratedLogo, format: 'png' | 'jpg') => {
    try {
      setDownloadingLogo(logo.id + format);
      
      // First try backend download endpoint
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/logo/${logo.id}/download/${format}`);
        
        if (response.ok) {
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          
          const element = document.createElement('a');
          element.href = url;
          element.download = `${businessName || 'logo'}-${logo.id}.${format}`;
          document.body.appendChild(element);
          element.click();
          document.body.removeChild(element);
          URL.revokeObjectURL(url);
          return;
        }
      } catch (backendError) {
        console.warn('Backend download failed, trying direct download:', backendError);
      }
      
      // Fallback to direct download from DALL-E URL
      const response = await fetch(logo.image_url, { mode: 'cors' });
      if (!response.ok) {
        throw new Error(`Direct download failed: ${response.statusText}`);
      }
      
      const blob = await response.blob();
      
      // Convert to desired format if needed
      if (format === 'jpg' && blob.type.includes('png')) {
        // Convert PNG to JPG using canvas
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        const convertedBlob = await new Promise<Blob>((resolve, reject) => {
          img.onload = () => {
            canvas.width = img.width;
            canvas.height = img.height;
            
            // Fill with white background for JPG
            ctx!.fillStyle = 'white';
            ctx!.fillRect(0, 0, canvas.width, canvas.height);
            ctx!.drawImage(img, 0, 0);
            
            canvas.toBlob((result) => {
              if (result) resolve(result);
              else reject(new Error('Canvas conversion failed'));
            }, 'image/jpeg', 0.9);
          };
          
          img.onerror = () => reject(new Error('Image load failed'));
          img.src = URL.createObjectURL(blob);
        });
        
        const url = URL.createObjectURL(convertedBlob);
        const element = document.createElement('a');
        element.href = url;
        element.download = `${businessName || 'logo'}-${logo.id}.${format}`;
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
        URL.revokeObjectURL(url);
      } else {
        // Direct download
        const url = URL.createObjectURL(blob);
        const element = document.createElement('a');
        element.href = url;
        element.download = `${businessName || 'logo'}-${logo.id}.${format}`;
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
        URL.revokeObjectURL(url);
      }
      
    } catch (error: any) {
      console.error('Download failed:', error);
      setError(`Failed to download ${format.toUpperCase()}: ${error.message}. The image URL may have expired.`);
    } finally {
      setDownloadingLogo(null);
    }
  };

  const downloadFromUrl = async (logo: GeneratedLogo) => {
    try {
      setDownloadingLogo(logo.id + 'url');
      
      // Download directly from DALL-E URL
      const response = await fetch(logo.image_url);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      
      const element = document.createElement('a');
      element.href = url;
      element.download = `${businessName || 'logo'}-${logo.id}-dalle.png`;
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
      URL.revokeObjectURL(url);
      
    } catch (error: any) {
      console.error('Direct download failed:', error);
      setError(`Failed to download from URL: ${error.message}`);
    } finally {
      setDownloadingLogo(null);
    }
  };

  const submitFeedback = async (logoId: string, rating: number, feedbackText?: string) => {
    try {
      const payload = {
        logo_id: logoId,
        rating: rating,
        feedback_text: feedbackText
      };
      
      const response = await fetch(`${API_BASE_URL}/api/v1/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });
      
      if (response.ok) {
        console.log('✅ Feedback submitted successfully');
      }
    } catch (error) {
      console.error('❌ Feedback submission failed:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="border-b border-white/10 backdrop-blur-sm bg-black/20">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-500 rounded-xl flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">LogoAI</h1>
                <p className="text-sm text-gray-400">Real AI-Powered Logo Generation with DALL-E 3</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {/* Backend Status Indicator */}
              <div className="flex items-center space-x-2">
                {backendConnected === null ? (
                  <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
                ) : backendConnected ? (
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                ) : (
                  <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                )}
                <span className="text-xs text-gray-400">
                  {backendConnected === null ? 'Checking...' : backendConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              
              <button 
                onClick={checkBackendConnection}
                className="px-3 py-1 bg-white/10 text-white rounded-lg hover:bg-white/20 transition-colors text-sm"
              >
                Reconnect
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-lg flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-red-200">{error}</p>
              <button 
                onClick={() => setError(null)}
                className="mt-2 text-sm text-red-300 hover:text-red-100 underline"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* Success/Stats Display */}
        {generationStats && (
          <div className="mb-6 p-4 bg-green-500/20 border border-green-500/30 rounded-lg flex items-start space-x-3">
            <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-green-200 font-medium">
                Successfully generated {generationStats.logos_generated} AI logos using {generationStats.ai_model}
              </p>
              <p className="text-sm text-green-300 mt-1">
                Generation time: {generationStats.total_time.toFixed(1)}s • 
                Cost: {generationStats.approximate_cost} • 
                Quality: {generationStats.quality}
              </p>
            </div>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex space-x-6 mb-8 border-b border-white/10">
          {[
            { id: 'generate', name: 'Generate', icon: Zap },
            { id: 'history', name: 'History', icon: History },
            { id: 'favorites', name: 'Favorites', icon: Heart }
          ].map(tab => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-400 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-white'
              }`}
            >
              <tab.icon className="w-5 h-5" />
              <span className="font-medium">{tab.name}</span>
            </button>
          ))}
        </div>

        {activeTab === 'generate' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Input Panel */}
            <div className="lg:col-span-1">
              <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10">
                <h2 className="text-xl font-semibold text-white mb-6 flex items-center">
                  <Settings className="w-5 h-5 mr-2" />
                  Logo Settings
                </h2>

                <div className="space-y-6">
                  {/* Business Name */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Business Name *
                    </label>
                    <input
                      type="text"
                      value={businessName}
                      onChange={(e) => setBusinessName(e.target.value)}
                      placeholder="Enter your business name"
                      className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  {/* Business Type */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Industry *
                    </label>
                    <select
                      value={businessType}
                      onChange={(e) => setBusinessType(e.target.value)}
                      className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="" className="bg-gray-800">Select industry</option>
                      {businessTypes.map(type => (
                        <option key={type} value={type} className="bg-gray-800">{type}</option>
                      ))}
                    </select>
                  </div>

                  {/* Business Description */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Business Description
                    </label>
                    <textarea
                      value={businessDescription}
                      onChange={(e) => setBusinessDescription(e.target.value)}
                      placeholder="Describe what your business does (optional)"
                      className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent h-20 resize-none"
                      maxLength={200}
                    />
                    <p className="text-xs text-gray-400 mt-1">{businessDescription.length}/200 characters</p>
                  </div>

                  {/* Target Audience */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Target Audience
                    </label>
                    <input
                      type="text"
                      value={targetAudience}
                      onChange={(e) => setTargetAudience(e.target.value)}
                      placeholder="e.g., young professionals, families"
                      className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  {/* Style Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-3">
                      Logo Style
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      {logoStyles.map(style => (
                        <button
                          key={style.id}
                          type="button"
                          onClick={() => setSelectedStyle(style.id)}
                          className={`p-3 rounded-lg border-2 transition-all ${
                            selectedStyle === style.id
                              ? 'border-blue-400 bg-blue-400/20 text-blue-400'
                              : 'border-white/20 bg-white/5 text-gray-300 hover:border-white/40'
                          }`}
                        >
                          <div className="font-medium">{style.name}</div>
                          <div className="text-xs opacity-75">{style.desc}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Color Palette */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-3">
                      <Palette className="w-4 h-4 inline mr-2" />
                      Color Palette
                    </label>
                    <div className="grid grid-cols-4 gap-3">
                      {colorPalettes.map((palette, index) => (
                        <button
                          key={`palette-${index}-${palette[0]}-${palette[1]}`}
                          type="button"
                          onClick={() => setSelectedColors(palette)}
                          className={`h-12 rounded-lg border-2 flex ${
                            JSON.stringify(selectedColors) === JSON.stringify(palette)
                              ? 'border-white scale-105'
                              : 'border-white/20 hover:border-white/40'
                          } transition-all`}
                        >
                          <div className="flex-1 rounded-l-lg" style={{ backgroundColor: palette[0] }}></div>
                          <div className="flex-1 rounded-r-lg" style={{ backgroundColor: palette[1] }}></div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Generate Button */}
                  <button
                    type="button"
                    onClick={generateLogos}
                    disabled={isGenerating || !businessName.trim() || !backendConnected}
                    className="w-full py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg font-semibold hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center space-x-2"
                  >
                    {isGenerating ? (
                      <>
                        <RefreshCw className="w-5 h-5 animate-spin" />
                        <span>Generating with DALL-E 3...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-5 h-5" />
                        <span>Generate Real AI Logos</span>
                      </>
                    )}
                  </button>
                  
                  {!backendConnected && (
                    <p className="text-xs text-red-400 text-center">
                      Backend disconnected. Please start the server.
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Results Panel */}
            <div className="lg:col-span-2">
              <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10 min-h-96">
                <h2 className="text-xl font-semibold text-white mb-6">
                  AI Generated Logos
                  {generationStats && (
                    <span className="text-sm text-gray-400 ml-2">
                      ({generationStats.ai_model} • {generationStats.quality})
                    </span>
                  )}
                </h2>

                {generatedLogos.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                    <Sparkles className="w-16 h-16 mb-4 opacity-50" />
                    <p className="text-lg mb-2">Ready to create your AI logo?</p>
                    <p className="text-sm text-center">
                      Enter your business details and click "Generate Real AI Logos" to see DALL-E 3 powered designs
                    </p>
                    <p className="text-xs text-center mt-2 text-yellow-400">
                      💰 Each generation costs ~$0.04-0.08 using OpenAI credits
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {generatedLogos.map((logo) => (
                      <div key={logo.id} className="p-4 bg-white/5 border border-white/10 rounded-lg">
                        {/* AI Generated Image */}
                        <div className="w-full h-48 flex items-center justify-center bg-white rounded-lg mb-4 overflow-hidden">
                          <img 
                            src={logo.image_url} 
                            alt={logo.name}
                            className="max-w-full max-h-full object-contain"
                            crossOrigin="anonymous"
                            onLoad={(e) => {
                              console.log('✅ Image loaded successfully:', logo.image_url);
                            }}
                            onError={(e) => {
                              console.error('❌ Image load failed:', logo.image_url);
                              const target = e.currentTarget;
                              
                              // Try to reload once
                              if (!target.dataset.retried) {
                                target.dataset.retried = 'true';
                                setTimeout(() => {
                                  target.src = logo.image_url + '?retry=' + Date.now();
                                }, 1000);
                                return;
                              }
                              
                              // Show error placeholder
                              target.src = 'data:image/svg+xml;base64,' + btoa(`
                                <svg width="400" height="200" xmlns="http://www.w3.org/2000/svg">
                                  <rect width="400" height="200" fill="#f3f4f6"/>
                                  <text x="200" y="90" font-family="Arial" font-size="16" fill="#9ca3af" text-anchor="middle">
                                    Image Load Failed
                                  </text>
                                  <text x="200" y="110" font-family="Arial" font-size="12" fill="#9ca3af" text-anchor="middle">
                                    DALL-E URL may have expired
                                  </text>
                                  <text x="200" y="130" font-family="Arial" font-size="10" fill="#9ca3af" text-anchor="middle">
                                    Try generating new logos
                                  </text>
                                </svg>
                              `);
                            }}
                          />
                        </div>
                        
                        {/* Logo Details */}
                        <div>
                          <h3 className="text-lg font-semibold text-white mb-2">{logo.name}</h3>
                          <div className="text-sm text-gray-400 mb-2 space-y-1">
                            <p>Style: {logo.style_info.style} • Variation {logo.style_info.variation}</p>
                            <p>AI Model: {logo.style_info.ai_model} • Quality: {logo.style_info.quality}</p>
                            <p>Confidence: {(logo.confidence_score * 100).toFixed(0)}% • Time: {logo.generation_time.toFixed(1)}s</p>
                          </div>
                          
                          {/* URL Info for Debugging */}
                          <div className="mb-3 p-2 bg-black/20 rounded text-xs">
                            <p className="text-gray-400 mb-1">Image URL:</p>
                            <p className="text-blue-400 break-all">{logo.image_url}</p>
                            <p className="text-gray-500 mt-1">
                              Status: {logo.image_url ? 'URL Available' : 'No URL'} • 
                              Local: {logo.local_path ? 'Saved' : 'Not Saved'}
                            </p>
                          </div>
                          {logo.dalle_revised_prompt && (
                            <details className="mb-3">
                              <summary className="text-xs text-blue-400 cursor-pointer hover:text-blue-300">
                                View DALL-E Prompt
                              </summary>
                              <p className="text-xs text-gray-400 mt-1 p-2 bg-black/20 rounded">
                                {logo.dalle_revised_prompt}
                              </p>
                            </details>
                          )}
                          
                          {/* Color Swatches */}
                          <div className="flex gap-2 mb-4">
                            {logo.colors_used.map((color, i) => (
                              <div
                                key={i}
                                className="w-6 h-6 rounded-full border border-white/20"
                                style={{ backgroundColor: color }}
                                title={color}
                              />
                            ))}
                          </div>

                          {/* Action Buttons */}
                          <div className="flex gap-2 flex-wrap">
                            <button
                              type="button"
                              onClick={() => toggleFavorite(logo.id)}
                              className={`px-3 py-2 rounded-lg transition-colors flex items-center ${
                                favorites.includes(logo.id)
                                  ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                                  : 'bg-white/10 text-gray-300 border border-white/20 hover:bg-white/20'
                              }`}
                            >
                              <Heart className={`w-4 h-4 ${favorites.includes(logo.id) ? 'fill-current' : ''}`} />
                            </button>
                            
                            {/* Direct Download from DALL-E URL */}
                            <button
                              type="button"
                              onClick={() => downloadFromUrl(logo)}
                              disabled={downloadingLogo === logo.id + 'url'}
                              className="px-3 py-2 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-lg hover:bg-blue-500/30 transition-colors disabled:opacity-50 flex items-center gap-1"
                            >
                              {downloadingLogo === logo.id + 'url' ? (
                                <RefreshCw className="w-4 h-4 animate-spin" />
                              ) : (
                                <Download className="w-4 h-4" />
                              )}
                              <span className="text-xs">Original</span>
                            </button>
                            
                            {/* PNG Download via Backend */}
                            <button
                              type="button"
                              onClick={() => downloadLogo(logo, 'png')}
                              disabled={downloadingLogo === logo.id + 'png'}
                              className="px-3 py-2 bg-green-500/20 text-green-400 border border-green-500/30 rounded-lg hover:bg-green-500/30 transition-colors disabled:opacity-50 flex items-center gap-1"
                            >
                              {downloadingLogo === logo.id + 'png' ? (
                                <RefreshCw className="w-4 h-4 animate-spin" />
                              ) : (
                                <FileImage className="w-4 h-4" />
                              )}
                              <span className="text-xs">PNG</span>
                            </button>
                            
                            {/* JPEG Download via Backend */}
                            <button
                              type="button"
                              onClick={() => downloadLogo(logo, 'jpg')}
                              disabled={downloadingLogo === logo.id + 'jpg'}
                              className="px-3 py-2 bg-orange-500/20 text-orange-400 border border-orange-500/30 rounded-lg hover:bg-orange-500/30 transition-colors disabled:opacity-50 flex items-center gap-1"
                            >
                              {downloadingLogo === logo.id + 'jpg' ? (
                                <RefreshCw className="w-4 h-4 animate-spin" />
                              ) : (
                                <Image className="w-4 h-4" />
                              )}
                              <span className="text-xs">JPG</span>
                            </button>
                            
                            {/* Feedback Button */}
                            <button
                              type="button"
                              onClick={() => submitFeedback(logo.id, 5, 'Great logo!')}
                              className="px-3 py-2 bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded-lg hover:bg-purple-500/30 transition-colors flex items-center gap-1"
                            >
                              <span className="text-xs">👍</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-8 border border-white/10 text-center">
            <History className="w-16 h-16 mx-auto mb-4 text-gray-400" />
            <h2 className="text-xl font-semibold text-white mb-2">Logo History</h2>
            <p className="text-gray-400">Your previously generated DALL-E 3 logos will appear here</p>
          </div>
        )}

        {activeTab === 'favorites' && (
          <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-8 border border-white/10">
            <div className="text-center mb-6">
              <Heart className="w-16 h-16 mx-auto mb-4 text-gray-400" />
              <h2 className="text-xl font-semibold text-white mb-2">Favorite Logos</h2>
              <p className="text-gray-400">Your favorited AI logos will be saved here</p>
            </div>
            
            {favorites.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {generatedLogos
                  .filter(logo => favorites.includes(logo.id))
                  .map((logo) => (
                    <div key={logo.id} className="p-4 bg-white/5 border border-white/10 rounded-lg">
                      <div className="w-full h-32 flex items-center justify-center bg-white rounded-lg mb-3 overflow-hidden">
                        <img 
                          src={logo.image_url} 
                          alt={logo.name}
                          className="max-w-full max-h-full object-contain"
                        />
                      </div>
                      <h3 className="text-white font-medium">{logo.name}</h3>
                      <p className="text-sm text-gray-400">Favorited AI logo</p>
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default LogoCreator;