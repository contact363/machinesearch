import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { getMachine, trackClick, searchMachines } from "../api/client"
import { formatPrice, formatDate, getSiteName } from "../utils/format"
import Navbar from "../components/Navbar"
import MachineCard from "../components/MachineCard"

export default function MachineDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [imgError, setImgError] = useState(false)

  const { data: machine, isLoading, error } = useQuery({
    queryKey: ["machine", id],
    queryFn: () => getMachine(id),
    enabled: !!id && id !== "undefined",
    retry: 1,
  })

  const { data: similar } = useQuery({
    queryKey: ["similar", machine?.brand],
    queryFn: () => searchMachines({ q: machine?.brand || "", limit: 6 }),
    enabled: !!machine?.brand,
  })

  const handleSupplierClick = () => {
    if (!machine?.source_url) return
    // Open immediately — must be synchronous from click event
    // or browsers block it as a popup
    window.open(machine.source_url, "_blank", "noopener,noreferrer")
    // Track in background, fire and forget
    trackClick(machine.id).catch(() => {})
  }

  if (isLoading) return (
    <div>
      <Navbar showSearch={true} />
      <div className="max-w-6xl mx-auto px-4 py-12 flex justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    </div>
  )

  if (error || !machine) return (
    <div>
      <Navbar showSearch={true} />
      <div className="max-w-6xl mx-auto px-4 py-12 text-center">
        <div className="text-6xl mb-4">😕</div>
        <h2 className="text-xl font-semibold text-gray-700 mb-2">Machine not found</h2>
        <p className="text-gray-500 text-sm mb-6">ID: {id}</p>
        <button onClick={() => navigate(-1)} className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700">
          Go Back
        </button>
      </div>
    </div>
  )

  const hasImage = machine.image_url && !imgError && machine.image_url.startsWith("http")

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar showSearch={true} />

      <div className="max-w-6xl mx-auto px-4 py-8">

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
          <button onClick={() => navigate("/")} className="hover:text-blue-600">Home</button>
          <span>/</span>
          <button onClick={() => navigate(-1)} className="hover:text-blue-600">Results</button>
          <span>/</span>
          <span className="text-gray-900 truncate max-w-xs">{machine.name}</span>
        </div>

        {/* Main content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 bg-white rounded-2xl shadow-sm p-6 mb-8">

          {/* LEFT — Image */}
          <div>
            <div className="w-full aspect-video bg-gray-100 rounded-xl overflow-hidden">
              {hasImage ? (
                <img
                  src={machine.image_url}
                  alt={machine.name}
                  className="w-full h-full object-cover"
                  referrerPolicy="no-referrer"
                  onError={() => setImgError(true)}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-gray-50">
                  <div className="text-8xl font-bold text-gray-200">
                    {machine.name?.charAt(0)?.toUpperCase() || "M"}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* RIGHT — Details */}
          <div className="flex flex-col">
            <h1 className="text-2xl font-bold text-gray-900 mb-3">{machine.name}</h1>

            <div className="text-3xl font-bold text-green-600 mb-4">
              {machine.price
                ? `€${Number(machine.price).toLocaleString()}`
                : "Contact for price"
              }
            </div>

            <div className="grid grid-cols-2 gap-3 mb-6 text-sm">
              {machine.brand && (
                <>
                  <span className="text-gray-500">Brand</span>
                  <span className="font-medium">{machine.brand}</span>
                </>
              )}
              {machine.location && (
                <>
                  <span className="text-gray-500">Location</span>
                  <span className="font-medium">{machine.location}</span>
                </>
              )}
              <span className="text-gray-500">Source</span>
              <span className="font-medium">{getSiteName(machine.site_name)}</span>
              <span className="text-gray-500">Listed</span>
              <span className="font-medium">{formatDate(machine.created_at)}</span>
            </div>

            <button
              onClick={handleSupplierClick}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-4 px-6 rounded-xl flex items-center justify-center gap-2 transition-colors text-base mt-auto"
            >
              View on Supplier Website
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </button>
          </div>
        </div>

        {/* Description */}
        {machine.description && (
          <div className="bg-white rounded-2xl shadow-sm p-6 mb-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Description</h2>
            <p className="text-gray-600 leading-relaxed whitespace-pre-line">{machine.description}</p>
          </div>
        )}

        {/* Specs */}
        {machine.specs && Object.keys(machine.specs).length > 0 && (
          <div className="bg-white rounded-2xl shadow-sm p-6 mb-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Specifications</h2>
            <div className="overflow-hidden rounded-xl border border-gray-100">
              <table className="w-full text-sm">
                <tbody>
                  {Object.entries(machine.specs).map(([k, v], i) => (
                    <tr key={k} className={i % 2 === 0 ? "bg-gray-50" : "bg-white"}>
                      <td className="px-4 py-3 font-medium text-gray-700 w-1/3 border-b border-gray-100">{k}</td>
                      <td className="px-4 py-3 text-gray-600 border-b border-gray-100">{String(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Similar machines */}
        {similar?.results?.length > 0 && (
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Similar Machines</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {similar.results
                .filter(m => m.id !== machine.id)
                .slice(0, 6)
                .map(m => <MachineCard key={m.id} machine={m} />)}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
