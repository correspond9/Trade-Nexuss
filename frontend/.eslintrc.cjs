module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
  },
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
    ecmaFeatures: {
      jsx: true,
    },
  },
  settings: {
    react: {
      version: "detect",
    },
  },
  plugins: ["react", "react-hooks", "react-refresh"],
  extends: ["eslint:recommended", "plugin:react/recommended", "plugin:react-hooks/recommended"],
  rules: {
    "react/prop-types": "off",
    "react-refresh/only-export-components": "off",
  },
  overrides: [
    {
      files: ["src/services/option-greeks-service.js", "src/utils/security-config.js", "theme_tokens/**/*.js"],
      env: {
        node: true,
      },
    },
  ],
};
