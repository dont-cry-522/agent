import { useState, useCallback, useRef, useEffect } from 'react'

interface UseResizableOptions {
  initialSize: number
  minSize: number
  maxSize: number
}

export function useResizable({ initialSize, minSize, maxSize }: UseResizableOptions) {
  const [size, setSize] = useState(initialSize)
  const dragging = useRef(false)
  const startX = useRef(0)
  const startSize = useRef(0)

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    dragging.current = true
    startX.current = e.clientX
    startSize.current = size
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }, [size])

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current) return
      const delta = e.clientX - startX.current
      const newSize = Math.min(maxSize, Math.max(minSize, startSize.current + delta))
      setSize(newSize)
    }
    const onMouseUp = () => {
      dragging.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [maxSize, minSize])

  return { size, onMouseDown }
}

interface DragHandleProps {
  onMouseDown: (e: React.MouseEvent) => void
  direction?: 'horizontal' | 'vertical'
}

export function DragHandle({ onMouseDown, direction = 'horizontal' }: DragHandleProps) {
  const cls = direction === 'horizontal'
    ? 'w-1.5 cursor-col-resize hover:bg-indigo-200 active:bg-indigo-300 transition-colors shrink-0 relative group'
    : 'h-1.5 cursor-row-resize hover:bg-indigo-200 active:bg-indigo-300 transition-colors shrink-0 relative group'

  return (
    <div className={cls} onMouseDown={onMouseDown}>
      <div className="absolute inset-y-0 -left-1 -right-1" />
      <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-0.5 rounded opacity-0 group-hover:opacity-100 bg-indigo-400 transition-opacity" />
    </div>
  )
}
