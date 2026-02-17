import { useState, useEffect, useRef } from 'react';
import { apiService } from '../../services/apiService';

const cloneDeep = (value) => JSON.parse(JSON.stringify(value));

const DEFAULT_COMPONENT_SETTINGS = {
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
    fontWeight: '400',
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
    fontWeight: '400',
    fontStyle: 'normal',
    fontSize: 14,
  },
  glassCards: {
    borderRadius:16,
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
    fontWeight: '400',
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
    fontWeight: '400',
    fontStyle: 'normal',
    fontSize: 14,
  },
};

const THEME_VAR_KEYS = [
  '--nui-border-radius',
  '--nui-shadow-distance',
  '--nui-shadow-intensity',
  '--nui-shadow-light-intensity',
  '--nui-shadow-dark-intensity',
  '--nui-shadow-blur',
  '--nui-bg-color',
  '--nui-shadow-light',
  '--nui-shadow-dark',
  '--nui-text-color',
  '--nui-logo-bg',
  '--nui-sidebar-color',
  '--nui-sidebar-opacity',
  '--nui-glass-card-color',
  '--nui-glass-card-opacity',
  '--nui-light-source',
  '--nui-heading-color',
  '--nui-body-color',
  '--nui-button-text-color',
  '--nui-heading-font-size',
  '--nui-body-font-size',
  '--nui-button-font-size',
  '--nui-button-font-family',
  '--nui-button-font-weight',
  '--nui-button-font-style',
];

export const useThemeLogic = () => {
  const [themeConfig, setThemeConfig] = useState({
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
  });

  const [componentSettings, setComponentSettings] = useState({
    ...cloneDeep(DEFAULT_COMPONENT_SETTINGS)
  });

  const styleTagRef = useRef(null);
  const originalThemeVarsRef = useRef(null);
  const keepAppliedOnUnmountRef = useRef(false);

  const themes = {
    'Default': {
      borderRadius: 10,
      shadowDistance: 6,
      shadowIntensity: 28,
      shadowLightIntensity: 45,
      shadowDarkIntensity: 30,
      shadowBlur: 14,
      backgroundColor: '#f8fafc',
      shadowLight: '#ffffff',
      shadowDark: '#cbd5e1',
      textColor: '#111827',
      logoBackground: '#2563eb',
      sidebarColor: '#1e293b',
      sidebarOpacity: 95,
      glassCardColor: '#ffffff',
      glassCardOpacity: 90,
      lightSource: 'top-left',
      headingColor: '#1e293b',
      bodyColor: '#475569',
      buttonTextColor: '#ffffff',
      headingFontSize: 26,
      bodyFontSize: 15,
      buttonFontSize: 14,
    },
    'Tailwind Mixed Light': {
      borderRadius: 12,
      shadowDistance: 6,
      shadowIntensity: 35,
      shadowLightIntensity: 55,
      shadowDarkIntensity: 30,
      shadowBlur: 14,
      backgroundColor: '#f8fafc',
      shadowLight: '#ffffff',
      shadowDark: '#cbd5e1',
      textColor: '#0f172a',
      logoBackground: '#0f172a',
      sidebarColor: '#111827',
      sidebarOpacity: 96,
      glassCardColor: '#ffffff',
      glassCardOpacity: 96,
      lightSource: 'top-left',
      headingColor: '#111827',
      bodyColor: '#334155',
      buttonTextColor: '#ffffff',
      headingFontSize: 26,
      bodyFontSize: 15,
      buttonFontSize: 14,
    },
    'Ocean': {
      borderRadius: 14,
      shadowDistance: 9,
      shadowIntensity: 44,
      shadowLightIntensity: 62,
      shadowDarkIntensity: 38,
      shadowBlur: 20,
      backgroundColor: '#e6f4ff',
      shadowLight: '#ffffff',
      shadowDark: '#60a5fa',
      textColor: '#0c4a6e',
      logoBackground: '#0ea5e9',
      sidebarColor: '#0c4a6e',
      sidebarOpacity: 90,
      glassCardColor: '#f0f9ff',
      glassCardOpacity: 85,
      lightSource: 'top-left',
      headingColor: '#0c4a6e',
      bodyColor: '#0e7490',
      buttonTextColor: '#ffffff',
      headingFontSize: 30,
      bodyFontSize: 16,
      buttonFontSize: 14,
    },
    'NeuMo': {
      borderRadius: 18,
      shadowDistance: 8,
      shadowIntensity: 52,
      shadowLightIntensity: 74,
      shadowDarkIntensity: 44,
      shadowBlur: 22,
      backgroundColor: '#eef2f7',
      shadowLight: '#ffffff',
      shadowDark: '#b6c2cf',
      textColor: '#18181b',
      logoBackground: '#52525b',
      sidebarColor: '#27272a',
      sidebarOpacity: 95,
      glassCardColor: '#eef2f7',
      glassCardOpacity: 95,
      lightSource: 'top-left',
      headingColor: '#18181b',
      bodyColor: '#3f3f46',
      buttonTextColor: '#ffffff',
      headingFontSize: 24,
      bodyFontSize: 15,
      buttonFontSize: 13,
    },
    'Dark': {
      borderRadius: 8,
      shadowDistance: 5,
      shadowIntensity: 82,
      shadowLightIntensity: 24,
      shadowDarkIntensity: 92,
      shadowBlur: 14,
      backgroundColor: '#111827',
      shadowLight: '#374151',
      shadowDark: '#000000',
      textColor: '#f9fafb',
      logoBackground: '#000000',
      sidebarColor: '#09090b',
      sidebarOpacity: 100,
      glassCardColor: '#1f2937',
      glassCardOpacity: 90,
      lightSource: 'top-left',
      headingColor: '#f3f4f6',
      bodyColor: '#d1d5db',
      buttonTextColor: '#ffffff',
      headingFontSize: 28,
      bodyFontSize: 16,
      buttonFontSize: 14,
    },
  };

  const themeComponentPresets = {
    'Default': cloneDeep(DEFAULT_COMPONENT_SETTINGS),
    'Tailwind Mixed Light': {
      ...cloneDeep(DEFAULT_COMPONENT_SETTINGS),
      buttons: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.buttons),
        borderRadius: 8,
        shadowDistance: 3,
        shadowBlur: 8,
        backgroundColor: '#2563eb',
        borderColor: '#2563eb',
      },
      inputs: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.inputs),
        borderRadius: 8,
        borderColor: '#cbd5e1',
      },
      glassCards: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.glassCards),
        borderRadius: 12,
        shadowDistance: 5,
        shadowBlur: 12,
      },
      sidebar: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.sidebar),
        backgroundColor: '#111827',
        textColor: '#e5e7eb',
      },
    },
    'Ocean': {
      ...cloneDeep(DEFAULT_COMPONENT_SETTINGS),
      buttons: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.buttons),
        backgroundColor: '#0ea5e9',
        borderColor: '#0284c7',
        shadowDark: '#0369a1',
      },
      inputs: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.inputs),
        backgroundColor: '#f0f9ff',
        borderColor: '#7dd3fc',
      },
      glassCards: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.glassCards),
        backgroundColor: '#e0f2fe',
        borderColor: '#7dd3fc',
        textColor: '#0c4a6e',
      },
      sidebar: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.sidebar),
        backgroundColor: '#0c4a6e',
        textColor: '#dbeafe',
      },
    },
    'NeuMo': {
      ...cloneDeep(DEFAULT_COMPONENT_SETTINGS),
      buttons: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.buttons),
        borderRadius: 14,
        shadowDistance: 6,
        shadowBlur: 16,
        backgroundColor: '#e2e8f0',
        textColor: '#1e293b',
        borderColor: '#cbd5e1',
        shadowDark: '#94a3b8',
      },
      inputs: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.inputs),
        borderRadius: 12,
        shadowDistance: 4,
        shadowBlur: 14,
        backgroundColor: '#eef2f7',
        borderColor: '#cbd5e1',
      },
      glassCards: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.glassCards),
        borderRadius: 18,
        shadowDistance: 8,
        shadowBlur: 18,
        backgroundColor: '#eef2f7',
        borderColor: '#d6dde7',
      },
      sidebar: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.sidebar),
        backgroundColor: '#dbe2ec',
        textColor: '#334155',
        borderColor: '#c1ccd9',
      },
    },
    'Dark': {
      ...cloneDeep(DEFAULT_COMPONENT_SETTINGS),
      buttons: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.buttons),
        backgroundColor: '#4f46e5',
        borderColor: '#4338ca',
        shadowLight: '#6366f1',
        shadowDark: '#0f172a',
      },
      inputs: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.inputs),
        backgroundColor: '#111827',
        textColor: '#f9fafb',
        borderColor: '#374151',
        shadowLight: '#374151',
        shadowDark: '#000000',
      },
      glassCards: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.glassCards),
        backgroundColor: '#1f2937',
        textColor: '#f3f4f6',
        borderColor: '#374151',
        shadowLight: '#374151',
        shadowDark: '#000000',
      },
      sidebar: {
        ...cloneDeep(DEFAULT_COMPONENT_SETTINGS.sidebar),
        backgroundColor: '#0b1220',
        textColor: '#e5e7eb',
        borderColor: '#1f2937',
      },
    },
  };

  const getThemePreset = (themeName) => {
    const presetConfig = themes[themeName];
    if (!presetConfig) {
      return null;
    }
    const presetComponents = themeComponentPresets[themeName] || themeComponentPresets['Default'];
    return {
      config: cloneDeep(presetConfig),
      componentSettings: cloneDeep(presetComponents),
    };
  };

  const hexToRgba = (hex, alpha) => {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  const getShadowDirection = (lightSource, distance = null) => {
    const actualDistance = distance || 10;
    switch(lightSource) {
      case 'top-left':
        return { x: actualDistance, y: actualDistance, xNeg: -actualDistance, yNeg: -actualDistance };
      case 'top-right':
        return { x: -actualDistance, y: actualDistance, xNeg: actualDistance, yNeg: -actualDistance };
      case 'bottom-left':
        return { x: actualDistance, y: -actualDistance, xNeg: -actualDistance, yNeg: actualDistance };
      case 'bottom-right':
        return { x: -actualDistance, y: -actualDistance, xNeg: actualDistance, yNeg: actualDistance };
      default:
        return { x: actualDistance, y: actualDistance, xNeg: -actualDistance, yNeg: -actualDistance };
    }
  };

  useEffect(() => {
    const hydrateFromLocal = () => {
      const savedConfig =
        localStorage.getItem('themeDraftConfig') ||
        localStorage.getItem('appliedThemeConfig') ||
        localStorage.getItem('customThemeConfig');
      const savedComponentSettings =
        localStorage.getItem('themeDraftComponentSettings') ||
        localStorage.getItem('appliedComponentSettings') ||
        localStorage.getItem('componentSettings');
      if (savedConfig) {
        try {
          setThemeConfig(JSON.parse(savedConfig));
        } catch (_e) {
          // ignore malformed local config
        }
      }
      if (savedComponentSettings) {
        try {
          setComponentSettings(JSON.parse(savedComponentSettings));
        } catch (_e) {
          // ignore malformed local component settings
        }
      }
    };

    const hydrateFromServer = async () => {
      try {
        const response = await apiService.get('/theme-config');
        const data = response?.data || response;
        const themeConfigFromServer = data?.theme_config;
        const componentSettingsFromServer = data?.component_settings;
        if (themeConfigFromServer && componentSettingsFromServer) {
          setThemeConfig(themeConfigFromServer);
          setComponentSettings(componentSettingsFromServer);
          localStorage.setItem('appliedThemeConfig', JSON.stringify(themeConfigFromServer));
          localStorage.setItem('appliedComponentSettings', JSON.stringify(componentSettingsFromServer));
          localStorage.setItem('customThemeConfig', JSON.stringify(themeConfigFromServer));
          localStorage.setItem('componentSettings', JSON.stringify(componentSettingsFromServer));
          localStorage.setItem('themeDraftConfig', JSON.stringify(themeConfigFromServer));
          localStorage.setItem('themeDraftComponentSettings', JSON.stringify(componentSettingsFromServer));
          return;
        }
      } catch (_e) {
        // ignore and fallback to local state
      }
      hydrateFromLocal();
    };

    hydrateFromServer();
  }, []);

  useEffect(() => {
    if (originalThemeVarsRef.current) return;
    const rootStyle = getComputedStyle(document.documentElement);
    const snapshot = {};
    THEME_VAR_KEYS.forEach((key) => {
      snapshot[key] = rootStyle.getPropertyValue(key);
    });
    originalThemeVarsRef.current = snapshot;
  }, []);

  useEffect(() => {
    // Apply all theme variables including component-specific CSS variables
    document.documentElement.style.setProperty('--nui-border-radius', `${themeConfig.borderRadius}px`);
    document.documentElement.style.setProperty('--nui-shadow-distance', `${themeConfig.shadowDistance}px`);
    document.documentElement.style.setProperty('--nui-shadow-intensity', themeConfig.shadowIntensity);
    document.documentElement.style.setProperty('--nui-shadow-light-intensity', themeConfig.shadowLightIntensity);
    document.documentElement.style.setProperty('--nui-shadow-dark-intensity', themeConfig.shadowDarkIntensity);
    document.documentElement.style.setProperty('--nui-shadow-blur', `${themeConfig.shadowBlur}px`);
    document.documentElement.style.setProperty('--nui-bg-color', themeConfig.backgroundColor);
    document.documentElement.style.setProperty('--nui-shadow-light', themeConfig.shadowLight);
    document.documentElement.style.setProperty('--nui-shadow-dark', themeConfig.shadowDark);
    document.documentElement.style.setProperty('--nui-text-color', themeConfig.textColor);
    document.documentElement.style.setProperty('--nui-logo-bg', themeConfig.logoBackground);
    document.documentElement.style.setProperty('--nui-sidebar-color', themeConfig.sidebarColor);
    document.documentElement.style.setProperty('--nui-sidebar-opacity', themeConfig.sidebarOpacity / 100);
    document.documentElement.style.setProperty('--nui-glass-card-color', themeConfig.glassCardColor);
    document.documentElement.style.setProperty('--nui-glass-card-opacity', themeConfig.glassCardOpacity / 100);
    document.documentElement.style.setProperty('--nui-light-source', themeConfig.lightSource);
    document.documentElement.style.setProperty('--nui-heading-color', themeConfig.headingColor);
    document.documentElement.style.setProperty('--nui-body-color', themeConfig.bodyColor);
    document.documentElement.style.setProperty('--nui-button-text-color', themeConfig.buttonTextColor);
    document.documentElement.style.setProperty('--nui-heading-font-size', `${themeConfig.headingFontSize}px`);
    document.documentElement.style.setProperty('--nui-body-font-size', `${themeConfig.bodyFontSize}px`);
    document.documentElement.style.setProperty('--nui-button-font-size', `${themeConfig.buttonFontSize}px`);
    document.documentElement.style.setProperty('--nui-button-font-family', themeConfig.buttonFontFamily);
    document.documentElement.style.setProperty('--nui-button-font-weight', themeConfig.buttonFontWeight);
    document.documentElement.style.setProperty('--nui-button-font-style', themeConfig.buttonFontStyle);

    // Apply component-specific settings
    Object.keys(componentSettings).forEach(component => {
      const settings = componentSettings[component];
      document.documentElement.style.setProperty(`--nui-${component}-border-radius`, `${settings.borderRadius}px`);
      document.documentElement.style.setProperty(`--nui-${component}-shadow-distance`, `${settings.shadowDistance}px`);
      document.documentElement.style.setProperty(`--nui-${component}-shadow-light-intensity`, settings.shadowLightIntensity);
      document.documentElement.style.setProperty(`--nui-${component}-shadow-dark-intensity`, settings.shadowDarkIntensity);
      document.documentElement.style.setProperty(`--nui-${component}-shadow-blur`, `${settings.shadowBlur}px`);
      document.documentElement.style.setProperty(`--nui-${component}-bg-color`, settings.backgroundColor);
      document.documentElement.style.setProperty(`--nui-${component}-shadow-light`, settings.shadowLight);
      document.documentElement.style.setProperty(`--nui-${component}-shadow-dark`, settings.shadowDark);
      document.documentElement.style.setProperty(`--nui-${component}-text-color`, settings.textColor);
      document.documentElement.style.setProperty(`--nui-${component}-border-width`, `${settings.borderWidth}px`);
      document.documentElement.style.setProperty(`--nui-${component}-border-style`, settings.borderStyle);
      document.documentElement.style.setProperty(`--nui-${component}-border-color`, settings.borderColor);
      document.documentElement.style.setProperty(`--nui-${component}-font-size`, `${settings.fontSize}px`);
      document.documentElement.style.setProperty(`--nui-${component}-font-family`, settings.fontFamily);
      document.documentElement.style.setProperty(`--nui-${component}-font-weight`, settings.fontWeight);
      document.documentElement.style.setProperty(`--nui-${component}-font-style`, settings.fontStyle);
      
      // Generate component-specific shadows
      const componentLightColor = settings.shadowLight;
      const componentDarkColor = settings.shadowDark;
      const componentLightIntensity = settings.shadowLightIntensity / 100;
      const componentDarkIntensity = settings.shadowDarkIntensity / 100;
      
      const applyComponentIntensity = (hexColor, intensity, isLightShadow) => {
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
      
      const componentLightRgba = applyComponentIntensity(componentLightColor, componentLightIntensity, true);
      const componentDarkRgba = applyComponentIntensity(componentDarkColor, componentDarkIntensity, false);
      const componentDirection = getShadowDirection(themeConfig.lightSource, settings.shadowDistance);
      
      const componentOuterShadow = `${componentDirection.x}px ${componentDirection.y}px ${settings.shadowBlur}px ${componentLightRgba}, ${componentDirection.xNeg}px ${componentDirection.yNeg}px ${settings.shadowBlur}px ${componentDarkRgba}`;
      const componentInnerShadow = `inset ${componentDirection.x}px ${componentDirection.y}px ${settings.shadowBlur}px ${componentLightRgba}, inset ${componentDirection.xNeg}px ${componentDirection.yNeg}px ${settings.shadowBlur}px ${componentDarkRgba}`;
      
      document.documentElement.style.setProperty(`--nui-${component}-outer-shadow`, componentOuterShadow);
      document.documentElement.style.setProperty(`--nui-${component}-inner-shadow`, componentInnerShadow);
    });
    
    // Apply shadow intensity to shadow colors
    const lightColor = themeConfig.shadowLight;
    const darkColor = themeConfig.shadowDark;
    const lightIntensity = themeConfig.shadowLightIntensity / 100;
    const darkIntensity = themeConfig.shadowDarkIntensity / 100;
    
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
    
    const lightRgba = applyIntensity(lightColor, lightIntensity, true);
    const darkRgba = applyIntensity(darkColor, darkIntensity, false);
    
    const direction = getShadowDirection(themeConfig.lightSource);
    
    const outerShadow = `${direction.x}px ${direction.y}px ${themeConfig.shadowBlur}px ${lightRgba}, ${direction.xNeg}px ${direction.yNeg}px ${themeConfig.shadowBlur}px ${darkRgba}`;
    const innerShadow = `inset ${direction.x}px ${direction.y}px ${themeConfig.shadowBlur}px ${lightRgba}, inset ${direction.xNeg}px ${direction.yNeg}px ${themeConfig.shadowBlur}px ${darkRgba}`;
    
    document.documentElement.style.setProperty('--nui-outer-shadow', outerShadow);
    document.documentElement.style.setProperty('--nui-inner-shadow', innerShadow);
    
    // Cleanup previous style tag
    if (styleTagRef.current) {
      styleTagRef.current.remove();
    }
    
    // Create dynamic CSS with proper glass card styling
    const css = `
      button {
        border-radius: var(--nui-buttons-border-radius, ${componentSettings.buttons.borderRadius}px) !important;
        box-shadow: var(--nui-buttons-outer-shadow) !important;
        border: var(--nui-buttons-border-width, ${componentSettings.buttons.borderWidth}px) var(--nui-buttons-border-style, ${componentSettings.buttons.borderStyle}) var(--nui-buttons-border-color, ${componentSettings.buttons.borderColor}) !important;
        font-family: var(--nui-buttons-font-family, ${componentSettings.buttons.fontFamily}) !important;
        font-weight: var(--nui-buttons-font-weight, ${componentSettings.buttons.fontWeight}) !important;
        font-style: var(--nui-buttons-font-style, ${componentSettings.buttons.fontStyle}) !important;
        font-size: var(--nui-buttons-font-size, ${componentSettings.buttons.fontSize}px) !important;
        transition: all 0.2s ease !important;
      }

      button:not([class*="bg-"]) {
        background-color: var(--nui-buttons-bg-color, ${componentSettings.buttons.backgroundColor}) !important;
      }

      button:not([class*="text-"]) {
        color: var(--nui-buttons-text-color, ${componentSettings.buttons.textColor}) !important;
      }
      
      button:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--nui-buttons-outer-shadow), 0 4px 8px rgba(0,0,0,0.1) !important;
      }
      
      button:active, button:focus {
        transform: translateY(0px) !important;
        box-shadow: var(--nui-buttons-inner-shadow) !important;
      }
      
      button:active:focus, button:focus-visible {
        transform: translateY(0px) !important;
        box-shadow: var(--nui-buttons-inner-shadow) !important;
      }
      
      input, select, textarea {
        border-radius: var(--nui-inputs-border-radius, ${componentSettings.inputs.borderRadius}px) !important;
        box-shadow: var(--nui-inputs-outer-shadow) !important;
        background-color: var(--nui-inputs-bg-color, ${componentSettings.inputs.backgroundColor}) !important;
        color: var(--nui-inputs-text-color, ${componentSettings.inputs.textColor}) !important;
        border: var(--nui-inputs-border-width, ${componentSettings.inputs.borderWidth}px) var(--nui-inputs-border-style, ${componentSettings.inputs.borderStyle}) var(--nui-inputs-border-color, ${componentSettings.inputs.borderColor}) !important;
        font-family: var(--nui-inputs-font-family, ${componentSettings.inputs.fontFamily}) !important;
        font-weight: var(--nui-inputs-font-weight, ${componentSettings.inputs.fontWeight}) !important;
        font-style: var(--nui-inputs-font-style, ${componentSettings.inputs.fontStyle}) !important;
        font-size: var(--nui-inputs-font-size, ${componentSettings.inputs.fontSize}px) !important;
      }
      
      .glass-card.glass-card {
        border-radius: var(--nui-glassCards-border-radius, ${componentSettings.glassCards.borderRadius}px) !important;
        box-shadow: var(--nui-glassCards-outer-shadow) !important;
        background-color: var(--nui-glassCards-bg-color, ${componentSettings.glassCards.backgroundColor}) !important;
        background: var(--nui-glassCards-bg-color, ${componentSettings.glassCards.backgroundColor}) !important;
        border: var(--nui-glassCards-border-width, ${componentSettings.glassCards.borderWidth}px) var(--nui-glassCards-border-style, ${componentSettings.glassCards.borderStyle}) var(--nui-glassCards-border-color, ${componentSettings.glassCards.borderColor}) !important;
        font-family: var(--nui-glassCards-font-family, ${componentSettings.glassCards.fontFamily}) !important;
        font-weight: var(--nui-glassCards-font-weight, ${componentSettings.glassCards.fontWeight}) !important;
        font-style: var(--nui-glassCards-font-style, ${componentSettings.glassCards.fontStyle}) !important;
        font-size: var(--nui-glassCards-font-size, ${componentSettings.glassCards.fontSize}px) !important;
      }
      input[type="range"] {
        box-shadow: none !important;
        border: none !important;
      }

      input[type="radio"],
      input[type="checkbox"] {
        box-shadow: none !important;
      }

      input[type="radio"] {
        border-radius: 50% !important;
      }
      
      .sidebar.sidebar, nav.nav, .sidebar-element nav {
        border-radius: var(--nui-sidebar-border-radius, ${componentSettings.sidebar.borderRadius}px) !important;
        box-shadow: var(--nui-sidebar-outer-shadow) !important;
        background-color: var(--nui-sidebar-bg-color, ${componentSettings.sidebar.backgroundColor}) !important;
        background: var(--nui-sidebar-bg-color, ${componentSettings.sidebar.backgroundColor}) !important;
        opacity: var(--nui-sidebar-opacity, ${themeConfig.sidebarOpacity / 100}) !important;
        color: var(--nui-sidebar-text-color, ${componentSettings.sidebar.textColor}) !important;
        font-family: var(--nui-sidebar-font-family, ${componentSettings.sidebar.fontFamily}) !important;
        font-weight: var(--nui-sidebar-font-weight, ${componentSettings.sidebar.fontWeight}) !important;
        font-style: var(--nui-sidebar-font-style, ${componentSettings.sidebar.fontStyle}) !important;
        font-size: var(--nui-sidebar-font-size, ${componentSettings.sidebar.fontSize}px) !important;
      }
      
      .sidebar.sidebar a, nav.nav a, .sidebar-element nav a {
        color: var(--nui-sidebar-text-color, ${componentSettings.sidebar.textColor}) !important;
        font-family: var(--nui-sidebar-font-family, ${componentSettings.sidebar.fontFamily}) !important;
        font-weight: var(--nui-sidebar-font-weight, ${componentSettings.sidebar.fontWeight}) !important;
        font-style: var(--nui-sidebar-font-style, ${componentSettings.sidebar.fontStyle}) !important;
        font-size: var(--nui-sidebar-font-size, ${componentSettings.sidebar.fontSize}px) !important;
      }
      
      body {
        ${themeConfig.backgroundType === 'gradient' ? 
          `background: linear-gradient(${themeConfig.gradientDirection}, ${themeConfig.gradientStart}, ${themeConfig.gradientEnd}) !important;` : 
          themeConfig.backgroundType === 'wallpaper' ? 
          `background: url(${themeConfig.wallpaperImage}) !important; background-size: cover !important;` : 
          `background-color: ${themeConfig.backgroundColor} !important;`}
      }
      
      h1, h2, h3, h4, h5, h6 {
        color: var(--nui-heading-color, ${themeConfig.headingColor}) !important;
        font-size: var(--nui-heading-font-size, ${themeConfig.headingFontSize}px) !important;
      }
      
      p, span, div {
        color: var(--nui-body-color, ${themeConfig.bodyColor}) !important;
        font-size: var(--nui-body-font-size, ${themeConfig.bodyFontSize}px) !important;
      }
    `;
    
    const styleTag = document.createElement('style');
    styleTag.textContent = css;
    document.head.appendChild(styleTag);
    styleTagRef.current = styleTag;
    
    // Save as draft only (preview state)
    localStorage.setItem('themeDraftConfig', JSON.stringify(themeConfig));
    localStorage.setItem('themeDraftComponentSettings', JSON.stringify(componentSettings));
  }, [themeConfig, componentSettings]);

  useEffect(() => {
    return () => {
      if (keepAppliedOnUnmountRef.current) {
        return;
      }

      try {
        if (styleTagRef.current) {
          styleTagRef.current.remove();
          styleTagRef.current = null;
        }

        const original = originalThemeVarsRef.current || {};
        THEME_VAR_KEYS.forEach((key) => {
          const value = original[key];
          if (value === undefined || value === null || value === '') {
            document.documentElement.style.removeProperty(key);
          } else {
            document.documentElement.style.setProperty(key, value);
          }
        });
      } catch (_e) {
        // best effort cleanup
      }
    };
  }, []);

  const applyThemeGlobally = () => {
    const persist = async () => {
      keepAppliedOnUnmountRef.current = true;
      localStorage.setItem('appliedThemeConfig', JSON.stringify(themeConfig));
      localStorage.setItem('appliedComponentSettings', JSON.stringify(componentSettings));
      localStorage.setItem('customThemeConfig', JSON.stringify(themeConfig));
      localStorage.setItem('componentSettings', JSON.stringify(componentSettings));
      localStorage.setItem('themeDraftConfig', JSON.stringify(themeConfig));
      localStorage.setItem('themeDraftComponentSettings', JSON.stringify(componentSettings));

      try {
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('theme:applied'));
        }
      } catch (_e) {
        // ignore event dispatch errors
      }

      await apiService.post('/admin/theme-config', {
        theme_config: themeConfig,
        component_settings: componentSettings,
      });

      return true;
    };

    return persist();
  };

  return {
    themeConfig,
    setThemeConfig,
    componentSettings,
    setComponentSettings,
    themes,
    styleTagRef,
    applyThemeGlobally,
    getThemePreset
  };
};