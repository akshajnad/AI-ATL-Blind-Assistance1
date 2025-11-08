'use client'

import Navigation from '@/components/Navigation'
import Button from '@/components/Button'
import { useRouter } from 'next/navigation'

export default function HelpPage() {
  const router = useRouter()

  return (
    <div className="min-h-screen flex flex-col">
      <Navigation />

      <main className="flex-1 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold mb-2">Help & Information</h1>
            <p className="text-gray-400">Learn how to use Kora effectively</p>
          </div>

          <div className="space-y-6">
            {/* Getting Started */}
            <section className="glass-panel p-6 rounded-lg">
              <h2 className="text-2xl font-semibold mb-4 flex items-center">
                <span className="mr-2">🚀</span>
                Getting Started
              </h2>

              <div className="space-y-4 text-gray-300">
                <div>
                  <h3 className="font-semibold text-white mb-2">1. Grant Camera Permissions</h3>
                  <p>Kora needs access to your camera to provide real-time vision assistance. When prompted, allow camera access in your browser.</p>
                </div>

                <div>
                  <h3 className="font-semibold text-white mb-2">2. Start a Session</h3>
                  <p>Click "Start Vision Session" on the home page or say "Hey Kora" to activate voice control. The live view will open with your camera feed.</p>
                </div>

                <div>
                  <h3 className="font-semibold text-white mb-2">3. Receive Guidance</h3>
                  <p>Kora will detect objects, measure distances, and provide voice guidance to help you navigate safely.</p>
                </div>
              </div>
            </section>

            {/* Features */}
            <section className="glass-panel p-6 rounded-lg">
              <h2 className="text-2xl font-semibold mb-4 flex items-center">
                <span className="mr-2">✨</span>
                Key Features
              </h2>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-kora-panel p-4 rounded-lg border border-kora-border">
                  <div className="text-2xl mb-2">🎯</div>
                  <h3 className="font-semibold mb-2">Object Detection</h3>
                  <p className="text-sm text-gray-400">
                    Real-time detection of people, vehicles, obstacles, and common objects using advanced AI.
                  </p>
                </div>

                <div className="bg-kora-panel p-4 rounded-lg border border-kora-border">
                  <div className="text-2xl mb-2">📏</div>
                  <h3 className="font-semibold mb-2">Depth Estimation</h3>
                  <p className="text-sm text-gray-400">
                    Measure distances to objects and obstacles for better spatial awareness.
                  </p>
                </div>

                <div className="bg-kora-panel p-4 rounded-lg border border-kora-border">
                  <div className="text-2xl mb-2">🔊</div>
                  <h3 className="font-semibold mb-2">Voice Guidance</h3>
                  <p className="text-sm text-gray-400">
                    Natural voice instructions powered by ElevenLabs for clear, human-like guidance.
                  </p>
                </div>

                <div className="bg-kora-panel p-4 rounded-lg border border-kora-border">
                  <div className="text-2xl mb-2">🗺️</div>
                  <h3 className="font-semibold mb-2">Spatial Mapping</h3>
                  <p className="text-sm text-gray-400">
                    3x3 grid overlay divides your view into zones for precise location information.
                  </p>
                </div>
              </div>
            </section>

            {/* Keyboard Shortcuts */}
            <section className="glass-panel p-6 rounded-lg">
              <h2 className="text-2xl font-semibold mb-4 flex items-center">
                <span className="mr-2">⌨️</span>
                Keyboard Shortcuts
              </h2>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="flex items-center">
                  <kbd className="px-3 py-2 bg-kora-panel rounded border border-kora-border mr-3 font-mono">Space</kbd>
                  <span className="text-gray-300">Start/Stop session</span>
                </div>

                <div className="flex items-center">
                  <kbd className="px-3 py-2 bg-kora-panel rounded border border-kora-border mr-3 font-mono">D</kbd>
                  <span className="text-gray-300">Describe surroundings</span>
                </div>

                <div className="flex items-center">
                  <kbd className="px-3 py-2 bg-kora-panel rounded border border-kora-border mr-3 font-mono">Q</kbd>
                  <span className="text-gray-300">Toggle quiet mode</span>
                </div>

                <div className="flex items-center">
                  <kbd className="px-3 py-2 bg-kora-panel rounded border border-kora-border mr-3 font-mono">Esc</kbd>
                  <span className="text-gray-300">Exit live view</span>
                </div>
              </div>
            </section>

            {/* Privacy */}
            <section className="glass-panel p-6 rounded-lg">
              <h2 className="text-2xl font-semibold mb-4 flex items-center">
                <span className="mr-2">🔒</span>
                Privacy & Security
              </h2>

              <div className="space-y-3 text-gray-300">
                <p>
                  <strong className="text-white">Local Processing:</strong> All vision processing happens in real-time. We don't store your camera feed or personal data.
                </p>
                <p>
                  <strong className="text-white">Secure Connection:</strong> All communications with the backend use encrypted WebSocket connections.
                </p>
                <p>
                  <strong className="text-white">No Recording:</strong> Kora does not record or save video footage. The camera feed is only used for real-time analysis.
                </p>
                <p>
                  <strong className="text-white">Settings Control:</strong> You have full control over voice, detection sensitivity, and other features through the Settings page.
                </p>
              </div>
            </section>

            {/* Troubleshooting */}
            <section className="glass-panel p-6 rounded-lg">
              <h2 className="text-2xl font-semibold mb-4 flex items-center">
                <span className="mr-2">🔧</span>
                Troubleshooting
              </h2>

              <div className="space-y-4">
                <div>
                  <h3 className="font-semibold text-white mb-2">Camera not working?</h3>
                  <p className="text-gray-300 text-sm">
                    Check your browser permissions and ensure no other application is using the camera. Try refreshing the page.
                  </p>
                </div>

                <div>
                  <h3 className="font-semibold text-white mb-2">No voice output?</h3>
                  <p className="text-gray-300 text-sm">
                    Make sure voice is enabled in Settings and your device volume is turned up. Check browser audio permissions.
                  </p>
                </div>

                <div>
                  <h3 className="font-semibold text-white mb-2">Connection issues?</h3>
                  <p className="text-gray-300 text-sm">
                    Ensure the backend server is running. The connection status is shown in the live view. Try reloading the page.
                  </p>
                </div>

                <div>
                  <h3 className="font-semibold text-white mb-2">Slow performance?</h3>
                  <p className="text-gray-300 text-sm">
                    Close other browser tabs and applications. Lower the sensitivity setting if needed. Ensure good lighting conditions.
                  </p>
                </div>
              </div>
            </section>

            {/* System Requirements */}
            <section className="glass-panel p-6 rounded-lg">
              <h2 className="text-2xl font-semibold mb-4 flex items-center">
                <span className="mr-2">💻</span>
                System Requirements
              </h2>

              <div className="grid md:grid-cols-2 gap-6 text-gray-300">
                <div>
                  <h3 className="font-semibold text-white mb-2">Supported Browsers</h3>
                  <ul className="list-disc list-inside space-y-1 text-sm">
                    <li>Chrome/Edge 90+</li>
                    <li>Firefox 88+</li>
                    <li>Safari 14+</li>
                  </ul>
                </div>

                <div>
                  <h3 className="font-semibold text-white mb-2">Recommended Hardware</h3>
                  <ul className="list-disc list-inside space-y-1 text-sm">
                    <li>720p+ webcam</li>
                    <li>4GB+ RAM</li>
                    <li>Stable internet connection</li>
                  </ul>
                </div>
              </div>
            </section>

            {/* Contact */}
            <section className="glass-panel p-6 rounded-lg bg-kora-gradient-dark">
              <h2 className="text-2xl font-semibold mb-4 flex items-center">
                <span className="mr-2">📧</span>
                Need More Help?
              </h2>

              <p className="text-gray-300 mb-4">
                If you're experiencing issues or have questions, we're here to help!
              </p>

              <div className="flex flex-wrap gap-3">
                <Button variant="primary" onClick={() => router.push('/live')}>
                  Start Using Kora
                </Button>
                <Button variant="secondary" onClick={() => router.push('/settings')}>
                  Adjust Settings
                </Button>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  )
}
