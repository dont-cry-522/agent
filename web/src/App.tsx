import { useState } from 'react'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import DocumentsPage from './components/DocumentsPage'

type Page = 'chat' | 'documents'

export default function App() {
  const [page, setPage] = useState<Page>('chat')
  const [currentConvId, setCurrentConvId] = useState('')
  const [chatKey, setChatKey] = useState(0)
  const [convRefresh, setConvRefresh] = useState(0)

  const handleNewChat = () => {
    setPage('chat')
    setCurrentConvId('')
    setChatKey((k) => k + 1)
    setConvRefresh((k) => k + 1)
  }

  const handleSelectConversation = (id: string) => {
    console.log('Switch to conversation:', id)
    setPage('chat')
    setCurrentConvId(id)
    setChatKey((k) => k + 1)
  }

  return (
    <div className="flex h-full bg-white">
      <Sidebar
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
        currentConvId={currentConvId}
        currentPage={page}
        onNavigate={setPage}
        refreshKey={convRefresh}
      />
      {page === 'chat' ? (
        <ChatArea key={chatKey} conversationId={currentConvId} />
      ) : (
        <DocumentsPage />
      )}
    </div>
  )
}
