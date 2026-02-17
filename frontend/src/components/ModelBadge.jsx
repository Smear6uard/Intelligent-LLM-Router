import { MODEL_COLORS } from '../utils/constants'

export default function ModelBadge({ model, size = 'sm' }) {
  const colors = MODEL_COLORS[model] || { bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500/30' }
  const sizeClasses = size === 'lg'
    ? 'px-3 py-1.5 text-sm'
    : 'px-2 py-0.5 text-xs'

  return (
    <span className={`inline-flex items-center rounded-full border font-mono font-medium ${colors.bg} ${colors.text} ${colors.border} ${sizeClasses}`}>
      {model}
    </span>
  )
}
