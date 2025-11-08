'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import LoadingScreen from '@/components/LoadingScreen'
import { FloatingCard } from '@/components/GlassPanel'

export default function HomePage() {
  const router = useRouter()
  const [isListening, setIsListening] = useState(false)
  const [isPulsing, setIsPulsing] = useState(true)
  const [isLoading, setIsLoading] = useState(true)

  // Show loading screen on first load
  useEffect(() => {
    const hasLoaded = sessionStorage.getItem('kora-loaded')
    if (hasLoaded) {
      setIsLoading(false)
    }
  }, [])

  const handleLoadingComplete = () => {
    setIsLoading(false)
    sessionStorage.setItem('kora-loaded', 'true')

    // Auto-announce page after loading
    const announcement = "Kora Vision Assistant. Tap anywhere to start."
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(announcement)
      utterance.rate = 0.9
      utterance.volume = 1.0
      setTimeout(() => {
        window.speechSynthesis.speak(utterance)
      }, 500)
    }
  }

  const handleStart = () => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance("Activating vision system")
      window.speechSynthesis.speak(utterance)
    }
    setIsListening(true)
    setTimeout(() => {
      router.push('/live')
    }, 600)
  }

  const handleSettings = (e) => {
    e.stopPropagation()
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance("Opening settings")
      window.speechSynthesis.speak(utterance)
    }
    router.push('/settings')
  }

  return (
    <>
      <AnimatePresence mode="wait">
        {isLoading && (
          <LoadingScreen key="loading" onComplete={handleLoadingComplete} />
        )}
      </AnimatePresence>

      {!isLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="min-h-screen bg-kora-mesh relative overflow-hidden"
        >
          {/* Abstract AR background elements */}
          <div className="absolute inset-0 bg-kora-gradient-ar"></div>

          {/* Floating ambient circles */}
          <motion.div
            animate={{ scale: [1, 1.1, 1], opacity: [0.1, 0.15, 0.1] }}
            transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute top-20 left-10 w-72 h-72 bg-kora-primary/10 rounded-full blur-3xl"
          />
          <motion.div
            animate={{ scale: [1, 1.15, 1], opacity: [0.1, 0.15, 0.1] }}
            transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
            className="absolute bottom-20 right-10 w-96 h-96 bg-kora-secondary/10 rounded-full blur-3xl"
          />

          {/* Main content */}
          <div
            className="relative min-h-screen flex flex-col items-center justify-center p-6"
            onClick={handleStart}
            role="button"
            tabIndex={0}
            aria-label="Start Kora Vision Assistant. Tap anywhere to begin."
          >
        {/* Logo and title */}
        <div className="text-center mb-12 animate-fade-in">
          <div className="mb-4">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-kora-primary to-kora-secondary rounded-3xl shadow-kora-xl mb-6">
              <svg className="w-12 h-12 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </div>
          </div>

          <h1 className="text-6xl font-bold mb-3 bg-gradient-to-r from-kora-primary via-kora-secondary to-kora-accent bg-clip-text text-transparent">
            KORA
          </h1>
          <p className="text-2xl text-kora-text-secondary font-medium">
            Your AI Vision Assistant
          </p>
        </div>

        {/* Pulsing mic button */}
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5, ease: 'easeOut' }}
          className="mb-16"
        >
          <div className="relative">
            {/* Outer pulsing rings */}
            <AnimatePresence>
              {isPulsing && (
                <>
                  <motion.div
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 1.2, opacity: 0 }}
                    className="absolute inset-0 w-48 h-48 -translate-x-1/2 -translate-y-1/2 left-1/2 top-1/2"
                  >
                    <motion.div
                      animate={{ scale: [1, 1.2, 1], opacity: [0.2, 0, 0.2] }}
                      transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                      className="absolute inset-0 bg-kora-primary/20 rounded-full"
                    />
                  </motion.div>
                  <motion.div
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 1.2, opacity: 0 }}
                    className="absolute inset-0 w-56 h-56 -translate-x-1/2 -translate-y-1/2 left-1/2 top-1/2"
                  >
                    <motion.div
                      animate={{ scale: [1, 1.2, 1], opacity: [0.15, 0, 0.15] }}
                      transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }}
                      className="absolute inset-0 bg-kora-secondary/15 rounded-full"
                    />
                  </motion.div>
                </>
              )}
            </AnimatePresence>

            {/* Main mic button */}
            <motion.button
              onClick={handleStart}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              transition={{ duration: 0.3, ease: 'easeInOut' }}
              className="relative w-40 h-40 rounded-full bg-gradient-to-br from-kora-primary to-kora-secondary shadow-kora-xl flex items-center justify-center"
              aria-label="Tap to start vision session"
            >
              {/* Glass overlay */}
              <div className="absolute inset-0 rounded-full bg-white/20 backdrop-blur-sm"></div>

              {/* 3D depth effect */}
              <div className="absolute inset-0 rounded-full shadow-inner opacity-20"></div>

              {/* Mic icon */}
              <motion.svg
                animate={isPulsing ? { scale: [1, 1.1, 1] } : {}}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                className="w-16 h-16 text-white relative z-10"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </motion.svg>
            </motion.button>
          </div>
        </motion.div>

        {/* Call to action */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.5 }}
          className="text-center"
        >
          <p className="text-xl text-kora-text-secondary mb-8 font-medium">
            Tap to Start
          </p>

          {/* Feature highlights */}
          <div className="grid grid-cols-3 gap-4 max-w-md mx-auto">
            <FloatingCard
              icon={
                <svg className="w-10 h-10 text-kora-primary mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              }
              description="Real-time Vision"
            />
            <FloatingCard
              icon={
                <svg className="w-10 h-10 text-kora-secondary mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              }
              description="AR Guidance"
            />
            <FloatingCard
              icon={
                <svg className="w-10 h-10 text-kora-accent mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                </svg>
              }
              description="Voice Feedback"
            />
          </div>
        </motion.div>
          </div>

          {/* Settings button - floating bottom right */}
          <motion.button
            onClick={handleSettings}
            whileHover={{ scale: 1.1, rotate: 45 }}
            whileTap={{ scale: 0.95 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="fixed bottom-8 right-8 w-16 h-16 rounded-2xl glass-panel flex items-center justify-center shadow-kora-lg"
            aria-label="Open settings"
          >
            <svg className="w-7 h-7 text-kora-text" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </motion.button>
        </motion.div>
      )}
    </>
  )
}
