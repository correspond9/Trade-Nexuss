# 🔧 Theme Tool Working Guide

## 📋 Overview
This guide explains the complete working of the Universal Theme Customization Tool, including all configuration options, CSS variables, and how each feature functions. Use this as your reference for understanding the theme system's behavior and configuration.

## 🎯 Core Architecture

### Theme Logic Hook (`ThemeLogic.jsx`)
The heart of the system that manages:
- **Global theme configuration**
- **Component-specific settings**
- **CSS variable injection**
- **Local storage persistence**
- **Dynamic style generation**

### State Management
```javascript
const {
  themeConfig,           // Global theme settings
  setThemeConfig,       // Update global settings
  componentSettings,    // Component-specific settings
  setComponentSettings, // Update component settings
  themes,              // Available theme presets
  styleTagRef          // Reference to injected styles
} = useThemeLogic();
```

## 🎨 Configuration Structure

### Global Theme Configuration
```javascript
themeConfig = {
  // Visual Properties
  borderRadius: 30,              // Global border radius (0-150px)
  shadowDistance: 10,             // Shadow distance (0-50px)
  shadowIntensity: 60,             // Shadow intensity (1-100%)
  shadowLightIntensity: 60,         // Light shadow intensity (1-100%)
  shadowDarkIntensity: 60,          // Dark shadow intensity (1-100%)
  shadowBlur: 20,                 // Shadow blur (0-50px)
  
  // Colors
  backgroundColor: '#e0e0e0',     // Main background color
  shadowLight: '#ffffff',            // Light shadow color
  shadowDark: '#5a5a5a',           // Dark shadow color
  textColor: '#333333',              // Main text color
  
  // Component Colors
  logoBackground: '#0f172a',         // Logo background
  sidebarColor: '#0f172a',          // Sidebar background
  glassCardColor: '#ffffff',          // Glass card background
  
  // Typography
  headingColor: '#333333',           // Heading text color
  bodyColor: '#666666',             // Body text color
  buttonTextColor: '#ffffff',         // Button text color
  headingFontSize: 24,               // Heading font size (10-40px)
  bodyFontSize: 16,                  // Body font size (10-24px)
  buttonFontSize: 14,                // Button font size (10-24px)
  
  // Font Properties
  buttonFontFamily: 'Inter',          // Button font family
  buttonFontWeight: 'regular',         // Button font weight
  buttonFontStyle: 'normal',           // Button font style
  
  // Background
  backgroundType: 'color',            // 'color' | 'gradient' | 'wallpaper'
  gradientStart: '#667eea',           // Gradient start color
  gradientEnd: '#764ba2',             // Gradient end color
  gradientDirection: 'to-right',      // Gradient direction
  wallpaperImage: null,               // Wallpaper image URL
  
  // Light Source
  lightSource: 'top-left'             // 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'
  
  // Opacity
  sidebarOpacity: 100,               // Sidebar opacity (10-100%)
  glassCardOpacity: 100              // Glass card opacity (10-100%)
};
```

### Component-Specific Settings
```javascript
componentSettings = {
  buttons: {
    borderRadius: 8,               // Border radius (0-50px)
    shadowDistance: 4,              // Shadow distance (0-20px)
    shadowLightIntensity: 70,         // Light shadow intensity (1-100%)
    shadowDarkIntensity: 70,          // Dark shadow intensity (1-100%)
    shadowBlur: 8,                   // Shadow blur (0-30px)
    backgroundColor: '#3b82f6',       // Button background
    shadowLight: '#ffffff',            // Button light shadow
    shadowDark: '#1e40af',           // Button dark shadow
    textColor: '#ffffff',              // Button text color
    borderWidth: 1,                   // Border width (0-10px, 0.25 precision)
    borderStyle: 'solid',              // Border style
    borderColor: '#2563eb',           // Border color
    fontFamily: 'Inter',              // Font family
    fontWeight: 'regular',             // Font weight
    fontStyle: 'normal',               // Font style
    fontSize: 14,                    // Font size (10-24px)
  },
  
  inputs: {
    // Same structure as buttons
    // Default: backgroundColor: '#ffffff', textColor: '#374151'
    // Default: borderRadius: 6, borderWidth: 1
  },
  
  glassCards: {
    // Same structure as buttons
    // Default: backgroundColor: '#ffffff', textColor: '#1f2937'
    // Default: borderRadius: 16, borderWidth: 1
  },
  
  sidebar: {
    // Same structure as buttons
    // Default: backgroundColor: '#0f172a', textColor: '#f1f5f9'
    // Default: borderRadius: 0, borderWidth: 0
  }
};
```

## 🎯 CSS Variables System

### Global CSS Variables
```css
:root {
  /* Border & Shadow */
  --nui-border-radius: 30px;
  --nui-shadow-distance: 10px;
  --nui-shadow-intensity: 60;
  --nui-shadow-light-intensity: 60;
  --nui-shadow-dark-intensity: 60;
  --nui-shadow-blur: 20px;
  
  /* Colors */
  --nui-bg-color: #e0e0e0;
  --nui-shadow-light: #ffffff;
  --nui-shadow-dark: #5a5a5a;
  --nui-text-color: #333333;
  
  /* Component Colors */
  --nui-logo-bg: #0f172a;
  --nui-sidebar-color: #0f172a;
  --nui-glass-card-color: #ffffff;
  
  /* Typography */
  --nui-heading-color: #333333;
  --nui-body-color: #666666;
  --nui-button-text-color: #ffffff;
  --nui-heading-font-size: 24px;
  --nui-body-font-size: 16px;
  --nui-button-font-size: 14px;
  
  /* Font Properties */
  --nui-button-font-family: Inter;
  --nui-button-font-weight: regular;
  --nui-button-font-style: normal;
  
  /* Background */
  --nui-light-source: top-left;
  --nui-sidebar-opacity: 1;
  --nui-glass-card-opacity: 1;
  
  /* Generated Shadows */
  --nui-outer-shadow: [dynamic];
  --nui-inner-shadow: [dynamic];
}
```

### Component-Specific CSS Variables
```css
:root {
  /* Buttons */
  --nui-buttons-border-radius: 8px;
  --nui-buttons-shadow-distance: 4px;
  --nui-buttons-shadow-light-intensity: 70%;
  --nui-buttons-shadow-dark-intensity: 70%;
  --nui-buttons-shadow-blur: 8px;
  --nui-buttons-bg-color: #3b82f6;
  --nui-buttons-shadow-light: #ffffff;
  --nui-buttons-shadow-dark: #1e40af;
  --nui-buttons-text-color: #ffffff;
  --nui-buttons-border-width: 1px;
  --nui-buttons-border-style: solid;
  --nui-buttons-border-color: #2563eb;
  --nui-buttons-font-family: Inter;
  --nui-buttons-font-weight: regular;
  --nui-buttons-font-style: normal;
  --nui-buttons-font-size: 14px;
  --nui-buttons-outer-shadow: [dynamic];
  --nui-buttons-inner-shadow: [dynamic];
  
  /* Similar variables for inputs, glassCards, sidebar... */
}
```

## 🎯 Shadow System

### Light Source Direction
The shadow system uses 4-directional lighting:

```javascript
// Light Source: 'top-left'
// Results in:
// Light shadow: bottom-right (positive x, positive y)
// Dark shadow: top-left (negative x, negative y)

// Light Source: 'top-right'
// Results in:
// Light shadow: bottom-left (negative x, positive y)
// Dark shadow: top-right (positive x, negative y)

// Light Source: 'bottom-left'
// Results in:
// Light shadow: top-right (positive x, negative y)
// Dark shadow: bottom-left (negative x, positive y)

// Light Source: 'bottom-right'
// Results in:
// Light shadow: top-left (negative x, negative y)
// Dark shadow: bottom-right (positive x, positive y)
```

### Shadow Intensity Calculation
```javascript
// Intensity affects shadow opacity
const applyIntensity = (hexColor, intensity, isLightShadow) => {
  const r = parseInt(hexColor.slice(1, 3), 16);
  const g = parseInt(hexColor.slice(3, 5), 16);
  const b = parseInt(hexColor.slice(5, 7), 16);
  
  if (hexColor === '#ffffff') {
    return `rgba(255, 255, 255, ${Math.max(0.1, intensity)})`;
  } else if (hexColor === '#000000') {
    return `rgba(0, 0, 0, ${Math.max(0.1, intensity)})`;
  } else {
    return `rgba(${r}, ${g}, ${b}, ${Math.max(0.1, intensity)})`;
  }
};

// Example: intensity = 0.6 (60%)
// Results in: rgba(255, 255, 255, 0.6) for white
// Results in: rgba(90, 90, 90, 0.6) for gray
```

### Generated Shadow CSS
```css
/* Outer Shadow (normal state) */
box-shadow: 
  10px 10px 20px rgba(255, 255, 255, 0.6),    /* Light shadow */
  -10px -10px 20px rgba(90, 90, 90, 0.6); /* Dark shadow */

/* Inner Shadow (pressed state) */
box-shadow: 
  inset 10px 10px 20px rgba(255, 255, 255, 0.6),    /* Light shadow */
  inset -10px -10px 20px rgba(90, 90, 90, 0.6); /* Dark shadow */
```

## 🎯 Component Behavior

### Button States
```css
/* Normal State */
button {
  border-radius: var(--nui-buttons-border-radius);
  box-shadow: var(--nui-buttons-outer-shadow);
  background-color: var(--nui-buttons-bg-color);
  color: var(--nui-buttons-text-color);
  transition: all 0.2s ease;
}

/* Hover State */
button:hover {
  transform: translateY(-2px);
  box-shadow: var(--nui-buttons-outer-shadow), 0 4px 8px rgba(0,0,0,0.1);
}

/* Pressed/Focused State */
button:active, button:focus {
  transform: translateY(0px);
  box-shadow: var(--nui-buttons-inner-shadow);
}
```

### Glass Card Effects
```css
.glass-card.glass-card {
  border-radius: var(--nui-glassCards-border-radius);
  box-shadow: var(--nui-glassCards-outer-shadow);
  background-color: var(--nui-glassCards-bg-color);
  background: var(--nui-glassCards-bg-color);
  /* Creates glass morphism effect */
}
```

### Sidebar Styling
```css
/* Container */
.sidebar.sidebar, nav.nav, .sidebar-element nav {
  background-color: var(--nui-sidebar-bg-color);
  opacity: var(--nui-sidebar-opacity);
  color: var(--nui-sidebar-text-color);
  font-family: var(--nui-sidebar-font-family);
}

/* Menu Items */
.sidebar.sidebar a, nav.nav a, .sidebar-element nav a {
  color: var(--nui-sidebar-text-color);
  font-family: var(--nui-sidebar-font-family);
  /* Ensures menu items inherit sidebar styling */
}
```

## 🎯 Theme Presets

### Default Theme
```javascript
'Default': {
  borderRadius: 12,
  shadowDistance: 8,
  shadowIntensity: 20,
  backgroundColor: '#f5f5f5',
  shadowLight: '#ffffff',
  shadowDark: '#d0d0d0',
  textColor: '#333333',
  // Clean, professional appearance
}
```

### Ocean Theme
```javascript
'Ocean': {
  borderRadius: 20,
  shadowDistance: 12,
  backgroundColor: '#e0f2fe',
  shadowLight: '#ffffff',
  shadowDark: '#0284c7',
  textColor: '#0c4a6e',
  // Blue-themed, calming appearance
}
```

### NeuMo Theme
```javascript
'NeuMo': {
  borderRadius: 16,
  shadowDistance: 6,
  backgroundColor: '#fafafa',
  shadowLight: '#ffffff',
  shadowDark: '#a1a1aa',
  textColor: '#18181b',
  // Modern neumorphism appearance
}
```

### Dark Theme
```javascript
'Dark': {
  borderRadius: 8,
  shadowDistance: 4,
  backgroundColor: '#18181b',
  shadowLight: '#27272a',
  shadowDark: '#000000',
  textColor: '#fafafa',
  // Dark mode appearance
}
```

## 🎯 Precision Controls

### Border Width Precision
```javascript
// All border width sliders support 0.25 precision
<input
  type="range"
  min="0"
  max="10"
  step="0.25"  // Allows: 0, 0.25, 0.5, 0.75, 1, 1.25, etc.
  onChange={(e) => onChange({...settings, borderWidth: parseFloat(e.target.value)})}
/>

// Applied to CSS:
border-width: 2.5px;  // Example with 0.25 precision
```

### Font Library
```javascript
const fontOptions = [
  'Inter', 'Arial', 'Helvetica', 'Times New Roman', 'Georgia',
  'Courier New', 'Verdana', 'Trebuchet MS', 'Palatino', 'Garamond',
  'Bookman', 'Comic Sans MS', 'Impact', 'Lucide Console', 'Tahoma',
  'Bebas Neue', 'Montserrat', 'Poppins', 'Roboto', 'Oswald',
  'Raleway', 'Playfair Display', 'Merriweather', 'Lato', 'Open Sans',
  'Nunito', 'Rubik', 'Ubuntu', 'Dancing Script', 'Pacifico',
  'Bangers', 'Press Start 2P', 'Fira Code', 'JetBrains Mono', 'Space Mono'
];
```

## 🎯 Background System

### Color Background
```javascript
backgroundType: 'color',
backgroundColor: '#e0e0e0',
// Applied CSS:
background-color: #e0e0e0 !important;
```

### Gradient Background
```javascript
backgroundType: 'gradient',
gradientStart: '#667eea',
gradientEnd: '#764ba2',
gradientDirection: 'to-right',
// Applied CSS:
background: linear-gradient(to-right, #667eea, #764ba2) !important;
```

### Wallpaper Background
```javascript
backgroundType: 'wallpaper',
wallpaperImage: 'data:image/jpeg;base64,...',
// Applied CSS:
background: url(data:image/jpeg;base64,...) !important;
background-size: cover !important;
```

## 🎯 Storage & Persistence

### Local Storage Keys
```javascript
// Theme Configuration
localStorage.setItem('customThemeConfig', JSON.stringify(themeConfig));

// Component Settings
localStorage.setItem('componentSettings', JSON.stringify(componentSettings));

// Saved Themes
localStorage.setItem('savedThemes', JSON.stringify(savedThemes));
```

### Automatic Loading
```javascript
useEffect(() => {
  const savedConfig = localStorage.getItem('customThemeConfig');
  const savedComponentSettings = localStorage.getItem('componentSettings');
  
  if (savedConfig) {
    setThemeConfig(JSON.parse(savedConfig));
  }
  if (savedComponentSettings) {
    setComponentSettings(JSON.parse(savedComponentSettings));
  }
}, []);
```

## 🎯 CSS Override Management

### Conflict Resolution
```css
/* All theme styles use !important to override external CSS */
button {
  border-radius: var(--nui-buttons-border-radius) !important;
  box-shadow: var(--nui-buttons-outer-shadow) !important;
  background-color: var(--nui-buttons-bg-color) !important;
}

/* Specific selectors for higher specificity */
.sidebar.sidebar, nav.nav, .sidebar-element nav {
  /* Higher specificity than generic selectors */
}
```

### Dynamic Style Injection
```javascript
// Styles are dynamically injected and updated
const css = `
  button { /* Generated styles */ }
  /* ... more styles */
`;

const styleTag = document.createElement('style');
styleTag.textContent = css;
document.head.appendChild(styleTag);
```

## 🎯 Performance Optimizations

### Efficient Updates
```javascript
// Only update when values actually change
useEffect(() => {
  // Apply CSS variables
}, [themeConfig, componentSettings]);

// Cleanup previous styles
if (styleTagRef.current) {
  styleTagRef.current.remove();
}
```

### Memory Management
```javascript
// Proper cleanup in useEffect
useEffect(() => {
  return () => {
    if (styleTagRef.current) {
      styleTagRef.current.remove();
    }
  };
}, []);
```

## 🎯 Troubleshooting

### Common Issues & Solutions

#### CSS Variables Not Applying
```javascript
// Ensure ThemeLogic is called before component render
const { themeConfig } = useThemeLogic();

// Check if CSS variables are set
console.log(getComputedStyle(document.documentElement).getPropertyValue('--nui-bg-color'));
```

#### Component Styles Not Updating
```javascript
// Ensure component is wrapped in theme provider
<ThemeProvider>
  <YourComponent />
</ThemeProvider>

// Check CSS specificity
button:active, button:focus {
  /* Use specific selectors */
}
```

#### Border Width Precision Not Working
```javascript
// Ensure parseFloat is used for decimal values
onChange={(e) => onChange({...settings, borderWidth: parseFloat(e.target.value)})}

// Ensure step="0.25" is set on input
<input step="0.25" />
```

#### Sidebar Menu Items Not Styled
```javascript
// Check for specific menu item selectors
.sidebar.sidebar a, nav.nav a, .sidebar-element nav a {
  /* Target menu items specifically */
}
```

## 🎯 Integration Examples

### Basic Integration
```jsx
import { ThemeCustomizer } from './theme-tool';

function App() {
  return (
    <div>
      <ThemeCustomizer />
      {/* Your application content */}
    </div>
  );
}
```

### Advanced Integration
```jsx
import { useThemeLogic, ButtonSettings } from './theme-tool';

function CustomComponent() {
  const { themeConfig, setThemeConfig } = useThemeLogic();
  
  return (
    <div style={{
      backgroundColor: themeConfig.backgroundColor,
      color: themeConfig.textColor
    }}>
      <ButtonSettings
        settings={themeConfig.buttons}
        onChange={(newSettings) => setThemeConfig({
          ...themeConfig,
          buttons: newSettings
        })}
      />
    </div>
  );
}
```

---

## 🎯 Quick Reference

### Essential Functions
- **useThemeLogic()**: Main hook for theme management
- **setThemeConfig()**: Update global theme settings
- **setComponentSettings()**: Update component-specific settings
- **applyTheme()**: Apply a theme preset

### Key CSS Variables
- **--nui-bg-color**: Main background color
- **--nui-text-color**: Main text color
- **--nui-buttons-bg-color**: Button background
- **--nui-buttons-text-color**: Button text color
- **--nui-sidebar-bg-color**: Sidebar background
- **--nui-sidebar-text-color**: Sidebar text color
- **--nui-outer-shadow**: Normal shadow state
- **--nui-inner-shadow**: Pressed shadow state

### Component Props
All settings components accept:
- **settings**: Current component configuration
- **onChange**: Update callback function
- **fontOptions**: Array of available fonts
- **fontWeightOptions**: Array of font weights

---

**This guide covers the complete working of the theme system. Reference this anytime you need to understand configuration options, CSS variables, or component behavior!** 🎯

**Last Updated**: January 23, 2026  
**Status**: Complete Working Reference