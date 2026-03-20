import { useNavigate } from 'react-router-dom'
import { formatPrice, getSiteName, truncate } from '../utils/format'

function MachineIcon() {
  return (
    <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  )
}

export default function MachineCard({ machine }) {
  const navigate = useNavigate()
  const { id, name, price, currency, brand, location, image_url, site_name } = machine

  return (
    <div
      onClick={() => navigate(`/machine/${id}`)}
      className="bg-white rounded-xl shadow-sm overflow-hidden cursor-pointer transition-all duration-200 hover:shadow-md hover:scale-[1.02] border border-gray-100"
    >
      {/* Image */}
      <div className="aspect-[4/3] bg-gray-100 overflow-hidden flex items-center justify-center">
        {image_url ? (
          <img
            src={image_url}
            alt={name}
            loading="lazy"
            className="w-full h-full object-cover"
            onError={e => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex' }}
          />
        ) : null}
        <div
          className={`w-full h-full items-center justify-center bg-gray-100 ${image_url ? 'hidden' : 'flex'}`}
          style={{ display: image_url ? 'none' : 'flex' }}
        >
          <MachineIcon />
        </div>
      </div>

      {/* Body */}
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 text-sm leading-snug line-clamp-2 mb-2">
          {truncate(name, 80)}
        </h3>

        {/* Price */}
        <p className={`text-sm font-bold mb-2 ${price ? 'text-green-600' : 'text-gray-400'}`}>
          {formatPrice(price, currency)}
        </p>

        {/* Brand + location row */}
        <div className="flex items-center gap-2 flex-wrap">
          {brand && (
            <span className="inline-block bg-blue-50 text-blue-700 text-xs font-medium px-2 py-0.5 rounded-full">
              {truncate(brand, 20)}
            </span>
          )}
          {location && (
            <span className="flex items-center gap-1 text-xs text-gray-500">
              <svg className="w-3 h-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
              </svg>
              {truncate(location, 25)}
            </span>
          )}
        </div>

        {/* Source site */}
        {site_name && (
          <p className="text-xs text-gray-400 mt-2 truncate">{getSiteName(site_name)}</p>
        )}
      </div>
    </div>
  )
}
