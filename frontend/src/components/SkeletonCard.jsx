export default function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden animate-pulse">
      <div className="aspect-[4/3] bg-gray-200" />
      <div className="p-4 space-y-3">
        <div className="h-4 bg-gray-200 rounded w-3/4" />
        <div className="h-4 bg-gray-200 rounded w-1/2" />
        <div className="flex gap-2 mt-2">
          <div className="h-5 bg-gray-200 rounded-full w-16" />
          <div className="h-5 bg-gray-200 rounded w-24" />
        </div>
        <div className="h-3 bg-gray-200 rounded w-2/3" />
      </div>
    </div>
  )
}
