# 🖥️ FeedVox AI Desktop Application

> **Electron-based Desktop UI** for the FeedVox AI Medical Transcription & Coding Suite

## 📋 Overview

This is the desktop application component of FeedVox AI, built with Electron.js to provide a beautiful, cross-platform interface for medical audio transcription and coding.

## 🚀 Quick Start

### Prerequisites
- **Node.js 18.0+** - [Download here](https://nodejs.org/)
- **npm 9.0+** (comes with Node.js)
- **FeedVox AI Backend** - Must be running on localhost:7717

### Installation & Setup

```bash
# Navigate to UI directory
cd ui

# Install dependencies
npm install

# Install Electron dependencies
npm run postinstall

# Start development mode
npm start
```

## 🛠️ Development

### Available Scripts

```bash
# Development mode with hot reload
npm start
npm run dev

# Build for production
npm run build
npm run dist:win      # Windows executable
npm run dist:mac      # macOS DMG  
npm run dist:linux    # Linux AppImage/DEB

# Utilities
npm run clean         # Clear build artifacts
npm run rebuild       # Clean install and build
```

### Project Structure

```
ui/
├── assets/           # Application icons and resources
├── backend/          # Backend source code (copied during build)
├── node_modules/     # Node.js dependencies
├── index.html        # Main application window
├── main.js           # Electron main process
├── renderer.js       # Electron renderer process
├── preload.js        # Secure context bridge
├── styles.css        # Application styles
├── package.json      # Project configuration
└── build.cmd         # Windows build script
```

## ⚙️ Configuration

### Backend Integration

The desktop app automatically connects to the backend server at:
- **URL**: http://localhost:7717
- **Health Check**: /health endpoint
- **API Base**: /api/v1/

### Electron Builder Settings

The application is configured for cross-platform builds:

```json
{
  "build": {
    "appId": "com.feedvox.ai.desktop",
    "productName": "FeedVox AI",
    "directories": {
      "output": "dist",
      "buildResources": "build"
    },
    "extraResources": [{
      "from": "backend",
      "to": "backend"
    }]
  }
}
```

## 🎯 Features

### Core UI Components
- **📁 File Upload**: Drag & drop audio file interface
- **📊 Progress Tracking**: Real-time processing status
- **📝 Results Display**: Tabbed view for transcripts, notes, and codes
- **⚙️ Settings Panel**: Backend connection and configuration
- **🔄 System Tray**: Minimize to tray functionality

### Audio Processing Interface
- **Supported Formats**: WAV, MP3, M4A, FLAC, OGG, WMA
- **File Validation**: Automatic format and size checking
- **Batch Processing**: Multiple file upload support
- **Progress Indicators**: Visual feedback for each processing stage

### Results Management
- **📝 Transcript View**: Raw transcription with editing capabilities
- **🏥 Medical Notes**: Structured clinical information display
- **📊 Medical Codes**: ICD-10, CPT, and SNOMED-CT code tables
- **📋 Export Options**: Copy to clipboard and file export

## 🔧 Backend Communication

### API Integration

The UI communicates with the backend via REST API:

```javascript
// Health check
const response = await fetch('http://localhost:7717/health');

// Upload audio
const formData = new FormData();
formData.append('audio_file', file);
const response = await fetch('http://localhost:7717/api/v1/transcription/upload', {
  method: 'POST',
  body: formData
});

// Extract medical notes
const response = await fetch('http://localhost:7717/api/v1/notes/extract', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ transcript_text: text })
});
```

### Backend Auto-Start

The main process automatically starts the Python backend:

```javascript
// Start backend with correct Python path
const pythonExecutable = path.join(feedvoxDir, 'venv', 'Scripts', 'python.exe');
const mainPyPath = path.join(backendPath, 'main.py');

backendProcess = spawn(pythonExecutable, [mainPyPath], {
  cwd: backendPath,
  stdio: ['ignore', 'pipe', 'pipe'],
  env: { ...process.env, PYTHONPATH: backendPath },
  windowsHide: true
});
```

## 🔍 Troubleshooting

### Common Issues

**App won't start:**
```bash
# Clear dependencies and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Backend connection failed:**
- Check if Python backend is running on localhost:7717
- Verify Python virtual environment is activated
- Check backend logs for errors

**Build failures:**
```bash
# Clear build cache
npm run clean

# Rebuild Electron native modules
npm run rebuild
```

**Audio upload issues:**
- Verify file format is supported
- Check file size (recommended < 100MB)
- Ensure proper file permissions

### Debug Mode

Enable debug logging:

```bash
# Set environment variable
export NODE_ENV=development
npm start

# Windows
set NODE_ENV=development
npm start
```

## 🏗️ Building for Distribution

### Windows Portable Executable

```bash
npm run dist:win
```

Output: `dist/FeedVox AI.exe`

### Requirements for Distribution
- Backend Python environment must be included
- Medical codes CSV files must be bundled
- All dependencies packaged in executable

### Build Optimization

```json
{
  "build": {
    "compression": "maximum",
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true
    }
  }
}
```

## 📦 Packaging

The application packages:
- ✅ Electron framework
- ✅ Node.js runtime
- ✅ UI assets and code
- ✅ Backend Python code
- ✅ Medical codes database
- ✅ Configuration files

## 🔐 Security

### Electron Security Features
- **Context Isolation**: Enabled for security
- **Node Integration**: Disabled in renderer
- **Preload Scripts**: Secure API exposure
- **CSP Headers**: Content Security Policy

### Best Practices
- All backend communication uses localhost
- No external network access required
- Local file system access for audio files
- Secure handling of medical data

---

## 🎉 Ready to Build!

The FeedVox AI desktop application is now clean, optimized, and ready for:
- ✅ Development and testing
- ✅ Cross-platform building
- ✅ Distribution as standalone executable
- ✅ Integration with backend services

**Happy coding!** 🚀 