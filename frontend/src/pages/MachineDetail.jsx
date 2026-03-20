import { useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { useMachine, useSearchResults } from '../hooks/useSearch'
import { trackClick } from '../api/client'
import Navbar from '../components/Navbar'
import MachineCard from '../components/MachineCard'
import { formatPrice, formatDate, getSiteName } from '../utils/format'

function MachineIconLarge() {
  return (
    <div className="w-full h-full flex items-center justify-center bg-gray-100 rounded-xl">
      <svg className="w-24 h-24 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
          d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    </div>
  )
}

export default function MachineDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [clickLoading, setClickLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [imgError, setImgError] = useState(false)

  const { data: machine, isLoading, isError } = useMachine(id)

  const brand = machine?.brand
  const { data: similarData } = useSearchResults(
    { q: brand, limit: 6, page: 1 },
  )
  const similar = (similarData?.results || []).filter(m => m.id !== id).slice(0, 6)

  const handleViewSupplier = async () => {
    if (!machine) return
    setClickLoading(true)
    try {
      const { redirect_url } = await trackClick(machine.id)
      window.open(redirect_url || machine.source_url, '_blank', 'noopener')
    } catch {
      window.open(machine.source_url, '_blank', 'noopener')
    } finally {
      setClickLoading(false)
    }
  }

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar showSearch />
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
          <div className="animate-pulse">
            <div className="h-4 w-48 bg-gray-200 rounded mb-8" />
            <div className="flex flex-col lg:flex-row gap-8">
              <div className="lg:w-[55%] aspect-[4/3] bg-gray-200 rounded-xl" />
              <div className="lg:w-[45%] space-y-4">
                <div className="h-8 bg-gray-200 rounded w-3/4" />
                <div className="h-6 bg-gray-200 rounded w-1/4" />
                <div className="h-32 bg-gray-200 rounded" />
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (isError || !machine) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar showSearch />
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-20 text-center">
          <div className="text-5xl mb-4">😞</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Machine not found</h2>
          <button onClick={() => navigate(-1)} className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700">
            Go Back
          </button>
        </div>
      </div>
    )
  }

  const specs = machine.specs && typeof machine.specs === 'object' && !Array.isArray(machine.specs)
    ? Object.entries(machine.specs)
    : null

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar showSearch />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-gray-500 mb-6 flex-wrap">
          <Link to="/" className="hover:text-blue-600">Home</Link>
          <span>›</span>
          <button onClick={() => navigate(-1)} className="hover:text-blue-600">Results</button>
          <span>›</span>
          <span className="text-gray-900 truncate max-w-xs">{machine.name}</span>
        </nav>

        {/* Two-column layout */}
        <div className="flex flex-col lg:flex-row gap-8">
          {/* LEFT: Image */}
          <div className="lg:w-[55%]">
            <div className="aspect-[4/3] rounded-xl overflow-hidden bg-gray-100">
              {machine.image_url && !imgError ? (
                <img
                  src={machine.image_url}
                  alt={machine.name}
                  className="w-full h-full object-cover"
                  onError={() => setImgError(true)}
                />
              ) : (
                <MachineIconLarge />
              )}
            </div>
          </div>

          {/* RIGHT: Info */}
          <div className="lg:w-[45%] flex flex-col gap-4">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 leading-tight">
              {machine.name}
            </h1>

            {/* Price */}
            {machine.price ? (
              <p className="text-3xl font-extrabold text-green-600">
                {formatPrice(machine.price, machine.currency)}
              </p>
            ) : (
              <p className="text-lg text-gray-400 font-medium">Contact supplier for price</p>
            )}

            {/* Info grid */}
            <div className="grid grid-cols-2 gap-3 bg-gray-50 rounded-xl p-4 border border-gray-100">
              {machine.brand && (
                <>
                  <span className="text-sm text-gray-500 font-medium">Brand</span>
                  <span className="text-sm text-gray-900">{machine.brand}</span>
                </>
              )}
              {machine.location && (
                <>
                  <span className="text-sm text-gray-500 font-medium">Location</span>
                  <span className="text-sm text-gray-900 flex items-center gap-1">
                    <svg className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                    </svg>
                    {machine.location}
                  </span>
                </>
              )}
              {machine.site_name && (
                <>
                  <span className="text-sm text-gray-500 font-medium">Source</span>
                  <span className="text-sm text-gray-900">{getSiteName(machine.site_name)}</span>
                </>
              )}
              {machine.created_at && (
                <>
                  <span className="text-sm text-gray-500 font-medium">Added</span>
                  <span className="text-sm text-gray-900">{formatDate(machine.created_at)}</span>
                </>
              )}
            </div>

            {/* CTA buttons */}
            <button
              onClick={handleViewSupplier}
              disabled={clickLoading}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-semibold rounded-xl py-3 text-base transition-colors"
            >
              {clickLoading ? (
                <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              )}
              View on Supplier Website
            </button>

            <button
              onClick={handleShare}
              className="w-full flex items-center justify-center gap-2 border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 font-medium rounded-xl py-3 text-sm transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
              </svg>
              {copied ? 'Link Copied!' : 'Share'}
            </button>
          </div>
        </div>

        {/* Below fold */}
        <div className="mt-10 space-y-8">
          {/* Description */}
          {machine.description && (
            <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Description</h2>
              <p className="text-gray-700 leading-relaxed whitespace-pre-line">{machine.description}</p>
            </div>
          )}

          {/* Specs */}
          {specs && specs.length > 0 && (
            <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Specifications</h2>
              <table className="w-full text-sm">
                <tbody>
                  {specs.map(([k, v], i) => (
                    <tr key={k} className={i % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                      <td className="py-2 px-3 font-medium text-gray-600 w-1/3 rounded-l">{k}</td>
                      <td className="py-2 px-3 text-gray-900 rounded-r">{String(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Similar machines */}
          {similar.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Similar Machines</h2>
              <div className="flex gap-4 overflow-x-auto pb-4 snap-x">
                {similar.map(m => (
                  <div key={m.id} className="flex-shrink-0 w-64 snap-start">
                    <MachineCard machine={m} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
