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
            // Fetch recordings from the server
            const response = await fetch('/recordings');
            if (response.ok) {
                const data = await response.json();
                const recordingsList = document.getElementById('recordingsList');
                recordingsList.innerHTML = ''; // Clear previous entries
                data.recordings.forEach(recording => {
                    const li = document.createElement('li');
                    li.innerHTML = `<a href="/recordings/${recording}" target="_blank">${recording}</a>`;
                    recordingsList.appendChild(li);
                });
            } else {
                console.error('Failed to fetch recordings');
            }
            recordingsMenu.style.display = 'block';
        } else {
            recordingsMenu.style.display = 'none';
        }
    }
}); 