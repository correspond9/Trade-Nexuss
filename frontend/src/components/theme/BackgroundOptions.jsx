import React from 'react';
import { Palette } from 'lucide-react';

const BackgroundOptions = ({ themeConfig, setThemeConfig }) => (
  <div className="bg-white/10 backdrop-blur-xl border border-white/10 rounded-2xl p-2 glass-card">
    <h3 className="text-base font-bold mb-2 flex items-center gap-2">
      <Palette className="w-4 h-4" />
      Background
    </h3>
    
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <div>
        <label className="block text-xs font-medium mb-1">Type</label>
        <select
          value={themeConfig.backgroundType}
          onChange={(e) => setThemeConfig({...themeConfig, backgroundType: e.target.value})}
          className="w-full px-2 py-1 rounded border border-gray-300 text-xs bg-white"
        >
          <option value="color">Color</option>
          <option value="gradient">Gradient</option>
          <option value="wallpaper">Wallpaper</option>
        </select>
      </div>

      {themeConfig.backgroundType === 'color' && (
        <div>
          <label className="block text-xs font-medium mb-1">Color</label>
          <div className="flex gap-1">
            <input
              type="color"
              value={themeConfig.backgroundColor}
              onChange={(e) => setThemeConfig({...themeConfig, backgroundColor: e.target.value})}
              className="h-6 w-12 rounded cursor-pointer"
            />
            <input
              type="text"
              value={themeConfig.backgroundColor}
              onChange={(e) => setThemeConfig({...themeConfig, backgroundColor: e.target.value})}
              className="flex-1 px-1 py-1 rounded border border-gray-300 text-xs"
              placeholder="#e0e0e0"
            />
          </div>
        </div>
      )}

      {themeConfig.backgroundType === 'gradient' && (
        <>
          <div>
            <label className="block text-xs font-medium mb-1">Start</label>
            <div className="flex gap-1">
              <input
                type="color"
                value={themeConfig.gradientStart}
                onChange={(e) => setThemeConfig({...themeConfig, gradientStart: e.target.value})}
                className="h-6 w-12 rounded cursor-pointer"
              />
              <input
                type="text"
                value={themeConfig.gradientStart}
                onChange={(e) => setThemeConfig({...themeConfig, gradientStart: e.target.value})}
                className="flex-1 px-1 py-1 rounded border border-gray-300 text-xs"
                placeholder="#667eea"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">End</label>
            <div className="flex gap-1">
              <input
                type="color"
                value={themeConfig.gradientEnd}
                onChange={(e) => setThemeConfig({...themeConfig, gradientEnd: e.target.value})}
                className="h-6 w-12 rounded cursor-pointer"
              />
              <input
                type="text"
                value={themeConfig.gradientEnd}
                onChange={(e) => setThemeConfig({...themeConfig, gradientEnd: e.target.value})}
                className="flex-1 px-1 py-1 rounded border border-gray-300 text-xs"
                placeholder="#764ba2"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Direction</label>
            <select
              value={themeConfig.gradientDirection}
              onChange={(e) => setThemeConfig({...themeConfig, gradientDirection: e.target.value})}
              className="w-full px-2 py-1 rounded border border-gray-300 text-xs bg-white"
            >
              <option value="to-right">→</option>
              <option value="to-left">←</option>
              <option value="to-bottom">↓</option>
              <option value="to-top">↑</option>
              <option value="to-bottom-right">↘</option>
              <option value="to-bottom-left">↙</option>
              <option value="to-top-right">↗</option>
              <option value="to-top-left">↖</option>
            </select>
          </div>
        </>
      )}

      {themeConfig.backgroundType === 'wallpaper' && (
        <div className="md:col-span-3">
          <label className="block text-xs font-medium mb-1">Upload</label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => {
              const file = e.target.files[0];
              if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                  setThemeConfig({...themeConfig, wallpaperImage: event.target.result});
                };
                reader.readAsDataURL(file);
              }
            }}
            className="w-full px-2 py-1 rounded border border-gray-300 text-xs bg-white"
          />
          {themeConfig.wallpaperImage && (
            <div className="mt-1">
              <img 
                src={themeConfig.wallpaperImage} 
                alt="Wallpaper" 
                className="w-full h-20 object-cover rounded"
              />
            </div>
          )}
        </div>
      )}
    </div>
  </div>
);

export default BackgroundOptions;