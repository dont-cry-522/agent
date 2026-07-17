import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import type { Message, SearchResultItem, TokenUsage, StreamStatus } from '../types'
import CitationPanel from './CitationPanel'

const API_BASE = '/api'

const EXAMPLE_QUESTIONS = [
  'MCP 是什么，和 REST API 有什么区别',
  'FastAPI 的请求验证怎么实现',
  'Python 异步编程的核心概念',
]

interface ChatAreaProps {
  onMenuClick: () => void
}

export default function ChatArea({ onMenuClick }: ChatAreaProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [status, setStatus] = useState<StreamStatus>('idle')
  const [streamingText, setStreamingText] = useState('')
  const [activeCitations, setActiveCitations] = useState<SearchResultItem[]>([])
  const [rerank, setRerank] = useState(true)
  const [showCitations, setShowCitations] = useState(false)
  const [citationW, setCitationW] = useState(320)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const onCitationDrag = (e: React.MouseEvent) => {
    e.preventDefault()
    const startX = e.clientX
    const onMove = (ev: MouseEvent) => {
      setCitationW((w) => Math.max(200, Math.min(500, w - (ev.clientX - startX))))
    }
    const onUp = () => {
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText])

  const handleSend = useCallback(async (text?: string) => {
    const q = (text || input).trim()
    if (!q || status !== 'idle') return

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: q,
      timestamp: Date.now(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setStatus('thinking')
    setStreamingText('')

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    let fullText = ''
    let finalCitations: SearchResultItem[] = []
    let finalRewritten = ''
    let finalMs = 0
    let finalUsage: TokenUsage | null = null
    const assistantId = (Date.now() + 1).toString()

    try {
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, rerank }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            switch (event.type) {
              case 'thinking':
                if (event.content.includes('检索')) setStatus('searching')
                break
              case 'token':
                fullText += event.content
                setStreamingText(fullText)
                setStatus('generating')
                break
              case 'done':
                finalCitations = event.citations || []
                finalRewritten = event.rewritten_query || ''
                finalMs = event.retrieval_ms || 0
                finalUsage = event.usage || null
                break
              case 'error':
                setStatus('error')
                setStreamingText(event.message || '请求失败')
                return
            }
          } catch { /* skip */ }
        }
      }

      setActiveCitations(finalCitations)

      const assistantMsg: Message = {
        id: assistantId,
        role: 'assistant',
        content: fullText,
        citations: finalCitations,
        rewrittenQuery: finalRewritten,
        retrievalMs: finalMs,
        usage: finalUsage || undefined,
        timestamp: Date.now(),
      }
      setMessages((prev) => [...prev, assistantMsg])
      setStreamingText('')
      setStatus('done')
    } catch (err) {
      setStatus('error')
      setStreamingText(err instanceof Error ? err.message : '请求失败')
    }
  }, [input, status, rerank])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }

  const renderMarkdown = (text: string) => (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={{
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-indigo-600 underline decoration-indigo-300 hover:decoration-indigo-600 transition-colors">
            {children}
          </a>
        ),
        code: ({ className, children, ...props }) => {
          const isInline = !className
          if (isInline) {
            return <code className="bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded text-[0.8125rem] font-mono" {...props}>{children}</code>
          }
          return <code className={className} {...props}>{children}</code>
        },
      }}
    >
      {text}
    </ReactMarkdown>
  )

  const isBusy = status !== 'idle' && status !== 'done'

  return (
    <div className="flex-1 flex h-full min-w-0">
      <div className="flex-1 flex flex-col min-w-0 bg-white">
        {/* 移动端顶部栏 */}
        <div className="lg:hidden flex items-center gap-3 px-4 py-2.5 border-b border-gray-100 shrink-0">
          <button
            onClick={onMenuClick}
            className="p-1.5 -ml-1 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
          >
            <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span className="text-sm font-medium text-gray-700">DocAgent</span>
          {activeCitations.length > 0 && (
            <button
              onClick={() => setShowCitations(!showCitations)}
              className="ml-auto p-1.5 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
            >
              <span className="text-xs text-indigo-500 font-medium">{activeCitations.length} 条引用</span>
            </button>
          )}
        </div>

        {messages.length === 0 && status === 'idle' ? (
          <div className="flex-1 flex items-center justify-center px-4 sm:px-8">
            <div className="text-center max-w-lg w-full -mt-16">
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gray-900 rounded-2xl mx-auto mb-4 sm:mb-6 flex items-center justify-center">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-gray-900 mb-2 tracking-tight">
                有什么可以帮助你的？
              </h2>
              <p className="text-gray-500 text-sm mb-6 sm:mb-8">
                向你的本地知识库提问，获取基于文档的精准回答
              </p>

              <div className="flex flex-col sm:flex-row flex-wrap justify-center gap-2">
                {EXAMPLE_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleSend(q)}
                    className="px-3 py-2.5 sm:px-4 sm:py-2.5 text-sm text-gray-600 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl transition-colors cursor-pointer text-left sm:max-w-[280px] leading-snug"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 sm:py-6 space-y-4 sm:space-y-6">{/* messages content same as before */}
              {messages.map((msg) => (
                <div key={msg.id} className="flex gap-2 sm:gap-3">
                  <div className={`w-6 h-6 sm:w-7 sm:h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                    msg.role === 'user' ? 'bg-gray-900' : 'bg-indigo-100'
                  }`}>
                    {msg.role === 'user' ? (
                      <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                    ) : (
                      <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    {msg.role === 'assistant' && msg.rewrittenQuery && (
                      <div className="text-xs text-indigo-400 mb-1.5">
                        改写查询：{msg.rewrittenQuery}
                      </div>
                    )}
                    <div className={`text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? 'text-gray-800 font-medium'
                        : 'prose prose-sm max-w-none prose-pre:bg-[#1e293b] prose-pre:text-[#e2e8f0] prose-pre:rounded-xl prose-pre:shadow-sm prose-code:before:content-none prose-code:after:content-none text-gray-700'
                    }`}>
                      {msg.role === 'assistant'
                        ? renderMarkdown(msg.content)
                        : <p className="whitespace-pre-wrap">{msg.content}</p>
                      }
                    </div>
                    {msg.role === 'assistant' && (
                      <div className="flex items-center gap-3 text-xs text-gray-400 mt-2 flex-wrap">
                        {msg.retrievalMs != null && (
                          <span>{(msg.retrievalMs / 1000).toFixed(1)}s</span>
                        )}
                        {msg.citations && msg.citations.length > 0 && (
                          <button
                            onClick={() => { setActiveCitations(msg.citations!); setShowCitations(true) }}
                            className="text-indigo-500 hover:text-indigo-700 font-medium transition-colors cursor-pointer"
                          >
                            {msg.citations.length} 条引用
                          </button>
                        )}
                        {msg.usage && (
                          <span>{msg.usage.total_tokens}t</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {isBusy && (
                <div className="flex gap-2 sm:gap-3">
                  <div className="w-6 h-6 sm:w-7 sm:h-7 rounded-lg bg-indigo-100 flex items-center justify-center shrink-0 mt-0.5">
                    <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="flex gap-1">
                        <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" />
                        <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }} />
                        <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }} />
                      </div>
                      <span className="text-sm text-gray-400">
                        {status === 'thinking' && '分析中'}
                        {status === 'searching' && '检索知识库'}
                        {status === 'generating' && '生成回答'}
                      </span>
                    </div>
                    {streamingText && (
                      <div className="prose prose-sm max-w-none prose-pre:bg-[#1e293b] prose-pre:text-[#e2e8f0] prose-pre:rounded-xl prose-pre:shadow-sm prose-code:before:content-none prose-code:after:content-none text-sm text-gray-700">
                        {renderMarkdown(streamingText)}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {status === 'error' && streamingText && (
                <div className="flex gap-2 sm:gap-3">
                  <div className="w-6 h-6 sm:w-7 sm:h-7 rounded-lg bg-red-100 flex items-center justify-center shrink-0 mt-0.5">
                    <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-red-600">{streamingText}</p>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>
        )}

        {/* 移动端引用面板 */}
        {showCitations && activeCitations.length > 0 && (
          <div className="lg:hidden border-t border-gray-100">
            <CitationPanel
              citations={activeCitations}
              onViewSource={(c) => setActiveCitations([c])}
            />
          </div>
        )}

        <div className="border-t border-gray-100 bg-white px-3 sm:px-6 py-3 sm:py-4">
          <div className="max-w-3xl mx-auto">
            <div className="relative flex items-end gap-2 sm:gap-3 bg-gray-50 border border-gray-200 rounded-2xl px-3 sm:px-5 py-2.5 sm:py-3.5 focus-within:border-indigo-300 focus-within:ring-2 focus-within:ring-indigo-100 transition-all">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="输入问题，Enter 发送"
                disabled={isBusy}
                rows={1}
                className="flex-1 bg-transparent outline-none text-sm sm:text-base text-gray-800 placeholder-gray-400 resize-none disabled:opacity-50 max-h-40"
              />
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => setRerank(!rerank)}
                  className={`hidden sm:flex items-center gap-1 px-2.5 py-1.5 text-[11px] font-medium rounded-lg transition-colors cursor-pointer ${
                    rerank
                      ? 'bg-indigo-50 text-indigo-600 border border-indigo-200'
                      : 'bg-white text-gray-400 border border-gray-200 hover:text-gray-600'
                  }`}
                  title="启用 Reranker 精排可提高准确性，但增加约 1s 延迟"
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${rerank ? 'bg-indigo-500' : 'bg-gray-300'}`} />
                  Rerank
                </button>
                <button
                  onClick={() => handleSend()}
                  disabled={isBusy || !input.trim()}
                  className="p-2 sm:p-2.5 bg-gray-900 text-white rounded-xl hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer"
                >
                  {isBusy ? (
                    <svg className="w-4 h-4 sm:w-5 sm:h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
            {rerank && (
              <p className="text-[11px] text-gray-400 text-center mt-2 hidden sm:block">
                Reranker 已启用 · 精排使结果更准确
              </p>
            )}
          </div>
        </div>
      </div>

      {/* 拖拽手柄 + 桌面端引用面板 */}
      <div className="hidden lg:flex shrink-0">
        <div
          className="w-1.5 bg-gray-200 hover:bg-indigo-400 active:bg-indigo-400 transition-colors shrink-0 cursor-col-resize relative"
          onMouseDown={onCitationDrag}
        >
          <div className="absolute inset-y-0 -left-1 -right-1" />
        </div>
        <div style={{ width: citationW, minWidth: 200, maxWidth: 500 }}>
          <CitationPanel
            citations={activeCitations}
            onViewSource={(c) => setActiveCitations([c])}
          />
        </div>
      </div>
    </div>
  )
}
