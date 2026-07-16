import { useEffect, useState } from 'react'
import { listDocuments } from '../api'
import type { DocumentItem } from '../types'

type Page = 'chat' | 'documents'

interface SidebarProps {
  onNewChat: () => void
  currentPage: Page
  onNavigate: (page: Page) => void
}

export default function Sidebar({ onNewChat, currentPage, onNavigate }: SidebarProps) {
  const [documents, setDocuments] = useState<DocumentItem[]>([])

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (currentPage === 'documents') {
      listDocuments()
        .then(setDocuments)
        .catch(() => {})
    }
  }, [currentPage])

  return (
    <aside className="w-72 bg-gray-50/50 border-r border-gray-100 flex flex-col h-full shrink-0">
      <div className="p-3 border-b border-gray-100 space-y-2">
        <button
          onClick={onNewChat}
          className="w-full py-2.5 px-3 bg-gray-900 text-white text-lg font-medium rounded-xl hover:bg-gray-800 transition-colors cursor-pointer flex items-center justify-center gap-1.5"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          新对话
        </button>

        <div className="flex rounded-lg bg-gray-100 p-0.5">
          <button
            onClick={() => onNavigate('chat')}
            className={`flex-1 py-1.5 text-lg font-medium rounded-md transition-all cursor-pointer ${
              currentPage === 'chat' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-400 hover:text-gray-600'
            }`}
          >
            对话
          </button>
          <button
            onClick={() => onNavigate('documents')}
            className={`flex-1 py-1.5 text-lg font-medium rounded-md transition-all cursor-pointer ${
              currentPage === 'documents' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-400 hover:text-gray-600'
            }`}
          >
            文档
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        <p className="text-lg font-semibold text-gray-400 mb-2 px-1">
          知识库
        </p>
        {documents.length === 0 ? (
          <p className="text-lg text-gray-400 px-1 py-3">暂无文档</p>
        ) : (
          <ul className="space-y-0.5">
            {documents.map((doc) => (
              <li
                key={doc.id}
                className="flex items-center gap-2.5 px-2 py-2 rounded-lg text-lg text-gray-600 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-4 h-4 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="truncate">{doc.original_name}</span>
                <span className="text-lg text-indigo-400 ml-auto shrink-0 font-medium">
                  {doc.chunk_count}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="p-3 border-t border-gray-100">
        <p className="text-sm text-gray-400 text-center">
          DocAgent
        </p>
      </div>
    </aside>
  )
}
