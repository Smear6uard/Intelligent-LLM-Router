import { motion } from 'framer-motion'

export default function ComplexityGauge({ value, size = 120 }) {
  const normalized = Math.max(1, Math.min(10, value))
  const percentage = (normalized - 1) / 9
  const angle = percentage * 180

  // Color interpolation: green (low) → yellow (mid) → red (high)
  const getColor = (pct) => {
    if (pct < 0.4) return '#22C55E'
    if (pct < 0.7) return '#EAB308'
    return '#EF4444'
  }
  const color = getColor(percentage)

  const r = (size / 2) - 10
  const cx = size / 2
  const cy = size / 2 + 5

  // Arc path for background
  const describeArc = (startAngle, endAngle) => {
    const startRad = (Math.PI / 180) * (180 + startAngle)
    const endRad = (Math.PI / 180) * (180 + endAngle)
    const x1 = cx + r * Math.cos(startRad)
    const y1 = cy + r * Math.sin(startRad)
    const x2 = cx + r * Math.cos(endRad)
    const y2 = cy + r * Math.sin(endRad)
    const largeArc = endAngle - startAngle > 180 ? 1 : 0
    return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`
  }

  const label = normalized <= 3 ? 'Low' : normalized <= 6 ? 'Medium' : 'High'

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size * 0.65} viewBox={`0 0 ${size} ${size * 0.65}`}>
        {/* Background arc */}
        <path
          d={describeArc(0, 180)}
          fill="none"
          stroke="#374151"
          strokeWidth="8"
          strokeLinecap="round"
        />
        {/* Value arc */}
        <motion.path
          d={describeArc(0, angle)}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
        {/* Value text */}
        <text x={cx} y={cy - 5} textAnchor="middle" className="fill-gray-100 text-2xl font-bold" style={{ fontSize: size * 0.22 }}>
          {normalized.toFixed(1)}
        </text>
        {/* Label */}
        <text x={cx} y={cy + 12} textAnchor="middle" className="fill-gray-400 text-xs" style={{ fontSize: size * 0.1 }}>
          {label}
        </text>
      </svg>
      <span className="text-xs text-gray-500 mt-1">Complexity</span>
    </div>
  )
}
