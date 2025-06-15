const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
    // File operations
    openFileDialog: () => ipcRenderer.invoke('open-file-dialog'),
    readFile: (filePath) => ipcRenderer.invoke('read-file', filePath),
    
    // Backend operations
    getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
    checkBackendStatus: () => ipcRenderer.invoke('check-backend-status'),
    restartBackend: () => ipcRenderer.invoke('restart-backend'),
    testBackendConnection: () => ipcRenderer.invoke('test-backend-connection'),
    
    // Window operations
    minimize: () => ipcRenderer.invoke('minimize-window'),
    close: () => ipcRenderer.invoke('close-window'),
    
    // Event listeners
    onStartRecording: (callback) => ipcRenderer.on('start-recording', callback),
    onOpenSettings: (callback) => ipcRenderer.on('open-settings', callback),
    
    // App info
    getAppVersion: () => ipcRenderer.invoke('get-app-version'),
    isPackaged: () => ipcRenderer.invoke('is-packaged'),
    
    // Platform info
    platform: process.platform,
    
    // Remove listeners
    removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel)
});

// Expose a limited API for development
if (process.env.NODE_ENV === 'development') {
    contextBridge.exposeInMainWorld('electronDev', {
        openDevTools: () => ipcRenderer.invoke('open-dev-tools'),
        getResourcesPath: () => ipcRenderer.invoke('get-resources-path')
    });
}

// Security: prevent node integration
window.addEventListener('DOMContentLoaded', () => {
    // Remove any potential node globals
    delete window.require;
    delete window.exports;
    delete window.module;
});

// Log that preload script has loaded
console.log('FeedVox AI preload script loaded successfully'); 