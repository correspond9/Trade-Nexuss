// Universal Theme Customization Tool
// Main export file for easy integration

export { useThemeLogic } from './ThemeLogic';
export { default as ThemeCustomizer } from './ThemeCustomizer';
export { default as ThemeSelection } from './ThemeSelection';
export { default as ButtonSettings } from './ButtonSettings';
export { default as InputSettings } from './InputSettings';
export { default as GlassCardSettings } from './GlassCardSettings';
export { default as SidebarSettings } from './SidebarSettings';
export { default as BackgroundOptions } from './BackgroundOptions';
export { GlobalControls, Notification } from './ThemeActions';
export { default as GlobalColorControls } from './GlobalColorControls';

// For easy import of all components
export const ThemeComponents = {
  ThemeCustomizer,
  ThemeSelection,
  ButtonSettings,
  InputSettings,
  GlassCardSettings,
  SidebarSettings,
  BackgroundOptions,
  GlobalControls,
  GlobalColorControls,
  Notification,
  useThemeLogic
};

// Default export
export default ThemeCustomizer;