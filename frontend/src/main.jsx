import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './app.jsx' 
import './index.css' // <-- This line tells React to use the Tailwind styles
import './components/core/neumorphic-theme.css'
import './components/core/theme-components.js'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
