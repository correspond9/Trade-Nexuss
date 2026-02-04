import React from 'react';

const ButtonSettings = ({ settings, onChange, fontOptions, fontWeightOptions }) => (
  <div className="space-y-3">
    <div>
      <label className="block text-xs font-medium mb-1">Border Radius: {settings.borderRadius}px</label>
      <input
        type="range"
        min="0"
        max="50"
        value={settings.borderRadius}
        onChange={(e) => onChange({...settings, borderRadius: parseInt(e.target.value)})}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
      />
    </div>
    <div>
      <label className="block text-xs font-medium mb-1">Shadow Distance: {settings.shadowDistance}px</label>
      <input
        type="range"
        min="0"
        max="20"
        value={settings.shadowDistance}
        onChange={(e) => onChange({...settings, shadowDistance: parseInt(e.target.value)})}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
      />
    </div>
    <div>
      <label className="block text-xs font-medium mb-1">Light Shadow Intensity: {settings.shadowLightIntensity}%</label>
      <input
        type="range"
        min="1"
        max="100"
        value={settings.shadowLightIntensity}
        onChange={(e) => onChange({...settings, shadowLightIntensity: parseInt(e.target.value)})}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
      />
    </div>
    <div>
      <label className="block text-xs font-medium mb-1">Dark Shadow Intensity: {settings.shadowDarkIntensity}%</label>
      <input
        type="range"
        min="1"
        max="100"
        value={settings.shadowDarkIntensity}
        onChange={(e) => onChange({...settings, shadowDarkIntensity: parseInt(e.target.value)})}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
      />
    </div>
    <div>
      <label className="block text-xs font-medium mb-1">Shadow Blur: {settings.shadowBlur}px</label>
      <input
        type="range"
        min="0"
        max="30"
        value={settings.shadowBlur}
        onChange={(e) => onChange({...settings, shadowBlur: parseInt(e.target.value)})}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
      />
    </div>
    <div>
      <label className="block text-xs font-medium mb-1">Background Color</label>
      <div className="flex gap-1">
        <input
          type="color"
          value={settings.backgroundColor}
          onChange={(e) => onChange({...settings, backgroundColor: e.target.value})}
          className="h-8 w-12 rounded cursor-pointer"
        />
        <input
          type="text"
          value={settings.backgroundColor}
          onChange={(e) => onChange({...settings, backgroundColor: e.target.value})}
          className="flex-1 px-2 py-1 rounded border border-gray-300 text-xs"
          placeholder="#3b82f6"
        />
      </div>
    </div>
    <div>
      <label className="block text-xs font-medium mb-1">Text Color</label>
      <div className="flex gap-1">
        <input
          type="color"
          value={settings.textColor}
          onChange={(e) => onChange({...settings, textColor: e.target.value})}
          className="h-8 w-12 rounded cursor-pointer"
        />
        <input
          type="text"
          value={settings.textColor}
          onChange={(e) => onChange({...settings, textColor: e.target.value})}
          className="flex-1 px-2 py-1 rounded border border-gray-300 text-xs"
          placeholder="#ffffff"
        />
      </div>
    </div>
    <div>
      <label className="block text-xs font-medium mb-1">Border Width: {settings.borderWidth}px</label>
      <input
        type="range"
        min="0"
        max="10"
        step="0.25"
        value={settings.borderWidth}
        onChange={(e) => onChange({...settings, borderWidth: parseFloat(e.target.value)})}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
      />
    </div>
    <div>
      <label className="block text-xs font-medium mb-1">Border Style</label>
      <select
        value={settings.borderStyle}
        onChange={(e) => onChange({...settings, borderStyle: e.target.value})}
        className="w-full px-2 py-1 rounded border border-gray-300 text-xs bg-white"
      >
        <option value="solid">Solid</option>
        <option value="dashed">Dashed</option>
        <option value="dotted">Dotted</option>
        <option value="double">Double</option>
        <option value="groove">Groove</option>
        <option value="ridge">Ridge</option>
        <option value="inset">Inset</option>
        <option value="outset">Outset</option>
      </select>
    </div>
    <div>
      <label className="block text-xs font-medium mb-1">Border Color</label>
      <div className="flex gap-1">
        <input
          type="color"
          value={settings.borderColor}
          onChange={(e) => onChange({...settings, borderColor: e.target.value})}
          className="h-8 w-12 rounded cursor-pointer"
        />
        <input
          type="text"
          value={settings.borderColor}
          onChange={(e) => onChange({...settings, borderColor: e.target.value})}
          className="flex-1 px-2 py-1 rounded border border-gray-300 text-xs"
          placeholder="#2563eb"
        />
      </div>
    </div>
    <div>
      <label className="block text-xs font-medium mb-1">Font Family</label>
      <select
        value={settings.fontFamily}
        onChange={(e) => onChange({...settings, fontFamily: e.target.value})}
        className="w-full px-2 py-1 rounded border border-gray-300 text-xs bg-white"
      >
        {fontOptions.map(font => (
          <option key={font} value={font}>{font}</option>
        ))}
      </select>
    </div>
    <div>
      <label className="block text-xs font-medium mb-1">Font Weight</label>
      <select
        value={settings.fontWeight}
        onChange={(e) => onChange({...settings, fontWeight: e.target.value})}
        className="w-full px-2 py-1 rounded border border-gray-300 text-xs bg-white"
      >
        {fontWeightOptions.map(weight => (
          <option key={weight} value={weight}>{weight}</option>
        ))}
      </select>
    </div>
    <div>
      <label className="block text-xs font-medium mb-1">Font Size: {settings.fontSize}px</label>
      <input
        type="range"
        min="10"
        max="24"
        value={settings.fontSize}
        onChange={(e) => onChange({...settings, fontSize: parseInt(e.target.value)})}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
      />
    </div>
  </div>
);

export default ButtonSettings;