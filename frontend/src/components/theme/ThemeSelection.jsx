import React from 'react';

export const ThemeSelection = ({ themes, selectedTheme, onThemeSelect }) => {
  return (
    <div className="bg-white/10 backdrop-blur-xl border border-white/10 rounded-2xl p-4 glass-card">
      <h2 className="text-lg font-semibold mb-3">Theme Selection</h2>
      <div className="grid grid-cols-4 gap-2">
        {Object.keys(themes).map(theme => (
          <button
            key={theme}
            onClick={() => onThemeSelect(theme)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              selectedTheme === theme 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {theme}
          </button>
        ))}
      </div>
    </div>
  );
};