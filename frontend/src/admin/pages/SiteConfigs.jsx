import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getSiteConfigs, createConfig, updateConfig, deleteConfig, toggleConfig, startScrape,
} from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../components/Toast'

const EMPTY_FORM = { name: '', start_url: '', display_name: '' }

function AddSiteForm({ onSuccess }) {
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const qc = useQueryClient()
  const toast = useToast()

  const set = (k, v) => setForm(prev => ({ ...prev, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name || !form.start_url) return
    setSaving(true)
    try {
      await createConfig({
        name: form.name.trim(),
        display_name: form.display_name.trim() || form.name.trim(),
        start_url: form.start_url.trim(),
        enabled: true,
        pagination: true,
        pagination_type: 'page_param',
        pagination_param: 'page',
        max_pages: 20,
        detail_page: false,
        mode: 'static',
        proxy_tier: 'none',
        rate_limit_delay: 2,
        base_url: '',
        selectors: { listing_container: '', name: '', price: '', image: '', location: '', detail_link: '', next_page: '' },
      })
      toast('Website added', 'success')
      setForm(EMPTY_FORM)
      qc.invalidateQueries({ queryKey: ['configs'] })
      onSuccess?.()
    } catch (e) {
      toast(e.response?.data?.detail || 'Failed to add website', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
      <h2 className="text-base font-bold text-gray-900 mb-4">Add New Website</h2>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Name <span className="text-red-400">*</span></label>
          <input
            value={form.name}
            onChange={e => set('name', e.target.value)}
            placeholder="e.g. machineryzone"
            required
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">URL <span className="text-red-400">*</span></label>
          <input
            value={form.start_url}
            onChange={e => set('start_url', e.target.value)}
            placeholder="https://example.com/machines"
            required
            type="url"
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Description / Display Name</label>
          <input
            value={form.display_name}
            onChange={e => set('display_name', e.target.value)}
            placeholder="Optional display name"
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
        <div className="sm:col-span-3 flex justify-end">
          <button type="submit" disabled={saving}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-semibold rounded-lg transition-colors flex items-center gap-2">
            {saving && <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
            Add Website
          </button>
        </div>
      </form>
    </div>
  )
}

export default function SiteConfigs() {
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [editCfg, setEditCfg] = useState(null)

  const qc = useQueryClient()
  const toast = useToast()

  const { data, isLoading, error } = useQuery({
    queryKey: ['configs'],
    queryFn: getSiteConfigs,
  })

  const deleteMut = useMutation({
    mutationFn: deleteConfig,
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ['configs'] })
      qc.invalidateQueries({ queryKey: ['machines'] })
      toast(`Deleted website + ${d.machines_removed ?? 0} machines`, 'success')
    },
    onError: e => toast(e.response?.data?.detail || 'Delete failed', 'error'),
  })

  const toggleMut = useMutation({
    mutationFn: toggleConfig,
    onSuccess: d => { qc.invalidateQueries({ queryKey: ['configs'] }); toast(d.enabled ? 'Enabled' : 'Disabled', 'success') },
  })

  const scrapeMut = useMutation({
    mutationFn: startScrape,
    onSuccess: (_, name) => toast(`Scraping started: ${name}`, 'success'),
    onError: e => toast(e.response?.data?.detail || 'Start failed', 'error'),
  })

  const configs = data?.configs || []

  const fmt = (dt) => dt ? new Date(dt).toLocaleDateString() : '—'

  return (
    <AdminLayout>
      <div>
        <AddSiteForm />

        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-base font-bold text-gray-900">Web Sources</h2>
            <span className="text-sm text-gray-500">{configs.length} site{configs.length !== 1 ? 's' : ''}</span>
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
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Name / URL</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Status</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Discovered</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">URLs</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Extracted</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Last Crawl</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {configs.map(cfg => (
                    <tr key={cfg.name} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <p className="font-semibold text-gray-800 text-sm">{cfg.display_name || cfg.name}</p>
                        <p className="text-xs text-blue-500 hover:underline truncate max-w-xs">
                          <a href={cfg.start_url} target="_blank" rel="noreferrer">{cfg.start_url || cfg.name}</a>
                        </p>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          cfg.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                        }`}>
                          {cfg.enabled ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">{fmt(cfg.created_at)}</td>
                      <td className="px-4 py-3 text-right text-sm font-medium text-gray-700">
                        {(cfg.machine_count || 0).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right text-sm font-medium text-gray-700">
                        {(cfg.machine_count || 0).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">{fmt(cfg.last_scraped)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => scrapeMut.mutate(cfg.name)}
                            disabled={scrapeMut.isPending}
                            title="Start crawl"
                            className="inline-flex items-center gap-1 px-2.5 py-1 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white text-xs rounded-lg transition-colors font-medium">
                            ▶ Run
                          </button>
                          <button
                            onClick={() => toggleMut.mutate(cfg.name)}
                            title={cfg.enabled ? 'Disable' : 'Enable'}
                            className="p-1.5 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors text-xs">
                            {cfg.enabled ? '⏸' : '▷'}
                          </button>
                          <button
                            onClick={() => setDeleteTarget(cfg.name)}
                            title="Delete"
                            className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition-colors">
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {configs.length === 0 && (
                    <tr>
                      <td colSpan={7} className="text-center py-10 text-gray-400">No websites configured yet</td>
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
