import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  getSiteConfigs, autoDetectConfig, deleteConfig, toggleConfig, startScrape,
} from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../components/Toast'

// ---------- URL input row ----------
function UrlRow({ onAdd, loading }) {
  const [url, setUrl] = useState('')
  const inputRef = useRef(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    const val = url.trim()
    if (!val) return
    onAdd(val)
    setUrl('')
    inputRef.current?.focus()
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        ref={inputRef}
        type="url"
        value={url}
        onChange={e => setUrl(e.target.value)}
        placeholder="https://example.com/machines  — paste any machine listing URL"
        required
        disabled={loading}
        className="flex-1 border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
      />
      <button
        type="submit"
        disabled={loading || !url.trim()}
        className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition-colors whitespace-nowrap"
      >
        {loading ? (
          <>
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Detecting…
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add & Auto-Detect
          </>
        )}
      </button>
    </form>
  )
}

// ---------- Batch paste panel ----------
function BatchPanel({ onBatchAdd, loading }) {
  const [text, setText] = useState('')
  const [open, setOpen] = useState(false)

  const handleSubmit = () => {
    const urls = text
      .split(/[\n,\s]+/)
      .map(u => u.trim())
      .filter(u => u.startsWith('http'))
    if (!urls.length) return
    onBatchAdd(urls)
    setText('')
    setOpen(false)
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        Paste multiple URLs at once
      </button>
      {open && (
        <div className="mt-3 border border-gray-200 rounded-xl p-4 bg-gray-50">
          <p className="text-xs text-gray-500 mb-2">Paste URLs — one per line, or comma-separated</p>
          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            rows={6}
            placeholder={`https://site1.com/machines\nhttps://site2.de/angebote\nhttps://site3.com/used-equipment`}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <div className="flex justify-end gap-2 mt-2">
            <button onClick={() => setOpen(false)} className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900">Cancel</button>
            <button
              onClick={handleSubmit}
              disabled={loading || !text.trim()}
              className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded-lg font-medium transition-colors"
            >
              Add All URLs
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------- Detection result toast card ----------
function DetectResult({ result, onClose }) {
  if (!result) return null
  return (
    <div className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${
      result.error
        ? 'bg-red-50 border-red-200 text-red-700'
        : result.needs_js
          ? 'bg-yellow-50 border-yellow-200 text-yellow-800'
          : 'bg-green-50 border-green-200 text-green-700'
    }`}>
      <div className="flex-1">
        {result.error ? (
          <p><strong>Failed:</strong> {result.error}</p>
        ) : result.needs_js ? (
          <p>
            <strong>{result.display_name}</strong> uses JavaScript rendering.
            Config saved — scrape will use dynamic mode.
            {result.detected_count > 0 && ` Detected ~${result.detected_count} items on page 1.`}
          </p>
        ) : (
          <p>
            <strong>{result.display_name}</strong> added.
            Detected <strong>{result.detected_count}</strong> items on page 1.
            Scraping in background…
          </p>
        )}
      </div>
      <button onClick={onClose} className="text-current opacity-50 hover:opacity-100 flex-shrink-0">✕</button>
    </div>
  )
}

// ---------- Queue bar (batch progress) ----------
function QueueBar({ queue }) {
  if (!queue.length) return null
  const done = queue.filter(q => q.status !== 'pending').length
  const pct = Math.round((done / queue.length) * 100)
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-blue-700">Processing {queue.length} URLs… ({done}/{queue.length})</p>
        <span className="text-sm text-blue-600">{pct}%</span>
      </div>
      <div className="h-1.5 bg-blue-200 rounded-full overflow-hidden">
        <div className="h-full bg-blue-600 rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {queue.map((q, i) => (
          <span key={i} className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            q.status === 'done' ? 'bg-green-100 text-green-700' :
            q.status === 'error' ? 'bg-red-100 text-red-700' :
            q.status === 'running' ? 'bg-blue-100 text-blue-700 animate-pulse' :
            'bg-gray-100 text-gray-500'
          }`}>
            {new URL(q.url).hostname.replace('www.', '')}
          </span>
        ))}
      </div>
    </div>
  )
}

// ---------- Main page ----------
export default function SiteConfigs() {
  const navigate = useNavigate()
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [lastResult, setLastResult] = useState(null)
  const [queue, setQueue] = useState([])   // batch processing queue
  const [batchRunning, setBatchRunning] = useState(false)

  const qc = useQueryClient()
  const toast = useToast()

  const { data, isLoading, error } = useQuery({
    queryKey: ['configs'],
    queryFn: getSiteConfigs,
    refetchInterval: batchRunning ? 3000 : false,
  })

  const deleteMut = useMutation({
    mutationFn: deleteConfig,
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ['configs'] })
      qc.invalidateQueries({ queryKey: ['machines'] })
      toast(`Deleted site + ${d.machines_removed ?? 0} machines`, 'success')
    },
    onError: e => toast(e.response?.data?.detail || 'Delete failed', 'error'),
  })

  const toggleMut = useMutation({
    mutationFn: toggleConfig,
    onSuccess: d => { qc.invalidateQueries({ queryKey: ['configs'] }); toast(d.enabled ? 'Enabled' : 'Disabled', 'success') },
  })

  const scrapeMut = useMutation({
    mutationFn: startScrape,
    onSuccess: (_, name) => {
      toast(`Scraping started: ${name}`, 'success')
      navigate('/admin/jobs')
    },
    onError: e => toast(e.response?.data?.detail || 'Start failed', 'error'),
  })

  // Single URL add with auto-detect
  const [detecting, setDetecting] = useState(false)
  const handleAddUrl = async (url) => {
    setDetecting(true)
    setLastResult(null)
    try {
      const result = await autoDetectConfig(url, '')
      setLastResult(result)
      qc.invalidateQueries({ queryKey: ['configs'] })
      toast(`Added ${result.display_name} — scraping in background`, 'success')
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Detection failed'
      setLastResult({ error: msg })
      toast(msg, 'error')
    } finally {
      setDetecting(false)
    }
  }

  // Batch URL processing
  const handleBatchAdd = async (urls) => {
    const items = urls.map(url => ({ url, status: 'pending' }))
    setQueue(items)
    setBatchRunning(true)
    setLastResult(null)

    for (let i = 0; i < items.length; i++) {
      setQueue(prev => prev.map((q, idx) => idx === i ? { ...q, status: 'running' } : q))
      try {
        await autoDetectConfig(items[i].url, '')
        setQueue(prev => prev.map((q, idx) => idx === i ? { ...q, status: 'done' } : q))
      } catch (e) {
        setQueue(prev => prev.map((q, idx) => idx === i ? { ...q, status: 'error' } : q))
      }
    }

    setBatchRunning(false)
    qc.invalidateQueries({ queryKey: ['configs'] })
    toast(`Finished adding ${urls.length} sites`, 'success')
    setTimeout(() => setQueue([]), 5000)
  }

  const configs = data?.configs || []
  const fmt = (dt) => dt ? new Date(dt).toLocaleDateString() : '—'

  return (
    <AdminLayout>
      <div className="space-y-5">
        {/* Header */}
        <div>
          <h1 className="text-lg font-bold text-gray-900 mb-1">Web Sources</h1>
          <p className="text-sm text-gray-400">Paste any machine listing page URL — we'll auto-detect the structure and start scraping.</p>
        </div>

        {/* URL input card */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-3">
          <UrlRow onAdd={handleAddUrl} loading={detecting || batchRunning} />
          <BatchPanel onBatchAdd={handleBatchAdd} loading={batchRunning} />
        </div>

        {/* Queue progress */}
        {queue.length > 0 && <QueueBar queue={queue} />}

        {/* Detection result */}
        {lastResult && <DetectResult result={lastResult} onClose={() => setLastResult(null)} />}

        {/* Sites table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <span className="font-semibold text-gray-900">
              Configured Sites
              <span className="ml-2 text-sm font-normal text-gray-400">({configs.length})</span>
            </span>
            <button
              onClick={() => { scrapeMut.mutate ? null : null; navigate('/admin/jobs') }}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              View scrape logs →
            </button>
          </div>

          {isLoading && (
            <div className="flex justify-center py-12">
              <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {error && (
            <div className="m-4 bg-red-50 border border-red-200 text-red-700 rounded-xl p-4">{error.message}</div>
          )}

          {!isLoading && !error && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="text-left px-5 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wide">Site / URL</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wide">Status</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wide">Mode</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wide">Machines</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wide">Last Crawl</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {configs.map(cfg => (
                    <tr key={cfg.name} className="hover:bg-gray-50 transition-colors">
                      <td className="px-5 py-3">
                        <p className="font-semibold text-gray-800 text-sm">{cfg.display_name || cfg.name}</p>
                        <a href={cfg.start_url} target="_blank" rel="noreferrer"
                          className="text-xs text-blue-500 hover:underline truncate max-w-xs block">
                          {cfg.start_url || cfg.name}
                        </a>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          cfg.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                        }`}>
                          {cfg.enabled && <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />}
                          {cfg.enabled ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                          cfg.mode === 'dynamic' ? 'bg-purple-100 text-purple-700' :
                          cfg.mode === 'stealth' ? 'bg-orange-100 text-orange-700' :
                          'bg-blue-50 text-blue-600'
                        }`}>
                          {cfg.mode || 'static'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-gray-800">
                        {(cfg.machine_count || 0).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-400">{fmt(cfg.last_scraped)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => scrapeMut.mutate(cfg.name)}
                            disabled={scrapeMut.isPending}
                            className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white text-xs rounded-lg transition-colors font-medium"
                          >
                            ▶ Run
                          </button>
                          <button
                            onClick={() => toggleMut.mutate(cfg.name)}
                            title={cfg.enabled ? 'Disable' : 'Enable'}
                            className="p-1.5 text-gray-400 hover:bg-gray-100 rounded-lg transition-colors text-xs"
                          >
                            {cfg.enabled ? '⏸' : '▷'}
                          </button>
                          <button
                            onClick={() => setDeleteTarget(cfg.name)}
                            className="p-1.5 text-red-400 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {configs.length === 0 && !isLoading && (
                    <tr>
                      <td colSpan={6} className="text-center py-16">
                        <div className="text-gray-300 text-4xl mb-3">🌐</div>
                        <p className="text-gray-500 font-medium">No sites added yet</p>
                        <p className="text-gray-400 text-sm mt-1">Paste a URL above to get started</p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <ConfirmModal
        isOpen={!!deleteTarget}
        title="Delete Website"
        message={`Remove "${deleteTarget}" and permanently delete ALL its machines from the database? This cannot be undone.`}
        onConfirm={() => { deleteMut.mutate(deleteTarget); setDeleteTarget(null) }}
        onCancel={() => setDeleteTarget(null)}
      />
    </AdminLayout>
  )
}
