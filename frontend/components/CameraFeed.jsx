'use client'

import { useEffect, useRef, useState, forwardRef, useImperativeHandle } from 'react'
import { motion } from 'framer-motion'

/**
 * CameraFeed component - Simple video stream for camera input
 * AR overlays are now handled by the CameraOverlay component
 */
const CameraFeed = forwardRef(({
  onFrame,
  isActive = true,
  className = ''
}, ref) => {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)
  const [error, setError] = useState(null)
  const [isReady, setIsReady] = useState(false)

  // Initialize camera
  useEffect(() => {
    if (!isActive) return

    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: 'environment'
          },
          audio: false
        })

        if (videoRef.current) {
          videoRef.current.srcObject = stream
          streamRef.current = stream
          setIsReady(true)
          setError(null)
        }
      } catch (err) {
        console.error('Camera error:', err)
        setError('Unable to access camera. Please grant camera permissions.')
      }
    }

    startCamera()

    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [isActive])

  // Expose video dimensions to parent
  useImperativeHandle(ref, () => ({
    getVideoDimensions: () => {
      if (videoRef.current) {
        return {
          width: videoRef.current.videoWidth,
          height: videoRef.current.videoHeight
        }
      }
      return { width: 640, height: 480 }
    }
  }))

  // Capture and send frames periodically
  useEffect(() => {
    if (!isReady || !onFrame) return

    const interval = setInterval(() => {
      const canvas = canvasRef.current
      const video = videoRef.current

      if (canvas && video) {
        const ctx = canvas.getContext('2d')
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
        const frameData = canvas.toDataURL('image/jpeg', 0.8)
        onFrame(frameData)
      }
    }, 100) // 10 FPS

    return () => clearInterval(interval)
  }, [isReady, onFrame])

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className={`flex items-center justify-center bg-black ${className}`}
      >
        <motion.div
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          className="text-center p-8 glass-panel rounded-2xl"
        >
          <div className="text-kora-danger text-2xl mb-4 font-bold">Camera Error</div>
          <div className="text-kora-text text-lg">{error}</div>
        </motion.div>
      </motion.div>
    )
  }

  return (
    <div className={`relative ${className}`}>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-full h-full object-cover"
      />
      <canvas
        ref={canvasRef}
        className="hidden" // Hidden - only used for frame capture
      />
      {!isReady && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 flex items-center justify-center bg-black"
        >
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="text-center glass-panel px-8 py-10 rounded-2xl"
          >
            <div className="relative w-20 h-20 mx-auto mb-6">
              <div className="absolute inset-0 border-4 border-kora-primary/20 rounded-full"></div>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                className="absolute inset-0 border-4 border-kora-primary border-t-transparent rounded-full"
              />
            </div>
            <div className="text-kora-text text-xl font-medium">Initializing vision systems...</div>
          </motion.div>
        </motion.div>
      )}
    </div>
  )
})

CameraFeed.displayName = 'CameraFeed'

export default CameraFeed
