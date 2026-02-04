/* Trade Nexxus - Neumorphic Theme Components */
/* Extracted from theme-preview.html for production use */

// Theme Management - Simplified
let currentTheme = 'default';

/**
 * Set the active theme
 * @param {string} theme - Theme name ('default', 'ocean', 'cloud', 'tradenexxus')
 * @param {HTMLElement} buttonElement - Optional button element to mark as active
 */
function setTheme(theme, buttonElement = null) {
    // Remove all theme classes
    document.body.classList.remove('theme-ocean', 'theme-cloud', 'theme-tradenexxus');
    
    // Add new theme class if not default
    if (theme !== 'default') {
        document.body.classList.add(`theme-${theme}`);
    }
    
    // Update active button
    document.querySelectorAll('.theme-selector .theme-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Activate clicked button
    if (buttonElement) {
        buttonElement.classList.add('active');
    }
    
    // Update current theme variable
    currentTheme = theme;
    
    // Dispatch custom event for theme change
    document.dispatchEvent(new CustomEvent('themeChanged', {
        detail: { theme, currentTheme }
    }));
    
    return currentTheme;
}

/**
 * Get the current active theme
 * @returns {string} Current theme name
 */
function getCurrentTheme() {
    return currentTheme;
}

/**
 * Export the current theme as CSS
 * @param {boolean} download - Whether to download as file (default: true)
 * @returns {string} Generated CSS
 */
function exportTheme(download = true) {
    const css = `/* Trade Nexxus Custom Neumorphic Theme */
:root {
    /* Base Variables */
    --nui-border-radius: ${getComputedStyle(document.documentElement).getPropertyValue('--nui-border-radius')};
    
    /* Universal Colors */
    --nui-bg-color: ${getComputedStyle(document.documentElement).getPropertyValue('--nui-bg-color')};
    --nui-border-color: ${getComputedStyle(document.documentElement).getPropertyValue('--nui-border-color')};
    
    /* Trading Colors */
    --tn-buy: ${getComputedStyle(document.documentElement).getPropertyValue('--tn-buy')};
    --tn-sell: ${getComputedStyle(document.documentElement).getPropertyValue('--tn-sell')};
    --tn-profit: ${getComputedStyle(document.documentElement).getPropertyValue('--tn-profit')};
    --tn-loss: ${getComputedStyle(document.documentElement).getPropertyValue('--tn-loss')};
    
    ${currentTheme !== 'default' ? `
    /* ${currentTheme.charAt(0).toUpperCase() + currentTheme.slice(1)} Theme */
    --nui-bg-color: ${getComputedStyle(document.documentElement).getPropertyValue('--nui-light-bg-color')};
    --nui-text-color: ${getComputedStyle(document.documentElement).getPropertyValue('--nui-light-text-color')};
    --nui-lights: ${getComputedStyle(document.documentElement).getPropertyValue('--nui-light-lights')};
    --nui-shadows: ${getComputedStyle(document.documentElement).getPropertyValue('--nui-light-shadows')};
    ` : ''}
}

/* Include the full Neumo UI styles from styles.css */
/* Add your custom components and overrides below */

/* Universal Theme Application */
body {
    background-color: var(--nui-bg-color);
}

.nui-neuromorphic, .nui-neuromorphic-inset {
    border: 2px solid var(--nui-border-color);
}
`.trim();

    if (download) {
        // Method 1: Copy to clipboard
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(css).then(() => {
                const fileName = `trade-nexxus-${currentTheme}-theme.css`;
                showExportNotification(`Theme CSS copied to clipboard!\n\nFile name: ${fileName}\n\nPaste this into a new .css file and save it.`);
                console.log(`Theme copied to clipboard: ${fileName}`);
            }).catch(err => {
                console.error('Failed to copy to clipboard:', err);
                fallbackExport(css);
            });
        } else {
            fallbackExport(css);
        }
    }
    
    return css;
}

/**
 * Show export notification
 * @param {string} message - Message to display
 */
function showExportNotification(message) {
    // Try to use alert first, fallback to console
    try {
        alert(message);
    } catch (e) {
        console.log(message);
    }
}

/**
 * Fallback export method
 * @param {string} css - CSS content to export
 */
function fallbackExport(css) {
    // Method 2: Display in textarea for manual copy
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: var(--nui-bg-color);
        border: 2px solid var(--nui-border-color);
        border-radius: var(--nui-border-radius);
        padding: 20px;
        box-shadow: var(--nui-dark-outer-shadow), var(--nui-dark-outer-light);
        z-index: 1000;
        max-width: 80%;
        max-height: 80%;
        overflow: auto;
    `;
    
    modal.innerHTML = `
        <h3 style="margin: 0 0 10px 0; color: var(--nui-text-color);">Export Theme CSS</h3>
        <p style="margin: 0 0 10px 0; color: var(--nui-text-color); font-size: 14px;">
            File name: <strong>trade-nexxus-${currentTheme}-theme.css</strong>
        </p>
        <textarea style="width: 100%; height: 300px; background: var(--nui-bg-color); 
                   color: var(--nui-text-color); border: 1px solid var(--nui-border-color); 
                   border-radius: var(--nui-border-radius); padding: 10px; 
                   font-family: monospace; font-size: 12px;">${css}</textarea>
        <div style="margin-top: 10px; text-align: right;">
            <button onclick="this.parentElement.parentElement.remove()" 
                    style="padding: 8px 16px; background: var(--tn-buy); color: white; 
                           border: none; border-radius: var(--nui-border-radius); 
                           cursor: pointer;">Close</button>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Auto-select text
    const textarea = modal.querySelector('textarea');
    textarea.select();
    textarea.setSelectionRange(0, 99999);
    
    console.log(`Theme displayed for manual copy: trade-nexxus-${currentTheme}-theme.css`);
}

/**
 * Initialize interactive demo buttons
 * @param {string[]} buttonIds - Array of button IDs to initialize
 */
function initializeInteractiveButtons(buttonIds = ['demo-btn1', 'demo-btn2', 'demo-btn3']) {
    buttonIds.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) {
            btn.addEventListener('click', function() {
                this.classList.add('nui-neuromorphic-active');
                setTimeout(() => this.classList.remove('nui-neuromorphic-active'), 150);
            });
        }
    });
}

/**
 * Initialize theme selector buttons
 * @param {string} selector - CSS selector for theme buttons
 */
function initializeThemeSelector(selector = '.theme-selector .theme-btn') {
    const themeButtons = document.querySelectorAll(selector);
    
    themeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const theme = this.dataset.theme || this.textContent.toLowerCase();
            setTheme(theme, this);
        });
    });
}

/**
 * Apply theme to a specific element
 * @param {HTMLElement} element - Element to apply theme to
 * @param {string} theme - Theme name
 */
function applyThemeToElement(element, theme) {
    // Remove all theme classes
    element.classList.remove('theme-ocean', 'theme-cloud', 'theme-tradenexxus');
    
    // Add new theme class if not default
    if (theme !== 'default') {
        element.classList.add(`theme-${theme}`);
    }
}

/**
 * Get available themes
 * @returns {string[]} Array of available theme names
 */
function getAvailableThemes() {
    return ['default', 'ocean', 'cloud', 'tradenexxus'];
}

/**
 * Check if a theme is valid
 * @param {string} theme - Theme name to check
 * @returns {boolean} Whether theme is valid
 */
function isValidTheme(theme) {
    return getAvailableThemes().includes(theme);
}

/**
 * Auto-initialize theme system
 * Call this function to set up the entire theme system
 */
function initializeThemeSystem() {
    // Initialize theme selector buttons
    initializeThemeSelector();
    
    // Initialize interactive demo buttons
    initializeInteractiveButtons();
    
    // Set default theme if not already set
    if (!currentTheme || currentTheme === 'default') {
        setTheme('default');
    }
    
    console.log('Trade Nexxus Theme System initialized');
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    // Node.js/CommonJS
    module.exports = {
        setTheme,
        getCurrentTheme,
        exportTheme,
        initializeThemeSystem,
        initializeThemeSelector,
        initializeInteractiveButtons,
        applyThemeToElement,
        getAvailableThemes,
        isValidTheme
    };
} else if (typeof window !== 'undefined') {
    // Browser global
    window.TradeNexxusTheme = {
        setTheme,
        getCurrentTheme,
        exportTheme,
        initializeThemeSystem,
        initializeThemeSelector,
        initializeInteractiveButtons,
        applyThemeToElement,
        getAvailableThemes,
        isValidTheme
    };
}

// Auto-initialize if DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeThemeSystem);
} else {
    initializeThemeSystem();
}
