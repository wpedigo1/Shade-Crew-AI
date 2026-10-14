import { lazy, StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'

const ModelMixObserver = lazy(() => import('./components/ModelMixObserver.jsx'))

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Suspense fallback={<div className="app-loading">Loading...</div>}>
      <ModelMixObserver />
    </Suspense>
  </StrictMode>,
)
