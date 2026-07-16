export interface SearchResultItem {
  title: string
  path: string
  score: number
  bm25_score: number
  fusion_score: number
  rerank_score: number
  content: string
  heading: string
  doc_title: string
}

export interface ChatResponse {
  question: string
  answer: string
  rewritten_query: string
  citations: SearchResultItem[]
  retrieval_ms: number
  error: string | null
}

export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: SearchResultItem[]
  rewrittenQuery?: string
  retrievalMs?: number
  usage?: TokenUsage
  timestamp: number
}

export interface DocumentItem {
  id: string
  filename: string
  original_name: string
  format: string
  file_size: number
  chunk_count: number
  status: string
  error: string
  created_at: string
}

export interface StatsResponse {
  document_count: number
  chunk_count: number
  total_size: number
  index_size_bytes: number
}

export type StreamStatus = 'idle' | 'thinking' | 'searching' | 'generating' | 'done' | 'error'
