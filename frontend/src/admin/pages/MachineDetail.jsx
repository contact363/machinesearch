import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getMachine, editMachine, trainMachine, deleteMachine,
  getMachineTypes, getMachineBrands,
} from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../components/Toast'

function TrainedBadge({ trained }) {
  if (trained) return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-[10px] font-semibold border border-green-200">
      <svg className="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
      </svg>
      Trained
    </span>
  )
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-100 text-gray-400 text-[10px] font-medium border border-gray-200">
      Untrained
    </span>
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
      <span className="text-gray-400 w-28 flex-shrink-0">{label}:</span>
      <span className="text-gray-700 font-medium truncate">{val ?? '—'}</span>
    </div>
  )
}

export default function MachineDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const toast = useToast()

  const [tab, setTab] = useState('edit')
  const [saving, setSaving] = useState(false)
  const [training, setTraining] = useState(false)
  const [trainResult, setTrainResult] = useState(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [imgIndex, setImgIndex] = useState(0)
  const [form, setForm] = useState(null)
  const [trainType, setTrainType] = useState('')
  const [trainBrand, setTrainBrand] = useState('')

  const { data: machine, isLoading, isError } = useQuery({
    queryKey: ['machine', id],
    queryFn: () => getMachine(id),
    onSuccess: m => {
      if (!form) {
        setForm({
          name: m.name || '',
          brand: m.brand || '',
          machine_type: m.machine_type || '',
          year_of_manufacture: m.year_of_manufacture || '',
          condition: m.condition || '',
          location: m.location || '',
          country_of_origin: m.country_of_origin || '',
          catalog_id: m.catalog_id || '',
          description: m.description || '',
          image_url: m.image_url || '',
          video_url: m.video_url || '',
          price: m.price || '',
          currency: m.currency || 'EUR',
          specs: m.specs ? JSON.stringify(m.specs, null, 2) : '',
        })
        setTrainType(m.machine_type || '')
        setTrainBrand(m.brand || '')
      }
    },
  })

  const { data: typesData } = useQuery({ queryKey: ['machine-types'], queryFn: getMachineTypes })
  const { data: brandsData } = useQuery({ queryKey: ['machine-brands'], queryFn: getMachineBrands })

  const types = typesData?.types || []
  const brands = brandsData?.brands || []

  const delMut = useMutation({
    mutationFn: () => deleteMachine(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['machines'] })
      toast('Machine deleted', 'success')
      navigate('/admin/machines')
    },
    onError: () => toast('Delete failed', 'error'),
  })

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const handleSave = async () => {
    setSaving(true)
    try {
      let specsObj = null
      if (form.specs.trim()) {
        try { specsObj = JSON.parse(form.specs) } catch { specsObj = null }
      }
      await editMachine(id, {
        ...form,
        specs: specsObj,
        price: form.price === '' ? null : Number(form.price),
        year_of_manufacture: form.year_of_manufacture === '' ? null : Number(form.year_of_manufacture),
      })
      toast('Machine saved', 'success')
      qc.invalidateQueries({ queryKey: ['machine', id] })
      qc.invalidateQueries({ queryKey: ['machines'] })
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
      const res = await trainMachine(id, { type_name: trainType.trim(), brand_name: trainBrand.trim() })
      setTrainResult(res)
      toast(`Trained → ${res.matched_type || '?'} / ${res.matched_brand || '?'}`, 'success')
      qc.invalidateQueries({ queryKey: ['machine', id] })
      qc.invalidateQueries({ queryKey: ['machines'] })
    } catch {
      toast('Training failed', 'error')
    } finally {
      setTraining(false)
    }
  }

  if (isLoading) return (
    <AdminLayout>
      <div className="flex justify-center py-20">
        <div className="w-7 h-7 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    </AdminLayout>
  )

  if (isError || !machine) return (
    <AdminLayout>
      <div className="text-center py-20 text-gray-400">Machine not found.</div>
    </AdminLayout>
  )

  const allImages = machine.all_images || (machine.image_url ? [machine.image_url] : [])

  return (
    <AdminLayout>
      <div className="max-w-5xl mx-auto space-y-5">

        {/* ── Header ── */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/admin/machines')}
            className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-800 border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 transition-colors"
          >
            ← Back
          </button>
          <div className="flex-1 min-w-0">
            <h1 className="text-sm font-bold text-gray-900 truncate">{machine.name}</h1>
            <p className="text-[10px] text-gray-400 font-mono">{machine.id}</p>
          </div>
          <TrainedBadge trained={machine.is_trained} />
          <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-gray-100 text-gray-600 font-medium text-[10px]">
            {machine.site_name}
          </span>
          <button
            onClick={() => setDeleteOpen(true)}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs border border-red-200 text-red-600 rounded-lg hover:bg-red-50 transition-colors"
          >
            Delete
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

          {/* ── Left: image gallery ── */}
          <div className="space-y-3">
            {allImages.length > 0 ? (
              <>
                <img
                  src={allImages[imgIndex]} alt=""
                  className="w-full aspect-video object-cover rounded-xl border border-gray-200 bg-gray-100"
                  onError={e => { e.target.onerror = null; e.target.className = 'w-full aspect-video bg-gray-100 rounded-xl border border-gray-200' }}
                />
                {allImages.length > 1 && (
                  <div className="flex gap-2 flex-wrap">
                    {allImages.map((img, i) => (
                      <img key={i} src={img} alt=""
                        onClick={() => setImgIndex(i)}
                        className={`w-12 h-12 object-cover rounded-lg border cursor-pointer transition-all ${i === imgIndex ? 'ring-2 ring-blue-500 border-blue-300' : 'border-gray-200 opacity-60 hover:opacity-100'}`}
                        onError={e => { e.target.onerror = null; e.target.style.display = 'none' }}
                      />
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="w-full aspect-video bg-gray-100 rounded-xl border border-gray-200 flex items-center justify-center text-gray-300 text-xs">No image</div>
            )}

            {machine.source_url && (
              <a href={machine.source_url} target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-blue-600 text-xs hover:underline">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                View source listing
              </a>
            )}

            <div className="text-[10px] text-gray-400 space-y-1 pt-1">
              <p>Views: {machine.view_count} &nbsp;·&nbsp; Clicks: {machine.click_count}</p>
              <p>Created: {machine.created_at ? new Date(machine.created_at).toLocaleString() : '—'}</p>
              {machine.updated_at && <p>Updated: {new Date(machine.updated_at).toLocaleString()}</p>}
            </div>
          </div>

          {/* ── Right: tabs (Edit / Train) ── */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 flex flex-col">

            {/* Tab bar */}
            <div className="flex border-b border-gray-100 px-5">
              {['edit', 'train'].map(t => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-4 py-3 text-xs font-semibold capitalize transition-colors border-b-2 -mb-px ${
                    tab === t ? 'text-blue-600 border-blue-600' : 'text-gray-400 border-transparent hover:text-gray-600'
                  }`}
                >
                  {t === 'train' ? 'Train / Classify' : 'Edit Fields'}
                </button>
              ))}
            </div>

            {/* Tab body */}
            <div className="overflow-y-auto flex-1 p-5">

              {tab === 'edit' && form && (
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Name" colSpan={2}>
                    <input value={form.name} onChange={e => set('name', e.target.value)}
                      className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  </Field>
                  <Field label="Brand">
                    <input value={form.brand} onChange={e => set('brand', e.target.value)}
                      list="brand-list"
                      className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    <datalist id="brand-list">{brands.map(b => <option key={b.id} value={b.name} />)}</datalist>
                  </Field>
                  <Field label="Machine Type">
                    <input value={form.machine_type} onChange={e => set('machine_type', e.target.value)}
                      list="type-list"
                      className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    <datalist id="type-list">{types.map(t => <option key={t.id} value={t.name} />)}</datalist>
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
                      Enter the correct Machine Type and Brand, then click <strong>Train</strong>.
                      The system will match or create these in the registry and mark this machine as classified.
                    </p>
                  </div>
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
                      <input value={trainType} onChange={e => setTrainType(e.target.value)}
                        list="train-type-list" placeholder="e.g. Turret Punch Press"
                        className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                      <datalist id="train-type-list">{types.map(t => <option key={t.id} value={t.name} />)}</datalist>
                    </Field>
                    <Field label="Brand (classify as)">
                      <input value={trainBrand} onChange={e => setTrainBrand(e.target.value)}
                        list="train-brand-list" placeholder="e.g. Amada"
                        className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                      <datalist id="train-brand-list">{brands.map(b => <option key={b.id} value={b.name} />)}</datalist>
                    </Field>
                  </div>
                  {trainResult && (
                    <div className="bg-green-50 border border-green-200 rounded-xl p-4">
                      <p className="text-xs font-semibold text-green-700 mb-2">Training Complete</p>
                      <div className="grid grid-cols-2 gap-2 text-xs text-green-700">
                        <div><span className="text-green-500">Type:</span> <strong>{trainResult.matched_type}</strong></div>
                        <div><span className="text-green-500">Brand:</span> <strong>{trainResult.matched_brand}</strong></div>
                      </div>
                    </div>
                  )}
                  <button
                    onClick={handleTrain}
                    disabled={training || (!trainType && !trainBrand)}
                    className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-sm font-semibold hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
                  >
                    {training ? 'Training...' : 'Train this Machine'}
                  </button>
                </div>
              )}
            </div>

            {/* Footer */}
            {tab === 'edit' && (
              <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-gray-100">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-5 py-2 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold disabled:opacity-50 transition-colors"
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <ConfirmModal
        isOpen={deleteOpen}
        title="Delete Machine"
        message={`Permanently delete "${machine.name}"? This cannot be undone.`}
        onConfirm={() => { delMut.mutate(); setDeleteOpen(false) }}
        onCancel={() => setDeleteOpen(false)}
      />
    </AdminLayout>
  )
}
