'use client'

import { forwardRef, useImperativeHandle } from 'react'
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
  useImperativeHandle(ref, () => ({
    getCurrentFrame: () => frame
  }), [frame])

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
      {frame ? (
        <motion.img
          key={frame}
          src={frame}
          alt="Vision feed"
          className="h-full w-full object-cover"
          initial={{ opacity: 0.15 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.35 }}
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center bg-black/80">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="rounded-2xl border border-white/20 bg-white/5 px-8 py-6 text-center backdrop-blur"
          >
            <div className="mb-3 text-xs uppercase tracking-[0.4em] text-white/60">
              {status}
            </div>
            <motion.div
              className="mx-auto h-12 w-12 rounded-full border-2 border-white/20 border-t-white"
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, ease: 'linear', duration: 1.4 }}
            />
          </motion.div>
        </div>
      )}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/30" />
    </div>
  )
})

export default CameraFeed
