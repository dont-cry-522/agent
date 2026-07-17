import { useState } from 'react'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import DocumentsPage from './components/DocumentsPage'

type Page = 'chat' | 'documents'

function DragBar({ onDrag }: { onDrag: (dx: number) => void }) {
  const onMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    const startX = e.clientX
    const onMove = (ev: MouseEvent) => onDrag(ev.clientX - startX)
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

  return (
    <div
      className="w-1.5 bg-gray-200 hover:bg-indigo-400 active:bg-indigo-400 transition-colors shrink-0 cursor-col-resize relative"
      onMouseDown={onMouseDown}
    >
      <div className="absolute inset-y-0 -left-1 -right-1" />
    </div>
  )
}

export default function App() {
  const [page, setPage] = useState<Page>('chat')
  const [chatKey, setChatKey] = useState(0)
  const [sidebarW, setSidebarW] = useState(288)

  const handleNewChat = () => {
    setPage('chat')
    setChatKey((k) => k + 1)
  }

  return (
    <div className="flex h-full bg-white overflow-hidden">
      {/* 侧栏 — 始终可见，最小 180px */}
      <div style={{ width: sidebarW, minWidth: 180, maxWidth: 440 }} className="shrink-1 flex">
        <Sidebar onNewChat={handleNewChat} currentPage={page} onNavigate={setPage} />
      </div>

      {/* 分隔条 — 始终可见 */}
      <DragBar onDrag={(dx) => setSidebarW((w) => Math.max(180, Math.min(440, w + dx)))} />

      {/* 主内容 */}
      <div className="flex-1 min-w-0 flex">
        {page === 'chat' ? (
          <ChatArea key={chatKey} onMenuClick={() => {}} />
        ) : (
          <DocumentsPage onMenuClick={() => {}} />
        )}
      </div>
    </div>
  )
}
