'use client'

import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { DetectionLabel } from './GlassPanel'

/**
 * CameraOverlay - AR-style overlay for object detection
 * Renders corner brackets, labels, and ripple animations
 */
export default function CameraOverlay({ detections = [], width, height, className = '' }) {
  const canvasRef = useRef(null)
  const [ripples, setRipples] = useState([])
  const prevDetectionsRef = useRef([])

  // Draw AR corner brackets on canvas
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !detections.length) return

    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, width, height)

    detections.forEach((det, index) => {
      const [x1, y1, x2, y2] = det.bbox
      const w = x2 - x1
      const h = y2 - y1
      const cornerLength = Math.min(w, h) * 0.2

      // Determine color based on distance
      let color = '#00d9a3' // Default teal
      if (det.distance) {
        if (det.distance < 1.0) color = '#ff3333' // Red - very close
        else if (det.distance < 2.5) color = '#ffaa00' // Orange - close
        else color = '#00d9a3' // Teal - safe
      }

      // Draw corner brackets with glow effect
      ctx.strokeStyle = color
      ctx.lineWidth = 3
      ctx.shadowColor = color
      ctx.shadowBlur = 10

      // Top-left corner
      ctx.beginPath()
      ctx.moveTo(x1, y1 + cornerLength)
      ctx.lineTo(x1, y1)
      ctx.lineTo(x1 + cornerLength, y1)
      ctx.stroke()

      // Top-right corner
      ctx.beginPath()
      ctx.moveTo(x2 - cornerLength, y1)
      ctx.lineTo(x2, y1)
      ctx.lineTo(x2, y1 + cornerLength)
      ctx.stroke()

      // Bottom-left corner
      ctx.beginPath()
      ctx.moveTo(x1, y2 - cornerLength)
      ctx.lineTo(x1, y2)
      ctx.lineTo(x1 + cornerLength, y2)
      ctx.stroke()

      // Bottom-right corner
      ctx.beginPath()
      ctx.moveTo(x2 - cornerLength, y2)
      ctx.lineTo(x2, y2)
      ctx.lineTo(x2, y2 - cornerLength)
      ctx.stroke()

      // Draw scanning line effect
      const scanY = y1 + (Date.now() % 1000) / 1000 * h
      ctx.strokeStyle = color + '40' // 25% opacity
      ctx.lineWidth = 1
      ctx.shadowBlur = 5
      ctx.beginPath()
      ctx.moveTo(x1, scanY)
      ctx.lineTo(x2, scanY)
      ctx.stroke()

      ctx.shadowBlur = 0
    })
  }, [detections, width, height])

  // Detect new objects and create ripple animations
  useEffect(() => {
    const prevIds = prevDetectionsRef.current.map(d => d.label + d.bbox.join(','))
    const currentIds = detections.map(d => d.label + d.bbox.join(','))

    detections.forEach((det, index) => {
      const id = det.label + det.bbox.join(',')
      if (!prevIds.includes(id)) {
        // New detection - create ripple
        const [x1, y1, x2, y2] = det.bbox
        const centerX = (x1 + x2) / 2
        const centerY = (y1 + y2) / 2

        const newRipple = {
          id: Date.now() + index,
          x: centerX,
          y: centerY,
          color: det.distance && det.distance < 2.5 ? '#ffaa00' : '#00d9a3'
        }

        setRipples(prev => [...prev, newRipple])

        // Remove ripple after animation completes
        setTimeout(() => {
          setRipples(prev => prev.filter(r => r.id !== newRipple.id))
        }, 1500)
      }
    })

    prevDetectionsRef.current = detections
  }, [detections])

  return (
    <div className={`absolute inset-0 pointer-events-none ${className}`}>
      {/* Canvas for AR brackets */}
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        className="absolute inset-0"
      />

      {/* Detection labels */}
      <AnimatePresence>
        {detections.map((det, index) => {
          const [x1, y1, x2, y2] = det.bbox
          const labelX = x1
          const labelY = Math.max(y1 - 10, 10) // Position above box, minimum 10px from top

          return (
            <motion.div
              key={`${det.label}-${index}`}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.3 }}
              style={{
                position: 'absolute',
                left: `${labelX}px`,
                top: `${labelY}px`,
              }}
            >
              <DetectionLabel
                label={det.label}
                confidence={det.confidence}
                distance={det.distance}
              />
            </motion.div>
          )
        })}
      </AnimatePresence>

      {/* Ripple animations for new detections */}
      <AnimatePresence>
        {ripples.map(ripple => (
          <motion.div
            key={ripple.id}
            initial={{ scale: 0, opacity: 0.6 }}
            animate={{ scale: 3, opacity: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1.5, ease: 'easeOut' }}
            style={{
              position: 'absolute',
              left: ripple.x,
              top: ripple.y,
              width: '100px',
              height: '100px',
              marginLeft: '-50px',
              marginTop: '-50px',
              borderRadius: '50%',
              border: `3px solid ${ripple.color}`,
              pointerEvents: 'none',
            }}
          />
        ))}
      </AnimatePresence>

      {/* Ambient AR grid overlay */}
      <div className="absolute inset-0 pointer-events-none">
        <div
          className="absolute inset-0 opacity-5"
          style={{
            backgroundImage: `
              linear-gradient(to right, #00d9a3 1px, transparent 1px),
              linear-gradient(to bottom, #00d9a3 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px'
          }}
        />
      </div>
    </div>
  )
}

/**
 * ARCornerFrame - Decorative AR corner frame for camera view
 */
export function ARCornerFrame({ className = '' }) {
  return (
    <div className={`absolute inset-0 pointer-events-none ${className}`}>
      {/* Top-left */}
      <svg className="absolute top-4 left-4 w-12 h-12 text-kora-primary opacity-60" viewBox="0 0 48 48" fill="none">
        <path d="M0 12V0H12" stroke="currentColor" strokeWidth="2" />
        <path d="M0 12V0H12" stroke="currentColor" strokeWidth="2" />
      </svg>

      {/* Top-right */}
      <svg className="absolute top-4 right-4 w-12 h-12 text-kora-primary opacity-60" viewBox="0 0 48 48" fill="none">
        <path d="M48 12V0H36" stroke="currentColor" strokeWidth="2" />
      </svg>

      {/* Bottom-left */}
      <svg className="absolute bottom-4 left-4 w-12 h-12 text-kora-primary opacity-60" viewBox="0 0 48 48" fill="none">
        <path d="M0 36V48H12" stroke="currentColor" strokeWidth="2" />
      </svg>

      {/* Bottom-right */}
      <svg className="absolute bottom-4 right-4 w-12 h-12 text-kora-primary opacity-60" viewBox="0 0 48 48" fill="none">
        <path d="M48 36V48H36" stroke="currentColor" strokeWidth="2" />
      </svg>

      {/* Crosshair center */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
        <motion.div
          animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          className="w-8 h-8 border-2 border-kora-primary rounded-full"
        />
        <div className="absolute top-1/2 left-1/2 w-16 h-0.5 bg-kora-primary/40 -translate-x-1/2 -translate-y-1/2" />
        <div className="absolute top-1/2 left-1/2 w-0.5 h-16 bg-kora-primary/40 -translate-x-1/2 -translate-y-1/2" />
      </div>
    </div>
  )
}
