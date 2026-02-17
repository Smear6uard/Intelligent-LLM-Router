import { API_BASE } from './constants'

async function fetchJSON(path, options = {}) {
  console.log(`[API] ${options.method || 'GET'} ${path}`)
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  console.log(`[API] ${path} -> ${res.status}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || `HTTP ${res.status}`)
  }
  const data = await res.json()
  console.log(`[API] ${path} parsed OK`)
  return data
}

export async function classifyPrompt(prompt) {
  return fetchJSON('/classify', {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  })
}

export async function getCompletion(prompt, { stream = true, model = null } = {}) {
  return fetchJSON('/completion', {
    method: 'POST',
    body: JSON.stringify({ prompt, stream: false, model }),
  })
}

export async function streamCompletion(prompt, { model = null, onMetadata, onChunk, onDone, onError }) {
  const res = await fetch(`${API_BASE}/completion`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, stream: true, model }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    onError?.(new Error(err.detail || `HTTP ${res.status}`))
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    let eventType = null
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        eventType = line.slice(7).trim()
      } else if (line.startsWith('data: ') && eventType) {
        try {
          const data = JSON.parse(line.slice(6))
          if (eventType === 'metadata') onMetadata?.(data)
          else if (eventType === 'chunk') onChunk?.(data.content)
          else if (eventType === 'done') onDone?.(data)
        } catch {
          // skip malformed JSON
        }
        eventType = null
      }
    }
  }
}

export async function runABTest(prompt, models = null) {
  return fetchJSON('/ab-test', {
    method: 'POST',
    body: JSON.stringify({ prompt, models }),
  })
}

export async function streamABTest(prompt, { models = null, onStart, onChunk, onModelDone, onComplete, onError }) {
  const res = await fetch(`${API_BASE}/ab-test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, models }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    onError?.(new Error(err.detail || `HTTP ${res.status}`))
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    let eventType = null
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        eventType = line.slice(7).trim()
      } else if (line.startsWith('data: ') && eventType) {
        try {
          const data = JSON.parse(line.slice(6))
          if (eventType === 'start') onStart?.(data)
          else if (eventType === 'chunk') onChunk?.(data)
          else if (eventType === 'model_done') onModelDone?.(data)
          else if (eventType === 'complete') onComplete?.(data)
        } catch {
          // skip malformed JSON
        }
        eventType = null
      }
    }
  }
}

export async function voteABTest(testId, winnerModel) {
  return fetchJSON(`/ab-test/${testId}/vote`, {
    method: 'POST',
    body: JSON.stringify({ winner_model: winnerModel }),
  })
}

// Mode
export const getMode = () => fetchJSON('/mode')

// Analytics
export const getAnalyticsSummary = () => fetchJSON('/analytics/summary')
export const getTimeseries = (days = 7) => fetchJSON(`/analytics/timeseries?days=${days}`)
export const getModelDistribution = () => fetchJSON('/analytics/model-distribution')
export const getCostComparison = () => fetchJSON('/analytics/cost-comparison')
export const getRecentRequests = (limit = 20) => fetchJSON(`/analytics/recent?limit=${limit}`)
export const getABTestHistory = (limit = 20) => fetchJSON(`/ab-tests/history?limit=${limit}`)
