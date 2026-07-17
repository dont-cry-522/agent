import { useState } from 'react'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import DocumentsPage from './components/DocumentsPage'
import { useResizable, DragHandle } from './components/ResizableHandle'

type Page = 'chat' | 'documents'

export default function App() {
  const [page, setPage] = useState<Page>('chat')
  const [chatKey, setChatKey] = useState(0)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const sidebar = useResizable({ initialSize: 288, minSize: 200, maxSize: 400 })
  const citations = useResizable({ initialSize: 320, minSize: 240, maxSize: 500, reverse: true })

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
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* 侧栏 */}
      <div
        className={`
          fixed lg:static inset-y-0 left-0 z-40
          transform transition-transform duration-200
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          lg:translate-x-0
        `}
        style={{ width: sidebar.size }}
      >
        <Sidebar
          onNewChat={handleNewChat}
          currentPage={page}
          onNavigate={handleNavigate}
        />
      </div>

      {/* 侧栏拖拽手柄 */}
      <div className="hidden lg:block">
        <DragHandle onMouseDown={sidebar.onMouseDown} />
      </div>

      {/* 主内容区 */}
      {page === 'chat' ? (
        <ChatArea
          key={chatKey}
          onMenuClick={() => setSidebarOpen(true)}
          citationWidth={citations.size}
          onCitationResize={citations.onMouseDown}
        />
      ) : (
        <DocumentsPage onMenuClick={() => setSidebarOpen(true)} />
      )}
    </div>
  )
}
