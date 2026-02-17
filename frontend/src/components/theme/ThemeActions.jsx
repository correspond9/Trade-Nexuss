import React, { useState } from 'react';
import { Save, RotateCcw, Check } from 'lucide-react';

export const ThemeActions = ({
  themeConfig,
  componentSettings,
  onNotification,
  themeName,
  onThemeNameChange,
  savedThemes = [],
  onSaveTheme,
  onLoadTheme,
  onDeleteTheme,
  onApplyTheme,
}) => {
  const [selectedSavedTheme, setSelectedSavedTheme] = useState('');

  const saveTheme = () => {
    if (typeof onSaveTheme === 'function') {
      onSaveTheme();
      return;
    }

    const themeData = {
      name: 'Custom Theme',
      config: themeConfig,
      componentSettings: componentSettings,
      timestamp: new Date().toISOString()
    };
    
    const savedThemes = JSON.parse(localStorage.getItem('savedThemes') || '[]');
    const existingIndex = savedThemes.findIndex(t => t.name === 'Custom Theme');
    
    if (existingIndex >= 0) {
      savedThemes[existingIndex] = themeData;
    } else {
      savedThemes.push(themeData);
    }
    
    localStorage.setItem('savedThemes', JSON.stringify(savedThemes));
    onNotification('Theme saved successfully!', 'success');
  };

  const resetTheme = () => {
    const defaultThemeConfig = {
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
    };

    const defaultComponentSettings = {
      buttons: {
        borderRadius: 8,
        shadowDistance: 4,
        shadowLightIntensity: 70,
        shadowDarkIntensity: 70,
        shadowBlur: 8,
        backgroundColor: '#3b82f6',
        shadowLight: '#ffffff',
        shadowDark: '#1e40af',
        textColor: '#ffffff',
        borderWidth: 1,
        borderStyle: 'solid',
        borderColor: '#2563eb',
        fontFamily: 'Inter',
        fontWeight: 'regular',
        fontStyle: 'normal',
        fontSize: 14,
      },
      inputs: {
        borderRadius: 6,
        shadowDistance: 2,
        shadowLightIntensity: 50,
        shadowDarkIntensity: 50,
        shadowBlur: 4,
        backgroundColor: '#ffffff',
        shadowLight: '#ffffff',
        shadowDark: '#9ca3af',
        textColor: '#374151',
        borderWidth: 1,
        borderStyle: 'solid',
        borderColor: '#d1d5db',
        fontFamily: 'Inter',
        fontWeight: 'regular',
        fontStyle: 'normal',
        fontSize: 14,
      },
      glassCards: {
        borderRadius: 16,
        shadowDistance: 8,
        shadowLightIntensity: 60,
        shadowDarkIntensity: 60,
        shadowBlur: 16,
        backgroundColor: '#ffffff',
        shadowLight: '#ffffff',
        shadowDark: '#6b7280',
        textColor: '#1f2937',
        borderWidth: 1,
        borderStyle: 'solid',
        borderColor: '#e5e7eb',
        fontFamily: 'Inter',
        fontWeight: 'regular',
        fontStyle: 'normal',
        fontSize: 14,
      },
      sidebar: {
        borderRadius: 0,
        shadowDistance: 4,
        shadowLightIntensity: 40,
        shadowDarkIntensity: 40,
        shadowBlur: 8,
        backgroundColor: '#0f172a',
        shadowLight: '#1e293b',
        shadowDark: '#020617',
        textColor: '#f1f5f9',
        borderWidth: 0,
        borderStyle: 'solid',
        borderColor: '#334155',
        fontFamily: 'Inter',
        fontWeight: 'regular',
        fontStyle: 'normal',
        fontSize: 14,
      },
    };

    // This would need to be passed up to parent to update state
    onNotification('Theme reset to default!', 'success');
    return { themeConfig: defaultThemeConfig, componentSettings: defaultComponentSettings };
  };

  const handleLoad = () => {
    if (!selectedSavedTheme) {
      onNotification('Please select a saved theme first.', 'error');
      return;
    }
    if (typeof onLoadTheme === 'function') {
      onLoadTheme(selectedSavedTheme);
    }
  };

  const handleDelete = () => {
    if (!selectedSavedTheme) {
      onNotification('Please select a saved theme first.', 'error');
      return;
    }
    if (typeof onDeleteTheme === 'function') {
      onDeleteTheme(selectedSavedTheme);
      setSelectedSavedTheme('');
    }
  };

  return (
    <div className="bg-white/10 backdrop-blur-xl border border-white/10 rounded-2xl p-4 glass-card">
      <h2 className="text-lg font-semibold mb-3">Actions</h2>
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium mb-1">Theme Name</label>
          <input
            type="text"
            value={themeName || ''}
            onChange={(e) => onThemeNameChange && onThemeNameChange(e.target.value)}
            className="w-full px-3 py-2 rounded border border-gray-300 text-sm"
            placeholder="e.g. Tailwind Mixed Pro"
          />
        </div>

        <button
          onClick={saveTheme}
          className="w-full px-4 py-2 bg-green-500 text-white rounded-lg font-medium hover:bg-green-600 transition-colors duration-200 flex items-center justify-center gap-2"
        >
          <Save className="w-4 h-4" />
          Save Theme
        </button>
        <button
          onClick={() => typeof onApplyTheme === 'function' && onApplyTheme()}
          className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors duration-200"
        >
          Apply to Whole Website
        </button>
        <button
          onClick={resetTheme}
          className="w-full px-4 py-2 bg-gray-500 text-white rounded-lg font-medium hover:bg-gray-600 transition-colors duration-200 flex items-center justify-center gap-2"
        >
          <RotateCcw className="w-4 h-4" />
          Reset to Default
        </button>

        <div className="pt-2 border-t border-gray-300/40">
          <label className="block text-xs font-medium mb-1">Saved Themes</label>
          <select
            value={selectedSavedTheme}
            onChange={(e) => setSelectedSavedTheme(e.target.value)}
            className="w-full px-3 py-2 rounded border border-gray-300 text-sm mb-2"
          >
            <option value="">Select saved theme</option>
            {savedThemes.map((item) => (
              <option key={item.name} value={item.name}>{item.name}</option>
            ))}
          </select>

          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={handleLoad}
              className="px-3 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 transition-colors duration-200"
            >
              Load
            </button>
            <button
              onClick={handleDelete}
              className="px-3 py-2 bg-red-500 text-white rounded-lg text-sm font-medium hover:bg-red-600 transition-colors duration-200"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export const Notification = ({ notification }) => {
  if (!notification) return null;
  
  return (
    <div className={`fixed bottom-4 right-4 px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 ${
      notification.type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
    }`}>
      <Check className="w-4 h-4" />
      {notification.message}
    </div>
  );
};