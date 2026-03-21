import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { getSiteName } from "../utils/format"

const API_URL = import.meta.env.VITE_API_URL || ""

export default function MachineCard({ machine }) {
  const navigate = useNavigate()
  const [imgState, setImgState] = useState("loading") // "loading" | "loaded" | "error"
  const [useProxy, setUseProxy] = useState(false)
  const timerRef = useRef(null)

  const hasValidUrl = !!(machine.image_url && machine.image_url.startsWith("http"))

  useEffect(() => {
    // Reset when machine changes
    setImgState(hasValidUrl ? "loading" : "error")
    setUseProxy(false)
    clearTimeout(timerRef.current)

    if (!hasValidUrl) return

    // After 5s still loading → try proxy
    timerRef.current = setTimeout(() => {
      setUseProxy(true)
    }, 5000)

    // After 10s proxy also hung → show fallback
    const fallbackTimer = setTimeout(() => {
      setImgState(prev => prev === "loading" ? "error" : prev)
    }, 10000)

    return () => {
      clearTimeout(timerRef.current)
      clearTimeout(fallbackTimer)
    }
  }, [machine.image_url, hasValidUrl])

  const handleLoad = () => {
    clearTimeout(timerRef.current)
    setImgState("loaded")
  }

  const handleError = () => {
    clearTimeout(timerRef.current)
    if (!useProxy) {
      // Direct load failed → try proxy immediately
      setUseProxy(true)
    } else {
      // Proxy also failed → show fallback
      setImgState("error")
    }
  }

  const imageSrc = useProxy && machine.image_url
    ? `${API_URL}/api/v1/search/image-proxy?url=${encodeURIComponent(machine.image_url)}`
    : machine.image_url

  return (
    <div
      className="bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all duration-200 cursor-pointer overflow-hidden group"
      onClick={() => navigate(`/machine/${machine.id}`)}
    >
      {/* Image area */}
      <div className="w-full h-48 overflow-hidden bg-gray-50 relative">
        {imgState === "error" ? (
          <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100">
            <div className="w-16 h-16 rounded-full bg-white shadow-sm flex items-center justify-center text-2xl font-bold text-gray-300">
              {machine.name?.charAt(0)?.toUpperCase() || "M"}
            </div>
          </div>
        ) : (
          <>
            {/* Skeleton while loading */}
            {imgState === "loading" && (
              <div className="absolute inset-0 bg-gray-100 animate-pulse" />
            )}
            <img
              key={imageSrc}
              src={imageSrc}
              alt={machine.name}
              className={`w-full h-full object-cover group-hover:scale-105 transition-transform duration-300 ${imgState === "loaded" ? "opacity-100" : "opacity-0"}`}
              loading="lazy"
              referrerPolicy="no-referrer"
              onLoad={handleLoad}
              onError={handleError}
            />
          </>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 text-sm leading-snug line-clamp-2 mb-3 min-h-[2.5rem]">
          {machine.name}
        </h3>

        <div className="text-base font-bold mb-2 text-green-600">
          {machine.price
            ? `€${Number(machine.price).toLocaleString()}`
            : <span className="text-gray-400 font-normal text-sm">Contact for price</span>
          }
        </div>

        {machine.brand && (
          <span className="inline-block bg-blue-50 text-blue-700 text-xs font-medium px-2.5 py-0.5 rounded-full mb-2">
            {machine.brand}
          </span>
        )}

        {machine.location && (
          <div className="flex items-center gap-1 text-gray-500 text-xs mb-1">
            <svg className="w-3 h-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd"/>
            </svg>
            <span className="truncate">{machine.location}</span>
          </div>
        )}

        <div className="text-gray-300 text-xs mt-2 pt-2 border-t border-gray-50">
          {getSiteName(machine.site_name)}
        </div>
      </div>
    </div>
  )
}
