'use client'

import { motion } from 'framer-motion'

/**
 * GlassPanel - Reusable liquid-glass UI component
 *
 * Variants:
 * - default: Standard glass panel with balanced blur and border
 * - glass: Ultra-clear glass with maximum transparency
 * - frosted: Heavy frosting with subtle glow
 * - panel: Solid panel with glass highlights
 */
export default function GlassPanel({
  children,
  className = '',
  variant = 'default',
  animate = true,
  delay = 0,
  ...props
}) {
  const variants = {
    default: 'bg-white/80 backdrop-blur-lg border border-white/20 shadow-kora-lg',
    glass: 'bg-white/60 backdrop-blur-md border border-white/30 shadow-kora-md',
    frosted: 'bg-white/90 backdrop-blur-xl border border-white/40 shadow-kora-xl',
    panel: 'bg-kora-panel backdrop-blur-lg border border-kora-border shadow-kora-lg',
    glow: 'bg-white/70 backdrop-blur-lg border border-kora-primary/30 shadow-kora-glow',
  }

  const animationProps = animate ? {
    initial: { opacity: 0, y: 10 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -10 },
    transition: {
      duration: 0.4,
      delay: delay,
      ease: [0.25, 0.1, 0.25, 1.0] // easeInOutCubic
    }
  } : {}

  return (
    <motion.div
      className={`
        ${variants[variant] || variants.default}
        rounded-2xl
        ${className}
      `}
      {...animationProps}
      {...props}
    >
      {/* Inner glass reflection layer */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-white/30 to-transparent pointer-events-none"></div>

      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </motion.div>
  )
}

/**
 * StatusPanel - Specialized glass panel for status messages
 */
export function StatusPanel({ children, status = 'info', className = '', ...props }) {
  const statusColors = {
    info: 'border-kora-info/30 shadow-kora-glow-blue',
    success: 'border-kora-success/30',
    warning: 'border-kora-warning/30',
    danger: 'border-kora-danger/30',
    active: 'border-kora-primary/40 shadow-kora-glow',
  }

  return (
    <GlassPanel
      variant="glass"
      className={`${statusColors[status]} ${className}`}
      {...props}
    >
      {children}
    </GlassPanel>
  )
}

/**
 * DetectionLabel - AR-style detection label with glass effect
 */
export function DetectionLabel({ label, confidence, distance, className = '', ...props }) {
  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0.8, opacity: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={`
        inline-flex items-center space-x-2 px-3 py-2 rounded-xl
        bg-white/90 backdrop-blur-md border border-white/40
        shadow-lg
        ${className}
      `}
      {...props}
    >
      <div className="flex flex-col">
        <span className="text-sm font-semibold text-kora-text">
          {label}
        </span>
        {(confidence || distance) && (
          <div className="flex items-center space-x-2 text-xs text-kora-text-secondary">
            {confidence && (
              <span>{Math.round(confidence * 100)}%</span>
            )}
            {distance && (
              <span>{distance}m</span>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}

/**
 * FloatingCard - Elevated card with glass effect for feature highlights
 */
export function FloatingCard({ icon, title, description, className = '', ...props }) {
  return (
    <motion.div
      whileHover={{ scale: 1.05, y: -5 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className={`
        bg-white rounded-2xl shadow-kora-xl border border-kora-border
        p-6 cursor-pointer
        ${className}
      `}
      {...props}
    >
      {/* Glass highlight */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-white/50 to-transparent pointer-events-none"></div>

      <div className="relative z-10 text-center">
        {icon && (
          <div className="mb-3">
            {icon}
          </div>
        )}
        {title && (
          <h3 className="text-lg font-semibold text-kora-text mb-1">{title}</h3>
        )}
        {description && (
          <p className="text-sm text-kora-text-secondary">{description}</p>
        )}
      </div>
    </motion.div>
  )
}
