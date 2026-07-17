import { useState } from 'react'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import DocumentsPage from './components/DocumentsPage'

type Page = 'chat' | 'documents'

export default function App() {
  const [page, setPage] = useState<Page>('chat')
  const [chatKey, setChatKey] = useState(0)

  const handleNewChat = () => {
    setPage('chat')
    setChatKey((k) => k + 1)
  }

  return (
    <div className="flex h-full bg-white">
      <Sidebar onNewChat={handleNewChat} currentPage={page} onNavigate={setPage} />
      {page === 'chat' ? <ChatArea key={chatKey} /> : <DocumentsPage />}
    </div>
  )
}
