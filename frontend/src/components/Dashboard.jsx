import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { BarChart3, TrendingDown, Zap, Clock, DollarSign, Activity } from 'lucide-react'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import {
  getAnalyticsSummary, getTimeseries, getModelDistribution,
  getCostComparison, getRecentRequests,
} from '../utils/api'
import { MODEL_COLORS, TASK_TYPE_LABELS, TASK_TYPE_COLORS } from '../utils/constants'
import ModelBadge from './ModelBadge'

const CHART_COLORS = ['#F97316', '#22C55E', '#3B82F6', '#A855F7', '#34D399', '#F59E0B']

function StatCard({ icon: Icon, label, value, sub, color = 'text-gray-100' }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-900 border border-gray-800 rounded-xl p-4"
    >
      <div className="flex items-center gap-2 mb-1">
        <Icon className="w-4 h-4 text-gray-500" />
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <div className={`text-2xl font-bold font-mono ${color}`}>{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
    </motion.div>
  )
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [timeseries, setTimeseries] = useState([])
  const [distribution, setDistribution] = useState([])
  const [costData, setCostData] = useState(null)
  const [recent, setRecent] = useState([])
  const [loading, setLoading] = useState(true)

  const loadData = useCallback(async () => {
    try {
      const [sum, ts, dist, cost, rec] = await Promise.all([
        getAnalyticsSummary(),
        getTimeseries(),
        getModelDistribution(),
        getCostComparison(),
        getRecentRequests(),
      ])
      setSummary(sum)
      setTimeseries(ts)
      setDistribution(dist)
      setCostData(cost)
      setRecent(rec)
    } catch (err) {
      console.error('Dashboard load error:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [loadData])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-gray-400">
        <div className="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mr-3" />
        Loading analytics...
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Stats Row */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon={Activity} label="Total Requests" value={summary.total_requests} sub={`${summary.requests_today} today`} />
          <StatCard icon={DollarSign} label="Total Cost" value={`$${(summary.total_cost_cents / 100).toFixed(2)}`} sub={`Saved ${summary.cost_savings_percent}%`} color="text-green-400" />
          <StatCard icon={Clock} label="Avg Latency" value={`${summary.avg_latency_ms.toFixed(0)}ms`} sub={`${summary.models_used} models used`} />
          <StatCard icon={TrendingDown} label="Cost Savings" value={`${summary.cost_savings_percent}%`} sub={`vs always using best model`} color="text-emerald-400" />
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Requests Over Time */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-gray-300">Requests Over Time</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={timeseries}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
              <XAxis dataKey="day" tick={{ fill: '#6B7280', fontSize: 11 }} tickFormatter={(d) => d.slice(5)} />
              <YAxis tick={{ fill: '#6B7280', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }} />
              <Line type="monotone" dataKey="requests" stroke="#3B82F6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Model Distribution */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-4 h-4 text-purple-400" />
            <span className="text-sm font-medium text-gray-300">Model Distribution</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={distribution}
                dataKey="count"
                nameKey="model"
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={2}
              >
                {distribution.map((entry, i) => (
                  <Cell key={entry.model} fill={MODEL_COLORS[entry.model]?.hex || CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }} />
              <Legend
                formatter={(value) => <span className="text-xs text-gray-400">{value}</span>}
                wrapperStyle={{ fontSize: 11 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Cost Comparison */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-4">
            <DollarSign className="w-4 h-4 text-green-400" />
            <span className="text-sm font-medium text-gray-300">Cost by Model</span>
          </div>
          {costData && (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={costData.by_model}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                <XAxis dataKey="model" tick={{ fill: '#6B7280', fontSize: 9 }} angle={-20} textAnchor="end" height={50} />
                <YAxis tick={{ fill: '#6B7280', fontSize: 11 }} tickFormatter={(v) => `${v.toFixed(1)}¢`} />
                <Tooltip
                  contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                  formatter={(v) => [`${v.toFixed(2)}¢`, 'Cost']}
                />
                <Bar dataKey="actual_cost" radius={[4, 4, 0, 0]}>
                  {costData.by_model.map((entry, i) => (
                    <Cell key={entry.model} fill={MODEL_COLORS[entry.model]?.hex || CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Latency Over Time */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-4 h-4 text-orange-400" />
            <span className="text-sm font-medium text-gray-300">Avg Latency Over Time</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={timeseries}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
              <XAxis dataKey="day" tick={{ fill: '#6B7280', fontSize: 11 }} tickFormatter={(d) => d.slice(5)} />
              <YAxis tick={{ fill: '#6B7280', fontSize: 11 }} tickFormatter={(v) => `${v}ms`} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                formatter={(v) => [`${v}ms`, 'Latency']}
              />
              <Line type="monotone" dataKey="avg_latency_ms" stroke="#F97316" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Requests Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-300">Recent Requests</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800">
                <th className="text-left py-2 pr-3">Prompt</th>
                <th className="text-left py-2 pr-3">Type</th>
                <th className="text-left py-2 pr-3">Complexity</th>
                <th className="text-left py-2 pr-3">Model</th>
                <th className="text-right py-2 pr-3">Latency</th>
                <th className="text-right py-2 pr-3">Tokens</th>
                <th className="text-right py-2">Cost</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((req) => (
                <tr key={req.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-2 pr-3 text-gray-300 max-w-64 truncate">{req.prompt}</td>
                  <td className="py-2 pr-3">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${TASK_TYPE_COLORS[req.task_type]}`}>
                      {TASK_TYPE_LABELS[req.task_type]}
                    </span>
                  </td>
                  <td className="py-2 pr-3 font-mono text-gray-400">{req.complexity?.toFixed(1)}</td>
                  <td className="py-2 pr-3"><ModelBadge model={req.model} /></td>
                  <td className="py-2 pr-3 text-right font-mono text-gray-400">{req.latency_ms}ms</td>
                  <td className="py-2 pr-3 text-right font-mono text-gray-400">{req.tokens_used}</td>
                  <td className="py-2 text-right font-mono text-gray-400">${req.cost_cents?.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
