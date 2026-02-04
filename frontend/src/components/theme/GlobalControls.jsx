import React from 'react';
import { Sliders } from 'lucide-react';

export const GlobalControls = ({ themeConfig, onThemeConfigChange }) => {
  return (
    <div className="bg-white/10 backdrop-blur-xl border border-white/10 rounded-2xl p-4 glass-card">
      <h3 className="text-base font-bold mb-3 flex items-center gap-2">
        <Sliders className="w-4 h-4" />
        Global Controls
      </h3>
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium mb-1">Light Source</label>
          <div className="grid grid-cols-4 gap-1">
            <button
              onClick={() => onThemeConfigChange({...themeConfig, lightSource: 'top-left'})}
              className={`p-2 rounded text-xs ${themeConfig.lightSource === 'top-left' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
            >
              ↖️
            </button>
            <button
              onClick={() => onThemeConfigChange({...themeConfig, lightSource: 'top-right'})}
              className={`p-2 rounded text-xs ${themeConfig.lightSource === 'top-right' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
            >
              ↗️
            </button>
            <button
              onClick={() => onThemeConfigChange({...themeConfig, lightSource: 'bottom-left'})}
              className={`p-2 rounded text-xs ${themeConfig.lightSource === 'bottom-left' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
            >
              ↙️
            </button>
            <button
              onClick={() => onThemeConfigChange({...themeConfig, lightSource: 'bottom-right'})}
              className={`p-2 rounded text-xs ${themeConfig.lightSource === 'bottom-right' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
            >
              ↘️
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};