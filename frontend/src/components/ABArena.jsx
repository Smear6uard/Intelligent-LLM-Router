import { useState, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Swords, Trophy, Clock, Coins, Hash, Send } from 'lucide-react'
import { streamABTest, voteABTest, getABTestHistory } from '../utils/api'
import { EXAMPLE_PROMPTS, TASK_TYPE_LABELS, TASK_TYPE_COLORS, MODEL_COLORS } from '../utils/constants'
import ModelBadge from './ModelBadge'

export default function ABArena() {
  const [prompt, setPrompt] = useState('')
  const [testMeta, setTestMeta] = useState(null)     // {test_id, task_type, complexity, models}
  const [modelTexts, setModelTexts] = useState({})    // {model: "streaming text..."}
  const [modelStats, setModelStats] = useState({})    // {model: {latency_ms, tokens_used, cost_cents}}
  const [isRunning, setIsRunning] = useState(false)
  const [voted, setVoted] = useState(false)
  const [winner, setWinner] = useState(null)
  const [history, setHistory] = useState(null)
  const [error, setError] = useState(null)
  const scrollRefs = useRef({})

  const handleRun = useCallback(async () => {
    if (!prompt.trim() || isRunning) return
    setIsRunning(true)
    setTestMeta(null)
    setModelTexts({})
    setModelStats({})
    setVoted(false)
    setWinner(null)
    setError(null)

    try {
      await streamABTest(prompt, {
        onStart: (data) => {
          setTestMeta(data)
          // Initialize empty text for each model
          const texts = {}
          data.models.forEach(m => { texts[m] = '' })
          setModelTexts(texts)
        },
        onChunk: (data) => {
          setModelTexts(prev => ({
            ...prev,
            [data.model]: (prev[data.model] || '') + data.content,
          }))
        },
        onModelDone: (data) => {
          setModelStats(prev => ({
            ...prev,
            [data.model]: data,
          }))
        },
        onComplete: () => {
          setIsRunning(false)
        },
        onError: (err) => {
          setError(err.message)
          setIsRunning(false)
        },
      })
      // Stream ended
      setIsRunning(false)
    } catch (err) {
      setError(err.message)
      setIsRunning(false)
    }
  }, [prompt, isRunning])

  const handleVote = async (model) => {
    if (!testMeta?.test_id || voted) return
    try {
      await voteABTest(testMeta.test_id, model)
      setVoted(true)
      setWinner(model)
    } catch {
      // ignore vote errors
    }
  }

  const loadHistory = async () => {
    const data = await getABTestHistory()
    setHistory(data)
  }

  const allModelsDone = testMeta && Object.keys(modelStats).length === testMeta.models.length

  return (
    <div className="space-y-6">
      {/* Input */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Swords className="w-4 h-4 text-purple-400" />
          <span className="text-sm font-medium text-gray-300">A/B Test Arena</span>
          <span className="text-xs text-gray-500">— Compare models head-to-head</span>
        </div>
        <div className="flex gap-3">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && e.metaKey) handleRun() }}
            placeholder="Enter a prompt to test across multiple models..."
            rows={2}
            className="flex-1 bg-gray-800/50 border border-gray-700/50 rounded-lg p-3 text-sm text-gray-200 placeholder-gray-500 resize-none focus:outline-none focus:border-purple-500/50"
          />
          <button
            onClick={handleRun}
            disabled={!prompt.trim() || isRunning}
            className="self-end flex items-center gap-1.5 px-4 py-2 bg-purple-500 hover:bg-purple-600 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Send className="w-3.5 h-3.5" />
            {isRunning ? 'Running...' : 'Battle!'}
          </button>
        </div>
        <div className="flex gap-2 mt-2">
          {EXAMPLE_PROMPTS.slice(0, 3).map((ex, i) => (
            <button
              key={i}
              onClick={() => setPrompt(ex.text)}
              className="text-xs px-2 py-1 rounded-md bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors"
            >
              {ex.type}
            </button>
          ))}
        </div>
      </div>

      {/* Loading (before start event) */}
      {isRunning && !testMeta && (
        <div className="flex items-center justify-center gap-3 py-12 text-gray-400">
          <div className="w-5 h-5 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
          <span className="text-sm">Starting models...</span>
        </div>
      )}

      {/* Streaming Results */}
      <AnimatePresence>
        {testMeta && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            {/* Test info */}
            <div className="flex items-center gap-3 text-sm text-gray-400">
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${TASK_TYPE_COLORS[testMeta.task_type]}`}>
                {TASK_TYPE_LABELS[testMeta.task_type]}
              </span>
              <span className="font-mono">complexity: {testMeta.complexity}</span>
              {isRunning && (
                <span className="flex items-center gap-1.5 text-purple-400">
                  <div className="w-3 h-3 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
                  Streaming...
                </span>
              )}
            </div>

            {/* Side by side results */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {testMeta.models.map((model, i) => {
                const text = modelTexts[model] || ''
                const stats = modelStats[model]
                const isDone = !!stats
                const isWinner = winner === model
                const colors = MODEL_COLORS[model] || {}
                const hasError = stats?.error

                return (
                  <motion.div
                    key={model}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className={`bg-gray-900 border rounded-xl p-4 transition-colors ${
                      isWinner ? `${colors.border} border-2` : 'border-gray-800'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <ModelBadge model={model} />
                      <div className="flex items-center gap-2">
                        {!isDone && text.length > 0 && (
                          <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
                        )}
                        {isDone && !hasError && (
                          <span className="text-[10px] text-green-400">Done</span>
                        )}
                        {isWinner && (
                          <span className="flex items-center gap-1 text-xs text-yellow-400">
                            <Trophy className="w-3 h-3" /> Winner
                          </span>
                        )}
                      </div>
                    </div>

                    <div
                      ref={(el) => { scrollRefs.current[model] = el }}
                      className="bg-gray-800/50 rounded-lg p-3 h-48 overflow-y-auto mb-3"
                    >
                      {text ? (
                        <pre className="whitespace-pre-wrap text-xs text-gray-300 font-mono leading-relaxed">
                          {text}
                          {!isDone && <span className="animate-pulse text-purple-400">|</span>}
                        </pre>
                      ) : (
                        <div className="flex items-center justify-center h-full text-gray-600 text-xs">
                          {isRunning ? 'Waiting for response...' : 'No response'}
                        </div>
                      )}
                    </div>

                    {isDone && !hasError && (
                      <div className="flex gap-3 text-xs text-gray-500 mb-3">
                        <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{stats.latency_ms}ms</span>
                        <span className="flex items-center gap-1"><Hash className="w-3 h-3" />{stats.tokens_used}</span>
                        <span className="flex items-center gap-1"><Coins className="w-3 h-3" />${stats.cost_cents?.toFixed(4)}</span>
                      </div>
                    )}

                    {allModelsDone && !voted && !hasError && (
                      <button
                        onClick={() => handleVote(model)}
                        className="w-full py-1.5 text-xs font-medium rounded-lg border border-gray-700 text-gray-400 hover:bg-gray-800 hover:text-gray-200 transition-colors"
                      >
                        Vote Best
                      </button>
                    )}
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {error && (
        <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg p-3">
          Error: {error}
        </div>
      )}

      {/* History */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-gray-300">Test History</span>
          <button onClick={loadHistory} className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
            {history ? 'Refresh' : 'Load History'}
          </button>
        </div>

        {history && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b border-gray-800">
                  <th className="text-left py-2 pr-3">Prompt</th>
                  <th className="text-left py-2 pr-3">Type</th>
                  <th className="text-left py-2 pr-3">Models</th>
                  <th className="text-left py-2 pr-3">Winner</th>
                  <th className="text-left py-2">Date</th>
                </tr>
              </thead>
              <tbody>
                {history.map((test) => (
                  <tr key={test.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="py-2 pr-3 text-gray-300 max-w-48 truncate">{test.prompt}</td>
                    <td className="py-2 pr-3">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${TASK_TYPE_COLORS[test.task_type]}`}>
                        {TASK_TYPE_LABELS[test.task_type]}
                      </span>
                    </td>
                    <td className="py-2 pr-3 font-mono text-gray-400">
                      {JSON.parse(test.models || '[]').length} models
                    </td>
                    <td className="py-2 pr-3">
                      {test.winner_model ? <ModelBadge model={test.winner_model} /> : <span className="text-gray-600">—</span>}
                    </td>
                    <td className="py-2 text-gray-500">{new Date(test.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
