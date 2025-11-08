'use client'

import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'

export default function LoadingScreen({ onComplete }) {
  const [progress, setProgress] = useState(0)
  const [text, setText] = useState('')
  const fullText = 'KORA'

  useEffect(() => {
    // Typing animation
    let currentIndex = 0
    const typingInterval = setInterval(() => {
      if (currentIndex < fullText.length) {
        setText(fullText.substring(0, currentIndex + 1))
        currentIndex++
      } else {
        clearInterval(typingInterval)
      }
    }, 150)

    // Progress bar
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(progressInterval)
          setTimeout(() => onComplete?.(), 500)
          return 100
        }
        return prev + 2
      })
    }, 30)

    return () => {
      clearInterval(typingInterval)
      clearInterval(progressInterval)
    }
  }, [onComplete, fullText])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="fixed inset-0 bg-gradient-to-br from-white via-kora-bg to-kora-panel flex items-center justify-center overflow-hidden"
    >
      {/* Ambient background effects */}
      <div className="absolute inset-0 bg-kora-mesh opacity-50"></div>

      {/* Breathing circle */}
      <motion.div
        animate={{
          scale: [1, 1.1, 1],
          opacity: [0.1, 0.15, 0.1],
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: "easeInOut"
        }}
        className="absolute w-96 h-96 rounded-full bg-gradient-to-br from-kora-primary to-kora-secondary blur-3xl"
      />

      {/* Main content */}
      <div className="relative z-10 text-center">
        {/* Logo typing animation */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="mb-12"
        >
          <h1 className="text-8xl font-bold tracking-tight mb-4">
            <span className="bg-gradient-to-r from-kora-primary via-kora-secondary to-kora-accent bg-clip-text text-transparent">
              {text}
              <motion.span
                animate={{ opacity: [1, 0, 1] }}
                transition={{ duration: 0.8, repeat: Infinity }}
                className="inline-block w-1 h-20 bg-kora-primary ml-2"
              />
            </span>
          </h1>
        </motion.div>

        {/* Status text */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.6 }}
          className="mb-8"
        >
          <p className="text-xl text-kora-text-secondary font-medium tracking-wide">
            Initializing Vision System
          </p>
        </motion.div>

        {/* Progress bar */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1, duration: 0.4 }}
          className="w-64 mx-auto"
        >
          <div className="h-1 bg-kora-border rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-kora-primary to-kora-secondary"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3, ease: "easeOut" }}
            />
          </div>
          <motion.p
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="text-sm text-kora-text-muted mt-4"
          >
            {progress}%
          </motion.p>
        </motion.div>
      </div>
    </motion.div>
  )
}
