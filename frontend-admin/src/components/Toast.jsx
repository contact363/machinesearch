import { createContext, useContext, useState, useCallback } from 'react'

const ToastCtx = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const show = useCallback((message, type = 'info') => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3000)
  }, [])

  const colors = { success: 'bg-green-600', error: 'bg-red-600', info: 'bg-blue-600' }

  return (
    <ToastCtx.Provider value={show}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`${colors[t.type] || colors.info} text-white px-4 py-3 rounded-lg shadow-lg text-sm max-w-xs animate-slide-in`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

export function useToast() {
  return useContext(ToastCtx)
}
