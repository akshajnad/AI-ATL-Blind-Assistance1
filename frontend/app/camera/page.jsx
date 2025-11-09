'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import AppDock from '@/components/AppDock'
import CameraFeed from '@/components/CameraFeed'
import CameraOverlay, { ARCornerFrame } from '@/components/CameraOverlay'
import { createSocket } from '@/lib/socket'

const DEFAULT_DIMENSIONS = { width: 640, height: 480 }
const INITIAL_CAPTION = 'Initializing vision systems...'

const CONNECTION_COLORS = {
  connecting: 'bg-yellow-400',
  connected: 'bg-emerald-400',
  disconnected: 'bg-red-400',
  error: 'bg-red-500'
}

export default function CameraPage() {
  const [detections, setDetections] = useState([])
  const [caption, setCaption] = useState(INITIAL_CAPTION)
  const [connectionStatus, setConnectionStatus] = useState('connecting')
  const [cameraDimensions, setCameraDimensions] = useState(DEFAULT_DIMENSIONS)
  const [frameData, setFrameData] = useState(null)
  const [environment] = useState('indoor')

  const socketRef = useRef(null)
  const feedRef = useRef(null)

  const updateCameraDimensions = useCallback(({ width, height }) => {
    if (typeof width !== 'number' || typeof height !== 'number') {
      return
    }

    setCameraDimensions((prev) => {
      if (prev.width === width && prev.height === height) {
        return prev
      }
      return { width, height }
    })
  }, [])

  const handleDetection = useCallback(
    (data) => {
      if (!data) return

      if (data.dimensions) {
        updateCameraDimensions({
          width: data.dimensions.width,
          height: data.dimensions.height
        })
      }

      if (data.frame) {
        const value = data.frame.startsWith('data:')
          ? data.frame
          : `data:image/jpeg;base64,${data.frame}`
        setFrameData(value)
      }

      if (Array.isArray(data.objects)) {
        const formatted = data.objects.map((obj) => ({
          bbox: obj.bbox,
          label: obj.label || obj.class || 'object',
          confidence: obj.confidence || 0,
          distance: obj.distance,
          color: obj.color
        }))
        setDetections(formatted)

        if (!data.message && !data.notes) {
          if (formatted.length) {
            const summary = formatted
              .slice(0, 3)
              .map((det) => det.label)
              .join(', ')
            setCaption(`Detected ${summary}${formatted.length > 3 ? '…' : ''}`)
          } else {
            setCaption('Scanning environment…')
          }
        }
      }

      if (data.message) {
        setCaption(data.message)
      } else if (data.notes) {
        setCaption(data.notes)
      }
    },
    [updateCameraDimensions]
  )

  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws'
    const socket = createSocket(wsUrl, {
      maxReconnectAttempts: 10,
      reconnectDelay: 2000
    })

    socketRef.current = socket
    const feedHandle = feedRef.current
    setConnectionStatus('connecting')
    setCaption(INITIAL_CAPTION)

    const handleOpen = () => {
      setConnectionStatus('connected')
      setCaption('Vision system active.')
    }

    const handleClose = () => {
      setConnectionStatus('disconnected')
      setCaption('Connection lost. Attempting to reconnect…')
      setFrameData(null)
    }

    const handleError = (error) => {
      console.error('WebSocket error:', error)
      setConnectionStatus('error')
      setCaption('Connection error. Please ensure the vision service is running.')
      setFrameData(null)
    }

    socket.on('open', handleOpen)
    socket.on('close', handleClose)
    socket.on('error', handleError)
    socket.on('frame', handleDetection)
    socket.on('detection', handleDetection)
    socket.connect()

    return () => {
      socket.off('open', handleOpen)
      socket.off('close', handleClose)
      socket.off('error', handleError)
      socket.off('frame', handleDetection)
      socket.off('detection', handleDetection)
      socket.disconnect()
      socketRef.current = null
      feedHandle?.clearFrame()
    }
  }, [handleDetection])

  const handleDescribe = useCallback(() => {
    if (!socketRef.current) return
    if (!socketRef.current.isConnected()) {
      setCaption('Vision service unavailable. Trying to reconnect…')
      return
    }
    setCaption('Analyzing environment…')
    socketRef.current.send({ type: 'describe' })
  }, [])

  const statusColor = useMemo(() => CONNECTION_COLORS[connectionStatus] || CONNECTION_COLORS.connecting, [connectionStatus])

  return (
    <div className="relative flex h-screen w-screen items-center justify-center overflow-hidden bg-black text-white">
      <CameraFeed
        ref={feedRef}
        isActive
        frame={frameData}
        status={caption}
        className="absolute inset-0 h-full w-full"
      />

      <CameraOverlay
        detections={detections}
        width={cameraDimensions.width}
        height={cameraDimensions.height}
        className="absolute inset-0"
      />

      <ARCornerFrame />

      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent" />

      <header className="absolute left-0 right-0 top-0 flex items-center justify-between px-6 py-6 text-sm">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col">
          <span className="text-xs uppercase tracking-[0.35em] text-white/70">Vision Assistant</span>
          <span className="text-2xl font-semibold tracking-[0.25em] text-white">Kora</span>
        </motion.div>

        <div className="flex items-center gap-4 text-white/80">
          <div className="flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5">
            <span className={`h-2.5 w-2.5 rounded-full ${statusColor}`} />
            <span className="text-xs uppercase tracking-[0.3em]">{connectionStatus}</span>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5">
            <span className="text-[10px] uppercase tracking-[0.3em]">Mode</span>
            <span className="text-xs uppercase tracking-[0.2em]">{environment}</span>
          </div>
        </div>
      </header>

      <AnimatePresence>
        {caption && (
          <motion.div
            key={caption}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.4 }}
            className="absolute bottom-36 left-1/2 w-[90vw] max-w-3xl -translate-x-1/2 text-center"
          >
            <div className="pointer-events-none inline-flex items-center justify-center rounded-full border border-white/20 bg-black/60 px-6 py-3 text-sm uppercase tracking-[0.35em] text-white/80 backdrop-blur">
              {caption}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AppDock
        showMic
        className="absolute bottom-10 left-1/2 -translate-x-1/2"
        onMicPress={handleDescribe}
      />
    </div>
  )
}
