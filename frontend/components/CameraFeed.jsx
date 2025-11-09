/* eslint-disable @next/next/no-img-element */
'use client'

import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { motion } from 'framer-motion'

const WAITING_MESSAGE = 'Waiting for vision feed…'

const CameraFeed = forwardRef(function CameraFeed(
  {
    frame,
    status = WAITING_MESSAGE,
    className = '',
    isActive = true
  },
  ref
) {
  const imageRef = useRef(null)
  const frameRef = useRef(frame ?? null)
  const framePresentRef = useRef(Boolean(frame))
  const [hasFrame, setHasFrame] = useState(Boolean(frame))

  const updateFramePresence = useCallback((present) => {
    if (framePresentRef.current !== present) {
      framePresentRef.current = present
      setHasFrame(present)
    }
  }, [])

  const setFrame = useCallback(
    (nextFrame) => {
      frameRef.current = nextFrame || null
      const element = imageRef.current
      if (element) {
        if (nextFrame) {
          if (element.src !== nextFrame) {
            element.src = nextFrame
          }
          element.style.opacity = '1'
        } else {
          element.removeAttribute('src')
          element.style.opacity = '0'
        }
      }
      updateFramePresence(Boolean(nextFrame))
    },
    [updateFramePresence]
  )

  const clearFrame = useCallback(() => {
    setFrame(null)
  }, [setFrame])

  useEffect(() => {
    if (!isActive) {
      clearFrame()
    }
  }, [clearFrame, isActive])

  useEffect(() => {
    if (typeof frame === 'string' && frame.length) {
      setFrame(frame)
    } else if (frame === null) {
      clearFrame()
    }
  }, [clearFrame, frame, setFrame])

  useImperativeHandle(
    ref,
    () => ({
      getCurrentFrame: () => frameRef.current,
      setFrame,
      clearFrame
    }),
    [clearFrame, setFrame]
  )

  if (!isActive) {
    return (
      <div className={`relative flex items-center justify-center bg-black/90 text-white ${className}`}>
        <div className="text-sm uppercase tracking-[0.3em] text-white/70">
          Vision paused
        </div>
      </div>
    )
  }

  return (
    <div className={`relative overflow-hidden bg-black ${className}`}>
      <img
        ref={imageRef}
        alt="Vision feed"
        className="h-full w-full object-cover transition-opacity duration-75 ease-out"
        style={{ opacity: hasFrame ? 1 : 0 }}
        loading="eager"
      />
      {!hasFrame && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/80">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="rounded-2xl border border-white/20 bg-white/5 px-8 py-6 text-center backdrop-blur"
          >
            <div className="mb-3 text-xs uppercase tracking-[0.4em] text-white/60">
              {status}
            </div>
            <motion.div
              className="mx-auto h-12 w-12 rounded-full border-2 border-white/20 border-t-white"
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, ease: 'linear', duration: 1.1 }}
            />
          </motion.div>
        </div>
      )}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/30" />
    </div>
  )
})

export default CameraFeed
