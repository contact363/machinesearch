import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMachine, editMachine, deleteMachine } from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../components/Toast'

export default function MachineDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const toast = useToast()

  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [imgIndex, setImgIndex] = useState(0)

  const { data: machine, isLoading, isError } = useQuery({
    queryKey: ['machine', id],
    queryFn: () => getMachine(id),
    onSuccess: m => {
      if (!form) setForm({
        name: m.name || '',
        brand: m.brand || '',
        machine_type: m.machine_type || '',
        year_of_manufacture: m.year_of_manufacture || '',
        condition: m.condition || '',
        location: m.location || '',
        price: m.price || '',
        currency: m.currency || 'EUR',
        catalog_id: m.catalog_id || '',
        country_of_origin: m.country_of_origin || '',
        description: m.description || '',
      })
    },
  })

  const saveMut = useMutation({
    mutationFn: data => editMachine(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['machine', id] })
      qc.invalidateQueries({ queryKey: ['machines'] })
      toast('Machine updated', 'success')
      setEditing(false)
    },
    onError: e => toast(e.response?.data?.detail || 'Save failed', 'error'),
  })

  const delMut = useMutation({
    mutationFn: () => deleteMachine(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['machines'] })
      toast('Machine deleted', 'success')
      navigate('/machines')
    },
    onError: e => toast(e.response?.data?.detail || 'Delete failed', 'error'),
  })

  const startEdit = () => {
    setForm({
      name: machine.name || '',
      brand: machine.brand || '',
      machine_type: machine.machine_type || '',
      year_of_manufacture: machine.year_of_manufacture || '',
      condition: machine.condition || '',
      location: machine.location || '',
      price: machine.price || '',
      currency: machine.currency || 'EUR',
      catalog_id: machine.catalog_id || '',
      country_of_origin: machine.country_of_origin || '',
      description: machine.description || '',
    })
    setEditing(true)
  }

  const Field = ({ label, value }) => (
    <div>
      <p className="text-xs text-gray-400 mb-0.5">{label}</p>
      <p className="text-sm text-gray-800">{value || '—'}</p>
    </div>
  )

  const InputField = ({ label, field, type = 'text' }) => (
    <div>
      <label className="text-xs text-gray-400 mb-0.5 block">{label}</label>
      {type === 'textarea' ? (
        <textarea
          rows={3}
          value={form[field]}
          onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      ) : (
        <input
          type={type}
          value={form[field]}
          onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      )}
    </div>
  )

  if (isLoading) return (
    <AdminLayout>
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
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
      <div className="max-w-5xl mx-auto space-y-6">

        {/* ── Header ── */}
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/machines')}
            className="text-gray-500 hover:text-gray-700 text-sm flex items-center gap-1">
            ← Back
          </button>
          <h1 className="text-lg font-semibold text-gray-800 truncate flex-1">{machine.name}</h1>
          <span className="bg-blue-50 text-blue-700 text-xs px-2 py-1 rounded">{machine.site_name}</span>
          {!editing && (
            <button onClick={startEdit}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors">
              Edit
            </button>
          )}
          <button onClick={() => setDeleteOpen(true)}
            className="px-4 py-2 bg-red-50 hover:bg-red-100 text-red-600 text-sm rounded-lg transition-colors">
            Delete
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* ── Left: images ── */}
          <div className="space-y-3">
            {allImages.length > 0 ? (
              <>
                <img src={allImages[imgIndex]} alt=""
                  className="w-full aspect-video object-cover rounded-xl border bg-gray-100"
                  onError={e => { e.target.onerror = null; e.target.src = '' }} />
                {allImages.length > 1 && (
                  <div className="flex gap-2 flex-wrap">
                    {allImages.map((img, i) => (
                      <img key={i} src={img} alt=""
                        onClick={() => setImgIndex(i)}
                        className={`w-14 h-14 object-cover rounded-lg border cursor-pointer ${i === imgIndex ? 'ring-2 ring-blue-500' : 'opacity-60 hover:opacity-100'}`}
                        onError={e => { e.target.onerror = null; e.target.style.display = 'none' }} />
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="w-full aspect-video bg-gray-100 rounded-xl border flex items-center justify-center text-gray-300">No image</div>
            )}

            {machine.source_url && (
              <a href={machine.source_url} target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-2 text-blue-600 text-sm hover:underline">
                🔗 View source listing
              </a>
            )}

            <div className="text-xs text-gray-400 space-y-1">
              <p>Views: {machine.view_count} &nbsp;|&nbsp; Clicks: {machine.click_count}</p>
              <p>Created: {machine.created_at ? new Date(machine.created_at).toLocaleString() : '—'}</p>
              <p>Updated: {machine.updated_at ? new Date(machine.updated_at).toLocaleString() : '—'}</p>
            </div>
          </div>

          {/* ── Right: details / edit form ── */}
          <div className="lg:col-span-2 space-y-5">

            {editing ? (
              <div className="bg-white rounded-xl shadow-sm p-6 space-y-4">
                <h2 className="font-semibold text-gray-700 text-sm">Edit Machine</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2"><InputField label="Name" field="name" /></div>
                  <InputField label="Brand" field="brand" />
                  <InputField label="Machine Type" field="machine_type" />
                  <InputField label="Year of Manufacture" field="year_of_manufacture" type="number" />
                  <InputField label="Condition" field="condition" />
                  <InputField label="Location" field="location" />
                  <InputField label="Price" field="price" type="number" />
                  <InputField label="Currency" field="currency" />
                  <InputField label="Catalog ID" field="catalog_id" />
                  <InputField label="Country of Origin" field="country_of_origin" />
                  <div className="col-span-2"><InputField label="Description" field="description" type="textarea" /></div>
                </div>
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => saveMut.mutate(form)}
                    disabled={saveMut.isPending}
                    className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
                  >
                    {saveMut.isPending ? 'Saving…' : 'Save'}
                  </button>
                  <button onClick={() => setEditing(false)}
                    className="px-5 py-2 border border-gray-200 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition-colors">
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="font-semibold text-gray-700 text-sm mb-4">Details</h2>
                <div className="grid grid-cols-2 gap-x-8 gap-y-4">
                  <Field label="Brand" value={machine.brand} />
                  <Field label="Machine Type" value={machine.machine_type} />
                  <Field label="Year" value={machine.year_of_manufacture} />
                  <Field label="Condition" value={machine.condition} />
                  <Field label="Location" value={machine.location} />
                  <Field label="Price" value={machine.price ? `${machine.price} ${machine.currency}` : null} />
                  <Field label="Catalog ID" value={machine.catalog_id} />
                  <Field label="Country of Origin" value={machine.country_of_origin} />
                  <Field label="Language" value={machine.language} />
                  <Field label="Featured" value={machine.is_featured ? 'Yes' : 'No'} />
                </div>
                {machine.description && (
                  <div className="mt-4">
                    <p className="text-xs text-gray-400 mb-1">Description</p>
                    <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3">{machine.description}</p>
                  </div>
                )}
              </div>
            )}

            {/* Specs table */}
            {machine.specs && Object.keys(machine.specs).length > 0 && (
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="font-semibold text-gray-700 text-sm mb-3">Specifications</h2>
                <table className="w-full text-xs border border-gray-100 rounded-lg overflow-hidden">
                  <tbody>
                    {Object.entries(machine.specs).map(([k, v]) => (
                      <tr key={k} className="border-b border-gray-50">
                        <td className="px-3 py-2 bg-gray-50 font-medium text-gray-600 w-2/5">{k}</td>
                        <td className="px-3 py-2 text-gray-700">{String(v)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      <ConfirmModal
        isOpen={deleteOpen}
        title="Delete Machine"
        message={`Delete "${machine.name}"? This cannot be undone.`}
        onConfirm={() => { delMut.mutate(); setDeleteOpen(false) }}
        onCancel={() => setDeleteOpen(false)}
      />
    </AdminLayout>
  )
}
