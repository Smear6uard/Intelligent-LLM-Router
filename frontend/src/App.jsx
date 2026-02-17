import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FlaskConical, Swords, BarChart3, Router } from 'lucide-react'
import Playground from './components/Playground'
import ABArena from './components/ABArena'
import Dashboard from './components/Dashboard'
import { getMode } from './utils/api'

const TABS = [
  { id: 'playground', label: 'Playground', icon: FlaskConical },
  { id: 'arena', label: 'A/B Arena', icon: Swords },
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
]

function ModeBadge({ modeInfo }) {
  if (!modeInfo) return null

  const isLive = modeInfo.mode === 'live'
  const isSpendCapped = modeInfo.reason === 'spend_cap_reached'

  const label = isLive ? 'LIVE' : isSpendCapped ? 'DEMO (spend cap)' : 'DEMO'

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-[10px] font-semibold px-2 py-0.5 rounded-full ${
        isLive
          ? 'bg-emerald-500/15 text-emerald-400'
          : 'bg-amber-500/15 text-amber-400'
      }`}
      title={
        isLive
          ? `Live mode — $${(modeInfo.spend_today_cents / 100).toFixed(2)} / $${(modeInfo.spend_cap_cents / 100).toFixed(2)} spent today`
          : isSpendCapped
            ? `Daily spend cap reached ($${(modeInfo.spend_cap_cents / 100).toFixed(2)})`
            : 'No API key configured — using mock responses'
      }
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          isLive ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
        }`}
      />
      {label}
    </span>
  )
}

export default function App() {
  const [activeTab, setActiveTab] = useState('playground')
  const [modeInfo, setModeInfo] = useState(null)

  useEffect(() => {
    const fetchMode = () => {
      getMode().then(setModeInfo).catch(() => {})
    }
    fetchMode()
    const interval = setInterval(fetchMode, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-2.5">
              <Router className="w-5 h-5 text-orange-400" />
              <h1 className="text-base font-semibold">
                <span className="gradient-text">LLM Router</span>
              </h1>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-400 font-mono">v1.0</span>
              <ModeBadge modeInfo={modeInfo} />
            </div>

            {/* Tabs */}
            <nav className="flex gap-1">
              {TABS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  className={`relative flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors ${
                    activeTab === id
                      ? 'text-gray-100'
                      : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                  {activeTab === id && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute inset-0 bg-gray-800 rounded-lg -z-10"
                      transition={{ type: 'spring', bounce: 0.15, duration: 0.4 }}
                    />
                  )}
                </button>
              ))}
            </nav>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            {activeTab === 'playground' && <Playground />}
            {activeTab === 'arena' && <ABArena />}
            {activeTab === 'dashboard' && <Dashboard />}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  )
}
