export function formatPrice(price, currency) {
  if (price == null || price === '' || price === 0) return 'Contact for price'
  const num = typeof price === 'string' ? parseFloat(price.replace(/[^0-9.]/g, '')) : price
  if (isNaN(num)) return price
  const symbol = currency === 'USD' ? '$' : currency === 'GBP' ? '£' : '€'
  return `${symbol}${num.toLocaleString('en-US', { maximumFractionDigits: 0 })}`
}

export function formatDate(dateString) {
  if (!dateString) return ''
  const d = new Date(dateString)
  if (isNaN(d)) return dateString
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function truncate(text, maxLength = 100) {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength).trimEnd() + '...'
}

const SITE_NAMES = {
  vib_kg:        'VIB-KG',
  bidspotter:    'BidSpotter',
  exapro:        'Exapro',
  used_machines: 'Used-Machines.com',
  fm_machines:   'FM-Machines',
  ucy_machines:  'UCY Machines',
  lrtt:          'LRTT',
  cnc_toerner:   'CNC Toerner',
}

export function getSiteName(site_name) {
  return SITE_NAMES[site_name] || site_name
}
