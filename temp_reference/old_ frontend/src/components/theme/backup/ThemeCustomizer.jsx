import React, { useState } from 'react';
import { useThemeLogic } from './ThemeLogic';

export default function ThemeCustomizer() {
  const [notification, setNotification] = useState(null);
  const [selectedTheme, setSelectedTheme] = useState('Custom Theme');

  const {
    themeConfig,
    setThemeConfig,
    themes
  } = useThemeLogic();

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  const applyTheme = (themeName) => {
    const theme = themes[themeName];
    if (theme) {
      setThemeConfig(theme);
      setSelectedTheme(themeName);
      showNotification(`${themeName} theme applied successfully!`);
    }
  };

  const resetTheme = () => {
    setThemeConfig({
      borderRadius: 30,
      shadowDistance: 10,
      shadowIntensity: 60,
      shadowLightIntensity: 60,
      shadowDarkIntensity: 60,
      shadowBlur: 20,
      backgroundColor: '#e0e0e0',
      shadowLight: '#ffffff',
      shadowDark: '#5a5a5a',
      textColor: '#333333',
      logoBackground: '#0f172a',
      sidebarColor: '#0f172a',
      sidebarOpacity: 100,
      glassCardColor: '#ffffff',
      glassCardOpacity: 100,
      lightSource: 'top-left',
      headingColor: '#333333',
      bodyColor: '#666666',
      buttonTextColor: '#ffffff',
      headingFontSize: 24,
      bodyFontSize: 16,
      buttonFontSize: 14,
      buttonFontFamily: 'Inter',
      buttonFontWeight: 'regular',
      buttonFontStyle: 'normal',
      backgroundType: 'color',
      gradientStart: '#667eea',
      gradientEnd: '#764ba2',
      gradientDirection: 'to-right',
      wallpaperImage: null,
    });
    setSelectedTheme('Custom Theme');
    showNotification('Theme reset to default!');
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Theme Customization</h1>
        
        <div className="bg-white/10 backdrop-blur-xl border border-white/10 rounded-2xl p-6 glass-card">
          <h2 className="text-lg font-semibold mb-4">Theme Selection</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {Object.keys(themes).map(theme => (
              <button
                key={theme}
                onClick={() => applyTheme(theme)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  selectedTheme === theme 
                    ? 'bg-blue-500 text-white' 
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {theme}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-md font-medium mb-3">Background Settings</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Background Color</label>
                  <input
                    type="color"
                    value={themeConfig.backgroundColor}
                    onChange={(e) => setThemeConfig({...themeConfig, backgroundColor: e.target.value})}
                    className="w-full h-10 rounded cursor-pointer"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Text Color</label>
                  <input
                    type="color"
                    value={themeConfig.textColor}
                    onChange={(e) => setThemeConfig({...themeConfig, textColor: e.target.value})}
                    className="w-full h-10 rounded cursor-pointer"
                  />
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-md font-medium mb-3">Shape Settings</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Border Radius: {themeConfig.borderRadius}px</label>
                  <input
                    type="range"
                    min="0"
                    max="50"
                    value={themeConfig.borderRadius}
                    onChange={(e) => setThemeConfig({...themeConfig, borderRadius: parseInt(e.target.value)})}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Shadow Distance: {themeConfig.shadowDistance}px</label>
                  <input
                    type="range"
                    min="0"
                    max="30"
                    value={themeConfig.shadowDistance}
                    onChange={(e) => setThemeConfig({...themeConfig, shadowDistance: parseInt(e.target.value)})}
                    className="w-full"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 flex gap-3">
            <button
              onClick={resetTheme}
              className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
            >
              Reset to Default
            </button>
            <button
              onClick={() => showNotification('Theme saved successfully!')}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              Save Theme
            </button>
          </div>
        </div>

        {/* Notification */}
        {notification && (
          <div className={`fixed top-4 right-4 px-4 py-2 rounded-lg text-white ${
            notification.type === 'success' ? 'bg-green-500' : 'bg-red-500'
          }`}>
            {notification.message}
          </div>
        )}
      </div>
    </div>
  );
}