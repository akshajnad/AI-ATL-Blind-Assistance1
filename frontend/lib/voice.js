/**
 * ElevenLabs voice integration for Kora
 * Handles text-to-speech with streaming and fallback audio
 */

export class VoiceEngine {
  constructor(apiKey) {
    this.apiKey = apiKey
    this.voiceId = 'pNInz6obpgDQGcFmaJgB' // ElevenLabs voice ID
    this.model = 'eleven_turbo_v2'
    this.audioQueue = []
    this.isPlaying = false
    this.enabled = true
    this.currentAudio = null
    this.fallbackAudioMap = {
      left: '/audio/left.mp3',
      right: '/audio/right.mp3',
      stop: '/audio/stop.mp3',
      forward: '/audio/forward.mp3',
      caution: '/audio/caution.mp3',
    }
  }

  async speak(text, options = {}) {
    if (!this.enabled) return

    // Try ElevenLabs streaming first
    if (this.apiKey && this.apiKey !== 'your_elevenlabs_key') {
      try {
        await this.speakWithElevenLabs(text, options)
      } catch (error) {
        console.error('ElevenLabs error, trying fallback:', error)
        this.speakWithFallback(text)
      }
    } else {
      // Use fallback audio
      this.speakWithFallback(text)
    }
  }

  async speakWithElevenLabs(text, options = {}) {
    const url = `https://api.elevenlabs.io/v1/text-to-speech/${this.voiceId}/stream`

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Accept': 'audio/mpeg',
        'Content-Type': 'application/json',
        'xi-api-key': this.apiKey,
      },
      body: JSON.stringify({
        text,
        model_id: this.model,
        voice_settings: {
          stability: options.stability || 0.5,
          similarity_boost: options.similarity || 0.75,
        },
      }),
    })

    if (!response.ok) {
      throw new Error(`ElevenLabs API error: ${response.status}`)
    }

    const audioBlob = await response.blob()
    const audioUrl = URL.createObjectURL(audioBlob)
    await this.playAudio(audioUrl)
  }

  speakWithFallback(text) {
    // Extract direction keywords and use pre-recorded audio
    const lowerText = text.toLowerCase()

    for (const [keyword, audioPath] of Object.entries(this.fallbackAudioMap)) {
      if (lowerText.includes(keyword)) {
        this.playAudio(audioPath)
        return
      }
    }

    // If no keyword match, use browser's speech synthesis
    this.speakWithBrowserTTS(text)
  }

  speakWithBrowserTTS(text) {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.rate = 1.0
      utterance.pitch = 1.0
      utterance.volume = 1.0
      window.speechSynthesis.speak(utterance)
    }
  }

  async playAudio(audioUrl) {
    return new Promise((resolve, reject) => {
      // Stop current audio if playing
      if (this.currentAudio) {
        this.currentAudio.pause()
        this.currentAudio.currentTime = 0
      }

      const audio = new Audio(audioUrl)
      this.currentAudio = audio

      audio.onended = () => {
        this.isPlaying = false
        this.currentAudio = null
        resolve()
      }

      audio.onerror = (error) => {
        this.isPlaying = false
        this.currentAudio = null
        reject(error)
      }

      audio.play()
        .then(() => {
          this.isPlaying = true
        })
        .catch(reject)
    })
  }

  stop() {
    if (this.currentAudio) {
      this.currentAudio.pause()
      this.currentAudio.currentTime = 0
      this.currentAudio = null
    }
    this.isPlaying = false

    // Stop browser TTS
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
  }

  setEnabled(enabled) {
    this.enabled = enabled
    if (!enabled) {
      this.stop()
    }
  }

  isCurrentlyPlaying() {
    return this.isPlaying
  }
}

// Export singleton creator
export function createVoiceEngine(apiKey) {
  return new VoiceEngine(apiKey)
}
