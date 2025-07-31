'use client';
import React, { useState, useRef } from 'react';
import { Upload, Download, Palette, Type, Sparkles, RefreshCw, Heart, History, Settings, Zap } from 'lucide-react';

// Type definitions
interface Logo {
  id: number;
  name: string;
  style: string;
  colors: string[];
  svg_content: string;
}

const LogoCreator = () => {
  const [businessName, setBusinessName] = useState('');
  const [businessType, setBusinessType] = useState('');
  const [selectedStyle, setSelectedStyle] = useState('modern');
  const [selectedColors, setSelectedColors] = useState(['#3B82F6', '#1E40AF']);
  const [generatedLogos, setGeneratedLogos] = useState<Logo[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState('generate');
  const [favorites, setFavorites] = useState<number[]>([]); // Fixed: Combined both declarations with proper typing

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

  const generateLogos = async () => {
    if (!businessName.trim()) {
      alert('Please enter a business name');
      return;
    }

    setIsGenerating(true);
    
    try {
      // We'll connect this to the backend later
      const mockLogos: Logo[] = [
        {
          id: 1,
          name: 'Logo Concept 1',
          style: 'modern',
          colors: selectedColors,
          svg_content: `<svg viewBox="0 0 200 80" xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="20" width="40" height="40" rx="8" fill="${selectedColors[0]}"/>
            <text x="60" y="45" font-family="Arial, sans-serif" font-size="24" font-weight="bold" fill="${selectedColors[1]}">${businessName}</text>
          </svg>`
        },
        {
          id: 2,
          name: 'Logo Concept 2',
          style: 'modern',
          colors: selectedColors,
          svg_content: `<svg viewBox="0 0 200 80" xmlns="http://www.w3.org/2000/svg">
            <circle cx="30" cy="40" r="20" fill="${selectedColors[0]}"/>
            <circle cx="35" cy="35" r="5" fill="${selectedColors[1]}"/>
            <text x="60" y="45" font-family="Arial, sans-serif" font-size="24" font-weight="bold" fill="${selectedColors[1]}">${businessName}</text>
          </svg>`
        }
      ];

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      setGeneratedLogos(mockLogos);
    } catch (error) {
      console.error('Error generating logos:', error);
      alert('Failed to generate logos. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const toggleFavorite = (logoId: number) => {
    setFavorites(prev =>
      prev.includes(logoId)
        ? prev.filter(id => id !== logoId)
        : [...prev, logoId]
    );
  };

  const downloadLogo = (logo: Logo, format: string = 'svg') => {
    const element = document.createElement('a');
    const file = new Blob([logo.svg_content], { type: 'image/svg+xml' });
    element.href = URL.createObjectURL(file);
    element.download = `${businessName || 'logo'}-${logo.id}.${format}`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
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
                <p className="text-sm text-gray-400">AI-Powered Logo Generation</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button className="px-4 py-2 bg-white/10 text-white rounded-lg hover:bg-white/20 transition-colors">
                Sign In
              </button>
              <button className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:from-blue-600 hover:to-purple-700 transition-colors">
                Get Pro
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Navigation Tabs */}
        <div className="flex space-x-6 mb-8 border-b border-white/10">
          {[
            { id: 'generate', name: 'Generate', icon: Zap },
            { id: 'history', name: 'History', icon: History },
            { id: 'favorites', name: 'Favorites', icon: Heart }
          ].map(tab => (
            <button
              key={tab.id}
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
                      Business Type
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

                  {/* Style Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-3">
                      Logo Style
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      {logoStyles.map(style => (
                        <button
                          key={style.id}
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
                          key={index}
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
                    onClick={generateLogos}
                    disabled={isGenerating || !businessName.trim()}
                    className="w-full py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg font-semibold hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center space-x-2"
                  >
                    {isGenerating ? (
                      <>
                        <RefreshCw className="w-5 h-5 animate-spin" />
                        <span>Generating...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-5 h-5" />
                        <span>Generate Logos</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Results Panel */}
            <div className="lg:col-span-2">
              <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10 min-h-96">
                <h2 className="text-xl font-semibold text-white mb-6">
                  Generated Logos
                </h2>

                {generatedLogos.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                    <Sparkles className="w-16 h-16 mb-4 opacity-50" />
                    <p className="text-lg mb-2">Ready to create your logo?</p>
                    <p className="text-sm text-center">
                      Enter your business details and click "Generate Logos" to see AI-powered designs
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {generatedLogos.map(logo => (
                      <div key={logo.id} className="bg-white/10 rounded-xl p-4 border border-white/10 hover:border-white/20 transition-colors group">
                        <div className="bg-white rounded-lg p-6 mb-4 aspect-[2.5/1] flex items-center justify-center">
                          <div dangerouslySetInnerHTML={{ __html: logo.svg_content }} />
                        </div>
                        
                        <div className="flex items-center justify-between mb-3">
                          <h3 className="font-medium text-white">{logo.name}</h3>
                          <button
                            onClick={() => toggleFavorite(logo.id)}
                            className={`p-2 rounded-lg transition-colors ${
                              favorites.includes(logo.id)
                                ? 'bg-red-500/20 text-red-400'
                                : 'bg-white/10 text-gray-400 hover:text-red-400'
                            }`}
                          >
                            <Heart className="w-4 h-4" />
                          </button>
                        </div>

                        <div className="flex space-x-2">
                          <button
                            onClick={() => downloadLogo(logo, 'svg')}
                            className="flex-1 py-2 px-3 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-colors text-sm flex items-center justify-center space-x-2"
                          >
                            <Download className="w-4 h-4" />
                            <span>SVG</span>
                          </button>
                          <button
                            onClick={() => downloadLogo(logo, 'png')}
                            className="flex-1 py-2 px-3 bg-purple-500/20 text-purple-400 rounded-lg hover:bg-purple-500/30 transition-colors text-sm flex items-center justify-center space-x-2"
                          >
                            <Download className="w-4 h-4" />
                            <span>PNG</span>
                          </button>
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
            <p className="text-gray-400">Your previously generated logos will appear here</p>
          </div>
        )}

        {activeTab === 'favorites' && (
          <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-8 border border-white/10 text-center">
            <Heart className="w-16 h-16 mx-auto mb-4 text-gray-400" />
            <h2 className="text-xl font-semibold text-white mb-2">Favorite Logos</h2>
            <p className="text-gray-400">Logos you've favorited will be saved here</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default LogoCreator;