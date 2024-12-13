document.addEventListener('DOMContentLoaded', function() {
    const fullScreenContainer = document.getElementById('fullScreenContainer');
    const fullScreenImage = document.getElementById('fullScreenImage');
    const ptzControls = document.getElementById('ptzControls');
    const settingsMenu = document.getElementById('settingsMenu');
    let currentCameraId = null;

    window.openFullScreen = function(src, cameraId) {
        fullScreenImage.src = src;
        fullScreenContainer.style.display = 'flex';
        currentCameraId = cameraId;
    };

    window.closeFullScreen = function() {
        fullScreenContainer.style.display = 'none';
        fullScreenImage.src = '';
        currentCameraId = null;
    };

    window.toggleSettingsMenu = function() {
        settingsMenu.style.display = settingsMenu.style.display === 'block' ? 'none' : 'block';
    };

    window.applySettings = function() {
        const recordLength = document.getElementById('recordLength').value;
        const fileSize = document.getElementById('fileSize').value;
        fetch(`/settings/${currentCameraId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ recordLength, fileSize })
        }).then(response => {
            if (!response.ok) {
                console.error('Failed to apply settings');
            }
        });
    };

    // Function to send PTZ commands
    window.sendPTZCommand = function(cameraId, pan, tilt, zoom) {
        // Prevent triggering fullscreen on button click
        event.stopPropagation();

        fetch(`/ptz/${cameraId}/move`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: 'continuous',
                pan: pan,
                tilt: tilt,
                zoom: zoom
            })
        }).then(response => {
            if (!response.ok) {
                console.error('PTZ command failed');
            }
        });
    };

    // PTZ controls
    ptzControls.querySelector('.ptz-up').addEventListener('mousedown', () => {
        sendPTZCommand(0, 1, 0);
    });
    ptzControls.querySelector('.ptz-down').addEventListener('mousedown', () => {
        sendPTZCommand(0, -1, 0);
    });
    ptzControls.querySelector('.ptz-left').addEventListener('mousedown', () => {
        sendPTZCommand(-1, 0, 0);
    });
    ptzControls.querySelector('.ptz-right').addEventListener('mousedown', () => {
        sendPTZCommand(1, 0, 0);
    });

    // Zoom controls
    ptzControls.querySelector('.zoom-in').addEventListener('mousedown', () => {
        sendPTZCommand(0, 0, 1);
    });
    ptzControls.querySelector('.zoom-out').addEventListener('mousedown', () => {
        sendPTZCommand(0, 0, -1);
    });

    // Stop on mouse up
    document.addEventListener('mouseup', () => {
        stopPTZ();
    });

    // Prevent fullscreen toggle when clicking PTZ buttons in minimized view
    document.querySelectorAll('.ptz-controls.minimized button').forEach(button => {
        button.addEventListener('click', function(event) {
            event.stopPropagation();
        });
    });

    function stopPTZ() {
        if (fullScreenContainer.style.display === 'flex' && currentCameraId !== null) {
            fetch(`/ptz/${currentCameraId}/stop`, {
                method: 'POST'
            }).then(response => {
                if (!response.ok) {
                    console.error('PTZ stop failed');
                }
            });
        }
    }

    // Function to update status ribbon indicators
    function updateStatusRibbon() {
        // ... existing fetch requests ...
    
        // Fetch and update Frame Rate
        fetch('/status/frame_rate')
            .then(response => response.json())
            .then(data => {
                const frameRate = document.getElementById('frameRate');
                frameRate.textContent = data.rate + 'fps'; // Example format
            })
            .catch(error => console.error('Error fetching frame rate:', error));
    
        // Fetch and update Stream Rate
        fetch('/status/stream_rate')
            .then(response => response.json())
            .then(data => {
                const streamRate = document.getElementById('streamRate');
                streamRate.textContent = data.rate + 'Mbps'; // Example format
            })
            .catch(error => console.error('Error fetching stream rate:', error));
    
        // Fetch and update Signal Strength
        fetch('/status/signal_strength')
            .then(response => response.json())
            .then(data => {
                const signalStrength = document.getElementById('signalStrength');
                signalStrength.textContent = data.strength; // Example format
                // Optionally, change color based on strength
                if (data.strength === 'Weak') {
                    signalStrength.className = 'status-indicator red';
                } else if (data.strength === 'Moderate') {
                    signalStrength.className = 'status-indicator yellow';
                } else {
                    signalStrength.className = 'status-indicator green';
                }
            })
            .catch(error => console.error('Error fetching signal strength:', error));
    }
    
    // Initial status update
    updateStatusRibbon();
    
    // Update status every 30 seconds
    setInterval(updateStatusRibbon, 30000);

    async function toggleRecordingsMenu() {
        const recordingsMenu = document.getElementById('recordingsMenu');
        
        if (recordingsMenu.style.display === 'none') {
            try {
                const response = await fetch('/recordings');
                if (!response.ok) throw new Error('Failed to fetch recordings');
                
                const data = await response.json();
                const recordingsList = document.getElementById('recordingsList');
                recordingsList.innerHTML = ''; // Clear previous entries
                
                data.recordings.forEach(recording => {
                    const li = document.createElement('li');
                    const size = (recording.size / 1024 / 1024).toFixed(2); // Convert to MB
                    li.innerHTML = `
                        <a href="${recording.url}" target="_blank">
                            <span class="recording-name">${recording.name}</span>
                            <span class="recording-info">
                                ${recording.date} | ${size} MB
                            </span>
                        </a>`;
                    recordingsList.appendChild(li);
                });
                
                recordingsMenu.style.display = 'block';
            } catch (error) {
                console.error('Error fetching recordings:', error);
                alert('Failed to load recordings');
            }
        } else {
            recordingsMenu.style.display = 'none';
        }
    }

    window.toggleRecordingsMenu = toggleRecordingsMenu;

    async function toggleRecording(cameraId) {
        const statusElement = document.getElementById(`recordStatus${cameraId}`);
        const durationElement = document.getElementById(`recordDuration${cameraId}`);
        const container = statusElement.closest('.camera-container');
        
        if (container.classList.contains('recording')) {
            // Stop recording
            stopRecording(cameraId);
            container.classList.remove('recording');
            statusElement.textContent = 'STANDBY';
            durationElement.textContent = '00:00';
        } else {
            // Start recording
            startRecording(cameraId);
            container.classList.add('recording');
            statusElement.textContent = 'RECORDING';
            startTimer(cameraId);
        }
    }

    function startTimer(cameraId) {
        const durationElement = document.getElementById(`recordDuration${cameraId}`);
        let seconds = 0;
        
        const timer = setInterval(() => {
            seconds++;
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            durationElement.textContent = 
                `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
                
            if (!durationElement.closest('.camera-container').classList.contains('recording')) {
                clearInterval(timer);
            }
        }, 1000);
    }

    function setQuality(cameraId, quality) {
        fetch(`/camera/${cameraId}/quality`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ quality })
        });
    }

    async function startRecording(cameraId) {
        try {
            const response = await fetch(`/camera/${cameraId}/record/start`, {
                method: 'POST'
            });
            const data = await response.json();
            console.log('Recording started:', data);
        } catch (error) {
            console.error('Failed to start recording:', error);
        }
    }

    async function stopRecording(cameraId) {
        try {
            const response = await fetch(`/camera/${cameraId}/record/stop`, {
                method: 'POST'
            });
            const data = await response.json();
            console.log('Recording stopped:', data);
        } catch (error) {
            console.error('Failed to stop recording:', error);
        }
    }

    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 500);
        }, 3000);
    }

    function updateRecordingStatuses() {
        document.querySelectorAll('[id^="recordButton_"]').forEach(async button => {
            const cameraId = button.id.split('_')[1];
            try {
                const response = await fetch(`/camera/${cameraId}/record/status`);
                if (!response.ok) throw new Error('Failed to get recording status');
                
                const status = await response.json();
                if (status.is_recording) {
                    button.classList.add('recording');
                } else {
                    button.classList.remove('recording');
                }
            } catch (error) {
                console.error(`Failed to update recording status for camera ${cameraId}:`, error);
            }
        });
    }

    setInterval(updateRecordingStatuses, 5000);

    function initializeSettings() {
        // Initialize range input displays
        document.getElementById('recordLength').addEventListener('input', function() {
            document.getElementById('recordLengthValue').textContent = this.value;
        });
        
        document.getElementById('fileSize').addEventListener('input', function() {
            document.getElementById('fileSizeValue').textContent = this.value;
        });
    }

    async function applySettings() {
        const settings = {
            recordLength: parseInt(document.getElementById('recordLength').value),
            fileSize: parseInt(document.getElementById('fileSize').value),
            autoRecord: document.getElementById('autoRecord').checked,
            quality: document.getElementById('quality').value,
            fps: parseInt(document.getElementById('fps').value)
        };

        try {
            const response = await fetch('/settings/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });

            if (!response.ok) throw new Error('Failed to update settings');

            showNotification('Settings updated successfully');
            toggleSettingsMenu();
        } catch (error) {
            console.error('Settings update error:', error);
            showNotification('Failed to update settings', 'error');
        }
    }

    // Add this to your document ready function
    document.addEventListener('DOMContentLoaded', function() {
        initializeSettings();
    });

    // Update the existing toggleSettingsMenu function
    function toggleSettingsMenu() {
        const settingsMenu = document.getElementById('settingsMenu');
        if (settingsMenu.style.display === 'none' || !settingsMenu.style.display) {
            settingsMenu.style.display = 'block';
            loadCurrentSettings();
        } else {
            settingsMenu.style.display = 'none';
        }
    }

    async function loadCurrentSettings() {
        try {
            const response = await fetch('/settings/current');
            if (!response.ok) throw new Error('Failed to load settings');
            
            const settings = await response.json();
            
            document.getElementById('recordLength').value = settings.recordLength;
            document.getElementById('recordLengthValue').textContent = settings.recordLength;
            document.getElementById('fileSize').value = settings.fileSize;
            document.getElementById('fileSizeValue').textContent = settings.fileSize;
            document.getElementById('autoRecord').checked = settings.autoRecord;
            document.getElementById('quality').value = settings.quality;
            document.getElementById('fps').value = settings.fps;
        } catch (error) {
            console.error('Failed to load settings:', error);
            showNotification('Failed to load current settings', 'error');
        }
    }
}); 