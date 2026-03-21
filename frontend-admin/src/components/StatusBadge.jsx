export default function StatusBadge({ status }) {
  const map = {
    completed: 'bg-green-100 text-green-700',
    active:    'bg-green-100 text-green-700',
    running:   'bg-blue-100 text-blue-700',
    failed:    'bg-red-100 text-red-700',
    inactive:  'bg-gray-100 text-gray-600',
    pending:   'bg-gray-100 text-gray-600',
  }
  const cls = map[status] || 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {status === 'running' && (
        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse inline-block" />
      )}
      {status}
    </span>
  )
}
