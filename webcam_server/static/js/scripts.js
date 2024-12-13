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
}); 