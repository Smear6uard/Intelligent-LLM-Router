import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Sparkles, Zap, Clock, Coins, Hash, RotateCcw } from 'lucide-react'
import { classifyPrompt, streamCompletion } from '../utils/api'
import { EXAMPLE_PROMPTS, TASK_TYPE_LABELS, TASK_TYPE_COLORS } from '../utils/constants'
import ModelBadge from './ModelBadge'
import ComplexityGauge from './ComplexityGauge'
import StreamingResponse from './StreamingResponse'

export default function Playground() {
  const [prompt, setPrompt] = useState('')
  const [classification, setClassification] = useState(null)
  const [responseText, setResponseText] = useState('')
  const [metadata, setMetadata] = useState(null)
  const [completionStats, setCompletionStats] = useState(null)
  const [isClassifying, setIsClassifying] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)

  const handleSubmit = useCallback(async () => {
    if (!prompt.trim() || isStreaming) return

    setClassification(null)
    setResponseText('')
    setMetadata(null)
    setCompletionStats(null)
    setIsClassifying(true)

    try {
      const cls = await classifyPrompt(prompt)
      setClassification(cls)
      setIsClassifying(false)

      setIsStreaming(true)
      await streamCompletion(prompt, {
        onMetadata: (meta) => setMetadata(meta),
        onChunk: (content) => setResponseText(prev => prev + content),
        onDone: (stats) => {
          setCompletionStats(stats)
          setIsStreaming(false)
        },
        onError: (err) => {
          setResponseText(`Error: ${err.message}`)
          setIsStreaming(false)
        },
      })
    } catch (err) {
      setIsClassifying(false)
      setIsStreaming(false)
      setResponseText(`Error: ${err.message}`)
    }
  }, [prompt, isStreaming])

  const handleReset = () => {
    setPrompt('')
    setClassification(null)
    setResponseText('')
    setMetadata(null)
    setCompletionStats(null)
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Main Panel */}
      <div className="lg:col-span-2 space-y-4">
        {/* Prompt Input */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-orange-400" />
            <span className="text-sm font-medium text-gray-300">Prompt</span>
          </div>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && e.metaKey) handleSubmit() }}
            placeholder="Enter a prompt to classify and route..."
            rows={4}
            className="w-full bg-gray-800/50 border border-gray-700/50 rounded-lg p-3 text-sm text-gray-200 placeholder-gray-500 resize-none focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/20"
          />
          <div className="flex items-center justify-between mt-3">
            <div className="flex gap-2 flex-wrap">
              {EXAMPLE_PROMPTS.slice(0, 4).map((ex, i) => (
                <button
                  key={i}
                  onClick={() => setPrompt(ex.text)}
                  className="text-xs px-2 py-1 rounded-md bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors"
                >
                  {ex.type}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Reset
              </button>
              <button
                onClick={handleSubmit}
                disabled={!prompt.trim() || isStreaming}
                className="flex items-center gap-1.5 px-4 py-1.5 bg-orange-500 hover:bg-orange-600 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-medium rounded-lg transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
                Route & Complete
              </button>
            </div>
          </div>
        </div>

        {/* Classification Analysis */}
        <AnimatePresence>
          {(isClassifying || classification) && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="bg-gray-900 border border-gray-800 rounded-xl p-4"
            >
              <div className="flex items-center gap-2 mb-3">
                <Zap className="w-4 h-4 text-blue-400" />
                <span className="text-sm font-medium text-gray-300">Classification</span>
              </div>

              {isClassifying ? (
                <div className="flex items-center gap-2 text-gray-400 text-sm">
                  <div className="w-4 h-4 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin" />
                  Analyzing prompt...
                </div>
              ) : classification && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Task Type</div>
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${TASK_TYPE_COLORS[classification.task_type] || ''}`}>
                      {TASK_TYPE_LABELS[classification.task_type] || classification.task_type}
                    </span>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Confidence</div>
                    <span className="text-sm font-mono text-gray-200">{(classification.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Routed To</div>
                    <ModelBadge model={classification.recommended_model} />
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Reason</div>
                    <span className="text-xs text-gray-400">{classification.routing_reason}</span>
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Streaming Response */}
        <AnimatePresence>
          {(responseText || isStreaming) && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              <StreamingResponse text={responseText} isStreaming={isStreaming} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Completion Stats */}
        <AnimatePresence>
          {completionStats && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-4 text-xs text-gray-400"
            >
              <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {completionStats.latency_ms}ms</span>
              <span className="flex items-center gap-1"><Hash className="w-3 h-3" /> {completionStats.tokens_used} tokens</span>
              <span className="flex items-center gap-1"><Coins className="w-3 h-3" /> ${completionStats.cost_cents.toFixed(4)}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Sidebar */}
      <div className="space-y-4">
        {/* Complexity Gauge */}
        {classification && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col items-center"
          >
            <ComplexityGauge value={classification.complexity} />
          </motion.div>
        )}

        {/* Signal Breakdown */}
        {classification?.signals && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-gray-900 border border-gray-800 rounded-xl p-4"
          >
            <div className="text-sm font-medium text-gray-300 mb-3">Signal Breakdown</div>
            <div className="space-y-2">
              {Object.entries(classification.signals).map(([key, val]) => (
                <div key={key}>
                  <div className="flex justify-between text-xs mb-0.5">
                    <span className="text-gray-400">{key.replace(/_/g, ' ')}</span>
                    <span className="font-mono text-gray-300">{val.toFixed(1)}</span>
                  </div>
                  <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(val / 10) * 100}%` }}
                      transition={{ duration: 0.5 }}
                      className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
                    />
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Example Prompts */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="text-sm font-medium text-gray-300 mb-3">Try These</div>
          <div className="space-y-2">
            {EXAMPLE_PROMPTS.map((ex, i) => (
              <button
                key={i}
                onClick={() => setPrompt(ex.text)}
                className="w-full text-left p-2 rounded-lg text-xs text-gray-400 hover:bg-gray-800 hover:text-gray-200 transition-colors"
              >
                <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium mr-2 ${TASK_TYPE_COLORS[ex.type]}`}>
                  {ex.type}
                </span>
                {ex.text.slice(0, 60)}...
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
