import { useState } from 'react'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import DocumentsPage from './components/DocumentsPage'

type Page = 'chat' | 'documents'

export default function App() {
  const [page, setPage] = useState<Page>('chat')
  const [chatKey, setChatKey] = useState(0)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleNewChat = () => {
    setPage('chat')
    setChatKey((k) => k + 1)
    setSidebarOpen(false)
  }

  const handleNavigate = (p: Page) => {
    setPage(p)
    setSidebarOpen(false)
  }

  return (
    <div className="flex h-full bg-white">
      {/* 移动端遮罩 */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* 侧栏：移动端 overlay，桌面端固定 */}
      <div
        className={`
          fixed lg:static inset-y-0 left-0 z-40 w-72
          transform transition-transform duration-200
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          lg:translate-x-0
        `}
      >
        <Sidebar
          onNewChat={handleNewChat}
          currentPage={page}
          onNavigate={handleNavigate}
        />
      </div>

      {/* 主内容区 */}
      {page === 'chat' ? (
        <ChatArea key={chatKey} onMenuClick={() => setSidebarOpen(true)} />
      ) : (
        <DocumentsPage onMenuClick={() => setSidebarOpen(true)} />
      )}
    </div>
  )
}
