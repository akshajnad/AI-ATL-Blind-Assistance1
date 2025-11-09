'use client'

import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'

const PLACEHOLDER_DIMENSIONS = { width: 640, height: 480 }

const CameraFeed = forwardRef(({ frameData, width, height, onDimensionsChange, className = '' }, ref) => {
  const canvasRef = useRef(null)
  const dimensionsRef = useRef({ ...PLACEHOLDER_DIMENSIONS })
  const [hasFrame, setHasFrame] = useState(false)

  // Normalize incoming dimensions from props
  useEffect(() => {
    const nextWidth = typeof width === 'number' && width > 0 ? width : dimensionsRef.current.width
    const nextHeight = typeof height === 'number' && height > 0 ? height : dimensionsRef.current.height
    if (nextWidth !== dimensionsRef.current.width || nextHeight !== dimensionsRef.current.height) {
      const nextDimensions = { width: nextWidth, height: nextHeight }
      dimensionsRef.current = nextDimensions
      if (typeof onDimensionsChange === 'function') {
        onDimensionsChange(nextDimensions)
      }
    }
  }, [width, height, onDimensionsChange])

  const imageSource = useMemo(() => {
    if (!frameData) return null
    return frameData.startsWith('data:') ? frameData : `data:image/jpeg;base64,${frameData}`
  }, [frameData])

  // Draw incoming frame on canvas so we can smoothly update without re-mounting DOM nodes
  useEffect(() => {
    if (!imageSource) return
    const canvas = canvasRef.current
    if (!canvas) return

    let cancelled = false
    const context = canvas.getContext('2d')
    const img = new Image()
    img.onload = () => {
      if (cancelled) return

      const imgWidth = img.naturalWidth || img.width
      const imgHeight = img.naturalHeight || img.height

      if (imgWidth && imgHeight) {
        if (canvas.width !== imgWidth || canvas.height !== imgHeight) {
          canvas.width = imgWidth
          canvas.height = imgHeight
        }

        const nextDimensions = { width: imgWidth, height: imgHeight }
        const prev = dimensionsRef.current
        if (prev.width !== imgWidth || prev.height !== imgHeight) {
          dimensionsRef.current = nextDimensions
          if (typeof onDimensionsChange === 'function') {
            onDimensionsChange(nextDimensions)
          }
        }
      }

      context.drawImage(img, 0, 0, canvas.width, canvas.height)
      setHasFrame(true)
    }
    img.onerror = () => {
      if (!cancelled) {
        setHasFrame(false)
      }
    }
    img.src = imageSource

    return () => {
      cancelled = true
    }
  }, [imageSource, onDimensionsChange])

  useImperativeHandle(ref, () => ({
    getVideoDimensions: () => ({ ...dimensionsRef.current })
  }), [])

  return (
    <div className={`relative overflow-hidden bg-black ${className}`}>
      <canvas
        ref={canvasRef}
        className="h-full w-full object-cover"
        style={{ width: '100%', height: '100%' }}
      />

      {!hasFrame && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4 }}
          className="absolute inset-0 flex items-center justify-center"
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="rounded-3xl border border-white/10 bg-white/5 px-8 py-10 text-center backdrop-blur"
          >
            <div className="relative mx-auto mb-6 h-20 w-20">
              <div className="absolute inset-0 rounded-full border-4 border-kora-primary/20" />
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1.4, repeat: Infinity, ease: 'linear' }}
                className="absolute inset-0 rounded-full border-4 border-kora-primary border-t-transparent"
              />
            </div>
            <div className="text-lg font-medium text-white/80">Waiting for camera feed…</div>
          </motion.div>
        </motion.div>
      )}
    </div>
  )
})

CameraFeed.displayName = 'CameraFeed'

export default CameraFeed

