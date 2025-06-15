const { app, BrowserWindow, Tray, Menu, ipcMain, dialog, shell, nativeImage } = require('electron');
const path = require('path');
const { spawn, exec, execSync } = require('child_process');
const fs = require('fs');
const axios = require('axios');
const http = require('http');

// Keep a global reference of the window object
let mainWindow;
let tray = null;
let backendProcess = null;
let isQuitting = false;

const isDev = process.env.NODE_ENV === 'development';
const BACKEND_URL = 'http://localhost:7717';

// App event handlers
app.whenReady().then(async () => {
    createWindow();
    createTray();
    
    // Check if backend is already running before starting a new one
    const isBackendRunning = await checkBackendStatus();
    if (!isBackendRunning) {
        console.log('Backend not running, starting new instance...');
        await startBackend();
    } else {
        console.log('Backend already running, skipping startup');
    }
    
    // Initial tray update after a short delay
    setTimeout(() => {
        updateTrayMenu().catch(console.error);
    }, 2000);
    
    // Check backend status periodically
    setInterval(() => {
        updateTrayMenu().catch(console.error);
    }, 10000);
});

app.on('window-all-closed', () => {
    // On macOS, keep app running even when all windows are closed
    if (process.platform !== 'darwin') {
        if (!tray) {
            app.quit();
        }
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});

app.on('before-quit', () => {
    console.log('App is quitting, cleaning up...');
    isQuitting = true;
    stopBackend();
});

app.on('will-quit', (event) => {
    console.log('App will quit');
    if (backendProcess) {
        event.preventDefault();
        stopBackend();
        setTimeout(() => {
            app.quit();
        }, 2000);
    }
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
    console.error('Uncaught Exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

function createWindow() {
    try {
        // Create the browser window
        mainWindow = new BrowserWindow({
            width: 1400,
            height: 900,
            minWidth: 1200,
            minHeight: 800,
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
                preload: path.join(__dirname, 'preload.js'),
                webSecurity: false, // Allow local file access for audio recording
                enableRemoteModule: false,
                sandbox: false
            },
            icon: getIconPath(),
            show: false,
            titleBarStyle: 'default',
            autoHideMenuBar: true,
            backgroundColor: '#f8fafc',
            title: 'FeedVox AI - Medical Transcription Suite'
        });
        
        console.log('Main window created successfully');
    } catch (error) {
        console.error('Failed to create window:', error);
        return;
    }

    // Load the app
    mainWindow.loadFile('index.html');

    // Show window when ready
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
        mainWindow.focus();
        
        if (isDev) {
            mainWindow.webContents.openDevTools();
        }
    });

    // Handle window closed
    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // Handle minimize to tray
    mainWindow.on('minimize', (event) => {
        if (tray) {
            event.preventDefault();
            mainWindow.hide();
            
            // Show notification on first minimize
            if (!mainWindow.hasMinimizedBefore) {
                if (process.platform === 'win32' && tray.displayBalloon) {
                    tray.displayBalloon({
                        iconType: 'info',
                        title: 'FeedVox AI',
                        content: 'App minimized to system tray. Click the tray icon to restore.'
                    });
                }
                mainWindow.hasMinimizedBefore = true;
            }
        }
    });

    // Handle close to tray
    mainWindow.on('close', (event) => {
        if (!isQuitting && tray) {
            event.preventDefault();
            mainWindow.hide();
            return false;
        }
    });
    
    // Setup window menu
    setupApplicationMenu();
}

function getIconPath() {
    // Try different icon formats
    const iconFormats = process.platform === 'win32' ? ['.ico', '.png'] : 
                       process.platform === 'darwin' ? ['.icns', '.png'] : ['.png'];
    
    for (const format of iconFormats) {
        const iconPath = path.join(__dirname, 'assets', `icon${format}`);
        if (fs.existsSync(iconPath)) {
            return iconPath;
        }
    }
    
    // Return a simple icon path
    return path.join(__dirname, 'assets', 'icon.png');
}

function createTray() {
    const iconPath = getIconPath();
    
    try {
        let trayIcon;
        if (fs.existsSync(iconPath)) {
            trayIcon = nativeImage.createFromPath(iconPath);
            if (trayIcon.isEmpty()) {
                trayIcon = nativeImage.createEmpty();
            }
        } else {
            trayIcon = nativeImage.createEmpty();
        }
        
        tray = new Tray(trayIcon);
        
        // Initialize tray menu
        updateTrayMenu().catch(console.error);
        tray.setToolTip('FeedVox AI - Medical Transcription Suite');
        
        // Handle tray click
        tray.on('click', () => {
            if (mainWindow) {
                if (mainWindow.isVisible()) {
                    mainWindow.hide();
                } else {
                    mainWindow.show();
                    mainWindow.focus();
                }
            }
        });
        
        // Handle double click
        tray.on('double-click', () => {
            if (mainWindow) {
                mainWindow.show();
                mainWindow.focus();
            }
        });
        
        console.log('System tray created successfully');
    } catch (error) {
        console.error('Failed to create system tray:', error);
    }
}

// Helper function to kill existing backend processes
async function killExistingBackends() {
    try {
        console.log('Checking for existing backend processes...');
        
        if (process.platform === 'win32') {
            // Kill processes on port 7717
            try {
                execSync('for /f "tokens=5" %a in (\'netstat -aon ^| find ":7717"\') do taskkill /f /pid %a 2>nul', { stdio: 'ignore' });
            } catch (error) {
                // Ignore errors - port might not be in use
            }
            
            // Kill any python processes running main.py
            try {
                execSync('taskkill /f /im python.exe /fi "WINDOWTITLE eq *main.py*" 2>nul', { stdio: 'ignore' });
                execSync('taskkill /f /im python3.exe /fi "WINDOWTITLE eq *main.py*" 2>nul', { stdio: 'ignore' });
            } catch (error) {
                // Ignore errors
            }
        } else {
            // Unix/Linux/macOS
            try {
                execSync('pkill -f "python.*main.py" 2>/dev/null || true', { stdio: 'ignore' });
                execSync('lsof -ti:7717 | xargs kill -9 2>/dev/null || true', { stdio: 'ignore' });
            } catch (error) {
                // Ignore errors
            }
        }
        
        // Wait a moment for processes to die
        await new Promise(resolve => setTimeout(resolve, 2000));
        console.log('Existing backend cleanup completed');
        
    } catch (error) {
        console.log('Backend cleanup error (non-critical):', error.message);
    }
}

// Helper function to check backend using native http module
function checkBackendWithHttp() {
    return new Promise((resolve) => {
        // Try both localhost and 127.0.0.1
        const hostnames = ['127.0.0.1', 'localhost'];
        let attempts = 0;
        
        function tryConnection(hostname) {
            const options = {
                hostname: hostname,
                port: 7717,
                path: '/health',
                method: 'GET',
                timeout: 6000
            };

            console.log(`Tray: Trying connection to ${hostname}:7717/health`);

            const req = http.request(options, (res) => {
                console.log(`Tray: HTTP status code from ${hostname}:`, res.statusCode);
                if (res.statusCode === 200) {
                    resolve(true);
                } else {
                    tryNextHost();
                }
            });

            req.on('error', (error) => {
                console.log(`Tray: HTTP request error from ${hostname}:`, error.code || error.message);
                tryNextHost();
            });

            req.on('timeout', () => {
                console.log(`Tray: HTTP request timeout from ${hostname}`);
                req.destroy();
                tryNextHost();
            });

            req.setTimeout(3000);
            req.end();
        }
        
        function tryNextHost() {
            attempts++;
            if (attempts < hostnames.length) {
                tryConnection(hostnames[attempts]);
            } else {
                console.log('Tray: All connection attempts failed');
                resolve(false);
            }
        }
        
        // Start with first hostname
        tryConnection(hostnames[0]);
    });
}

async function updateTrayMenu() {
    if (!tray || tray.isDestroyed()) {
        console.log('Tray: Cannot update - tray not available');
        return;
    }
    
    console.log('Tray: Updating menu and checking backend status...');
    
    // Check backend status for menu using native http with axios fallback
    let backendStatusLabel = 'Checking...';
    let isBackendRunning = false;
    
    try {
        // First try native HTTP
        isBackendRunning = await checkBackendWithHttp();
        
        // If native HTTP fails, try axios as fallback
        if (!isBackendRunning) {
            console.log('Tray: Native HTTP failed, trying axios fallback...');
            try {
                const response = await axios.get(`${BACKEND_URL}/health`, { 
                    timeout: 3000,
                    validateStatus: (status) => status === 200
                });
                isBackendRunning = response.status === 200;
                console.log('Tray: Axios fallback result:', response.status);
            } catch (axiosError) {
                console.log('Tray: Axios fallback also failed:', axiosError.code || axiosError.message);
            }
        }
        
        backendStatusLabel = isBackendRunning ? '✅ Connected' : '❌ Offline';
        console.log('Tray: Final backend status check result:', isBackendRunning ? 'Connected' : 'Offline');
    } catch (error) {
        backendStatusLabel = '❌ Offline';
        isBackendRunning = false;
        console.log('Tray: Backend status check failed:', error.message);
    }
    
    const contextMenu = Menu.buildFromTemplate([
        {
            label: 'FeedVox AI',
            enabled: false
        },
        { type: 'separator' },
        {
            label: 'Show Application',
            click: () => {
                if (mainWindow && !mainWindow.isDestroyed()) {
                    mainWindow.show();
                    mainWindow.focus();
                }
            },
            accelerator: 'CmdOrCtrl+Shift+F'
        },
        {
            label: 'New Recording',
            click: () => {
                if (mainWindow && !mainWindow.isDestroyed()) {
                    mainWindow.show();
                    mainWindow.focus();
                    mainWindow.webContents.send('start-recording');
                }
            },
            accelerator: 'CmdOrCtrl+R'
        },
        { type: 'separator' },
        {
            label: 'Backend Status',
            submenu: [
                {
                    label: backendStatusLabel,
                    enabled: false
                },
                { type: 'separator' },
                {
                    label: 'Check Status',
                    click: async () => {
                        const status = await checkBackendStatus();
                        dialog.showMessageBox(null, {
                            type: status ? 'info' : 'warning',
                            title: 'Backend Status',
                            message: status ? 'Backend is running normally' : 'Backend is not responding',
                            detail: status ? `Backend is available at ${BACKEND_URL}` : 'Try restarting the backend service'
                        });
                    }
                },
                {
                    label: isBackendRunning ? 'Stop Backend' : 'Start Backend',
                    click: () => {
                        if (isBackendRunning) {
                            stopBackend();
                        } else {
                            startBackend();
                        }
                    }
                },
                {
                    label: 'Restart Backend',
                    click: () => {
                        restartBackend();
                    }
                }
            ]
        },
        { type: 'separator' },
        {
            label: 'Open Backend API',
            click: () => {
                shell.openExternal(`${BACKEND_URL}/docs`);
            }
        },
        { type: 'separator' },
        {
            label: 'Quit FeedVox AI',
            click: () => {
                isQuitting = true;
                app.quit();
            },
            accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q'
        }
    ]);

    try {
        tray.setContextMenu(contextMenu);
        tray.setToolTip(`FeedVox AI - Backend: ${isBackendRunning ? 'Connected' : 'Offline'}`);
        
        // Update tray icon based on status
        if (isBackendRunning) {
            tray.setImage(getIconPath());
        } else {
            tray.setImage(getIconPath()); // Could use different icon for offline state
        }
        
        console.log('Tray: Menu updated successfully - Backend:', isBackendRunning ? 'Connected' : 'Offline');
    } catch (error) {
        console.error('Error setting tray menu:', error);
    }
}

function setupApplicationMenu() {
    const template = [
        {
            label: 'File',
            submenu: [
                {
                    label: 'New Recording',
                    accelerator: 'CmdOrCtrl+R',
                    click: () => {
                        if (mainWindow) {
                            mainWindow.webContents.send('start-recording');
                        }
                    }
                },
                { type: 'separator' },
                {
                    role: 'quit'
                }
            ]
        },
        {
            label: 'Edit',
            submenu: [
                { role: 'undo' },
                { role: 'redo' },
                { type: 'separator' },
                { role: 'cut' },
                { role: 'copy' },
                { role: 'paste' }
            ]
        },
        {
            label: 'View',
            submenu: [
                { role: 'reload' },
                { role: 'forceReload' },
                { role: 'toggleDevTools' },
                { type: 'separator' },
                { role: 'resetZoom' },
                { role: 'zoomIn' },
                { role: 'zoomOut' },
                { type: 'separator' },
                { role: 'togglefullscreen' }
            ]
        },
        {
            label: 'Backend',
            submenu: [
                {
                    label: 'Check Status',
                    click: async () => {
                        const status = await checkBackendStatus();
                        dialog.showMessageBox(mainWindow, {
                            type: status ? 'info' : 'warning',
                            title: 'Backend Status',
                            message: status ? 'Backend is running' : 'Backend is not responding'
                        });
                    }
                },
                {
                    label: 'Restart Backend',
                    click: () => {
                        restartBackend();
                    }
                },
                {
                    label: 'Open API Documentation',
                    click: () => {
                        shell.openExternal(`${BACKEND_URL}/docs`);
                    }
                }
            ]
        },
        {
            label: 'Help',
            submenu: [
                {
                    label: 'About FeedVox AI',
                    click: () => {
                        dialog.showMessageBox(mainWindow, {
                            type: 'info',
                            title: 'About FeedVox AI',
                            message: 'FeedVox AI - Medical Transcription Suite',
                            detail: 'Advanced AI-powered medical transcription and coding system'
                        });
                    }
                }
            ]
        }
    ];

    // macOS specific menu adjustments
    if (process.platform === 'darwin') {
        template.unshift({
            label: app.getName(),
            submenu: [
                { role: 'about' },
                { type: 'separator' },
                { role: 'services' },
                { type: 'separator' },
                { role: 'hide' },
                { role: 'hideothers' },
                { role: 'unhide' },
                { type: 'separator' },
                { role: 'quit' }
            ]
        });
    }

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
}

async function checkBackendStatus() {
    try {
        const isRunning = await checkBackendWithHttp();
        console.log('checkBackendStatus result:', isRunning);
        
        // Update tray menu by recreating it
        if (tray) {
            updateTrayMenu().catch(console.error);
        }
        
        return isRunning;
    } catch (error) {
        console.log('checkBackendStatus error:', error.message);
        
        // Update tray menu by recreating it
        if (tray) {
            updateTrayMenu().catch(console.error);
        }
        
        return false;
    }
}

async function startBackend() {
    // Kill any existing backend processes first
    await killExistingBackends();
    
    if (backendProcess) {
        console.log('Backend process already exists');
        return;
    }

    // Double-check if backend is already running on the port
    const isRunning = await checkBackendStatus();
    if (isRunning) {
        console.log('Backend already running on port 7717, skipping startup');
        return;
    }

    console.log('Starting FeedVox AI backend...');
    
    // Determine backend path and python executable
    let backendPath;
    let pythonExecutable;
    
    if (app.isPackaged) {
        // Production: use bundled backend
        backendPath = path.join(process.resourcesPath, 'backend');
        pythonExecutable = path.join(process.resourcesPath, 'backend', 'venv', 'Scripts', 'python.exe');
        console.log('Using bundled backend path:', backendPath);
        console.log('Using bundled Python executable:', pythonExecutable);
    } else {
        // Development: use local backend
        backendPath = path.join(__dirname, 'backend');
        // Get the absolute path to the parent directory's venv
        const uiDir = __dirname;  // C:\...\feedvox.ai\ui
        const feedvoxDir = path.dirname(uiDir);  // C:\...\feedvox.ai
        pythonExecutable = path.join(feedvoxDir, 'venv', 'Scripts', 'python.exe');
        console.log('Using development backend path:', backendPath);
        console.log('Using development Python executable:', pythonExecutable);
    }
    
    const mainPyPath = path.join(backendPath, 'main.py');
    
    // Check if Python executable exists
    if (!fs.existsSync(pythonExecutable)) {
        const error = `Python executable not found: ${pythonExecutable}`;
        console.error(error);
        if (mainWindow) {
            dialog.showErrorBox('Python Error', error);
        }
        return;
    }
    
    // Check if backend main.py exists
    if (!fs.existsSync(mainPyPath)) {
        const error = `Backend main.py not found: ${mainPyPath}`;
        console.error(error);
        if (mainWindow) {
            dialog.showErrorBox('Backend Error', error);
        }
        return;
    }
    
    console.log(`Using backend main.py: ${mainPyPath}`);
    
    try {
        // Set environment variables for the backend
        const env = {
            ...process.env,
            FEEDVOX_BUNDLED: app.isPackaged ? '1' : '0',
            PYTHONPATH: backendPath
        };
        
        backendProcess = spawn(pythonExecutable, [mainPyPath], {
            cwd: backendPath,
            stdio: ['ignore', 'pipe', 'pipe'],
            env: env,
            windowsHide: true,  // Hide console window on Windows
            detached: false
        });
        
        // Handle backend output
        backendProcess.stdout.on('data', (data) => {
            const output = data.toString().trim();
            console.log('Backend:', output);
            
            // Check for startup success messages
            if (output.includes('started successfully') || output.includes('Uvicorn running')) {
                console.log('Backend startup detected!');
                setTimeout(() => {
                    updateTrayMenu().catch(console.error);
                }, 2000);
            }
        });
        
        backendProcess.stderr.on('data', (data) => {
            const error = data.toString().trim();
            console.error('Backend Error:', error);
            
            // Check for critical errors
            if (error.includes('ModuleNotFoundError') || error.includes('ImportError')) {
                console.error('Backend dependency error detected');
            }
        });
        
        backendProcess.on('close', (code) => {
            console.log(`Backend process exited with code ${code}`);
            backendProcess = null;
            
            // Show notification if backend crashed
            if (code !== 0 && !isQuitting && tray) {
                if (process.platform === 'win32' && tray.displayBalloon) {
                    tray.displayBalloon({
                        iconType: 'error',
                        title: 'FeedVox AI Backend',
                        content: 'Backend service stopped unexpectedly. Click to restart.'
                    });
                }
                
                // Update tray to show offline status
                updateTrayMenu().catch(console.error);
            }
        });
        
        backendProcess.on('error', (error) => {
            console.error('Failed to start backend:', error);
            backendProcess = null;
            
            let errorMessage = `Failed to start backend service: ${error.message}`;
            
            if (error.code === 'ENOENT') {
                errorMessage = `Python executable not found: ${pythonExecutable}\n\nPlease ensure Python is installed and available in PATH.`;
            }
            
            if (mainWindow) {
                dialog.showErrorBox('Backend Startup Error', errorMessage);
            }
        });
        
        console.log('Backend process started with PID:', backendProcess.pid);
        
        // Wait for backend to be ready with multiple checks
        let attempts = 0;
        const maxAttempts = 30; // 30 seconds
        
        const checkReady = async () => {
            attempts++;
            const status = await checkBackendStatus();
            
            if (status) {
                console.log('Backend is ready!');
                updateTrayMenu().catch(console.error);
                
                if (tray && process.platform === 'win32' && tray.displayBalloon) {
                    tray.displayBalloon({
                        iconType: 'info',
                        title: 'FeedVox AI',
                        content: 'Backend service started successfully!'
                    });
                }
            } else if (attempts < maxAttempts && backendProcess) {
                // Try again in 1 second
                setTimeout(checkReady, 1000);
            } else {
                console.log('Backend startup timeout or process died');
                updateTrayMenu().catch(console.error);
            }
        };
        
        // Start checking after 3 seconds
        setTimeout(checkReady, 3000);
        
    } catch (error) {
        console.error('Error starting backend:', error);
        backendProcess = null;
    }
}

function stopBackend() {
    if (backendProcess) {
        console.log('Stopping backend...');
        backendProcess.kill('SIGTERM');
        
        // Force kill after 10 seconds
        setTimeout(() => {
            if (backendProcess) {
                backendProcess.kill('SIGKILL');
            }
        }, 10000);
        
        backendProcess = null;
    }
}

async function restartBackend() {
    console.log('Restarting backend...');
    
    // Kill all existing backends first
    await killExistingBackends();
    
    stopBackend();
    
    // Wait for cleanup
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Start fresh backend
    await startBackend();
}

// IPC handlers
ipcMain.handle('get-backend-url', () => {
    return BACKEND_URL;
});

ipcMain.handle('check-backend-status', async () => {
    return await checkBackendStatus();
});

ipcMain.handle('test-backend-connection', async () => {
    console.log('=== Manual Backend Connection Test ===');
    
    // Test 1: Native HTTP to 127.0.0.1
    console.log('Test 1: Native HTTP to 127.0.0.1:7717');
    const test1 = await checkBackendWithHttp();
    console.log('Result 1:', test1);
    
    // Test 2: Axios to localhost
    console.log('Test 2: Axios to localhost:7717');
    try {
        const response = await axios.get('http://localhost:7717/health', { timeout: 3000 });
        console.log('Result 2: Success -', response.status);
    } catch (error) {
        console.log('Result 2: Failed -', error.code || error.message);
    }
    
    // Test 3: Axios to 127.0.0.1
    console.log('Test 3: Axios to 127.0.0.1:7717');
    try {
        const response = await axios.get('http://127.0.0.1:7717/health', { timeout: 3000 });
        console.log('Result 3: Success -', response.status);
    } catch (error) {
        console.log('Result 3: Failed -', error.code || error.message);
    }
    
    console.log('=== End Connection Test ===');
    return { test1, timestamp: new Date().toISOString() };
});

ipcMain.handle('restart-backend', async () => {
    await restartBackend();
    return { success: true };
});

ipcMain.handle('open-file-dialog', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openFile'],
        filters: [
            {
                name: 'Audio Files',
                extensions: ['mp3', 'wav', 'm4a', 'flac', 'ogg', 'aac', 'mp4', 'mov', 'avi']
            },
            {
                name: 'All Files',
                extensions: ['*']
            }
        ]
    });
    
    return result;
});

ipcMain.handle('read-file', async (event, filePath) => {
    try {
        const fs = require('fs');
        const fileBuffer = fs.readFileSync(filePath);
        return {
            success: true,
            buffer: Array.from(fileBuffer),
            size: fileBuffer.length
        };
    } catch (error) {
        console.error('Error reading file:', error);
        return {
            success: false,
            error: error.message
        };
    }
});

// Window operations
ipcMain.handle('minimize-window', () => {
    if (mainWindow) {
        mainWindow.minimize();
    }
});

ipcMain.handle('close-window', () => {
    if (mainWindow) {
        mainWindow.close();
    }
});

// App info
ipcMain.handle('get-app-version', () => {
    return app.getVersion();
});

ipcMain.handle('is-packaged', () => {
    return app.isPackaged;
});

// Development tools
ipcMain.handle('open-dev-tools', () => {
    if (mainWindow && isDev) {
        mainWindow.webContents.openDevTools();
    }
});

ipcMain.handle('get-resources-path', () => {
    return process.resourcesPath;
});

// Prevent multiple instances
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
    console.log('Another instance is already running. Exiting...');
    app.quit();
} else {
    app.on('second-instance', (event, commandLine, workingDirectory) => {
        // Someone tried to run a second instance, focus our window instead
        console.log('Second instance detected, focusing existing window');
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            if (!mainWindow.isVisible()) mainWindow.show();
            mainWindow.focus();
        }
    });
} 