import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  getSiteConfigs, autoDetectConfig, detectSite, detectBulkSites,
  createConfig, deleteConfig, toggleConfig, startScrape,
} from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../components/Toast'

// ─── Detection result card ────────────────────────────────────────────────────
function DetectionCard({ result, onConfirm, onAddAnyway, onAddWithProxy, onDismiss }) {
  if (!result) return null

  const isReady = result.scrapable_now
  const isBlocked = result.framework === 'blocked'
  const isDynamic = !isReady && !isBlocked

  return (
    <div className={`rounded-xl border p-4 text-sm ${
      isReady
        ? 'bg-green-50 border-green-200'
        : isBlocked
          ? 'bg-red-50 border-red-200'
          : 'bg-yellow-50 border-yellow-200'
    }`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-lg ${isReady ? 'text-green-600' : isBlocked ? 'text-red-500' : 'text-yellow-600'}`}>
              {isReady ? '✓' : isBlocked ? '✕' : '⚠'}
            </span>
            <span className={`font-semibold ${isReady ? 'text-green-800' : isBlocked ? 'text-red-700' : 'text-yellow-800'}`}>
              {isReady
                ? 'Static site — ready to scrape'
                : isBlocked
                  ? 'Site is blocking requests'
                  : `Dynamic site (${result.framework}) — needs Playwright`}
            </span>
            {result.framework && result.framework !== 'blocked' && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-white/60 text-gray-600 font-mono">
                {result.framework}
              </span>
            )}
          </div>
          <p className={`text-xs mb-3 ${isReady ? 'text-green-700' : isBlocked ? 'text-red-600' : 'text-yellow-700'}`}>
            {result.reason}
          </p>

          {isReady && result.suggested_config?.selectors && (
            <div className="bg-white/60 rounded-lg p-2 mb-3 text-xs font-mono">
              <p className="text-gray-500 mb-1 font-sans font-medium">Auto-detected selectors:</p>
              {Object.entries(result.suggested_config.selectors)
                .filter(([, v]) => v)
                .map(([k, v]) => (
                  <div key={k} className="flex gap-2">
                    <span className="text-gray-400 w-28 shrink-0">{k}:</span>
                    <span className="text-gray-700 truncate">{v}</span>
                  </div>
                ))}
              {result.detected_count > 0 && (
                <p className="mt-1 text-gray-500 font-sans">
                  ~{result.detected_count} items detected on page 1
                  {result.confidence && ` · confidence: ${result.confidence}`}
                </p>
              )}
            </div>
          )}

          {isDynamic && (
            <p className="text-xs text-yellow-700 mb-3">
              This site uses <strong>{result.framework}</strong>.
              Upgrade to Standard plan to enable Playwright rendering.
            </p>
          )}

          {isBlocked && (
            <p className="text-xs text-red-600 mb-3">
              This site blocks scrapers. Add proxy support to enable.
            </p>
          )}

          <div className="flex gap-2 flex-wrap">
            {isReady && (
              <button
                onClick={() => onConfirm(result)}
                className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-xs rounded-lg font-medium"
              >
                Confirm & Add
              </button>
            )}
            {isDynamic && (
              <button
                onClick={() => onAddAnyway(result)}
                className="px-3 py-1.5 bg-yellow-500 hover:bg-yellow-600 text-white text-xs rounded-lg font-medium"
              >
                Add Anyway (disabled)
              </button>
            )}
            {isBlocked && (
              <button
                onClick={() => onAddWithProxy(result)}
                className="px-3 py-1.5 bg-red-500 hover:bg-red-600 text-white text-xs rounded-lg font-medium"
              >
                Add with Proxy (disabled)
              </button>
            )}
            <button
              onClick={onDismiss}
              className="px-3 py-1.5 text-gray-500 hover:text-gray-700 text-xs rounded-lg font-medium"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Bulk results table ───────────────────────────────────────────────────────
function BulkResultsTable({ results, onAddOne, onAddAllReady, onAddAll, adding }) {
  if (!results.length) return null

  const ready = results.filter(r => r.scrapable_now && !r.error)
  const total = results.length

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-700">
          Detection Results
          <span className="ml-2 text-xs font-normal text-gray-400">
            {ready.length} ready / {total} total
          </span>
        </span>
        <div className="flex gap-2">
          <button
            onClick={onAddAllReady}
            disabled={adding || ready.length === 0}
            className="px-3 py-1.5 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-xs rounded-lg font-medium"
          >
            Add All Ready ({ready.length})
          </button>
          <button
            onClick={onAddAll}
            disabled={adding}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs rounded-lg font-medium"
          >
            Add All ({total})
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/50">
              <th className="text-left px-4 py-2 font-semibold text-gray-500 uppercase tracking-wide">URL</th>
              <th className="text-left px-3 py-2 font-semibold text-gray-500 uppercase tracking-wide">Framework</th>
              <th className="text-left px-3 py-2 font-semibold text-gray-500 uppercase tracking-wide">Status</th>
              <th className="text-right px-3 py-2 font-semibold text-gray-500 uppercase tracking-wide">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {results.map((r, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-blue-600 truncate max-w-xs">
                  {r.error ? (
                    <span className="text-red-500">{r.url}</span>
                  ) : (
                    <a href={r.url} target="_blank" rel="noreferrer" className="hover:underline">
                      {r.url?.replace(/^https?:\/\/(www\.)?/, '')}
                    </a>
                  )}
                </td>
                <td className="px-3 py-2">
                  <span className={`px-1.5 py-0.5 rounded font-medium ${
                    r.framework === 'static' || r.framework === 'wordpress'
                      ? 'bg-green-100 text-green-700'
                      : r.framework === 'blocked'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {r.framework || '—'}
                  </span>
                </td>
                <td className="px-3 py-2">
                  {r.error ? (
                    <span className="text-red-500">Error: {r.error}</span>
                  ) : r.scrapable_now ? (
                    <span className="text-green-600 font-medium">Ready</span>
                  ) : r.framework === 'blocked' ? (
                    <span className="text-red-500">Blocked</span>
                  ) : (
                    <span className="text-yellow-600">Needs Playwright</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right">
                  {!r.error && (
                    <button
                      onClick={() => onAddOne(r)}
                      disabled={adding}
                      className="px-2 py-1 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded text-xs font-medium disabled:opacity-50"
                    >
                      Add
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Progress bar for bulk processing ────────────────────────────────────────
function ProgressBar({ label, current, total }) {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-blue-700">{label}</p>
        <span className="text-sm text-blue-600">{current}/{total} ({pct}%)</span>
      </div>
      <div className="h-1.5 bg-blue-200 rounded-full overflow-hidden">
        <div className="h-full bg-blue-600 rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

// ─── Mode badge ───────────────────────────────────────────────────────────────
function ModeBadge({ mode }) {
  const map = {
    static: 'bg-green-100 text-green-700',
    dynamic: 'bg-yellow-100 text-yellow-700',
    stealth: 'bg-orange-100 text-orange-700',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-medium ${map[mode] || 'bg-blue-50 text-blue-600'}`}>
      {mode || 'static'}
    </span>
  )
}

// ─── Scrapable dot ────────────────────────────────────────────────────────────
function ScrapableDot({ scrapable, reason, health, lastError }) {
  const tooltip = !scrapable
    ? (lastError ? `Last error: ${lastError}` : reason || 'Not scrapable')
    : 'Scrapable'
  return (
    <span title={tooltip} className="cursor-help inline-flex items-center gap-1">
      <span className={`w-2.5 h-2.5 rounded-full inline-block ${
        scrapable ? 'bg-green-500' : health === 'failing' ? 'bg-orange-400' : 'bg-red-400'
      }`} />
      {health === 'failing' && (
        <span className="text-xs text-orange-500 font-medium">failing</span>
      )}
      {health === 'disabled' && (
        <span className="text-xs text-red-500 font-medium">auto-off</span>
      )}
    </span>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function SiteConfigs() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('single') // 'single' | 'bulk'
  const [deleteTarget, setDeleteTarget] = useState(null)

  // Single URL tab state
  const [singleUrl, setSingleUrl] = useState('')
  const [detecting, setDetecting] = useState(false)
  const [detectionResult, setDetectionResult] = useState(null)
  const [confirming, setConfirming] = useState(false)

  // Bulk tab state
  const [bulkText, setBulkText] = useState('')
  const [bulkDetecting, setBulkDetecting] = useState(false)
  const [bulkResults, setBulkResults] = useState([])
  const [bulkProgress, setBulkProgress] = useState({ current: 0, total: 0 })
  const [bulkAdding, setBulkAdding] = useState(false)

  const qc = useQueryClient()
  const toast = useToast()

  const { data, isLoading, error } = useQuery({
    queryKey: ['configs'],
    queryFn: getSiteConfigs,
    refetchInterval: (bulkDetecting || bulkAdding) ? 3000 : false,
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

  // ── Single URL: detect ────────────────────────────────────────────────────
  const handleDetect = async (e) => {
    e.preventDefault()
    const url = singleUrl.trim()
    if (!url) return
    setDetecting(true)
    setDetectionResult(null)
    try {
      const result = await detectSite(url)
      setDetectionResult(result)
    } catch (err) {
      toast(err.response?.data?.detail || err.message || 'Detection failed', 'error')
    } finally {
      setDetecting(false)
    }
  }

  // ── Single URL: confirm & add (re-runs auto-detect which saves + scrapes) ──
  const handleConfirm = async (result) => {
    setConfirming(true)
    try {
      const r = await autoDetectConfig(result.url, '')
      toast(`Added ${r.display_name} — scraping in background`, 'success')
      setDetectionResult(null)
      setSingleUrl('')
      qc.invalidateQueries({ queryKey: ['configs'] })
    } catch (err) {
      toast(err.response?.data?.detail || 'Failed to add site', 'error')
    } finally {
      setConfirming(false)
    }
  }

  // ── Single URL: add anyway (dynamic/blocked — disabled) ───────────────────
  const handleAddAnyway = async (result) => {
    setConfirming(true)
    try {
      const cfg = {
        ...result.suggested_config,
        mode: 'dynamic',
        enabled: false,
      }
      await createConfig(cfg)
      toast(`Added ${cfg.name} (disabled — upgrade to enable)`, 'success')
      setDetectionResult(null)
      setSingleUrl('')
      qc.invalidateQueries({ queryKey: ['configs'] })
    } catch (err) {
      toast(err.response?.data?.detail || 'Failed to add site', 'error')
    } finally {
      setConfirming(false)
    }
  }

  // ── Single URL: add with proxy (blocked — disabled) ───────────────────────
  const handleAddWithProxy = async (result) => {
    setConfirming(true)
    try {
      const cfg = {
        ...result.suggested_config,
        proxy_tier: 'datacenter',
        enabled: false,
      }
      await createConfig(cfg)
      toast(`Added ${cfg.name} (disabled — add proxy to enable)`, 'success')
      setDetectionResult(null)
      setSingleUrl('')
      qc.invalidateQueries({ queryKey: ['configs'] })
    } catch (err) {
      toast(err.response?.data?.detail || 'Failed to add site', 'error')
    } finally {
      setConfirming(false)
    }
  }

  // ── Bulk: detect all ──────────────────────────────────────────────────────
  const handleBulkDetect = async () => {
    const urls = bulkText
      .split(/[\n,]+/)
      .map(u => u.trim())
      .filter(u => u.startsWith('http'))
      .slice(0, 50)

    if (!urls.length) {
      toast('No valid URLs found', 'error')
      return
    }

    setBulkDetecting(true)
    setBulkResults([])
    setBulkProgress({ current: 0, total: urls.length })

    try {
      const data = await detectBulkSites(urls)
      setBulkResults(data.results || [])
      setBulkProgress({ current: urls.length, total: urls.length })
      toast(`Detected ${urls.length} sites`, 'success')
    } catch (err) {
      toast(err.response?.data?.detail || 'Bulk detection failed', 'error')
    } finally {
      setBulkDetecting(false)
    }
  }

  // ── Bulk: add one site ────────────────────────────────────────────────────
  const addSiteFromResult = async (r) => {
    if (r.scrapable_now) {
      await autoDetectConfig(r.url, '')
    } else {
      const cfg = {
        ...r.suggested_config,
        enabled: false,
        mode: r.mode || 'dynamic',
        proxy_tier: r.framework === 'blocked' ? 'datacenter' : 'none',
      }
      await createConfig(cfg)
    }
  }

  const handleBulkAddOne = async (result) => {
    setBulkAdding(true)
    try {
      await addSiteFromResult(result)
      toast(`Added ${result.url}`, 'success')
      qc.invalidateQueries({ queryKey: ['configs'] })
    } catch (err) {
      toast(err.response?.data?.detail || 'Failed to add site', 'error')
    } finally {
      setBulkAdding(false)
    }
  }

  const handleAddAllReady = async () => {
    const ready = bulkResults.filter(r => r.scrapable_now && !r.error)
    setBulkAdding(true)
    let added = 0
    for (const r of ready) {
      try {
        await addSiteFromResult(r)
        added++
      } catch { /* continue */ }
    }
    setBulkAdding(false)
    qc.invalidateQueries({ queryKey: ['configs'] })
    toast(`Added ${added} of ${ready.length} ready sites`, 'success')
  }

  const handleAddAll = async () => {
    setBulkAdding(true)
    let added = 0
    for (const r of bulkResults) {
      if (r.error) continue
      try {
        await addSiteFromResult(r)
        added++
      } catch { /* continue */ }
    }
    setBulkAdding(false)
    qc.invalidateQueries({ queryKey: ['configs'] })
    toast(`Added ${added} sites`, 'success')
  }

  const configs = data?.configs || []
  const fmt = (dt) => dt ? new Date(dt).toLocaleDateString() : '—'
  const isLoading2 = confirming || bulkAdding

  return (
    <AdminLayout>
      <div className="space-y-5">
        {/* Header */}
        <div>
          <h1 className="text-lg font-bold text-gray-900 mb-1">Web Sources</h1>
          <p className="text-sm text-gray-400">Add machine listing sites — we'll auto-detect the structure and start scraping.</p>
        </div>

        {/* Add New Sources card */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="border-b border-gray-100 flex">
            {['single', 'bulk'].map(tab => (
              <button
                key={tab}
                onClick={() => { setActiveTab(tab); setDetectionResult(null) }}
                className={`px-5 py-3 text-sm font-medium transition-colors ${
                  activeTab === tab
                    ? 'text-blue-600 border-b-2 border-blue-500 bg-blue-50/30'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab === 'single' ? 'Single URL' : 'Bulk Add (up to 50)'}
              </button>
            ))}
          </div>

          <div className="p-5 space-y-4">
            {/* ─ Single URL tab ─ */}
            {activeTab === 'single' && (
              <>
                <form onSubmit={handleDetect} className="flex gap-2">
                  <input
                    type="url"
                    value={singleUrl}
                    onChange={e => setSingleUrl(e.target.value)}
                    placeholder="https://example.com/machines  — paste any machine listing URL"
                    required
                    disabled={detecting || confirming}
                    className="flex-1 border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
                  />
                  <button
                    type="submit"
                    disabled={detecting || confirming || !singleUrl.trim()}
                    className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition-colors whitespace-nowrap"
                  >
                    {detecting ? (
                      <>
                        <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Detecting…
                      </>
                    ) : 'Detect & Add'}
                  </button>
                </form>

                {detectionResult && (
                  <DetectionCard
                    result={detectionResult}
                    onConfirm={handleConfirm}
                    onAddAnyway={handleAddAnyway}
                    onAddWithProxy={handleAddWithProxy}
                    onDismiss={() => setDetectionResult(null)}
                  />
                )}

                {confirming && (
                  <div className="flex items-center gap-2 text-sm text-blue-600">
                    <span className="w-4 h-4 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
                    Adding site and starting scrape…
                  </div>
                )}
              </>
            )}

            {/* ─ Bulk tab ─ */}
            {activeTab === 'bulk' && (
              <>
                <textarea
                  value={bulkText}
                  onChange={e => setBulkText(e.target.value)}
                  rows={8}
                  placeholder={`Paste URLs one per line (max 50):\n\nhttps://site1.com/machines\nhttps://site2.de/angebote\nhttps://site3.com/used-equipment`}
                  disabled={bulkDetecting}
                  className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
                />
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleBulkDetect}
                    disabled={bulkDetecting || !bulkText.trim()}
                    className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition-colors"
                  >
                    {bulkDetecting ? (
                      <>
                        <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Detecting…
                      </>
                    ) : 'Detect All'}
                  </button>
                  <span className="text-xs text-gray-400">
                    {bulkText.split(/[\n,]+/).filter(u => u.trim().startsWith('http')).length} URLs detected
                  </span>
                </div>

                {bulkDetecting && (
                  <ProgressBar
                    label="Detecting sites…"
                    current={bulkProgress.current}
                    total={bulkProgress.total}
                  />
                )}

                {bulkResults.length > 0 && (
                  <BulkResultsTable
                    results={bulkResults}
                    onAddOne={handleBulkAddOne}
                    onAddAllReady={handleAddAllReady}
                    onAddAll={handleAddAll}
                    adding={bulkAdding}
                  />
                )}
              </>
            )}
          </div>
        </div>

        {/* Configured Sites table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <span className="font-semibold text-gray-900">
              Configured Sites
              <span className="ml-2 text-sm font-normal text-gray-400">({configs.length})</span>
            </span>
            <button
              onClick={() => navigate('/admin/jobs')}
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
                    <th className="text-left px-4 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wide">Scrapable</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wide">Machines</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wide">Last Crawl</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-500 text-xs uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {configs.map(cfg => (
                    <tr key={cfg.name} className={`hover:bg-gray-50 transition-colors ${cfg.health === 'failing' ? 'bg-orange-50/30' : cfg.health === 'disabled' ? 'bg-red-50/20' : ''}`}>
                      <td className="px-5 py-3">
                        <p className="font-semibold text-gray-800 text-sm flex items-center gap-2">
                          {cfg.display_name || cfg.name}
                          {cfg.health === 'failing' && (
                            <span title={`${cfg.consecutive_failures} consecutive failures`} className="text-orange-500 text-xs">⚠</span>
                          )}
                          {cfg.health === 'disabled' && (
                            <span title="Auto-disabled after 5 failures" className="text-red-500 text-xs">✕ auto-off</span>
                          )}
                        </p>
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
                        <ModeBadge mode={cfg.mode} />
                      </td>
                      <td className="px-4 py-3">
                        <ScrapableDot
                          scrapable={cfg.scrapable_now}
                          health={cfg.health}
                          lastError={cfg.last_error}
                        />
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
                      <td colSpan={7} className="text-center py-16">
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
