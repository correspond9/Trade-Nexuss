# 🚀 Installation Guide

## 📋 Prerequisites
- React 16+ or 17+ or 18+
- Modern JavaScript environment
- CSS support for CSS variables
- Tailwind CSS (recommended for styling)

## 📦 Quick Installation

### 1. Copy Files
```bash
# Copy the entire theme-tool folder to your project
cp -r theme-tool /path/to/your/project/src/components/theme
```

### 2. Install Dependencies
```bash
# Install required dependencies
npm install lucide-react

# Or if you don't have React
npm install react react-dom
```

## 🎯 Basic Integration

### Method 1: Complete Theme Customizer
```jsx
import React from 'react';
import { ThemeCustomizer } from './components/theme';

function App() {
  return (
    <div>
      <ThemeCustomizer />
      {/* Your app content */}
    </div>
  );
}
```

### Method 2: Individual Components
```jsx
import React from 'react';
import { useThemeLogic, ButtonSettings } from './components/theme';

function YourComponent() {
  const { themeConfig, setThemeConfig } = useThemeLogic();
  
  return (
    <div>
      <ButtonSettings 
        settings={themeConfig.buttons}
        onChange={(newSettings) => setThemeConfig({
          ...themeConfig,
          buttons: newSettings
        })}
        fontOptions={['Inter', 'Arial', 'Helvetica']}
        fontWeightOptions={['regular', 'bold', 'semibold']}
      />
    </div>
  );
}
```

## 🎨 Advanced Usage

### Custom Theme Provider
```jsx
import React, { createContext, useContext } from 'react';
import { useThemeLogic } from './theme';

const ThemeContext = createContext();

export const ThemeProvider = ({ children }) => {
  const themeLogic = useThemeLogic();
  
  return (
    <ThemeContext.Provider value={themeLogic}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);
```

### Apply to Existing Components
```jsx
import { useTheme } from './theme';

function ExistingButton({ children, ...props }) {
  const { themeConfig } = useTheme();
  
  return (
    <button 
      style={{
        backgroundColor: themeConfig.buttons.backgroundColor,
        color: themeConfig.buttons.textColor,
        borderRadius: `${themeConfig.buttons.borderRadius}px`,
        fontFamily: themeConfig.buttons.fontFamily
      }}
      {...props}
    >
      {children}
    </button>
  );
}
```

## 🔧 Configuration Options

### Theme Structure
```javascript
const themeConfig = {
  // Global settings
  borderRadius: 30,
  shadowDistance: 10,
  shadowIntensity: 60,
  backgroundColor: '#e0e0e0',
  textColor: '#333333',
  
  // Component-specific settings
  buttons: {
    backgroundColor: '#3b82f6',
    textColor: '#ffffff',
    borderRadius: 8,
    fontFamily: 'Inter',
    // ... more button settings
  },
  inputs: {
    backgroundColor: '#ffffff',
    textColor: '#374151',
    borderRadius: 6,
    // ... more input settings
  },
  // ... glassCards, sidebar
};
```

### CSS Variables Applied
```css
:root {
  --nui-border-radius: 30px;
  --nui-bg-color: #e0e0e0;
  --nui-text-color: #333333;
  
  --nui-buttons-bg-color: #3b82f6;
  --nui-buttons-text-color: #ffffff;
  --nui-buttons-border-radius: 8px;
  
  /* 50+ more variables... */
}
```

## 🎯 Features Included

### ✅ Core Functionality
- **Real-time Updates**: Instant visual feedback
- **Component Controls**: Buttons, Inputs, Glass Cards, Sidebar
- **Advanced Shadows**: Directional lighting with intensity
- **Font Library**: 30+ fonts including fancy bold options
- **Precision Controls**: Decimal border widths (0.25, 0.5, 0.75)
- **Theme Persistence**: Local storage integration
- **Pressed States**: Professional button interactions

### ✅ Advanced Features
- **CSS Override Management**: Handles external conflicts
- **Responsive Design**: Works across all screen sizes
- **Cross-browser**: Compatible with all modern browsers
- **Accessibility**: Focus states and keyboard navigation
- **Performance**: Optimized rendering and updates

## 🎨 Customization Options

### Visual Properties
- **Colors**: Background, text, border, shadow colors
- **Typography**: Font family, weight, style, size
- **Shadows**: Distance, blur, intensity, direction
- **Borders**: Width, style, color, radius
- **Effects**: Opacity, transitions, hover states

### Background Types
- **Solid Colors**: Hex color picker
- **Gradients**: Multi-directional gradients
- **Wallpapers**: Image upload support

### Theme Presets
- **Default**: Clean, professional look
- **Ocean**: Blue-themed design
- **NeuMo**: Modern neumorphism
- **Dark**: Dark mode support

## 🚀 Production Deployment

### Build Integration
```javascript
// vite.config.js
export default {
  resolve: {
    alias: {
      '@theme': '/src/components/theme'
    }
  }
}
```

### Performance Optimization
- **Bundle Size**: Lightweight implementation (~50KB)
- **Tree Shaking**: Unused components eliminated
- **CSS Generation**: Dynamic, efficient style injection
- **Memory Management**: Proper cleanup and disposal

## 🔧 Troubleshooting

### Common Issues

#### CSS Variables Not Applying
```jsx
// Ensure ThemeLogic is called before component render
useEffect(() => {
  // Theme variables are applied here
}, []);
```

#### Component Styles Not Updating
```jsx
// Check if component is wrapped in ThemeProvider
<ThemeProvider>
  <YourComponent />
</ThemeProvider>
```

#### Tailwind Conflicts
```css
/* Use !important to override Tailwind utilities */
button {
  background-color: var(--nui-buttons-bg-color) !important;
}
```

### Browser Compatibility
- ✅ Chrome/Edge: Full functionality
- ✅ Firefox: Full functionality
- ✅ Safari: Full functionality
- ✅ Mobile: Responsive design

## 📚 API Reference

### useThemeLogic Hook
```javascript
const {
  themeConfig,           // Current theme configuration
  setThemeConfig,       // Update theme configuration
  componentSettings,    // Component-specific settings
  setComponentSettings, // Update component settings
  themes,              // Available theme presets
  styleTagRef          // Reference to injected styles
} = useThemeLogic();
```

### Component Props
All components accept:
- `settings`: Current component settings
- `onChange`: Update callback function
- `fontOptions`: Array of available fonts
- `fontWeightOptions`: Array of font weights

## 🎯 Best Practices

### Performance
1. **Memoize Components**: Prevent unnecessary re-renders
2. **Optimize Updates**: Batch state changes
3. **Clean Resources**: Proper cleanup in useEffect
4. **Lazy Load**: Load theme components as needed

### User Experience
1. **Real-time Preview**: Show changes immediately
2. **Smooth Transitions**: Use CSS transitions
3. **Responsive Design**: Test on all screen sizes
4. **Accessibility**: Include keyboard navigation

### Code Organization
1. **Component Structure**: Keep components modular
2. **State Management**: Centralize theme state
3. **CSS Variables**: Use consistent naming
4. **Documentation**: Comment complex logic

---

**Status**: ✅ Production Ready  
**Version**: 1.0.0  
**Support**: Full documentation and examples included