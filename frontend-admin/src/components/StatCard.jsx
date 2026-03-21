export default function StatCard({ title, value, icon, color, subtitle, pulse }) {
  const colors = {
    blue:   { bg: 'bg-blue-50',   border: 'border-blue-500',  text: 'text-blue-600' },
    green:  { bg: 'bg-green-50',  border: 'border-green-500', text: 'text-green-600' },
    purple: { bg: 'bg-purple-50', border: 'border-purple-500',text: 'text-purple-600' },
    orange: { bg: 'bg-orange-50', border: 'border-orange-500',text: 'text-orange-600' },
  }
  const c = colors[color] || colors.blue

  return (
    <div className={`bg-white rounded-xl shadow-sm border-l-4 ${c.border} p-5 flex items-center gap-4`}>
      <div className={`${c.bg} ${c.text} rounded-full p-3 text-xl ${pulse ? 'animate-pulse' : ''}`}>
        {icon}
      </div>
      <div>
        <p className="text-sm text-gray-500 font-medium">{title}</p>
        <p className="text-2xl font-bold text-gray-800">{value ?? '—'}</p>
        {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  )
}
