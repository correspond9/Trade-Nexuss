import React, { useState, useEffect } from 'react';

const ThemeSelector = () => {
  const [currentTheme, setCurrentTheme] = useState('default');
  const [isOpen, setIsOpen] = useState(false);

  const availableThemes = [
    { id: 'default', name: 'Default', description: 'Light beige theme' },
    { id: 'original-neumorphic', name: 'Original Neumorphic', description: 'Original neumorphic design' },
    { id: 'ocean', name: 'Ocean', description: 'Blue ocean theme' },
    { id: 'cloud', name: 'Cloud', description: 'Soft gray theme' },
    { id: 'trade-nexxus', name: 'Trade Nexxus', description: 'Dark professional theme' }
  ];

  // Function to apply theme colors directly
  const applyThemeColors = (theme) => {
    const themeColors = {
      'default': { bg: '#dedad3', text: '#1d2532' },
      'original-neumorphic': { bg: '#ECF0F3', text: '#31344b' },
      'ocean': { bg: '#e8f3ff', text: '#2b3645' },
      'cloud': { bg: '#e9edf5', text: '#6b7486' },
      'trade-nexxus': { bg: '#0a0e27', text: '#e4e4e7' }
    };
    
    const colors = themeColors[theme] || themeColors['default'];
    
    // Apply to body with inline styles
    document.body.style.setProperty('background-color', colors.bg, 'important');
    document.body.style.setProperty('color', colors.text, 'important');
    document.body.style.setProperty('transition', 'all 0.3s ease', 'important');
    
    // Apply neumorphic effects for original-neumorphic theme
    if (theme === 'original-neumorphic') {
      // Create neumorphic style element
      let neumorphicStyles = document.getElementById('neumorphic-effects');
      if (!neumorphicStyles) {
        neumorphicStyles = document.createElement('style');
        neumorphicStyles.id = 'neumorphic-effects';
        document.head.appendChild(neumorphicStyles);
      }
      
      neumorphicStyles.textContent = `
        /* Neumorphic Effects */
        .nui-neuromorphic {
          background-color: ${colors.bg} !important;
          border-radius: 1rem !important;
          box-shadow: 
            inset 2px 2px 5px rgba(255, 255, 255, 0.96),
            inset -3px -3px 7px rgba(0, 0, 0, 0.6) !important;
          transition: all 0.3s ease-in-out !important;
        }
        
        .nui-neuromorphic-inset {
          background-color: ${colors.bg} !important;
          border-radius: 1rem !important;
          box-shadow: 
            inset 0.25rem 0.25rem 0.5rem rgba(255, 255, 255, 0.96),
            inset -0.25rem -0.25rem 0.5rem rgba(0, 0, 0, 0.6) !important;
        }
        
        .nui-neuromorphic:hover {
          box-shadow: 
            inset -0.35rem -0.35rem 0.9rem 0.2rem rgba(255, 255, 255, 0.96),
            inset 0.5rem 0.5rem 1rem 0.2rem rgba(0, 0, 0, 0.6) !important;
        }
        
        /* Apply to buttons */
        button, .btn, [role="button"] {
          background-color: ${colors.bg} !important;
          color: ${colors.text} !important;
          border: none !important;
          border-radius: 1rem !important;
          box-shadow: 
            inset 2px 2px 5px rgba(255, 255, 255, 0.96),
            inset -3px -3px 7px rgba(0, 0, 0, 0.6) !important;
          transition: all 0.3s ease-in-out !important;
        }
        
        button:hover, .btn:hover, [role="button"]:hover {
          box-shadow: 
            inset -0.35rem -0.35rem 0.9rem 0.2rem rgba(255, 255, 255, 0.96),
            inset 0.5rem 0.5rem 1rem 0.2rem rgba(0, 0, 0, 0.6) !important;
        }
        
        button:active, .btn:active, [role="button"]:active {
          box-shadow: 
            inset 2px 2px 5px rgba(255, 255, 255, 0.96),
            inset -3px -3px 7px rgba(0, 0, 0, 0.6) !important;
        }
        
        /* Apply to cards and containers */
        .card, .nui-card, div[class*="bg-"], div[class*="card"] {
          background-color: ${colors.bg} !important;
          border-radius: 1rem !important;
          box-shadow: 
            inset 2px 2px 5px rgba(255, 255, 255, 0.96),
            inset -3px -3px 7px rgba(0, 0, 0, 0.6) !important;
        }
        
        /* Apply to inputs */
        input, textarea, select, .form-control {
          background-color: ${colors.bg} !important;
          color: ${colors.text} !important;
          border: 0.0625rem solid rgba(236, 240, 243, 0.15) !important;
          border-radius: 0.55rem !important;
          box-shadow: 
            inset 2px 2px 5px rgba(255, 255, 255, 0.96),
            inset -3px -3px 7px rgba(0, 0, 0, 0.6) !important;
        }
        
        input:focus, textarea:focus, select:focus, .form-control:focus {
          box-shadow: 
            inset 2px 2px 5px rgba(255, 255, 255, 0.96),
            inset -3px -3px 7px rgba(0, 0, 0, 0.6),
            0 0 0 0.0625rem rgba(203, 204, 214, 0.5) !important;
        }
      `;
    } else {
      // Remove neumorphic effects for other themes
      const neumorphicStyles = document.getElementById('neumorphic-effects');
      if (neumorphicStyles) {
        neumorphicStyles.remove();
      }
    }
    
    // Apply to main content areas
    const mainElements = document.querySelectorAll('main, .main-content, #root');
    mainElements.forEach(el => {
      el.style.setProperty('background-color', colors.bg, 'important');
      el.style.setProperty('color', colors.text, 'important');
    });
  };

  useEffect(() => {
    // Initialize theme system
    if (window.TradeNexxusTheme) {
      window.TradeNexxusTheme.initializeThemeSystem();
      
      // Get current theme from system
      const theme = window.TradeNexxusTheme.getCurrentTheme();
      setCurrentTheme(theme);
      
      // Apply theme colors directly via inline styles
      applyThemeColors(theme);
      
      // Listen for theme changes
      const handleThemeChange = (event) => {
        setCurrentTheme(event.detail.theme);
        applyThemeColors(event.detail.theme);
      };
      
      document.addEventListener('themeChanged', handleThemeChange);
      
      return () => {
        document.removeEventListener('themeChanged', handleThemeChange);
      };
    }
  }, []);

  const handleThemeChange = (themeId) => {
    if (window.TradeNexxusTheme) {
      window.TradeNexxusTheme.setTheme(themeId);
      setCurrentTheme(themeId);
      setIsOpen(false);
    }
  };

  const getCurrentThemeInfo = () => {
    return availableThemes.find(theme => theme.id === currentTheme) || availableThemes[0];
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
      >
        <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
        </svg>
        <span className="font-medium">{getCurrentThemeInfo().name}</span>
        <svg 
          className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
          <div className="p-2">
            <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Themes
            </div>
            {availableThemes.map((theme) => (
              <button
                key={theme.id}
                onClick={() => handleThemeChange(theme.id)}
                className={`w-full text-left px-3 py-2 rounded-md transition-colors ${
                  currentTheme === theme.id
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'hover:bg-gray-50 text-gray-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{theme.name}</div>
                    <div className="text-xs text-gray-500">{theme.description}</div>
                  </div>
                  {currentTheme === theme.id && (
                    <svg className="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ThemeSelector;
