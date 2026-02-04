import React from 'react';
import { Palette } from 'lucide-react';

export const GlobalColorControls = ({ themeConfig, onThemeConfigChange }) => {
  return (
    <div className="bg-white/10 backdrop-blur-xl border border-white/10 rounded-2xl p-4 glass-card">
      <h3 className="text-base font-bold mb-3 flex items-center gap-2">
        <Palette className="w-4 h-4" />
        Global Colors
      </h3>
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium mb-1">Logo Background</label>
          <div className="flex gap-1">
            <input
              type="color"
              value={themeConfig.logoBackground}
              onChange={(e) => onThemeConfigChange({...themeConfig, logoBackground: e.target.value})}
              className="h-8 w-12 rounded cursor-pointer"
            />
            <input
              type="text"
              value={themeConfig.logoBackground}
              onChange={(e) => onThemeConfigChange({...themeConfig, logoBackground: e.target.value})}
              className="flex-1 px-2 py-1 rounded border border-gray-300 text-xs"
              placeholder="#0f172a"
            />
          </div>
        </div>
        
        <div>
          <label className="block text-xs font-medium mb-1">Sidebar Background</label>
          <div className="flex gap-1">
            <input
              type="color"
              value={themeConfig.sidebarColor}
              onChange={(e) => onThemeConfigChange({...themeConfig, sidebarColor: e.target.value})}
              className="h-8 w-12 rounded cursor-pointer"
            />
            <input
              type="text"
              value={themeConfig.sidebarColor}
              onChange={(e) => onThemeConfigChange({...themeConfig, sidebarColor: e.target.value})}
              className="flex-1 px-2 py-1 rounded border border-gray-300 text-xs"
              placeholder="#0f172a"
            />
          </div>
        </div>
        
        <div>
          <label className="block text-xs font-medium mb-1">Sidebar Opacity: {themeConfig.sidebarOpacity}%</label>
          <input
            type="range"
            min="10"
            max="100"
            value={themeConfig.sidebarOpacity}
            onChange={(e) => onThemeConfigChange({...themeConfig, sidebarOpacity: parseInt(e.target.value)})}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
        </div>
      </div>
    </div>
  );
};