// FeedVox AI - Medical Transcription & Coding
// Desktop Application Renderer Process

// Configuration
const CONFIG = {
    API_BASE_URL: 'http://localhost:7717',
    SUPPORTED_FORMATS: ['audio/wav', 'audio/mp3', 'audio/m4a', 'audio/flac', 'audio/ogg', 'audio/aac', 'audio/webm', 'audio/mp4'],
    MAX_FILE_SIZE: 500 * 1024 * 1024, // 500MB
    UPLOAD_TIMEOUT: 300000, // 5 minutes
    NOTE_TIMEOUT: 60000,    // 1 minute
    PROCESSING_CHECK_INTERVAL: 1000, // 1 second
    BACKEND_CHECK_INTERVAL: 5000     // 5 seconds
};

// Global state
let currentAudioFile = null;
let mediaRecorder = null;
let recordingStartTime = null;
let recordingTimer = null;
let isRecording = false;
let currentProcessingStep = 0;
let processingStartTime = null;
let currentResults = {
    transcript: null,
    notes: null,
    codes: null
};

// DOM elements cache
const elements = {};

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeElements();
    initializeEventListeners();
    initializeBackendStatus();
    loadSettings();
    showToast('System', 'FeedVox AI Desktop started successfully', 'success');
});

function initializeElements() {
    // Cache DOM elements for better performance
    elements.uploadPage = document.getElementById('upload-page');
    elements.processingPage = document.getElementById('processing-page');
    elements.resultsPage = document.getElementById('results-page');
    
    elements.uploadArea = document.getElementById('upload-area');
    elements.uploadPlaceholder = document.getElementById('upload-placeholder');
    elements.fileSelected = document.getElementById('file-selected');
    elements.fileName = document.getElementById('file-name');
    elements.fileSize = document.getElementById('file-size');
    elements.fileType = document.getElementById('file-type');
    elements.fileDuration = document.getElementById('file-duration');
    elements.previewAudio = document.getElementById('preview-audio');
    elements.removeFile = document.getElementById('remove-file');
    elements.recordBtn = document.getElementById('record-btn');
    elements.stopBtn = document.getElementById('stop-btn');
    elements.processBtn = document.getElementById('process-btn');
    elements.clearBtn = document.getElementById('clear-btn');
    elements.browseBtn = document.getElementById('browse-btn');
    elements.recordingIndicator = document.getElementById('recording-indicator');
    elements.recordingTimer = document.getElementById('recording-timer');
    elements.uploadProgress = document.getElementById('upload-progress');
    elements.progressText = document.getElementById('progress-text');
    elements.progressPercent = document.getElementById('progress-percent');
    elements.progressFill = document.getElementById('progress-fill');
    
    elements.processingTitle = document.getElementById('processing-title');
    elements.processingSubtitle = document.getElementById('processing-subtitle');
    elements.processingStatus = document.getElementById('processing-status');
    elements.processingDuration = document.getElementById('processing-duration');
    elements.processingProgress = document.getElementById('processing-progress');
    elements.cancelProcessingBtn = document.getElementById('cancel-processing');
    elements.processingSteps = {
        upload: document.getElementById('step-upload'),
        transcribe: document.getElementById('step-transcribe'),
        extract: document.getElementById('step-extract'),
        codes: document.getElementById('step-codes')
    };
    
    elements.navTranscript = document.getElementById('nav-transcript');
    elements.navNotes = document.getElementById('nav-notes');
    elements.navCodes = document.getElementById('nav-codes');
    elements.transcriptTab = document.getElementById('transcript-tab');
    elements.medicalNoteTab = document.getElementById('medical-note-tab');
    elements.medicalCodesTab = document.getElementById('medical-codes-tab');
    elements.transcriptContent = document.getElementById('transcript-content');
    elements.nextToNotesBtn = document.getElementById('next-to-notes');
    elements.nextToCodesBtn = document.getElementById('next-to-codes');
    elements.noteExtractionStatus = document.getElementById('note-extraction-status');
    elements.codesExtractionStatus = document.getElementById('codes-extraction-status');
    elements.newRecordingBtn = document.getElementById('new-recording');
    elements.exportResultsBtn = document.getElementById('export-results');
    
    elements.settingsModal = document.getElementById('settings-modal');
    elements.settingsBtn = document.getElementById('settings-btn');
    elements.closeSettingsBtn = document.getElementById('close-settings');
    elements.backendUrl = document.getElementById('backend-url');
    elements.testConnectionBtn = document.getElementById('test-connection');
    elements.restartBackendBtn = document.getElementById('restart-backend-btn');
    elements.saveSettingsBtn = document.getElementById('save-settings');
    
    elements.backendStatus = document.getElementById('backend-status');
    elements.minimizeBtn = document.getElementById('minimize-btn');
}

function initializeEventListeners() {
    // Recording controls
    elements.recordBtn?.addEventListener('click', startRecording);
    elements.stopBtn?.addEventListener('click', stopRecording);
    elements.processBtn?.addEventListener('click', processAudio);
    elements.clearBtn?.addEventListener('click', clearAudio);
    elements.browseBtn?.addEventListener('click', browseFiles);
    elements.removeFile?.addEventListener('click', removeSelectedFile);
    elements.previewAudio?.addEventListener('click', previewAudio);
    
    // Processing controls
    elements.cancelProcessingBtn?.addEventListener('click', cancelProcessing);
    
    // Results navigation
    elements.navTranscript?.addEventListener('click', () => switchResultsTab('transcript'));
    elements.navNotes?.addEventListener('click', () => switchResultsTab('notes'));
    elements.navCodes?.addEventListener('click', () => switchResultsTab('codes'));
    elements.nextToNotesBtn?.addEventListener('click', extractMedicalNotes);
    elements.nextToCodesBtn?.addEventListener('click', extractMedicalCodes);
    elements.newRecordingBtn?.addEventListener('click', startNewRecording);
    elements.exportResultsBtn?.addEventListener('click', exportResults);
    
    // Copy buttons
    document.getElementById('copy-transcript')?.addEventListener('click', () => copyToClipboard(elements.transcriptContent?.textContent));
    document.getElementById('copy-note')?.addEventListener('click', copyMedicalNote);
    
    // Settings
    elements.settingsBtn?.addEventListener('click', openSettings);
    elements.closeSettingsBtn?.addEventListener('click', closeSettings);
    elements.testConnectionBtn?.addEventListener('click', testConnection);
    elements.restartBackendBtn?.addEventListener('click', restartBackend);
    elements.saveSettingsBtn?.addEventListener('click', saveSettings);
    
    // Window controls
    elements.minimizeBtn?.addEventListener('click', minimizeWindow);
    
    // Drag and drop
    elements.uploadArea?.addEventListener('dragover', handleDragOver);
    elements.uploadArea?.addEventListener('drop', handleDrop);
    elements.uploadArea?.addEventListener('dragleave', () => elements.uploadArea?.classList.remove('dragover'));
    
    // Settings modal backdrop
    elements.settingsModal?.addEventListener('click', (e) => {
        if (e.target === elements.settingsModal) closeSettings();
    });
}

// Backend status management
async function updateBackendStatus() {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const response = await fetch(`${CONFIG.API_BASE_URL}/health`, {
            method: 'GET',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            const data = await response.json();
            setBackendStatus('connected', 'Connected');
            console.log('Backend health check successful:', data);
        } else {
            setBackendStatus('disconnected', `Error ${response.status}`);
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            setBackendStatus('disconnected', 'Connection timeout');
        } else {
            setBackendStatus('disconnected', 'Backend Offline');
        }
        console.warn('Backend health check failed:', error);
    }
}

function setBackendStatus(status, text) {
    if (!elements.backendStatus) return;
    
    elements.backendStatus.className = `status-indicator ${status}`;
    const statusText = elements.backendStatus.querySelector('span');
    if (statusText) {
        statusText.textContent = text;
    }
}

function initializeBackendStatus() {
    setBackendStatus('connecting', 'Connecting...');
    updateBackendStatus();
    
    // Check backend status periodically
    setInterval(updateBackendStatus, CONFIG.BACKEND_CHECK_INTERVAL);
}

// Page Navigation
function showPage(pageName) {
    console.log('Switching to page:', pageName);
    
    // Hide all pages
    elements.uploadPage?.classList.add('hidden');
    elements.processingPage?.classList.add('hidden');
    elements.resultsPage?.classList.add('hidden');
    
    // Show target page
    switch (pageName) {
        case 'upload':
            elements.uploadPage?.classList.remove('hidden');
            break;
        case 'processing':
            elements.processingPage?.classList.remove('hidden');
            break;
        case 'results':
            elements.resultsPage?.classList.remove('hidden');
            break;
    }
}

// Recording Functions
async function startRecording() {
    try {
        console.log('Starting recording...');
        
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 44100
            }
        });
        
        let options = { mimeType: 'audio/webm;codecs=opus' };
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            options = { mimeType: 'audio/webm' };
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                options = {}; // Use default
            }
        }
        
        mediaRecorder = new MediaRecorder(stream, options);
        const chunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                chunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = () => {
            const blob = new Blob(chunks, { type: 'audio/webm' });
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
            const filename = `recording-${timestamp}.webm`;
            
            currentAudioFile = new File([blob], filename, { type: 'audio/webm' });
            console.log('Recording completed:', currentAudioFile);
            
            displaySelectedFile(currentAudioFile);
            if (elements.processBtn) elements.processBtn.disabled = false;
            if (elements.clearBtn) elements.clearBtn.disabled = false;
            
            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
            
            showToast('Recording', 'Audio recorded successfully!', 'success');
        };
        
        mediaRecorder.start(1000); // Collect data every second
        isRecording = true;
        recordingStartTime = Date.now();
        
        // Update UI
        if (elements.recordBtn) elements.recordBtn.style.display = 'none';
        if (elements.stopBtn) elements.stopBtn.style.display = 'inline-flex';
        if (elements.recordingIndicator) elements.recordingIndicator.style.display = 'flex';
        
        // Start timer
        recordingTimer = setInterval(updateRecordingTimer, 1000);
        
        showToast('Recording', 'Recording started', 'info');
        
    } catch (error) {
        console.error('Error starting recording:', error);
        showToast('Recording Error', 'Could not access microphone. Please check permissions.', 'error');
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        console.log('Stopping recording...');
        mediaRecorder.stop();
        isRecording = false;
        
        // Update UI
        if (elements.recordBtn) elements.recordBtn.style.display = 'inline-flex';
        if (elements.stopBtn) elements.stopBtn.style.display = 'none';
        if (elements.recordingIndicator) elements.recordingIndicator.style.display = 'none';
        
        // Clear timer
        if (recordingTimer) {
            clearInterval(recordingTimer);
            recordingTimer = null;
        }
    }
}

function updateRecordingTimer() {
    if (!recordingStartTime || !elements.recordingTimer) return;
    
    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    elements.recordingTimer.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// File handling
async function browseFiles() {
    try {
        if (window.electronAPI?.openFileDialog) {
        const result = await window.electronAPI.openFileDialog();
            console.log('File dialog result:', result);
        
            if (result && !result.canceled && result.filePaths && result.filePaths.length > 0) {
            const filePath = result.filePaths[0];
                const fileName = filePath.split(/[\\/]/).pop();
                
                // Create a proper file object for Electron using IPC
                try {
                    const fileData = await window.electronAPI.readFile(filePath);
                    
                    if (!fileData.success) {
                        throw new Error(fileData.error || 'Failed to read file');
                    }
                    
                    // Convert array back to Uint8Array and create blob
                    const fileBuffer = new Uint8Array(fileData.buffer);
                    const fileBlob = new Blob([fileBuffer], { 
                        type: getFileTypeFromExtension(fileName) 
                    });
                    
                    // Create a File object that FormData can handle
                    const file = new File([fileBlob], fileName, {
                        type: getFileTypeFromExtension(fileName)
                    });
                    
                    // Add additional properties for display
                    Object.defineProperty(file, 'path', { value: filePath, writable: false });
                    Object.defineProperty(file, 'size', { value: fileData.size, writable: false });
                    
                    currentAudioFile = file;
                    displaySelectedFile(file);
                    if (elements.processBtn) elements.processBtn.disabled = false;
                    if (elements.clearBtn) elements.clearBtn.disabled = false;
                    showToast('File Upload', 'Audio file selected successfully!', 'success');
                    
            } catch (fileError) {
                    console.error('Error reading file:', fileError);
                    showToast('File Error', 'Could not read the selected file', 'error');
                }
            }
        } else {
            // Fallback for web version
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'audio/*';
            input.onchange = (e) => {
                const file = e.target.files[0];
                if (file) {
                    currentAudioFile = file;
                    displaySelectedFile(file);
                    if (elements.processBtn) elements.processBtn.disabled = false;
                    if (elements.clearBtn) elements.clearBtn.disabled = false;
                    showToast('File Upload', 'Audio file selected successfully!', 'success');
                }
            };
            input.click();
        }
    } catch (error) {
        console.error('Error browsing files:', error);
        showToast('File Error', 'Could not browse files', 'error');
    }
}

function clearAudio() {
    currentAudioFile = null;
    hideSelectedFile();
    if (elements.processBtn) elements.processBtn.disabled = true;
    if (elements.clearBtn) elements.clearBtn.disabled = true;
    if (elements.uploadProgress) elements.uploadProgress.classList.add('hidden');
    
    showToast('Audio Cleared', 'Audio file cleared', 'info');
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    elements.uploadArea?.classList.add('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    elements.uploadArea?.classList.remove('dragover');
    
    const files = Array.from(e.dataTransfer.files);
    const audioFile = files.find(file => file.type.startsWith('audio/'));
    
    if (audioFile) {
        currentAudioFile = audioFile;
        displaySelectedFile(audioFile);
        if (elements.processBtn) elements.processBtn.disabled = false;
        if (elements.clearBtn) elements.clearBtn.disabled = false;
        showToast('File Upload', `Audio file "${audioFile.name}" loaded successfully!`, 'success');
    } else {
        showToast('File Error', 'Please drop a valid audio file', 'error');
    }
}

// Processing Functions
async function processAudio() {
    if (!currentAudioFile) {
        showToast('Processing Error', 'No audio file to process', 'error');
        return;
    }
    
    console.log('Starting audio processing...');
    
    // Switch to processing page
    showPage('processing');
    
    // Initialize processing state
    currentProcessingStep = 0;
    processingStartTime = Date.now();
    updateProcessingUI();
    
    try {
        // Step 1: Upload and Transcribe
        await processStep1Upload();
        
        // Auto-switch to results page with transcript
        showPage('results');
        switchResultsTab('transcript');
        
        showToast('Processing', 'Audio transcription completed!', 'success');
        
    } catch (error) {
        console.error('Processing error:', error);
        showToast('Processing Error', error.message || 'Processing failed', 'error');
        showPage('upload');
    }
}

async function processStep1Upload() {
    console.log('Step 1: Upload and Transcribe');
    
    setProcessingStep(1, 'Uploading and transcribing audio...');
    
        const formData = new FormData();
    formData.append('audio_file', currentAudioFile, currentAudioFile.name);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.UPLOAD_TIMEOUT);
    
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/api/v1/transcription/upload`, {
            method: 'POST',
            body: formData,
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Transcription failed:', response.status, response.statusText, errorText);
            throw new Error(`Transcription failed (${response.status}): ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('Transcription result:', result);
        
        if (!result.success) {
            throw new Error(result.message || 'Transcription failed');
        }
        
        // Store transcript result
        currentResults.transcript = result;
        
        // Update transcript UI
        displayTranscript(result.text);
        
        setProcessingStep(2, 'Transcription completed');
        
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('Upload timeout - please try with a smaller file');
        }
        throw error;
    }
}

async function extractMedicalNotes() {
    if (!currentResults.transcript?.text) {
        showToast('Error', 'No transcript available for note extraction', 'error');
        return;
    }
    
    console.log('Extracting medical notes...');
    console.log('Transcript text:', currentResults.transcript.text);
    
    // Switch to notes tab and show loading
    switchResultsTab('notes');
    if (elements.noteExtractionStatus) elements.noteExtractionStatus.style.display = 'flex';
    if (elements.navNotes) elements.navNotes.classList.add('loading');
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), CONFIG.NOTE_TIMEOUT);
        
        const requestBody = {
            transcript_text: currentResults.transcript.text
        };
        
        console.log('Making API request to:', `${CONFIG.API_BASE_URL}/api/v1/notes/extract`);
        console.log('Request body:', requestBody);
        
        const response = await fetch(`${CONFIG.API_BASE_URL}/api/v1/notes/extract`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        console.log('Response status:', response.status);
        console.log('Response headers:', Object.fromEntries(response.headers.entries()));
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Note extraction failed:', response.status, response.statusText, errorText);
            throw new Error(`Medical note extraction failed (${response.status}): ${response.statusText}`);
        }
        
        const noteResult = await response.json();
        console.log('Note extraction result:', noteResult);
        
        if (!noteResult.success) {
            throw new Error(noteResult.message || 'Medical note extraction failed');
        }
        
        // Store notes result
        currentResults.notes = noteResult;
        
        // Update notes UI
        displayMedicalNotes(noteResult.medical_note);
        
        // Update navigation
        if (elements.navNotes) {
            elements.navNotes.classList.remove('loading');
            elements.navNotes.classList.add('completed');
        }
        
        // Show action buttons
        if (elements.noteExtractionStatus) elements.noteExtractionStatus.style.display = 'none';
        const saveBtn = document.getElementById('save-note');
        const copyBtn = document.getElementById('copy-note');
        if (saveBtn) saveBtn.style.display = 'inline-flex';
        if (copyBtn) copyBtn.style.display = 'inline-flex';
        if (elements.nextToCodesBtn) elements.nextToCodesBtn.style.display = 'inline-flex';
        
        showToast('Medical Notes', 'Medical notes extracted successfully!', 'success');
        
    } catch (error) {
        console.error('Note extraction error:', error);
        console.error('Error stack:', error.stack);
        if (elements.noteExtractionStatus) elements.noteExtractionStatus.style.display = 'none';
        if (elements.navNotes) elements.navNotes.classList.remove('loading');
        
        if (error.name === 'AbortError') {
            showToast('Note Extraction Error', 'Extraction timeout - please try again', 'error');
        } else {
            showToast('Note Extraction Error', error.message || 'Failed to extract medical notes', 'error');
        }
    }
}

async function extractMedicalCodes() {
    if (!currentResults.notes?.medical_codes) {
        showToast('Error', 'No medical notes available for code extraction', 'error');
        return;
    }
    
    console.log('Extracting medical codes...');
    
    // Switch to codes tab and show loading
    switchResultsTab('codes');
    if (elements.codesExtractionStatus) elements.codesExtractionStatus.style.display = 'flex';
    if (elements.navCodes) elements.navCodes.classList.add('loading');
    
    try {
        // Medical codes are already included in the notes response
        const codes = currentResults.notes.medical_codes;
        
        // Store codes result
        currentResults.codes = codes;
        
        // Update codes UI
        displayMedicalCodes(codes);
        
        // Update navigation
        if (elements.navCodes) {
            elements.navCodes.classList.remove('loading');
            elements.navCodes.classList.add('completed');
        }
        if (elements.codesExtractionStatus) elements.codesExtractionStatus.style.display = 'none';
        
        showToast('Medical Codes', 'Medical codes extracted successfully!', 'success');
        
            } catch (error) {
        console.error('Code extraction error:', error);
        if (elements.codesExtractionStatus) elements.codesExtractionStatus.style.display = 'none';
        if (elements.navCodes) elements.navCodes.classList.remove('loading');
        showToast('Code Extraction Error', error.message || 'Failed to extract medical codes', 'error');
    }
}

function setProcessingStep(step, message) {
    currentProcessingStep = step;
    
    // Update status
    if (elements.processingStatus) elements.processingStatus.textContent = message;
    if (elements.processingProgress) elements.processingProgress.textContent = `${Math.round((step / 4) * 100)}%`;
    
    // Update step indicators
    const stepNames = ['upload', 'transcribe', 'extract', 'codes'];
    stepNames.forEach((stepName, index) => {
        const stepElement = elements.processingSteps?.[stepName];
        if (stepElement) {
            stepElement.classList.remove('active', 'completed');
            if (index + 1 < step) {
                stepElement.classList.add('completed');
            } else if (index + 1 === step) {
                stepElement.classList.add('active');
            }
        }
    });
}

function updateProcessingUI() {
    const timer = setInterval(() => {
        if (currentProcessingStep === 0 || elements.processingPage?.classList.contains('hidden')) {
            clearInterval(timer);
            return;
        }
        
        // Update duration
        if (processingStartTime && elements.processingDuration) {
            const elapsed = Math.floor((Date.now() - processingStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            elements.processingDuration.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
    }, 1000);
}

function cancelProcessing() {
    console.log('Cancelling processing...');
    currentProcessingStep = 0;
    showPage('upload');
    showToast('Processing', 'Processing cancelled', 'info');
}

// Results Functions
function switchResultsTab(tab) {
    console.log('Switching to results tab:', tab);
    
    // Update navigation
    elements.navTranscript?.classList.remove('active');
    elements.navNotes?.classList.remove('active');
    elements.navCodes?.classList.remove('active');
    
    // Update content
    elements.transcriptTab?.classList.remove('active');
    elements.medicalNoteTab?.classList.remove('active');
    elements.medicalCodesTab?.classList.remove('active');
    
    switch (tab) {
        case 'transcript':
            elements.navTranscript?.classList.add('active');
            elements.transcriptTab?.classList.add('active');
            break;
        case 'notes':
            elements.navNotes?.classList.add('active');
            elements.medicalNoteTab?.classList.add('active');
            break;
        case 'codes':
            elements.navCodes?.classList.add('active');
            elements.medicalCodesTab?.classList.add('active');
            break;
    }
}

function displayTranscript(text) {
    if (elements.transcriptContent) {
        elements.transcriptContent.innerHTML = '';
        const textNode = document.createElement('div');
        textNode.textContent = text;
        textNode.style.whiteSpace = 'pre-wrap';
        elements.transcriptContent.appendChild(textNode);
        
        // Show next button and mark transcript as completed
        if (elements.nextToNotesBtn) elements.nextToNotesBtn.style.display = 'inline-flex';
        if (elements.navTranscript) elements.navTranscript.classList.add('completed');
    }
}

function displayMedicalNotes(notes) {
    const fieldMapping = {
        'chief_complaint': 'chief-complaint',
        'history_present_illness': 'history-present-illness',
        'past_medical_history': 'past-medical-history',
        'medications': 'medications',
        'allergies': 'allergies',
        'social_history': 'social-history',
        'family_history': 'family-history',
        'vital_signs': 'vital-signs',
        'physical_exam': 'physical-exam',
        'assessment': 'assessment',
        'plan': 'plan'
    };
    
    Object.entries(fieldMapping).forEach(([noteField, elementId]) => {
        const element = document.getElementById(elementId);
        if (element && notes[noteField]) {
            element.textContent = notes[noteField];
        }
    });
}

function displayMedicalCodes(codes) {
    // Update code counts
    const icdCount = document.getElementById('icd-count');
    const cptCount = document.getElementById('cpt-count');
    const snomedCount = document.getElementById('snomed-count');
    
    if (icdCount) icdCount.textContent = `${codes.icd_codes?.length || 0} ICD`;
    if (cptCount) cptCount.textContent = `${codes.cpt_codes?.length || 0} CPT`;
    if (snomedCount) snomedCount.textContent = `${codes.snomed_codes?.length || 0} SNOMED`;
    
    // Display ICD codes
    const icdContainer = document.getElementById('icd-codes');
    if (icdContainer) {
        icdContainer.innerHTML = '';
        if (codes.icd_codes?.length > 0) {
            codes.icd_codes.forEach(code => {
                const codeElement = createCodeElement(code, 'ICD-10');
                icdContainer.appendChild(codeElement);
            });
        } else {
            icdContainer.innerHTML = '<p class="placeholder">No ICD codes found</p>';
        }
    }
    
    // Display CPT codes
    const cptContainer = document.getElementById('cpt-codes');
    if (cptContainer) {
        cptContainer.innerHTML = '';
        if (codes.cpt_codes?.length > 0) {
            codes.cpt_codes.forEach(code => {
                const codeElement = createCodeElement(code, 'CPT');
                cptContainer.appendChild(codeElement);
            });
        } else {
            cptContainer.innerHTML = '<p class="placeholder">No CPT codes found</p>';
        }
    }
    
    // Display SNOMED codes
    const snomedContainer = document.getElementById('snomed-codes');
    if (snomedContainer) {
        snomedContainer.innerHTML = '';
        if (codes.snomed_codes?.length > 0) {
            codes.snomed_codes.forEach(code => {
                const codeElement = createCodeElement(code, 'SNOMED');
                snomedContainer.appendChild(codeElement);
            });
        } else {
            snomedContainer.innerHTML = '<p class="placeholder">No SNOMED codes found</p>';
        }
    }
}

function createCodeElement(code, type) {
    const div = document.createElement('div');
    div.className = 'code-item';
    
    const codeNumber = code.code || code.concept_id;
    const description = code.description || code.pt;
    const confidence = code.confidence || 0.8;
    const section = code.section || 'General';
    
    div.innerHTML = `
            <div class="code-info">
            <div class="code-number">${type}: ${codeNumber}</div>
            <div class="code-description">${description}</div>
            </div>
        <div class="code-meta">
            <div class="code-confidence">${Math.round(confidence * 100)}%</div>
            <div class="code-section">${section}</div>
        </div>
    `;
    
    return div;
}

// File Display Functions
function displaySelectedFile(file) {
    if (!file || !elements.fileSelected) return;
    
    // Show file info, hide placeholder
    elements.uploadArea?.classList.add('has-file');
    elements.fileSelected.style.display = 'flex';
    
    // Update file details
    if (elements.fileName) elements.fileName.textContent = file.name || 'Unknown file';
    if (elements.fileSize) elements.fileSize.textContent = formatFileSize(file.size || 0);
    if (elements.fileType) elements.fileType.textContent = getFileType(file.type || file.name || '');
    
    // Get audio duration if possible
    if (file.type?.startsWith('audio/') || file.name?.match(/\.(mp3|wav|m4a|flac|ogg|aac|webm)$/i)) {
        getAudioDuration(file).then(duration => {
            if (elements.fileDuration) {
                elements.fileDuration.textContent = formatDuration(duration);
            }
        }).catch(() => {
            if (elements.fileDuration) elements.fileDuration.textContent = '--:--';
        });
        
        // Show preview button for audio files
        if (elements.previewAudio) elements.previewAudio.style.display = 'inline-flex';
    } else {
        if (elements.fileDuration) elements.fileDuration.textContent = '--:--';
        if (elements.previewAudio) elements.previewAudio.style.display = 'none';
    }
}

function hideSelectedFile() {
    if (!elements.fileSelected) return;
    
    // Hide file info, show placeholder
    elements.uploadArea?.classList.remove('has-file');
    elements.fileSelected.style.display = 'none';
    
    // Reset file details
    if (elements.fileName) elements.fileName.textContent = 'No file selected';
    if (elements.fileSize) elements.fileSize.textContent = '0 MB';
    if (elements.fileType) elements.fileType.textContent = 'Unknown';
    if (elements.fileDuration) elements.fileDuration.textContent = '--:--';
    if (elements.previewAudio) elements.previewAudio.style.display = 'none';
}

function removeSelectedFile() {
    currentAudioFile = null;
    hideSelectedFile();
    if (elements.processBtn) elements.processBtn.disabled = true;
    if (elements.clearBtn) elements.clearBtn.disabled = true;
    showToast('File Removed', 'Audio file removed', 'info');
}

function previewAudio() {
    if (!currentAudioFile) return;
    
    try {
        // Handle different file object types
        let url;
        if (currentAudioFile.path && window.electronAPI) {
            // For Electron file paths, use file:// protocol with proper encoding
            const normalizedPath = currentAudioFile.path.replace(/\\/g, '/');
            url = `file:///${normalizedPath}`;
        } else if (currentAudioFile instanceof File || currentAudioFile instanceof Blob) {
            url = URL.createObjectURL(currentAudioFile);
        } else {
            showToast('Preview Error', 'Invalid file object', 'error');
            return;
        }
        
        const audio = new Audio();
        
        const cleanup = () => {
            if (url.startsWith('blob:')) {
                URL.revokeObjectURL(url);
            }
        };
        
        audio.addEventListener('loadedmetadata', () => {
            audio.currentTime = 0;
            audio.play().then(() => {
                showToast('Preview', 'Playing audio preview...', 'info');
                
                // Stop after 10 seconds or at end
                setTimeout(() => {
                    if (!audio.paused) {
                        audio.pause();
                        showToast('Preview', 'Preview stopped', 'info');
                    }
                    cleanup();
                }, 10000);
                
                audio.addEventListener('ended', () => {
                    cleanup();
                });
            }).catch(error => {
                console.error('Error playing audio:', error);
                showToast('Preview Error', 'Could not play audio preview', 'error');
                cleanup();
            });
        });
        
        audio.addEventListener('error', () => {
            showToast('Preview Error', 'Could not load audio file', 'error');
            cleanup();
        });
        
        audio.src = url;
        
    } catch (error) {
        console.error('Error creating audio preview:', error);
        showToast('Preview Error', 'Could not create audio preview', 'error');
    }
}

// Utility Functions for File Display
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function getFileType(mimeTypeOrName) {
    if (!mimeTypeOrName) return 'Unknown';
    
    if (mimeTypeOrName.includes('audio/')) {
        const type = mimeTypeOrName.split('/')[1].toUpperCase();
        return type === 'MPEG' ? 'MP3' : type;
    }
    
    const extension = mimeTypeOrName.split('.').pop()?.toUpperCase();
    return extension || 'Unknown';
}

function getFileTypeFromExtension(fileName) {
    if (!fileName) return '';
    
    const extension = fileName.split('.').pop()?.toLowerCase();
    const audioTypes = {
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'm4a': 'audio/mp4',
        'flac': 'audio/flac',
        'ogg': 'audio/ogg',
        'aac': 'audio/aac',
        'webm': 'audio/webm'
    };
    
    return audioTypes[extension] || '';
}

function formatDuration(seconds) {
    if (!seconds || isNaN(seconds)) return '--:--';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function getAudioDuration(file) {
    return new Promise((resolve, reject) => {
        try {
            // Handle different file object types
            let url;
            if (file.path && window.electronAPI) {
                // For Electron file paths, use file:// protocol with proper encoding
                const normalizedPath = file.path.replace(/\\/g, '/');
                url = `file:///${normalizedPath}`;
            } else if (file instanceof File || file instanceof Blob) {
                url = URL.createObjectURL(file);
            } else {
                reject(new Error('Invalid file object'));
                return;
            }
            
            const audio = new Audio();
            
            const cleanup = () => {
                if (url.startsWith('blob:')) {
                    URL.revokeObjectURL(url);
                }
            };
            
            audio.addEventListener('loadedmetadata', () => {
                cleanup();
                resolve(audio.duration);
            });
            
            audio.addEventListener('error', (e) => {
                cleanup();
                reject(new Error('Could not load audio: ' + (e.message || 'Unknown error')));
            });
            
            // Set a timeout to prevent hanging
            setTimeout(() => {
                cleanup();
                reject(new Error('Audio loading timeout'));
            }, 5000);
            
            audio.src = url;
    } catch (error) {
            reject(new Error('Error creating audio element: ' + error.message));
        }
    });
}

function startNewRecording() {
    // Reset state
    currentAudioFile = null;
    currentResults = { transcript: null, notes: null, codes: null };
    
    // Reset UI
    hideSelectedFile();
    if (elements.processBtn) elements.processBtn.disabled = true;
    if (elements.clearBtn) elements.clearBtn.disabled = true;
    if (elements.uploadProgress) elements.uploadProgress.classList.add('hidden');
    
    // Reset navigation states
    elements.navTranscript?.classList.remove('completed', 'active');
    elements.navNotes?.classList.remove('completed', 'active', 'loading');
    elements.navCodes?.classList.remove('completed', 'active', 'loading');
    
    // Go back to upload page
    showPage('upload');
    
    showToast('New Recording', 'Ready for new recording', 'info');
}

function exportResults() {
    if (!currentResults.transcript) {
        showToast('Export Error', 'No results to export', 'error');
        return;
    }
    
    const data = {
        timestamp: new Date().toISOString(),
        transcript: currentResults.transcript.text,
        medical_notes: currentResults.notes?.medical_note || {},
        medical_codes: currentResults.codes || {}
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `feedvox-results-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showToast('Export', 'Results exported successfully', 'success');
}

// Utility Functions
function copyToClipboard(text) {
    if (!text) {
        showToast('Copy Error', 'No text to copy', 'error');
        return;
    }
    
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied', 'Text copied to clipboard', 'success');
    }).catch(err => {
        console.error('Failed to copy text:', err);
        showToast('Copy Error', 'Failed to copy text', 'error');
    });
}

function copyMedicalNote() {
    const noteFields = [
        'chief-complaint', 'history-present-illness', 'past-medical-history',
        'medications', 'allergies', 'social-history', 'family-history',
        'vital-signs', 'physical-exam', 'assessment', 'plan'
    ];
    
    let noteText = 'MEDICAL NOTE\n' + '='.repeat(50) + '\n\n';
    
    noteFields.forEach(fieldId => {
        const element = document.getElementById(fieldId);
        if (element) {
            const label = element.parentElement?.querySelector('h4')?.textContent || fieldId;
            const content = element.textContent?.trim();
            if (content && content !== 'Not extracted yet' && content !== 'Click to edit...') {
                noteText += `${label}:\n${content}\n\n`;
            }
        }
    });
    
    copyToClipboard(noteText);
}

// Settings Functions
function openSettings() {
    if (elements.backendUrl) elements.backendUrl.value = CONFIG.API_BASE_URL;
    elements.settingsModal?.classList.add('show');
}

function closeSettings() {
    elements.settingsModal?.classList.remove('show');
}

async function testConnection() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/health`);
        if (response.ok) {
            showToast('Connection Test', 'Backend connection successful!', 'success');
        } else {
            showToast('Connection Test', 'Backend connection failed', 'error');
        }
    } catch (error) {
        showToast('Connection Test', 'Cannot reach backend server', 'error');
    }
}

async function restartBackend() {
    try {
        showToast('Backend', 'Restarting backend...', 'info');
        
        if (window.electronAPI?.restartBackend) {
        await window.electronAPI.restartBackend();
            showToast('Backend', 'Backend restart initiated', 'success');
        } else {
            showToast('Backend', 'Backend restart not available', 'error');
        }
    } catch (error) {
        console.error('Error restarting backend:', error);
        showToast('Backend Error', 'Failed to restart backend', 'error');
    }
}

function saveSettings() {
    closeSettings();
    showToast('Settings', 'Settings saved successfully', 'success');
}

function loadSettings() {
    if (elements.backendUrl) elements.backendUrl.value = CONFIG.API_BASE_URL;
}

function minimizeWindow() {
    if (window.electronAPI?.minimize) {
        window.electronAPI.minimize();
    }
}

// Toast Functions
function showToast(title, message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    toast.innerHTML = `
        <div class="toast-header">
                <div class="toast-title">${title}</div>
            <button class="toast-close">&times;</button>
            </div>
        <div class="toast-message">${message}</div>
    `;
    
    // Add close functionality
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn?.addEventListener('click', () => {
        toast.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    });
    
    toastContainer.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }
    }, 5000);
}

// Error handling
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    showToast('Error', 'An unexpected error occurred', 'error');
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    showToast('Error', 'An unexpected error occurred', 'error');
    event.preventDefault();
});

// Electron IPC handling
if (window.electronAPI) {
    window.electronAPI.onStartRecording?.(() => {
        if (!isRecording) {
            startRecording();
        }
    });
    
    window.electronAPI.onOpenSettings?.(() => {
        openSettings();
    });
}