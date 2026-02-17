import { useEffect, useRef } from 'react'

export default function StreamingResponse({ text, isStreaming }) {
  const containerRef = useRef(null)

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [text])

  if (!text && !isStreaming) return null

  return (
    <div
      ref={containerRef}
      className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 max-h-96 overflow-y-auto"
    >
      <pre className="whitespace-pre-wrap text-sm text-gray-200 font-mono leading-relaxed">
        {text}
        {isStreaming && (
          <span className="cursor-blink inline-block w-2 h-4 bg-gray-400 ml-0.5 align-middle" />
        )}
      </pre>
    </div>
  )
}
