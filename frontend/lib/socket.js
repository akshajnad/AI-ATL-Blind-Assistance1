/**
 * WebSocket client for Kora backend communication
 * Handles auto-reconnection and message parsing
 */

export class KoraSocket {
  constructor(url, options = {}) {
    this.url = url
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = options.maxReconnectAttempts || 10
    this.reconnectDelay = options.reconnectDelay || 2000
    this.shouldReconnect = true
    this.listeners = {
      open: [],
      close: [],
      error: [],
      message: [],
      detection: [],
    }
  }

  connect() {
    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
        this.emit('open')
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket closed', event.code, event.reason)
        this.emit('close', event)

        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`)
          setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.emit('error', error)
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.emit('message', data)

          // If it's a detection message, emit detection event
          if (data.type === 'detection' || data.objects || data.bbox) {
            this.emit('detection', data)
          }
        } catch (error) {
          console.error('Failed to parse message:', error)
          this.emit('message', event.data)
        }
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      this.emit('error', error)
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = typeof data === 'string' ? data : JSON.stringify(data)
      this.ws.send(message)
      return true
    }
    console.warn('WebSocket not connected')
    return false
  }

  sendFrame(imageData) {
    // Send base64 encoded frame for analysis
    this.send({
      type: 'frame',
      data: imageData,
      timestamp: Date.now(),
    })
  }

  on(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback)
    }
  }

  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback)
    }
  }

  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(data))
    }
  }

  disconnect() {
    this.shouldReconnect = false
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN
  }
}

// Export a singleton instance creator
export function createSocket(url, options) {
  return new KoraSocket(url, options)
}
