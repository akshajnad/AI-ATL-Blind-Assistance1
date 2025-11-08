'use client'

import { motion } from 'framer-motion'

export default function MicButton({ isActive, isListening, onClick }) {
  return (
    <div className="relative">
      {/* Outer glow rings when active */}
      {isActive && (
        <>
          <motion.div
            animate={{
              scale: [1, 1.4, 1],
              opacity: [0.3, 0, 0.3],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut"
            }}
            className="absolute inset-0 w-28 h-28 -translate-x-1/2 -translate-y-1/2 left-1/2 top-1/2"
          >
            <div className="w-full h-full rounded-full bg-kora-primary blur-xl" />
          </motion.div>

          <motion.div
            animate={{
              scale: [1, 1.3, 1],
              opacity: [0.4, 0, 0.4],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 0.5
            }}
            className="absolute inset-0 w-28 h-28 -translate-x-1/2 -translate-y-1/2 left-1/2 top-1/2"
          >
            <div className="w-full h-full rounded-full bg-kora-secondary blur-xl" />
          </motion.div>
        </>
      )}

      {/* Main button */}
      <motion.button
        onClick={onClick}
        whileTap={{ scale: 0.92 }}
        whileHover={{ scale: 1.05 }}
        className={`
          relative w-24 h-24 rounded-full
          flex items-center justify-center
          transition-all duration-500
          ${isActive
            ? 'bg-gradient-to-br from-kora-primary via-kora-secondary to-kora-accent shadow-kora-glow'
            : 'bg-white/80 backdrop-blur-lg border-2 border-white/40 shadow-kora-xl'
          }
        `}
        aria-label={isActive ? "Deactivate microphone" : "Activate microphone"}
      >
        {/* Inner glass layer */}
        <div className="absolute inset-0 rounded-full bg-gradient-to-br from-white/30 to-transparent" />

        {/* Icon */}
        <motion.div
          animate={isListening ? {
            scale: [1, 1.1, 1],
          } : {}}
          transition={{
            duration: 1,
            repeat: isListening ? Infinity : 0,
            ease: "easeInOut"
          }}
          className="relative z-10"
        >
          {isActive ? (
            <svg className="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          ) : (
            <svg className="w-10 h-10 text-kora-text" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          )}
        </motion.div>

        {/* 3D press depth effect */}
        <div className="absolute inset-0 rounded-full shadow-inner opacity-20" />
      </motion.button>

      {/* Waveform under mic when listening */}
      {isListening && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="absolute -bottom-12 left-1/2 -translate-x-1/2 flex items-end space-x-1"
        >
          {[...Array(7)].map((_, i) => (
            <motion.div
              key={i}
              animate={{
                height: ['8px', '24px', '8px'],
              }}
              transition={{
                duration: 0.8,
                repeat: Infinity,
                ease: "easeInOut",
                delay: i * 0.1
              }}
              className="w-1 rounded-full bg-gradient-to-t from-kora-primary to-kora-secondary"
            />
          ))}
        </motion.div>
      )}
    </div>
  )
}
