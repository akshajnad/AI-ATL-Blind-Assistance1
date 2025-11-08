'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import GlassPanel from '@/components/GlassPanel'

export default function SettingsPage() {
  const router = useRouter()
  const [settings, setSettings] = useState({
    voiceEnabled: true,
    voiceVolume: 80,
    sensitivity: 'medium',
    environmentMode: 'indoor',
  })

  // Load settings from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('kora-settings')
    if (saved) {
      setSettings(JSON.parse(saved))
    }

    // Announce page
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance("Settings")
      utterance.rate = 0.9
      setTimeout(() => window.speechSynthesis.speak(utterance), 500)
    }
  }, [])

  // Save settings to localStorage
  const updateSetting = (key, value) => {
    const newSettings = { ...settings, [key]: value }
    setSettings(newSettings)
    localStorage.setItem('kora-settings', JSON.stringify(newSettings))

    // Voice feedback
    if ('speechSynthesis' in window) {
      const messages = {
        voiceEnabled: value ? "Voice enabled" : "Voice disabled",
        voiceVolume: `Volume ${value} percent`,
        sensitivity: `Sensitivity ${value}`,
        environmentMode: `Environment mode ${value}`,
      }
      const utterance = new SpeechSynthesisUtterance(messages[key])
      window.speechSynthesis.speak(utterance)
    }
  }

  const handleBack = () => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance("Going back")
      window.speechSynthesis.speak(utterance)
    }
    router.back()
  }

  const resetSettings = () => {
    const defaults = {
      voiceEnabled: true,
      voiceVolume: 80,
      sensitivity: 'medium',
      environmentMode: 'indoor',
    }
    setSettings(defaults)
    localStorage.setItem('kora-settings', JSON.stringify(defaults))

    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance("Settings reset to defaults")
      window.speechSynthesis.speak(utterance)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
      className="min-h-screen bg-kora-mesh relative overflow-hidden"
    >
      {/* Background elements */}
      <div className="absolute inset-0 bg-kora-gradient-ar"></div>

      {/* Ambient breathing circles */}
      <motion.div
        animate={{ scale: [1, 1.1, 1], opacity: [0.1, 0.15, 0.1] }}
        transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute top-20 right-10 w-96 h-96 bg-kora-accent/10 rounded-full blur-3xl"
      />

      {/* Header */}
      <motion.div
        initial={{ y: -50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="relative z-10 frosted border-b border-kora-border px-6 py-6 mb-6"
      >
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <h1 className="text-3xl font-bold text-kora-text">Settings</h1>
          <motion.button
            onClick={handleBack}
            whileHover={{ scale: 1.1, x: -5 }}
            whileTap={{ scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="w-12 h-12 rounded-xl bg-white/80 flex items-center justify-center shadow-kora-md"
            aria-label="Go back"
          >
            <svg className="w-6 h-6 text-kora-text" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
            </svg>
          </motion.button>
        </div>
      </motion.div>

      <div className="relative z-10 max-w-2xl mx-auto px-6 pb-20 space-y-4">
        {/* Voice Settings Card */}
        <GlassPanel variant="frosted" delay={0.1} className="p-6 space-y-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-kora-primary to-kora-secondary flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-semibold text-kora-text">Voice & Audio</h2>
              <p className="text-sm text-kora-text-secondary">Manage voice guidance</p>
            </div>
          </div>

          {/* Voice Toggle */}
          <motion.label
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="flex items-center justify-between p-4 rounded-xl bg-kora-panel cursor-pointer"
          >
            <div className="flex-1">
              <div className="font-medium text-kora-text">Voice Guidance</div>
              <div className="text-sm text-kora-text-secondary">Enable voice instructions</div>
            </div>
            <motion.button
              onClick={() => updateSetting('voiceEnabled', !settings.voiceEnabled)}
              className={`
                relative w-14 h-8 rounded-full
                ${settings.voiceEnabled
                  ? 'bg-gradient-to-r from-kora-primary to-kora-secondary shadow-kora-glow'
                  : 'bg-gray-300'
                }
              `}
              role="switch"
              aria-checked={settings.voiceEnabled}
              aria-label="Toggle voice guidance"
            >
              <motion.div
                animate={{ x: settings.voiceEnabled ? 24 : 4 }}
                transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                className="absolute top-1 w-6 h-6 rounded-full bg-white shadow-lg"
              />
            </motion.button>
          </motion.label>

          {/* Volume Slider */}
          <div className="p-4 rounded-xl bg-kora-panel">
            <label className="block">
              <div className="flex items-center justify-between mb-3">
                <span className="font-medium text-kora-text">Volume</span>
                <span className="text-kora-primary font-semibold">{settings.voiceVolume}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="10"
                value={settings.voiceVolume}
                onChange={(e) => updateSetting('voiceVolume', parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer"
                style={{
                  background: `linear-gradient(to right, #00d9a3 0%, #00b8ff ${settings.voiceVolume}%, #e5e7eb ${settings.voiceVolume}%, #e5e7eb 100%)`
                }}
                aria-label="Adjust voice volume"
              />
            </label>
          </div>
        </GlassPanel>

        {/* Detection Settings Card */}
        <GlassPanel variant="frosted" delay={0.2} className="p-6 space-y-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-kora-info to-kora-accent flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-semibold text-kora-text">Vision Detection</h2>
              <p className="text-sm text-kora-text-secondary">Configure detection settings</p>
            </div>
          </div>

          {/* Sensitivity */}
          <div className="p-4 rounded-xl bg-kora-panel">
            <label className="block">
              <div className="font-medium text-kora-text mb-3">Detection Sensitivity</div>
              <select
                value={settings.sensitivity}
                onChange={(e) => updateSetting('sensitivity', e.target.value)}
                className="w-full bg-white border-2 border-kora-border text-kora-text text-base px-4 py-3 rounded-xl appearance-none cursor-pointer hover:border-kora-primary transition-all focus:border-kora-primary focus:outline-none"
                aria-label="Select detection sensitivity"
              >
                <option value="low">Low - Fewer alerts</option>
                <option value="medium">Medium - Balanced</option>
                <option value="high">High - Maximum awareness</option>
              </select>
            </label>
          </div>

          {/* Environment Mode */}
          <div className="p-4 rounded-xl bg-kora-panel">
            <label className="block">
              <div className="font-medium text-kora-text mb-3">Environment Mode</div>
              <div className="grid grid-cols-2 gap-3">
                <motion.button
                  onClick={() => updateSetting('environmentMode', 'indoor')}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  transition={{ duration: 0.2 }}
                  className={`
                    px-4 py-3 rounded-xl font-medium
                    ${settings.environmentMode === 'indoor'
                      ? 'bg-gradient-to-r from-kora-primary to-kora-secondary text-white shadow-kora-glow'
                      : 'bg-white text-kora-text border-2 border-kora-border'
                    }
                  `}
                  aria-label="Set indoor mode"
                >
                  Indoor
                </motion.button>
                <motion.button
                  onClick={() => updateSetting('environmentMode', 'outdoor')}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  transition={{ duration: 0.2 }}
                  className={`
                    px-4 py-3 rounded-xl font-medium
                    ${settings.environmentMode === 'outdoor'
                      ? 'bg-gradient-to-r from-kora-primary to-kora-secondary text-white shadow-kora-glow'
                      : 'bg-white text-kora-text border-2 border-kora-border'
                    }
                  `}
                  aria-label="Set outdoor mode"
                >
                  Outdoor
                </motion.button>
              </div>
            </label>
          </div>
        </GlassPanel>

        {/* Reset Button */}
        <motion.button
          onClick={resetSettings}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          whileHover={{ scale: 1.02, backgroundColor: '#ff3333' }}
          whileTap={{ scale: 0.98 }}
          className="w-full bg-white border-2 border-kora-danger text-kora-danger font-semibold text-lg px-6 py-4 rounded-2xl shadow-kora-md"
          aria-label="Reset all settings to defaults"
        >
          Reset to Defaults
        </motion.button>
      </div>
    </motion.div>
  )
}
