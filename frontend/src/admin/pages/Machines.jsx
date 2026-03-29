import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getMachines, deleteMachine, deleteBySite,
  getSiteConfigs, toggleFeatured,
  editMachine, trainMachine, getMachineTypes, getMachineBrands,
} from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../components/Toast'

const PAGE_SIZE = 50

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------
function MachineImage({ url, name }) {
  const [err, setErr] = useState(false)
  const initial = (name || '?')[0].toUpperCase()
  if (!url || err) {
    return (
      <div className="w-9 h-9 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-400 text-xs font-bold flex-shrink-0">
        {initial}
      </div>
    )
  }
  return (
    <img
      src={url} alt=""
      className="w-9 h-9 object-cover rounded-lg border border-gray-200 flex-shrink-0"
      onError={() => setErr(true)}
    />
  )
}

function StarButton({ active, onClick, loading }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      title={active ? 'Remove featured' : 'Mark as featured'}
      className={`w-7 h-7 flex items-center justify-center rounded-lg transition-all ${
        active
          ? 'text-amber-500 bg-amber-50 border border-amber-200 hover:bg-amber-100'
          : 'text-gray-300 border border-gray-200 hover:text-amber-400 hover:border-amber-200 hover:bg-amber-50'
      } ${loading ? 'opacity-50 cursor-wait' : ''}`}
    >
      <svg className="w-3.5 h-3.5" fill={active ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
      </svg>
    </button>
  )
}

function TrainedBadge({ trained }) {
  if (trained) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-[10px] font-semibold border border-green-200">
        <svg className="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
        Trained
      </span>
    )
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-100 text-gray-400 text-[10px] font-medium border border-gray-200">
      Untrained
    </span>
  )
}

// ---------------------------------------------------------------------------
// Edit + Train Modal
// ---------------------------------------------------------------------------
function EditMachineModal({ machine, onClose, onSaved }) {
  const toast = useToast()
  const qc = useQueryClient()

  const [form, setForm] = useState({
    name: machine.name || '',
    brand: machine.brand || '',
    machine_type: machine.machine_type || '',
    year_of_manufacture: machine.year_of_manufacture || '',
    condition: machine.condition || '',
    location: machine.location || '',
    country_of_origin: machine.country_of_origin || '',
    catalog_id: machine.catalog_id || '',
    description: machine.description || '',
    image_url: machine.image_url || '',
    video_url: machine.video_url || '',
    price: machine.price || '',
    currency: machine.currency || 'EUR',
    specs: machine.specs ? JSON.stringify(machine.specs, null, 2) : '',
  })

  const [trainType, setTrainType] = useState(machine.machine_type || '')
  const [trainBrand, setTrainBrand] = useState(machine.brand || '')
  const [saving, setSaving] = useState(false)
  const [training, setTraining] = useState(false)
  const [trainResult, setTrainResult] = useState(null)
  const [tab, setTab] = useState('edit') // 'edit' | 'train'

  const { data: typesData } = useQuery({ queryKey: ['machine-types'], queryFn: getMachineTypes })
  const { data: brandsData } = useQuery({ queryKey: ['machine-brands'], queryFn: getMachineBrands })

  const types = typesData?.types || []
  const brands = brandsData?.brands || []

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const handleSave = async () => {
    setSaving(true)
    try {
      let specsObj = null
      if (form.specs.trim()) {
        try { specsObj = JSON.parse(form.specs) } catch { specsObj = null }
      }
      await editMachine(machine.id, {
        ...form,
        specs: specsObj,
        price: form.price === '' ? null : Number(form.price),
        year_of_manufacture: form.year_of_manufacture === '' ? null : Number(form.year_of_manufacture),
      })
      toast('Machine saved', 'success')
      qc.invalidateQueries({ queryKey: ['machines'] })
      onSaved()
    } catch {
      toast('Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleTrain = async () => {
    setTraining(true)
    setTrainResult(null)
    try {
      const res = await trainMachine(machine.id, {
        type_name: trainType.trim(),
        brand_name: trainBrand.trim(),
      })
      setTrainResult(res)
      toast(`Trained → ${res.matched_type || '?'} / ${res.matched_brand || '?'}`, 'success')
      qc.invalidateQueries({ queryKey: ['machines'] })
    } catch {
      toast('Training failed', 'error')
    } finally {
      setTraining(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-sm font-bold text-gray-900">Edit Machine</h2>
            <p className="text-xs text-gray-400 mt-0.5 font-mono truncate max-w-xs">{machine.id}</p>
          </div>
          <div className="flex items-center gap-2">
            <TrainedBadge trained={machine.is_trained} />
            <button onClick={onClose} className="w-7 h-7 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-100 px-6">
          {['edit', 'train'].map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2.5 text-xs font-semibold capitalize transition-colors border-b-2 -mb-px ${
                tab === t
                  ? 'text-blue-600 border-blue-600'
                  : 'text-gray-400 border-transparent hover:text-gray-600'
              }`}
            >
              {t === 'train' ? 'Train / Classify' : 'Edit Fields'}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 px-6 py-4">

          {tab === 'edit' && (
            <div className="grid grid-cols-2 gap-4">
              <Field label="Name" colSpan={2}>
                <input value={form.name} onChange={e => set('name', e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </Field>

              <Field label="Brand">
                <input value={form.brand} onChange={e => set('brand', e.target.value)}
                  list="brand-list"
                  className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                <datalist id="brand-list">
                  {brands.map(b => <option key={b.id} value={b.name} />)}
                </datalist>
              </Field>

              <Field label="Machine Type">
                <input value={form.machine_type} onChange={e => set('machine_type', e.target.value)}
                  list="type-list"
                  className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                <datalist id="type-list">
                  {types.map(t => <option key={t.id} value={t.name} />)}
                </datalist>
              </Field>

              <Field label="Year of Manufacture">
                <input type="number" value={form.year_of_manufacture} onChange={e => set('year_of_manufacture', e.target.value)}
                  placeholder="e.g. 2018"
                  className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </Field>

              <Field label="Condition">
                <select value={form.condition} onChange={e => set('condition', e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="">— Select —</option>
                  <option value="used">Used</option>
                  <option value="refurbished">Refurbished</option>
                  <option value="new">New</option>
                </select>
              </Field>

              <Field label="Location">
                <input value={form.location} onChange={e => set('location', e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </Field>

              <Field label="Country of Origin">
                <input value={form.country_of_origin} onChange={e => set('country_of_origin', e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </Field>

              <Field label="Catalog ID">
                <input value={form.catalog_id} onChange={e => set('catalog_id', e.target.value)}
                  placeholder="e.g. 1058-26042"
                  className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </Field>

              <Field label="Price">
                <input type="number" value={form.price} onChange={e => set('price', e.target.value)}
                  placeholder="Leave blank = Price on Request"
                  className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </Field>

              <Field label="Currency">
                <select value={form.currency} onChange={e => set('currency', e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="EUR">EUR</option>
                  <option value="USD">USD</option>
                  <option value="GBP">GBP</option>
                </select>
              </Field>

              <Field label="Image URL" colSpan={2}>
                <input value={form.image_url} onChange={e => set('image_url', e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono" />
              </Field>

              <Field label="Video URL" colSpan={2}>
                <input value={form.video_url} onChange={e => set('video_url', e.target.value)}
                  placeholder="YouTube or Vimeo link"
                  className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono" />
              </Field>

              <Field label="Description" colSpan={2}>
                <textarea value={form.description} onChange={e => set('description', e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y" />
              </Field>

              <Field label="Specs (JSON)" colSpan={2}>
                <textarea value={form.specs} onChange={e => set('specs', e.target.value)}
                  rows={5}
                  className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono resize-y" />
              </Field>
            </div>
          )}

          {tab === 'train' && (
            <div className="space-y-5">
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                <p className="text-xs text-blue-700 font-medium mb-1">How Training Works</p>
                <p className="text-xs text-blue-600">
                  Enter the correct Machine Type and Brand below, then click <strong>Train</strong>.
                  The system will match or create these in the registry and mark this machine as classified.
                  Future scraped machines with the same type/brand will auto-match.
                </p>
              </div>

              {/* Current machine info */}
              <div className="bg-gray-50 rounded-xl p-4 space-y-2">
                <p className="text-xs font-semibold text-gray-600 mb-2">Current Machine Data</p>
                <Row label="Name" val={machine.name} />
                <Row label="Brand" val={machine.brand} />
                <Row label="Scraped Type" val={machine.machine_type} />
                <Row label="Year" val={machine.year_of_manufacture} />
                <Row label="Site" val={machine.site_name} />
                <Row label="Catalog ID" val={machine.catalog_id} />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <Field label="Machine Type (classify as)">
                  <input
                    value={trainType}
                    onChange={e => setTrainType(e.target.value)}
                    list="train-type-list"
                    placeholder="e.g. Turret Punch Press"
                    className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <datalist id="train-type-list">
                    {types.map(t => <option key={t.id} value={t.name} />)}
                  </datalist>
                </Field>

                <Field label="Brand (classify as)">
                  <input
                    value={trainBrand}
                    onChange={e => setTrainBrand(e.target.value)}
                    list="train-brand-list"
                    placeholder="e.g. Amada"
                    className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <datalist id="train-brand-list">
                    {brands.map(b => <option key={b.id} value={b.name} />)}
                  </datalist>
                </Field>
              </div>

              {/* Train result */}
              {trainResult && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4">
                  <p className="text-xs font-semibold text-green-700 mb-2">Training Complete</p>
                  <div className="grid grid-cols-2 gap-2 text-xs text-green-700">
                    <div><span className="text-green-500">Type matched:</span> <strong>{trainResult.matched_type}</strong></div>
                    <div><span className="text-green-500">Brand matched:</span> <strong>{trainResult.matched_brand}</strong></div>
                  </div>
                </div>
              )}

              <button
                onClick={handleTrain}
                disabled={training || (!trainType && !trainBrand)}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-sm font-semibold hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
              >
                {training ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Training...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.347a3.5 3.5 0 01-4.95 0l-.347-.347z" />
                    </svg>
                    Train this Machine
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-100">
          <button onClick={onClose}
            className="px-4 py-2 text-xs text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
            Cancel
          </button>
          {tab === 'edit' && (
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-5 py-2 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              {saving && <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>}
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function Field({ label, children, colSpan }) {
  return (
    <div className={colSpan === 2 ? 'col-span-2' : ''}>
      <label className="block text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">{label}</label>
      {children}
    </div>
  )
}

function Row({ label, val }) {
  return (
    <div className="flex gap-2 text-xs">
      <span className="text-gray-400 w-24 flex-shrink-0">{label}:</span>
      <span className="text-gray-700 font-medium truncate">{val ?? '—'}</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------
export default function Machines() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [model, setModel] = useState('')
  const [debouncedModel, setDebouncedModel] = useState('')
  const [siteFilter, setSiteFilter] = useState('')
  const [brandFilter, setBrandFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [yearSort, setYearSort] = useState('')   // '' | 'asc' | 'desc'
  const [selectedIds, setSelectedIds] = useState([])
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [showBulkConfirm, setShowBulkConfirm] = useState(false)
  const [togglingId, setTogglingId] = useState(null)

  const qc = useQueryClient()
  const toast = useToast()

  useEffect(() => {
    const t = setTimeout(() => { setDebouncedModel(model); setPage(1) }, 400)
    return () => clearTimeout(t)
  }, [model])

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['machines', page, debouncedModel, siteFilter, brandFilter, typeFilter, yearSort],
    queryFn: () => getMachines({
      page,
      limit: PAGE_SIZE,
      model: debouncedModel || undefined,
      site_name: siteFilter || undefined,
      brand: brandFilter || undefined,
      machine_type: typeFilter || undefined,
      year_sort: yearSort || undefined,
    }),
    staleTime: 0,
  })

  const { data: configsData } = useQuery({
    queryKey: ['configs'],
    queryFn: getSiteConfigs,
  })

  const delOne = useMutation({
    mutationFn: deleteMachine,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['machines'] })
      toast('Machine deleted', 'success')
    },
    onError: e => toast(e.response?.data?.detail || 'Delete failed', 'error'),
  })

  const delBySite = useMutation({
    mutationFn: deleteBySite,
    onSuccess: d => {
      qc.invalidateQueries({ queryKey: ['machines'] })
      toast(`Deleted ${d.deleted} machines`, 'success')
    },
    onError: e => toast(e.response?.data?.detail || 'Bulk delete failed', 'error'),
  })

  const machines = data?.machines || []
  const total = data?.total || 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const sites = configsData?.configs?.map(c => c.name) || []
  const brands = data?.available_brands || []
  const types = data?.available_types || []

  const allSelected = machines.length > 0 && machines.every(m => selectedIds.includes(m.id))
  const toggleAll = () => setSelectedIds(allSelected ? [] : machines.map(m => m.id))
  const toggleOne = id => setSelectedIds(prev =>
    prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
  )

  const handleToggleFeatured = async (id, current) => {
    setTogglingId(id)
    try {
      const res = await toggleFeatured(id)
      qc.setQueryData(['machines', page, debouncedSearch, siteFilter, brandFilter], old => {
        if (!old) return old
        return {
          ...old,
          machines: old.machines.map(m =>
            m.id === id ? { ...m, is_featured: res.is_featured } : m
          ),
        }
      })
      toast(res.is_featured ? 'Marked as featured' : 'Removed from featured', 'success')
    } catch {
      toast('Failed to update featured status', 'error')
    } finally {
      setTogglingId(null)
    }
  }

  const formatPrice = m => {
    if (!m.price) return '—'
    const sym = m.currency === 'USD' ? '$' : m.currency === 'EUR' ? '€' : (m.currency || '')
    return `${sym}${Number(m.price).toLocaleString()}`
  }

  const handleClear = () => {
    setModel(''); setDebouncedModel(''); setSiteFilter(''); setBrandFilter('')
    setTypeFilter(''); setYearSort(''); setPage(1); setSelectedIds([])
  }

  const toggleYearSort = () => {
    setYearSort(prev => prev === 'asc' ? 'desc' : prev === 'desc' ? '' : 'asc')
    setPage(1)
  }

  const pageButtons = () => {
    const pages = []
    const start = Math.max(1, Math.min(page - 3, totalPages - 6))
    const end = Math.min(totalPages, start + 6)
    for (let i = start; i <= end; i++) pages.push(i)
    return pages
  }

  return (
    <AdminLayout>
      <div className="space-y-4">

        {/* Toolbar */}
        <div className="bg-white rounded-xl border border-gray-200 px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            {/* Website (dropdown) */}
            <select
              value={siteFilter}
              onChange={e => { setSiteFilter(e.target.value); setBrandFilter(''); setTypeFilter(''); setPage(1) }}
              className="text-xs border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-600"
            >
              <option value="">All Websites</option>
              {sites.map(s => <option key={s} value={s}>{s}</option>)}
            </select>

            {/* Type (dropdown) */}
            <select
              value={typeFilter}
              onChange={e => { setTypeFilter(e.target.value); setPage(1) }}
              className="text-xs border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-600"
            >
              <option value="">All Types</option>
              {types.map(t => <option key={t} value={t}>{t}</option>)}
            </select>

            {/* Brand (dropdown) */}
            <select
              value={brandFilter}
              onChange={e => { setBrandFilter(e.target.value); setPage(1) }}
              className="text-xs border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-600"
            >
              <option value="">All Brands</option>
              {brands.map(b => <option key={b} value={b}>{b}</option>)}
            </select>

            {/* Model (text input — typing) */}
            <div className="relative">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                value={model}
                onChange={e => setModel(e.target.value)}
                placeholder="Model search..."
                className="pl-8 pr-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-44"
              />
            </div>

            {/* Clear filters */}
            {(model || siteFilter || brandFilter || typeFilter || yearSort) && (
              <button onClick={handleClear} className="text-xs text-gray-500 hover:text-gray-700 px-2 py-2">
                Clear filters
              </button>
            )}

            <div className="flex-1" />

            {/* Count + pagination info */}
            <span className="text-xs text-gray-500 tabular-nums">
              {total.toLocaleString()} machines · page {page}/{totalPages}
            </span>

            {/* Refresh */}
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="flex items-center gap-1.5 px-3 py-2 text-xs border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600 transition-colors disabled:opacity-60"
            >
              <svg className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {isFetching ? 'Refreshing...' : 'Refresh'}
            </button>

            {/* Bulk delete */}
            {selectedIds.length > 0 && (
              <button
                onClick={() => setShowBulkConfirm(true)}
                className="flex items-center gap-1.5 px-3 py-2 text-xs bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete {selectedIds.length}
              </button>
            )}
          </div>
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="flex justify-center py-20">
            <div className="w-7 h-7 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50/60">
                    <th className="w-8 px-3 py-3">
                      <input type="checkbox" checked={allSelected} onChange={toggleAll}
                        className="rounded border-gray-300 accent-blue-600" />
                    </th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]"></th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Machine</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Site</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Brand</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Type</th>
                    <th
                      className="text-left px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px] cursor-pointer select-none hover:text-blue-500 whitespace-nowrap"
                      onClick={toggleYearSort}
                      title="Sort by year"
                    >
                      Year {yearSort === 'asc' ? '↑' : yearSort === 'desc' ? '↓' : '↕'}
                    </th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Price</th>
                    <th className="text-center px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Status</th>
                    <th className="text-center px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Featured</th>
                    <th className="text-center px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {machines.map(m => (
                    <tr key={m.id} className={`hover:bg-gray-50/80 transition-colors ${selectedIds.includes(m.id) ? 'bg-blue-50/60' : ''}`}>
                      <td className="px-3 py-2.5">
                        <input type="checkbox" checked={selectedIds.includes(m.id)} onChange={() => toggleOne(m.id)}
                          className="rounded border-gray-300 accent-blue-600" />
                      </td>
                      <td className="px-3 py-2.5">
                        <MachineImage url={m.image_url} name={m.name} />
                      </td>
                      <td className="px-3 py-2.5 max-w-[180px]">
                        <p className="font-medium text-gray-800 truncate" title={m.name}>{m.name}</p>
                        <p className="text-gray-400 text-[10px] mt-0.5 font-mono truncate">{m.id.slice(0, 8)}…</p>
                      </td>
                      <td className="px-3 py-2.5">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-gray-100 text-gray-600 font-medium text-[10px]">
                          {m.site_name || '—'}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-gray-600 max-w-[100px] truncate">{m.brand || '—'}</td>
                      <td className="px-3 py-2.5 text-gray-500 max-w-[120px] truncate" title={m.machine_type}>
                        {m.machine_type || '—'}
                      </td>
                      <td className="px-3 py-2.5 text-gray-500 whitespace-nowrap">{m.year_of_manufacture || '—'}</td>
                      <td className="px-3 py-2.5 font-semibold text-gray-800 whitespace-nowrap">{formatPrice(m)}</td>
                      <td className="px-3 py-2.5 text-center">
                        <TrainedBadge trained={m.is_trained} />
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <div className="flex justify-center">
                          <StarButton
                            active={m.is_featured}
                            loading={togglingId === m.id}
                            onClick={() => handleToggleFeatured(m.id, m.is_featured)}
                          />
                        </div>
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center justify-center gap-1">
                          {/* Edit button → full page */}
                          <button
                            onClick={() => navigate(`/admin/machines/${m.id}`)}
                            className="inline-flex items-center justify-center w-7 h-7 rounded-lg border border-gray-200 text-gray-400 hover:text-blue-500 hover:border-blue-200 hover:bg-blue-50 transition-colors"
                            title="Edit machine"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          {/* Source link */}
                          {m.source_url ? (
                            <a
                              href={m.source_url} target="_blank" rel="noreferrer"
                              className="inline-flex items-center justify-center w-7 h-7 rounded-lg border border-gray-200 text-blue-500 hover:bg-blue-50 hover:border-blue-200 transition-colors"
                              title="View source"
                            >
                              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                            </a>
                          ) : <span className="text-gray-300 w-7" />}
                          {/* Delete */}
                          <button
                            onClick={() => setDeleteTarget(m.id)}
                            className="inline-flex items-center justify-center w-7 h-7 rounded-lg border border-gray-200 text-gray-400 hover:text-red-500 hover:border-red-200 hover:bg-red-50 transition-colors"
                            title="Delete"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {machines.length === 0 && (
                    <tr>
                      <td colSpan={11} className="text-center py-16 text-gray-400">
                        <svg className="w-8 h-8 mx-auto mb-2 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        No machines found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
              <p className="text-xs text-gray-500 tabular-nums">
                {total === 0 ? '0' : `${((page - 1) * PAGE_SIZE) + 1}–${Math.min(page * PAGE_SIZE, total)}`} of {total.toLocaleString()}
              </p>
              <div className="flex items-center gap-1">
                <button onClick={() => setPage(1)} disabled={page <= 1}
                  className="px-2 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition-colors">«</button>
                <button onClick={() => setPage(p => p - 1)} disabled={page <= 1}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition-colors">Prev</button>
                {pageButtons().map(pg => (
                  <button key={pg} onClick={() => setPage(pg)}
                    className={`px-3 py-1.5 border rounded-lg text-xs transition-colors ${
                      pg === page
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'border-gray-200 text-gray-500 hover:bg-gray-50'
                    }`}>
                    {pg}
                  </button>
                ))}
                <button onClick={() => setPage(p => p + 1)} disabled={page >= totalPages}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition-colors">Next</button>
                <button onClick={() => setPage(totalPages)} disabled={page >= totalPages}
                  className="px-2 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition-colors">»</button>
              </div>
            </div>
          </div>
        )}
      </div>

      <ConfirmModal
        isOpen={!!deleteTarget}
        title="Delete Machine"
        message="Permanently delete this machine from the database?"
        onConfirm={() => { delOne.mutate(deleteTarget); setDeleteTarget(null) }}
        onCancel={() => setDeleteTarget(null)}
      />

      <ConfirmModal
        isOpen={showBulkConfirm}
        title="Delete Selected"
        message={`Permanently delete ${selectedIds.length} machine(s)? This cannot be undone.`}
        onConfirm={async () => {
          for (const id of selectedIds) await delOne.mutateAsync(id).catch(() => {})
          setSelectedIds([])
          setShowBulkConfirm(false)
          qc.invalidateQueries({ queryKey: ['machines'] })
        }}
        onCancel={() => setShowBulkConfirm(false)}
      />
    </AdminLayout>
  )
}
