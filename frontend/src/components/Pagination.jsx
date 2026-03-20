export default function Pagination({ currentPage, totalPages, onPageChange }) {
  if (totalPages <= 1) return null

  const getPages = () => {
    const pages = []
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i)
      return pages
    }
    pages.push(1)
    if (currentPage > 4) pages.push('...')
    const start = Math.max(2, currentPage - 2)
    const end = Math.min(totalPages - 1, currentPage + 2)
    for (let i = start; i <= end; i++) pages.push(i)
    if (currentPage < totalPages - 3) pages.push('...')
    pages.push(totalPages)
    return pages
  }

  const btnBase = 'px-3 py-2 text-sm rounded-lg font-medium transition-colors min-w-[36px] text-center'
  const active = 'bg-blue-600 text-white'
  const inactive = 'text-gray-700 hover:bg-gray-100'
  const disabled = 'text-gray-300 cursor-not-allowed'

  return (
    <nav className="flex items-center justify-center gap-1 mt-8 flex-wrap" aria-label="Pagination">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className={`${btnBase} ${currentPage === 1 ? disabled : inactive} flex items-center gap-1`}
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        <span className="hidden sm:inline">Prev</span>
      </button>

      {getPages().map((page, i) =>
        page === '...' ? (
          <span key={`ellipsis-${i}`} className="px-2 py-2 text-gray-400 text-sm">…</span>
        ) : (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className={`${btnBase} ${page === currentPage ? active : inactive}`}
          >
            {page}
          </button>
        )
      )}

      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className={`${btnBase} ${currentPage === totalPages ? disabled : inactive} flex items-center gap-1`}
      >
        <span className="hidden sm:inline">Next</span>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </nav>
  )
}
