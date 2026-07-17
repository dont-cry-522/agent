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
  conversation_id: string
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

export interface ConversationItem {
  id: string
  title: string
  message_count: number
  updated_at: string
}

export interface MessageItem {
  id: string
  role: string
  content: string
  created_at: string
}

export interface ConversationDetail {
  id: string
  title: string
  messages: MessageItem[]
  updated_at: string
}

export type StreamStatus = 'idle' | 'thinking' | 'searching' | 'generating' | 'done' | 'error'
