import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getSiteConfigs, createConfig, updateConfig, deleteConfig, toggleConfig, startScrape,
} from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'
import StatusBadge from '../components/StatusBadge'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../components/Toast'

const NEW_TEMPLATE = {
  name: '', display_name: '', start_url: '', language: 'en',
  pagination: true, pagination_type: 'page_param', pagination_param: 'page',
  max_pages: 20, detail_page: false, mode: 'static', proxy_tier: 'none',
  rate_limit_delay: 2, enabled: true, base_url: '',
  selectors: {
    listing_container: '', name: '', price: '', image: '',
    location: '', detail_link: '', next_page: '',
  },
}

function ConfigModal({ isOpen, onClose, initial, isEdit }) {
  const [jsonText, setJsonText] = useState(
    () => JSON.stringify(initial || NEW_TEMPLATE, null, 2)
  )
  const [jsonError, setJsonError] = useState('')
  const [saving, setSaving] = useState(false)
  const qc = useQueryClient()
  const toast = useToast()

  if (!isOpen) return null

  const handleChange = val => {
    setJsonText(val)
    try { JSON.parse(val); setJsonError('') }
    catch (e) { setJsonError(e.message) }
  }

  const handleSave = async () => {
    let parsed
    try { parsed = JSON.parse(jsonText) }
    catch { return }
    setSaving(true)
    try {
      if (isEdit) {
        await updateConfig(parsed.name, parsed)
        toast('Config updated', 'success')
      } else {
        await createConfig(parsed)
        toast('Config created', 'success')
      }
      qc.invalidateQueries({ queryKey: ['configs'] })
      onClose()
    } catch (e) {
      toast(e.response?.data?.detail || 'Save failed', 'error')
    } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h3 className="text-lg font-semibold text-gray-800">
            {isEdit ? `Edit: ${initial?.name}` : 'Add New Site'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
        </div>
        <div className="flex-1 overflow-auto px-6 py-4">
          <textarea
            value={jsonText}
            onChange={e => handleChange(e.target.value)}
            className={`w-full h-96 font-mono text-xs p-3 rounded-lg border-2 transition-colors focus:outline-none ${
              jsonError ? 'border-red-400 bg-red-50' : 'border-gray-200 focus:border-blue-400'
            }`}
          />
          {jsonError && <p className="text-red-600 text-xs mt-1">{jsonError}</p>}
        </div>
        <div className="flex justify-end gap-3 px-6 py-4 border-t">
          <button onClick={onClose} className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors">
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!!jsonError || saving}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg transition-colors flex items-center gap-2"
          >
            {saving && <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
            Save
          </button>
        </div>
      </div>
    </div>
  )
}

export default function SiteConfigs() {
  const [showAdd, setShowAdd] = useState(false)
  const [editCfg, setEditCfg] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)

  const qc = useQueryClient()
  const toast = useToast()

  const { data, isLoading, error } = useQuery({
    queryKey: ['configs'],
    queryFn: getSiteConfigs,
  })

  const deleteMut = useMutation({
    mutationFn: deleteConfig,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['configs'] }); toast('Deleted', 'success') },
    onError: e => toast(e.response?.data?.detail || 'Delete failed', 'error'),
  })

  const toggleMut = useMutation({
    mutationFn: toggleConfig,
    onSuccess: d => { qc.invalidateQueries({ queryKey: ['configs'] }); toast(`${d.enabled ? 'Enabled' : 'Disabled'}`, 'success') },
  })

  const scrapeMut = useMutation({
    mutationFn: startScrape,
    onSuccess: (_, name) => toast(`Scraping started: ${name}`, 'success'),
    onError: e => toast(e.response?.data?.detail || 'Start failed', 'error'),
  })

  const configs = data?.configs || []

  return (
    <AdminLayout>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">{configs.length} site{configs.length !== 1 ? 's' : ''}</p>
          <button
            onClick={() => setShowAdd(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg font-medium transition-colors"
          >
            + Add Site
          </button>
        </div>

        {isLoading && (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4">
            {error.message}
          </div>
        )}

        {!isLoading && !error && (
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Display Name</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Last Scraped</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Machines</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {configs.map(cfg => (
                  <tr key={cfg.name} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-gray-700">{cfg.name}</td>
                    <td className="px-4 py-3 text-gray-800">{cfg.display_name || cfg.name}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={cfg.enabled ? 'active' : 'inactive'} />
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {cfg.last_scraped
                        ? new Date(cfg.last_scraped).toLocaleString()
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-gray-700">
                      {cfg.machine_count?.toLocaleString() || 0}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          title="Scrape now"
                          onClick={() => scrapeMut.mutate(cfg.name)}
                          className="p-1.5 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                        >▶</button>
                        <button
                          title="Edit"
                          onClick={() => setEditCfg(cfg)}
                          className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        >✏</button>
                        <button
                          title={cfg.enabled ? 'Disable' : 'Enable'}
                          onClick={() => toggleMut.mutate(cfg.name)}
                          className="p-1.5 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                        >{cfg.enabled ? '⏸' : '▷'}</button>
                        <button
                          title="Delete"
                          onClick={() => setDeleteTarget(cfg.name)}
                          className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                        >🗑</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {configs.length === 0 && (
                  <tr><td colSpan={6} className="text-center py-8 text-gray-400">No configs found</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <ConfigModal isOpen={showAdd} onClose={() => setShowAdd(false)} isEdit={false} />
      <ConfigModal isOpen={!!editCfg} onClose={() => setEditCfg(null)} initial={editCfg} isEdit />

      <ConfirmModal
        isOpen={!!deleteTarget}
        title="Delete Config"
        message={`Are you sure you want to delete "${deleteTarget}"?`}
        onConfirm={() => { deleteMut.mutate(deleteTarget); setDeleteTarget(null) }}
        onCancel={() => setDeleteTarget(null)}
      />
    </AdminLayout>
  )
}
