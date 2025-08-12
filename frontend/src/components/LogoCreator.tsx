"use client"

import React, { useState, useEffect, useCallback } from 'react';
import { Sparkles, RefreshCw, Heart, History, Settings, Zap, Image, FileImage, AlertCircle, CheckCircle, Info, ExternalLink, Cloud, Shield } from 'lucide-react';

// Updated interfaces to match Vertex AI backend
interface LogoResponse {
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
    location?: string;
  };
  colors_used: string[];
  generation_time: number;
  confidence_score: number;
  prompt_used: string;
}

interface GenerationStats {
  total_time: number;
  logos_generated: number;
  ai_model: string;
  quality: string;
  approximate_cost: string;
  real_ai_generated: boolean;
}

interface BusinessInfo {
  name: string;
  industry: string;
  description?: string;
  target_audience?: string;
}

interface LogoStyle {
  style_type: string;
  color_palette: string[];
  font_preference?: string;
}

interface LogoGenerationRequest {
  business_info: BusinessInfo;
  style: LogoStyle;
  variations?: number;
  imagen_model?: string;
}

interface GenerationResponse {
  success: boolean;
  data: {
    logos: LogoResponse[];
    generation_stats: GenerationStats;
  };
}

const VertexLogoCreator = () => {
  // Fix hydration: Initialize with stable values and use useEffect for client-side only data
  const [isClient, setIsClient] = useState(false);
  const [businessName, setBusinessName] = useState('');
  const [businessType, setBusinessType] = useState('');
  const [businessDescription, setBusinessDescription] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [selectedStyle, setSelectedStyle] = useState('modern');
  const [selectedColors, setSelectedColors] = useState(['#3B82F6', '#1E40AF']);
  const [selectedModel, setSelectedModel] = useState('imagegeneration@006');
  const [variations] = useState(2);
  const [generatedLogos, setGeneratedLogos] = useState<LogoResponse[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState('generate');
  const [favorites, setFavorites] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [downloadingLogo, setDownloadingLogo] = useState<string | null>(null);
  const [generationStats, setGenerationStats] = useState<GenerationStats | null>(null);
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);
  const [debugInfo, setDebugInfo] = useState<any>(null);

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

  const vertexModels = [
    { 
      id: 'imagegeneration@006', 
      name: 'Imagen 3 (Latest)', 
      desc: 'Latest Vertex AI Imagen model with improved quality', 
      cost: '$0.030 per image' 
    },
    { 
      id: 'imagegeneration@005', 
      name: 'Imagen 2.5', 
      desc: 'Previous generation model, slightly lower cost', 
      cost: '$0.025 per image' 
    }
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

  // Helper function to safely stringify objects
  const safeStringify = (obj: any): string => {
    try {
      return JSON.stringify(obj, null, 2);
    } catch (e) {
      return `[Unable to stringify: ${String(obj)}]`;
    }
  };

  // Check backend connection function using useCallback to avoid hoisting issues
  const checkBackendConnection = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/`);
      const data = await response.json();
      
      console.log('🔍 Backend response:', data);
      
      // More flexible backend connection check
      if (data.status === 'healthy' || data.status === 'ready') {
        setBackendConnected(true);
        setDebugInfo(data);
        setError(null); // Clear any previous errors
        console.log('✅ Vertex AI backend connected:', data);
      } else if (data.status === 'complete' && data.summary?.ready_for_generation) {
        // Handle diagnostics response format
        setBackendConnected(true);
        setDebugInfo(data);
        setError(null);
        console.log('✅ Vertex AI backend ready (from diagnostics):', data);
      } else {
        setBackendConnected(false);
        setDebugInfo(data);
        console.log('⚠️ Backend responded but not fully ready:', data);
        if (data.status === 'auth_missing') {
          setError('Google Cloud authentication not configured. Please run setup commands.');
        }
      }
    } catch (error) {
      console.error('❌ Backend connection failed:', error);
      setBackendConnected(false);
      setError(`Backend connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }, [API_BASE_URL]);

  // Run diagnostics function using useCallback
  const runDiagnostics = useCallback(async () => {
    try {
      setError(null);
      const response = await fetch(`${API_BASE_URL}/api/v1/diagnostics`);
      
      if (!response.ok) {
        throw new Error(`Diagnostics failed: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('🔍 Diagnostics results:', data);
      setDebugInfo(data);
      
      // Check if the system is ready for generation
      if (data.summary?.ready_for_generation) {
        setBackendConnected(true); // Enable the generate button
        setError(null);
        console.log('✅ Diagnostics passed! System ready for generation');
        alert('✅ Diagnostics passed! Vertex AI system is ready for logo generation.');
      } else if (data.results?.recommendations?.length > 0) {
        setError(`Diagnostics found issues: ${data.results.recommendations.join('. ')}`);
        setBackendConnected(false);
      } else {
        setError('Diagnostics completed but system may not be ready for generation.');
        setBackendConnected(false);
      }
    } catch (error: any) {
      console.error('❌ Diagnostics failed:', error);
      setError(`Failed to run diagnostics: ${error instanceof Error ? error.message : 'Unknown error'}. Backend may not be running.`);
      setBackendConnected(false);
    }
  }, [API_BASE_URL]);

  // Fix hydration: Ensure client-side only rendering for dynamic content
  useEffect(() => {
    setIsClient(true);
    checkBackendConnection();
  }, [checkBackendConnection]);

  // Generate logos function
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
      setError('Vertex AI backend is not ready. Please check authentication and run diagnostics.');
      return;
    }

    setIsGenerating(true);
    setError(null);
    setGenerationStats(null);
    
    try {
      // Prepare request payload for Vertex AI backend
      const requestPayload: LogoGenerationRequest = {
        business_info: {
          name: businessName,
          industry: businessType,
          description: businessDescription || undefined,
          target_audience: targetAudience || undefined
        },
        style: {
          style_type: selectedStyle,
          color_palette: selectedColors.slice(0, 2),
          font_preference: "sans-serif"
        },
        variations: variations,
        imagen_model: selectedModel
      };

      console.log('🚀 Sending request to Vertex AI backend:', requestPayload);

      const response = await fetch(`${API_BASE_URL}/api/v1/generate-logos`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestPayload)
      });

      console.log('📊 Response status:', response.status);
      console.log('📨 Response headers:', Object.fromEntries(response.headers.entries()));

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
          console.error('❌ Error response data:', errorData);
        } catch (parseError) {
          console.error('❌ Could not parse error response as JSON');
          errorData = { detail: `HTTP ${response.status}: ${response.statusText}` };
        }
        
        const errorMessage = errorData?.detail || errorData?.message || `HTTP ${response.status}: ${response.statusText}`;
        throw new Error(errorMessage);
      }

      const data: GenerationResponse = await response.json();
      console.log('✅ Success response:', data);
      
      if (data.success && data.data) {
        setGeneratedLogos(data.data.logos || []);
        setGenerationStats(data.data.generation_stats);
        console.log('✅ Vertex AI logos generated successfully:', data.data.generation_stats);
        
        if (data.data.logos?.length === 0) {
          setError('No logos were generated. Please try again with different parameters.');
        }
      } else {
        console.error('❌ Success flag is false or missing data:', data);
        throw new Error('Generation completed but no logos were returned');
      }
      
    } catch (error: any) {
      console.error('❌ Error generating logos:', error);
      
      let errorMessage = 'Unknown error occurred';
      
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      } else if (error && typeof error === 'object') {
        errorMessage = error.detail || error.message || safeStringify(error);
      }
      
      // Enhanced error categorization for Vertex AI
      if (errorMessage.includes('429') || errorMessage.toLowerCase().includes('rate limit')) {
        setError('Rate limit reached. Please wait 30 seconds before generating more logos.');
      } else if (errorMessage.includes('authentication') || errorMessage.includes('401')) {
        setError('Authentication failed. Please run: gcloud auth application-default login');
      } else if (errorMessage.includes('403') || errorMessage.toLowerCase().includes('forbidden')) {
        setError('Access denied. Please enable Vertex AI API and billing in Google Cloud Console.');
      } else if (errorMessage.includes('404')) {
        setError('Vertex AI service not found. Please check if Vertex AI API is enabled in your project.');
      } else if (errorMessage.includes('billing')) {
        setError('Billing not enabled. Please enable billing for your Google Cloud project.');
      } else if (errorMessage.includes('Failed to fetch') || errorMessage.toLowerCase().includes('network')) {
        setError('Cannot connect to backend. Please ensure the Vertex AI server is running on http://localhost:8000');
        setBackendConnected(false);
      } else {
        setError(`Failed to generate logos: ${errorMessage}`);
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

  const downloadLogo = async (logo: LogoResponse, format: 'png' | 'jpg') => {
    try {
      setDownloadingLogo(logo.id + format);
      
      const response = await fetch(`${API_BASE_URL}/api/v1/logo/${logo.id}/download/${format}`);
      
      if (!response.ok) {
        throw new Error(`Download failed: ${response.status} ${response.statusText}`);
      }
      
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      
      const element = document.createElement('a');
      element.href = url;
      element.download = `${businessName || 'logo'}-${logo.id}.${format}`;
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
      URL.revokeObjectURL(url);
      
    } catch (error: any) {
      console.error('Download failed:', error);
      setError(`Failed to download ${format.toUpperCase()}: ${error instanceof Error ? error.message : 'Unknown error'}`);
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

  const calculateEstimatedCost = () => {
    const modelConfig = vertexModels.find(m => m.id === selectedModel);
    const costPerImage = modelConfig?.id === 'imagegeneration@006' ? 0.03 : 0.025;
    return (costPerImage * variations).toFixed(3);
  };

  // Don't render dynamic content until client-side
  if (!isClient) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Cloud className="w-16 h-16 text-blue-400 mx-auto mb-4 animate-pulse" />
          <h1 className="text-2xl font-bold text-white mb-2">Loading Vertex AI Logo Generator...</h1>
          <p className="text-gray-400">Initializing Google Cloud integration</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      {/* Header */}
      <header className="border-b border-white/10 backdrop-blur-sm bg-black/20">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-indigo-500 rounded-xl flex items-center justify-center">
                <Cloud className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Vertex AI Logo Generator</h1>
                <p className="text-sm text-gray-400">Powered by Google Vertex AI Imagen • Professional Authentication</p>
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
                  {backendConnected === null ? 'Checking...' : backendConnected ? 'Vertex AI Ready' : 'Not Ready'}
                </span>
              </div>
              
              <button 
                onClick={checkBackendConnection}
                className="px-3 py-1 bg-white/10 text-white rounded-lg hover:bg-white/20 transition-colors text-sm"
              >
                Refresh Status
              </button>
              
              <button 
                onClick={runDiagnostics}
                className="px-3 py-1 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-lg hover:bg-blue-500/30 transition-colors text-sm"
              >
                Run Diagnostics
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
              <div className="mt-2 space-x-2">
                <button 
                  onClick={() => setError(null)}
                  className="text-sm text-red-300 hover:text-red-100 underline"
                >
                  Dismiss
                </button>
                <button 
                  onClick={runDiagnostics}
                  className="text-sm text-blue-300 hover:text-blue-100 underline"
                >
                  Run Diagnostics
                </button>
                <a
                  href={`${API_BASE_URL}/api/v1/setup-guide`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-green-300 hover:text-green-100 underline inline-flex items-center gap-1"
                >
                  Setup Guide <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          </div>
        )}

        {/* Debug Info Display */}
        {debugInfo && (
          <details className="mb-6">
            <summary className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg cursor-pointer text-blue-300 hover:text-blue-200">
              <Info className="w-4 h-4 inline mr-2" />
              Vertex AI Backend Debug Information (Click to expand)
            </summary>
            <div className="mt-2 p-4 bg-black/20 border border-white/10 rounded-lg">
              <pre className="text-xs text-gray-300 whitespace-pre-wrap overflow-x-auto">
                {safeStringify(debugInfo)}
              </pre>
            </div>
          </details>
        )}

        {/* Success/Stats Display */}
        {generationStats && (
          <div className="mb-6 p-4 bg-green-500/20 border border-green-500/30 rounded-lg flex items-start space-x-3">
            <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-green-200 font-medium">
                Successfully generated {generationStats.logos_generated} Vertex AI logos using {generationStats.ai_model}
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
                  Vertex AI Logo Settings
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

                  {/* Vertex AI Model Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-3">
                      Google Vertex AI Model
                    </label>
                    <div className="space-y-3">
                      {vertexModels.map(model => (
                        <button
                          key={model.id}
                          type="button"
                          onClick={() => setSelectedModel(model.id)}
                          className={`w-full p-3 rounded-lg border-2 transition-all text-left ${
                            selectedModel === model.id
                              ? 'border-blue-400 bg-blue-400/20 text-blue-400'
                              : 'border-white/20 bg-white/5 text-gray-300 hover:border-white/40'
                          }`}
                        >
                          <div className="flex justify-between items-start">
                            <div>
                              <div className="font-medium flex items-center gap-2">
                                <Shield className="w-4 h-4" />
                                {model.name}
                              </div>
                              <div className="text-xs opacity-75">{model.desc}</div>
                            </div>
                            <div className="text-xs font-mono">{model.cost}</div>
                          </div>
                        </button>
                      ))}
                    </div>
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
                      <Sparkles className="w-4 h-4 inline mr-2" />
                      Color Palette (Vertex AI optimized)
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

                  {/* Cost Estimate */}
                  <div className="p-3 bg-black/20 rounded-lg border border-yellow-500/30">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-yellow-400">Estimated Cost:</span>
                      <span className="text-lg font-bold text-yellow-400">${calculateEstimatedCost()}</span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      {variations} logos × {vertexModels.find(m => m.id === selectedModel)?.cost || '$0.030'} (Vertex AI)
                    </p>
                  </div>

                  {/* Generate Button */}
                  <button
                    type="button"
                    onClick={generateLogos}
                    disabled={isGenerating || !businessName.trim() || !businessType || !backendConnected}
                    className="w-full py-4 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-lg font-semibold hover:from-blue-600 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center space-x-2"
                  >
                    {isGenerating ? (
                      <>
                        <RefreshCw className="w-5 h-5 animate-spin" />
                        <span>Generating with Vertex AI...</span>
                      </>
                    ) : (
                      <>
                        <Cloud className="w-5 h-5" />
                        <span>Generate Vertex AI Logos</span>
                      </>
                    )}
                  </button>
                  
                  {/* Status Messages */}
                  {!backendConnected && (
                    <div className="text-xs text-center space-y-1">
                      <p className="text-red-400">
                        ❌ Vertex AI backend not ready
                      </p>
                      <button
                        onClick={runDiagnostics}
                        className="text-blue-400 hover:text-blue-300 underline"
                      >
                        Click "Run Diagnostics" above to enable generation
                      </button>
                    </div>
                  )}
                  
                  {backendConnected && (
                    <p className="text-xs text-green-400 text-center">
                      ✅ Vertex AI ready for generation
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Results Panel */}
            <div className="lg:col-span-2">
              <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10 min-h-96">
                <h2 className="text-xl font-semibold text-white mb-6">
                  Google Vertex AI Generated Logos
                  {generationStats && (
                    <span className="text-sm text-gray-400 ml-2">
                      ({generationStats.ai_model} • {generationStats.quality})
                    </span>
                  )}
                </h2>

                {generatedLogos.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                    <Cloud className="w-16 h-16 mb-4 opacity-50" />
                    <p className="text-lg mb-2">Ready to create with Vertex AI?</p>
                    <p className="text-sm text-center">
                      Enter your business details and click generate to create professional logos
                    </p>
                    <div className="mt-4 text-xs text-center space-y-1">
                      <p className="text-blue-400">🔐 Secure OAuth2 authentication</p>
                      <p className="text-green-400">☁️ Google Cloud Vertex AI integration</p>
                      <p className="text-purple-400">🔍 Comprehensive diagnostics included</p>
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {generatedLogos.map((logo) => (
                      <div key={logo.id} className="p-4 bg-white/5 border border-white/10 rounded-lg">
                        {/* Vertex AI Generated Image */}
                        <div className="w-full h-48 flex items-center justify-center bg-white rounded-lg mb-4 overflow-hidden">
                          <img 
                            src={logo.image_url} 
                            alt={logo.name}
                            className="max-w-full max-h-full object-contain"
                            onLoad={(e) => {
                              console.log('✅ Vertex AI image loaded successfully:', logo.image_url);
                            }}
                            onError={(e) => {
                              console.error('❌ Vertex AI image load failed:', logo.image_url);
                              const target = e.currentTarget;
                              
                              // Show error placeholder
                              target.src = 'data:image/svg+xml;base64,' + btoa(`
                                <svg width="400" height="200" xmlns="http://www.w3.org/2000/svg">
                                  <rect width="400" height="200" fill="#f3f4f6"/>
                                  <text x="200" y="90" font-family="Arial" font-size="16" fill="#9ca3af" text-anchor="middle">
                                    Vertex AI Load Failed
                                  </text>
                                  <text x="200" y="110" font-family="Arial" font-size="12" fill="#9ca3af" text-anchor="middle">
                                    Image may not be available
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
                            {logo.style_info.location && (
                              <p>Location: {logo.style_info.location} • Method: {logo.style_info.generation_method}</p>
                            )}
                          </div>
                          
                          {/* Local Path Info */}
                          <div className="mb-3 p-2 bg-black/20 rounded text-xs">
                            <p className="text-gray-400 mb-1">Local Path:</p>
                            <p className="text-green-400 break-all">{logo.local_path || 'Not saved locally'}</p>
                            <p className="text-gray-500 mt-1">
                              Status: {logo.local_path ? 'Saved Locally' : 'Memory Only'} • 
                              Source: Vertex AI
                            </p>
                          </div>
                          
                          <details className="mb-3">
                            <summary className="text-xs text-blue-400 cursor-pointer hover:text-blue-300">
                              View Vertex AI Prompt
                            </summary>
                            <p className="text-xs text-gray-400 mt-1 p-2 bg-black/20 rounded">
                              {logo.prompt_used}
                            </p>
                          </details>
                          
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
                            
                            {/* PNG Download */}
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
                            
                            {/* JPEG Download */}
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
                              onClick={() => submitFeedback(logo.id, 5, 'Great Vertex AI logo!')}
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
            <h2 className="text-xl font-semibold text-white mb-2">Vertex AI Logo History</h2>
            <p className="text-gray-400">Your previously generated Google Vertex AI logos will appear here</p>
          </div>
        )}

        {activeTab === 'favorites' && (
          <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-8 border border-white/10">
            <div className="text-center mb-6">
              <Heart className="w-16 h-16 mx-auto mb-4 text-gray-400" />
              <h2 className="text-xl font-semibold text-white mb-2">Favorite Vertex AI Logos</h2>
              <p className="text-gray-400">Your favorited Google Vertex AI logos will be saved here</p>
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
                      <p className="text-sm text-gray-400">Favorited Vertex AI logo</p>
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <footer className="mt-12 pt-8 border-t border-white/10 text-center text-gray-400">
          <p className="text-sm">
            Powered by Google Vertex AI Imagen • Professional Authentication • Enterprise Grade
          </p>
          <p className="text-xs mt-2">
            Secure OAuth2 • Cloud-native • Enhanced diagnostics • Production ready
          </p>
        </footer>
      </div>
    </div>
  );
};

export default VertexLogoCreator;