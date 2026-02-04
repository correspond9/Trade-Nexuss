# Trade Nexxus - Neumorphic Theme System

A comprehensive neumorphic design system with theme switching capabilities for the Trade Nexxus project.

## 📁 File Structure

```
frontend/theme_tokens/
├── neumorphic-theme.css      # Main theme CSS file
├── theme-components.js        # Theme management JavaScript
├── themes/                    # Individual theme files
│   ├── default.css           # Default theme
│   ├── ocean.css             # Ocean theme
│   ├── cloud.css             # Cloud theme
│   └── trade-nexxus.css      # Trade Nexxus theme
└── README.md                  # This documentation
```

## 🚀 Quick Start

### 1. Include in Your HTML

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your App - Trade Nexxus Theme</title>
    
    <!-- Include the theme CSS -->
    <link rel="stylesheet" href="../theme_tokens/neumorphic-theme.css">
    
    <!-- Optional: Include individual theme files -->
    <link rel="stylesheet" href="../theme_tokens/themes/default.css">
    <link rel="stylesheet" href="../theme_tokens/themes/ocean.css">
    <link rel="stylesheet" href="../theme_tokens/themes/cloud.css">
    <link rel="stylesheet" href="../theme_tokens/themes/trade-nexxus.css">
</head>
<body>
    <!-- Your content here -->
    
    <!-- Include the theme components JavaScript -->
    <script src="../theme_tokens/theme-components.js"></script>
</body>
</html>
```

### 2. Basic Usage

```javascript
// Set a theme
TradeNexxusTheme.setTheme('ocean');

// Get current theme
const currentTheme = TradeNexxusTheme.getCurrentTheme();

// Export current theme
TradeNexxusTheme.exportTheme();

// Apply theme to specific element
const element = document.getElementById('my-component');
TradeNexxusTheme.applyThemeToElement(element, 'cloud');
```

## 🎨 Available Themes

- **default** - Light beige theme with subtle shadows
- **ocean** - Blue ocean theme with cool tones
- **cloud** - Soft gray theme with cloud-like appearance
- **trade-nexxus** - Dark professional trading theme

## 🧩 Component Classes

### Neumorphic Elements

```html
<!-- Basic neumorphic container -->
<div class="nui-neuromorphic">Content here</div>

<!-- Inset (pressed) appearance -->
<div class="nui-neuromorphic-inset">Pressed content</div>

<!-- Clickable elements -->
<button class="nui-neuromorphic nui-clickable">Click me</button>

<!-- Convex (raised) appearance -->
<div class="nui-neuromorphic nui-neuromorphic-convex">Raised content</div>

<!-- Concave (inset) appearance -->
<div class="nui-neuromorphic nui-neuromorphic-concave">Inset content</div>
```

### Form Elements

```html
<!-- Input fields -->
<input type="text" class="nui-input" placeholder="Enter text...">
<input type="email" class="nui-input" placeholder="Email...">
<input type="password" class="nui-input" placeholder="Password...">
<select class="nui-input">
    <option>Select option...</option>
</select>
<textarea class="nui-input" placeholder="Message..."></textarea>
```

### Trading-Specific Buttons

```html
<!-- Buy button -->
<button class="nui-neuromorphic nui-buy nui-clickable">BUY</button>

<!-- Sell button -->
<button class="nui-neuromorphic nui-sell nui-clickable">SELL</button>

<!-- Profit indicator -->
<button class="nui-neuromorphic nui-profit nui-clickable">PROFIT</button>

<!-- Loss indicator -->
<button class="nui-neuromorphic nui-loss nui-clickable">LOSS</button>

<!-- Primary action -->
<button class="nui-neuromorphic nui-primary nui-clickable">Primary Action</button>
```

## 🎯 Theme Switching

### HTML Theme Selector

```html
<div class="theme-selector">
    <button class="theme-btn" data-theme="default">Default</button>
    <button class="theme-btn" data-theme="ocean">Ocean</button>
    <button class="theme-btn" data-theme="cloud">Cloud</button>
    <button class="theme-btn" data-theme="trade-nexxus">Trade Nexxus</button>
</div>

<script>
// Initialize theme selector (auto-initializes on load)
TradeNexxusTheme.initializeThemeSelector('.theme-selector .theme-btn');
</script>
```

### Programmatic Theme Switching

```javascript
// Set theme programmatically
TradeNexxusTheme.setTheme('ocean');

// Listen for theme changes
document.addEventListener('themeChanged', (event) => {
    console.log('Theme changed to:', event.detail.theme);
    // Update your app state here
});

// Check if theme is valid
if (TradeNexxusTheme.isValidTheme('ocean')) {
    TradeNexxusTheme.setTheme('ocean');
}
```

## 🎨 CSS Variables

### Base Variables

```css
:root {
    --nui-border-radius: 1rem;
    --nui-font-size-xs: 0.75rem;
    --nui-font-size-sm: 0.875rem;
    --nui-font-size-md: 1rem;
    --nui-font-size-lg: 1.125rem;
    --nui-spacing-xs: 0.25rem;
    --nui-spacing-sm: 0.5rem;
    --nui-spacing-md: 1rem;
    --nui-spacing-lg: 1.5rem;
}
```

### Theme Colors

```css
:root {
    --nui-bg-color: #dedad3;
    --nui-text-color: #1d2532;
    --nui-lights: #ffffff;
    --nui-shadows: #000000;
    --nui-border-color: #3b82f6;
}
```

### Trading Colors

```css
:root {
    --tn-profit: #10b981;
    --tn-loss: #ef4444;
    --tn-buy: #3b82f6;
    --tn-sell: #f59e0b;
}
```

## 🔧 Advanced Usage

### Custom Component Styling

```css
.my-custom-component {
    /* Use neumorphic base styles */
    background: var(--nui-bg-color);
    border-radius: var(--nui-border-radius);
    box-shadow: var(--nui-dark-outer-shadow), var(--nui-dark-outer-dark);
    
    /* Add custom styles */
    padding: var(--nui-spacing-md);
    color: var(--nui-text-color);
    
    /* Make it interactive */
    transition: all 0.3s ease;
}

.my-custom-component:hover {
    transform: translateY(-2px);
}

.my-custom-component:active {
    box-shadow: var(--nui-dark-inset-shadow), var(--nui-dark-inset-dark);
}
```

### Theme-Specific Overrides

```css
/* Override styles for specific themes */
.theme-ocean .my-custom-component {
    --nui-border-color: #2563eb;
}

.theme-cloud .my-custom-component {
    --nui-border-color: #6366f1;
}

.theme-tradenexxus .my-custom-component {
    --nui-border-color: #1e40af;
}
```

## 📱 Responsive Design

The theme system includes responsive design support:

```css
@media (max-width: 768px) {
    :root {
        --nui-border-radius: 0.75rem;
        --nui-spacing-md: 0.75rem;
        --nui-spacing-lg: 1rem;
    }
}
```

## 🎯 Interactive Elements

### Demo Buttons

```html
<button id="demo-btn1" class="nui-neuromorphic nui-neuromorphic-concave">Hover Me</button>
<button id="demo-btn2" class="nui-neuromorphic nui-buy nui-neuromorphic-concave">Click Me</button>
<button id="demo-btn3" class="nui-neuromorphic nui-sell nui-neuromorphic-concave">Press Me</button>

<script>
// Initialize interactive demo buttons
TradeNexxusTheme.initializeInteractiveButtons(['demo-btn1', 'demo-btn2', 'demo-btn3']);
</script>
```

## 📤 Export Themes

### Export Current Theme

```javascript
// Copy to clipboard
TradeNexxusTheme.exportTheme();

// Get CSS without copying
const css = TradeNexxusTheme.exportTheme(false);
console.log(css);
```

### Exported CSS Structure

The exported CSS includes:
- Base variables (border radius, colors)
- Universal colors (background, text, border)
- Trading colors (buy, sell, profit, loss)
- Theme-specific variables (if not default)

## 🔍 API Reference

### Functions

| Function | Description | Parameters | Returns |
|----------|-------------|------------|---------|
| `setTheme(theme, buttonElement)` | Set active theme | `theme: string`, `buttonElement?: HTMLElement` | `string` |
| `getCurrentTheme()` | Get current theme | - | `string` |
| `exportTheme(download)` | Export theme as CSS | `download?: boolean` | `string` |
| `initializeThemeSystem()` | Initialize entire system | - | `void` |
| `initializeThemeSelector(selector)` | Initialize theme buttons | `selector?: string` | `void` |
| `initializeInteractiveButtons(buttonIds)` | Initialize demo buttons | `buttonIds?: string[]` | `void` |
| `applyThemeToElement(element, theme)` | Apply theme to element | `element: HTMLElement`, `theme: string` | `void` |
| `getAvailableThemes()` | Get available themes | - | `string[]` |
| `isValidTheme(theme)` | Check if theme is valid | `theme: string` | `boolean` |

### Events

| Event | Description | Detail |
|-------|-------------|--------|
| `themeChanged` | Fired when theme changes | `{ theme: string, currentTheme: string }` |

## 🎨 Design Principles

### Neumorphic Design
- **Soft Shadows**: Multiple layered shadows create depth
- **Subtle Contrast**: Gentle color differences
- **Organic Shapes**: Rounded corners and smooth transitions
- **Tactile Feel**: Elements appear pressable and interactive

### Theme System
- **Consistent Variables**: All colors use CSS variables
- **Easy Switching**: One function call changes entire theme
- **Component Isolation**: Themes don't interfere with component logic
- **Export Capability**: Themes can be exported as standalone CSS

## 🚀 Integration with Frameworks

### React Integration

```jsx
import { useEffect } from 'react';
import '../theme_tokens/neumorphic-theme.css';

function ThemeProvider({ children }) {
    useEffect(() => {
        // Initialize theme system
        if (window.TradeNexxusTheme) {
            window.TradeNexxusTheme.initializeThemeSystem();
        }
    }, []);

    return <>{children}</>;
}

function ThemeButton({ theme, children }) {
    const handleClick = () => {
        if (window.TradeNexxusTheme) {
            window.TradeNexxusTheme.setTheme(theme);
        }
    };

    return (
        <button 
            className="nui-neuromorphic nui-clickable theme-btn" 
            data-theme={theme}
            onClick={handleClick}
        >
            {children}
        </button>
    );
}
```

### Vue Integration

```vue
<template>
    <div>
        <button 
            v-for="theme in themes" 
            :key="theme"
            class="nui-neuromorphic nui-clickable theme-btn"
            :data-theme="theme"
            @click="setTheme(theme)"
        >
            {{ theme.charAt(0).toUpperCase() + theme.slice(1) }}
        </button>
    </div>
</template>

<script>
import '../theme_tokens/neumorphic-theme.css';

export default {
    data() {
        return {
            themes: ['default', 'ocean', 'cloud', 'trade-nexxus']
        };
    },
    methods: {
        setTheme(theme) {
            if (window.TradeNexxusTheme) {
                window.TradeNexxusTheme.setTheme(theme);
            }
        }
    },
    mounted() {
        if (window.TradeNexxusTheme) {
            window.TradeNexxusTheme.initializeThemeSystem();
        }
    }
};
</script>
```

## 🔧 Customization

### Adding New Themes

1. Create a new theme file in `themes/` directory
2. Define theme variables
3. Include the theme file in your HTML

```css
/* themes/custom.css */
.theme-custom {
    --nui-bg-color: #your-bg-color;
    --nui-text-color: #your-text-color;
    --nui-lights: #your-light-color;
    --nui-shadows: #your-shadow-color;
    --nui-border-color: #your-border-color;
}
```

### Custom Components

```css
.my-custom-card {
    /* Base neumorphic styles */
    background: var(--nui-bg-color);
    border-radius: var(--nui-border-radius);
    box-shadow: var(--nui-dark-outer-shadow), var(--nui-dark-outer-dark);
    
    /* Custom styles */
    padding: var(--nui-spacing-lg);
    margin: var(--nui-spacing-md);
    
    /* Interactive states */
    transition: all 0.3s ease;
}

.my-custom-card:hover {
    transform: translateY(-2px);
    box-shadow: 
        var(--nui-dark-outer-shadow), 
        var(--nui-dark-outer-dark),
        0 8px 25px rgba(0, 0, 0, 0.15);
}
```

## 📝 Notes

- **Reference Tool**: `theme-preview.html` in `integration/` folder is the design reference tool
- **Production Files**: Use files in `theme_tokens/` for production
- **Browser Support**: Modern browsers with CSS custom properties support
- **Performance**: CSS variables provide excellent performance for theme switching
- **Accessibility**: Focus styles included for keyboard navigation
- **Responsive**: Mobile-friendly with responsive breakpoints

## 🤝 Contributing

When adding new themes or components:
1. Test in `theme-preview.html` first
2. Export and copy to `theme_tokens/` folder
3. Update this README with new features
4. Ensure cross-browser compatibility

---

**Trade Nexxus Theme System** - Professional neumorphic design for trading applications.
