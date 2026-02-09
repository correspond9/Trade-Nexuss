import { useThemeLogic } from './ThemeLogic';
import ThemeCustomizer from './ThemeCustomizer';
import ThemeSelection from './ThemeSelection';
import ButtonSettings from './ButtonSettings';
import InputSettings from './InputSettings';
import GlassCardSettings from './GlassCardSettings';
import SidebarSettings from './SidebarSettings';
import BackgroundOptions from './BackgroundOptions';
import { GlobalControls, Notification } from './ThemeActions';
import GlobalColorControls from './GlobalColorControls';

export {
  useThemeLogic,
  ThemeCustomizer,
  ThemeSelection,
  ButtonSettings,
  InputSettings,
  GlassCardSettings,
  SidebarSettings,
  BackgroundOptions,
  GlobalControls,
  Notification,
  GlobalColorControls,
};

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
