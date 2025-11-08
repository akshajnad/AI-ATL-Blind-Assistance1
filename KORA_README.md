# 🎯 KORA - AI Vision Assistant

**Real-time AI-powered vision assistance using computer vision and voice guidance**

Kora is a web-based assistive technology application that combines real-time object detection, depth estimation, and natural voice guidance to help users navigate their environment safely and independently.

---

## 🌟 Features

- **🎥 Real-time Object Detection** - YOLOv8-powered detection of people, vehicles, obstacles, and 80+ object classes
- **📏 Depth Estimation** - MiDaS depth sensing to measure distances to objects
- **🔊 Voice Guidance** - Natural voice instructions powered by ElevenLabs (with browser TTS fallback)
- **🗺️ Spatial Mapping** - 3x3 grid overlay for precise spatial awareness
- **⚡ WebSocket Streaming** - Low-latency real-time communication between frontend and backend
- **🎨 Beautiful UI** - Dark, futuristic design with Tailwind CSS and smooth animations
- **♿ Accessibility First** - ARIA labels, keyboard controls, and screen reader support
- **📱 Responsive Design** - Works on desktop and mobile devices

---

## 📁 Project Structure

```
AI-ATL-Blind-Assistance/
├── frontend/                # Next.js web application (JavaScript)
│   ├── app/                # Next.js App Router pages
│   │   ├── page.js        # Home page with animated mic
│   │   ├── live/          # Live camera feed with AR overlays
│   │   ├── settings/      # Settings and preferences
│   │   └── help/          # Help and documentation
│   ├── components/         # Reusable React components
│   │   ├── CameraFeed.jsx # Camera with canvas overlay
│   │   ├── Navigation.jsx # Top navigation bar
│   │   └── Button.jsx     # Styled button component
│   ├── lib/               # Utility libraries
│   │   ├── socket.js      # WebSocket client
│   │   └── voice.js       # ElevenLabs voice engine
│   ├── public/            # Static assets
│   └── package.json       # Frontend dependencies
│
├── vision/                # FastAPI backend (Python)
│   ├── main.py           # FastAPI app with WebSocket endpoint
│   ├── pipeline.py       # Vision processing pipeline
│   ├── schemas.py        # Pydantic data models
│   └── demo.py           # OpenCV demo application
│
├── ElevenLabs/           # Voice integration module
├── SnowFlake/            # Claude AI integration
└── requirements.txt      # Python dependencies
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **Webcam** (for camera input)
- **(Optional)** ElevenLabs API key for premium voice

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-repo/AI-ATL-Blind-Assistance.git
cd AI-ATL-Blind-Assistance
```

### 2️⃣ Set Up Backend (Python)

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server
cd vision
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend will start at `http://localhost:8000`

- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- WebSocket endpoint: `ws://localhost:8000/ws`

### 3️⃣ Set Up Frontend (Next.js)

In a **new terminal**:

```bash
cd frontend

# Install Node dependencies
npm install

# Copy environment template
cp .env.local.example .env.local

# (Optional) Add your ElevenLabs API key to .env.local
# NEXT_PUBLIC_ELEVEN_API_KEY=your_key_here

# Start the development server
npm run dev
```

The frontend will start at `http://localhost:3000`

### 4️⃣ Open Kora

1. Navigate to `http://localhost:3000` in your browser
2. Click **"Start Vision Session"** or say **"Hey Kora"**
3. Allow camera permissions when prompted
4. The live view will open with AR overlays and voice guidance!

---

## 🎮 How to Use

### Home Page (`/`)

- **Animated microphone** - Click to activate wake word listening
- **"Start Vision Session"** button - Jump directly to live view
- **Feature overview** - Learn about Kora's capabilities

### Live View (`/live`)

- **Real-time camera feed** with object detection overlays
- **Voice guidance** speaks detection results
- **Live captions** display current status
- **Detection list** shows all detected objects with confidence scores
- **Connection status** indicator (top left)

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Start/Stop session |
| `D` | Describe surroundings |
| `Q` | Toggle quiet mode (mute voice) |
| `Esc` | Exit to home page |

### Settings Page (`/settings`)

Customize your experience:
- **Voice & Audio**: Enable/disable voice, adjust volume, speech rate
- **Vision & Detection**: Sensitivity, environment mode (indoor/outdoor), motion detection
- **Accessibility**: High contrast mode
- **Advanced**: Developer mode for debug info

### Help Page (`/help`)

- Getting started guide
- Feature explanations
- Keyboard shortcuts
- Troubleshooting tips
- Privacy information

---

## ⚙️ Configuration

### Frontend Environment Variables

Edit `frontend/.env.local`:

```env
# Backend WebSocket URL
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# ElevenLabs API Key (optional, falls back to browser TTS)
NEXT_PUBLIC_ELEVEN_API_KEY=your_elevenlabs_key_here
```

### Backend Configuration

The backend uses:
- **YOLOv8 Nano** (`yolov8n.pt`) - Lightweight object detection
- **MiDaS Small** - Depth estimation
- **Environment modes**: Indoor (all objects) / Outdoor (filtered + classical CV)

No additional configuration needed for basic operation.

---

## 🔧 Development

### Frontend Development

```bash
cd frontend

# Development server with hot reload
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

### Backend Development

```bash
cd vision

# Run with auto-reload
uvicorn main:app --reload

# Run demo application (OpenCV visualization)
python demo.py --camera 0 --environment outdoor
```

### Testing the Integration

1. Start backend: `uvicorn main:app --reload`
2. Start frontend: `npm run dev`
3. Open `http://localhost:3000/live`
4. You should see:
   - Camera feed with green bounding boxes
   - Real-time FPS counter
   - Voice guidance speaking detected objects
   - Connection status: "connected"

---

## 🎨 Tech Stack

### Frontend
- **Next.js 14** - React framework with App Router
- **React 18** - UI library
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Animations (optional)
- **WebSocket API** - Real-time communication

### Backend
- **FastAPI** - Modern Python web framework
- **YOLOv8** (Ultralytics) - Object detection
- **MiDaS** (PyTorch) - Depth estimation
- **OpenCV** - Computer vision utilities
- **WebSocket** - Real-time streaming

### AI & Voice
- **ElevenLabs API** - Premium text-to-speech
- **Browser Speech Synthesis** - Fallback TTS
- **Snowflake Cortex** - Claude AI integration (optional)

---

## 📊 Architecture

```
┌─────────────┐         WebSocket          ┌─────────────┐
│   Browser   │ ◄─────────────────────────► │   FastAPI   │
│  (Next.js)  │    JSON detection data      │   Backend   │
└─────────────┘                             └─────────────┘
      │                                            │
      │ getUserMedia                               │
      ▼                                            ▼
┌─────────────┐                           ┌─────────────┐
│   Webcam    │                           │   YOLOv8    │
│   Stream    │                           │   + MiDaS   │
└─────────────┘                           └─────────────┘
      │                                            │
      │ base64 frames                              │
      └────────────────────────────────────────────┘
                                                   │
                                                   ▼
                                          ┌─────────────┐
                                          │  Detection  │
                                          │   Results   │
                                          └─────────────┘
                                                   │
                                                   ▼
                                          ┌─────────────┐
                                          │ Voice Engine│
                                          │ (ElevenLabs)│
                                          └─────────────┘
```

**Data Flow:**

1. **Camera** captures frames via `getUserMedia`
2. **Frontend** encodes frames as base64 and sends via WebSocket
3. **Backend** decodes frames and runs through YOLOv8 + MiDaS
4. **Detection results** sent back as JSON with bboxes, labels, distances
5. **Frontend** draws AR overlays on canvas and triggers voice guidance
6. **Voice engine** speaks instructions using ElevenLabs or browser TTS

---

## 🐛 Troubleshooting

### Camera Not Working

- **Check permissions**: Browser needs camera access
- **Close other apps**: Only one app can use the camera at a time
- **Try different browser**: Chrome/Edge recommended
- **Check console**: Open DevTools (F12) for error messages

### No Voice Output

- **Check volume**: System and browser volume must be up
- **Enable voice**: Go to Settings → Voice & Audio → Enable
- **API key**: If using ElevenLabs, verify key in `.env.local`
- **Fallback**: Browser TTS works without API key

### WebSocket Connection Failed

- **Backend running?**: Check `http://localhost:8000/health`
- **Port conflict**: Make sure port 8000 is free
- **CORS issue**: Check browser console for CORS errors
- **Firewall**: Ensure firewall allows localhost connections

### Low FPS / Slow Performance

- **Close tabs**: Free up browser resources
- **Lower sensitivity**: Settings → Detection → Low sensitivity
- **Good lighting**: Better lighting improves detection speed
- **CPU/GPU**: Vision processing is computationally intensive

### Build Errors

```bash
# Frontend: Clear cache and reinstall
cd frontend
rm -rf node_modules .next
npm install
npm run build

# Backend: Reinstall dependencies
pip install --upgrade -r requirements.txt
```

---

## 🔒 Privacy & Security

- ✅ **No data storage** - Camera feed is never recorded or saved
- ✅ **Local processing** - All vision processing happens locally
- ✅ **Encrypted WebSocket** - Secure real-time communication
- ✅ **No tracking** - No analytics or user tracking
- ✅ **Open source** - Full transparency of code

---

## 🚧 Roadmap

- [ ] Mobile app (React Native)
- [ ] Offline mode with service workers
- [ ] GPS integration for outdoor navigation
- [ ] Multi-language voice support
- [ ] Cloud deployment (Docker + K8s)
- [ ] AI scene description with Claude
- [ ] Haptic feedback for mobile devices

---

## 👥 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See `LICENSE` file for details.

---

## 🙏 Acknowledgments

- **YOLOv8** by Ultralytics - Object detection
- **MiDaS** by Intel ISL - Depth estimation
- **ElevenLabs** - Voice synthesis
- **FastAPI** - Web framework
- **Next.js** - React framework
- **Tailwind CSS** - Styling

---

## 📧 Contact

For questions, issues, or feedback:

- **GitHub Issues**: [Create an issue](https://github.com/your-repo/issues)
- **Email**: your-email@example.com

---

**Made with ❤️ for accessibility**

*Kora - Your AI vision companion*
