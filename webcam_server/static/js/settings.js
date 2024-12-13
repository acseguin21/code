document.addEventListener('DOMContentLoaded', function() {
    // Update slider values
    document.querySelectorAll('.slider').forEach(slider => {
        const valueDisplay = slider.nextElementSibling;
        slider.addEventListener('input', function() {
            valueDisplay.textContent = this.value;
        });
    });

    // Handle recording controls
    document.querySelectorAll('.start-record').forEach(button => {
        button.addEventListener('click', function() {
            const cameraId = this.dataset.camera;
            startRecording(cameraId);
        });
    });

    document.querySelectorAll('.stop-record').forEach(button => {
        button.addEventListener('click', function() {
            const cameraId = this.dataset.camera;
            stopRecording(cameraId);
        });
    });

    // Load recordings list
    loadRecordings();
});

async function startRecording(cameraId) {
    try {
        const response = await fetch(`/camera/${cameraId}/record/start`, {
            method: 'POST'
        });
        const data = await response.json();
        if (data.status === 'started') {
            showNotification('Recording started', 'success');
        }
    } catch (error) {
        showNotification('Failed to start recording', 'error');
    }
}

async function stopRecording(cameraId) {
    try {
        const response = await fetch(`/camera/${cameraId}/record/stop`, {
            method: 'POST'
        });
        const data = await response.json();
        if (data.status === 'stopped') {
            showNotification('Recording stopped', 'success');
            loadRecordings(); // Refresh recordings list
        }
    } catch (error) {
        showNotification('Failed to stop recording', 'error');
    }
}

async function loadRecordings() {
    try {
        const response = await fetch('/api/recordings');
        const recordings = await response.json();
        const recordingsList = document.getElementById('recordingsList');
        recordingsList.innerHTML = recordings.map(recording => `
            <div class="recording-item">
                <span class="recording-name">${recording.filename}</span>
                <span class="recording-date">${new Date(recording.date).toLocaleString()}</span>
                <a href="/api/recordings/download/${recording.filename}" class="download-button">Download</a>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load recordings:', error);
    }
}

function showNotification(message, type) {
    // Add notification implementation here
    console.log(`${type}: ${message}`);
} 