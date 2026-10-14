import { lazy, StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

const ModelMixObserver = lazy(() => import('./components/ModelMixObserver.jsx'))

const RootView = window.location.pathname.replace(/\/$/, '') === '/modelmix'
  ? ModelMixObserver
  : App

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Suspense fallback={<div className="app-loading">Loading...</div>}>
      <RootView />
    </Suspense>
  </StrictMode>,
)
