let currentMeetingId = null;
let websocket = null;
let mediaRecorder = null;
let audioContext = null;
let analyser = null;
let microphone = null;
let isRecording = false;

// File input change handler
const audioFile = document.getElementById('audio-file')
audioFile.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            document.getElementById('selected-filename').textContent = file.name;
            document.getElementById('file-selected').style.display = 'flex';
        } else {
            document.getElementById('file-selected').style.display = 'none';
        }
    });

// Tab switching
function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    event.target.classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Load data for specific tabs
    if (tabName === 'meetings') {
        loadMeetings();
    } else if (tabName === 'insights') {
        loadInsights();
    } else if (tabName === 'fine-tuning') {
        loadFineTuningExamples();
    }
}

// Create meeting
const meetingForm = document.getElementById('meeting-form');
meetingForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const title = document.getElementById('meeting-title').value;
    const date = document.getElementById('meeting-date').value;
    const participants = document.getElementById('participants').value.split(',').map(p => p.trim());

    try {
        const response = await fetch('/api/meetings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, date, participants })
        });

        const data = await response.json();
        currentMeetingId = data.id;

        // Show upload section
        document.getElementById('upload-section').style.display = 'block';
        document.getElementById('meeting-form').reset();

        alert('Meeting created! Now upload the audio recording.');
    } catch (error) {
        alert('Error creating meeting: ' + error.message);
    }
});

// Upload audio
async function uploadAudio() {
    const fileInput = document.getElementById('audio-file');
    
    if (!fileInput.files[0]) {
        alert('Please select an audio file');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const response = await fetch(`/api/meetings/${currentMeetingId}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Upload failed');

        alert(`Audio uploaded successfully! Processing will take a few minutes using English transcription.`);
        fileInput.value = '';
        document.getElementById('file-selected').style.display = 'none';
        document.getElementById('upload-section').style.display = 'none';
        currentMeetingId = null;

        // Switch to meetings tab
        document.querySelector('.tab:nth-child(2)').click();
    } catch (error) {
        alert('Error uploading audio: ' + error.message);
    }
}

// Load meetings
async function loadMeetings() {
    try {
        const response = await fetch('/api/meetings');
        const meetings = await response.json();

        const listContainer = document.getElementById('meetings-list');

        if (meetings.length === 0) {
            listContainer.innerHTML = `
                <div class="empty-state">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"></path>
                    </svg>
                    <p>No meetings yet. Upload your first recording!</p>
                </div>
            `;
            return;
        }

        listContainer.innerHTML = meetings.map(meeting => `
            <div class="meeting-item">
                <div class="meeting-info" onclick="showMeetingDetail(${meeting.id})">
                    <h3>${meeting.title}</h3>
                    <p style="color: #64748b; font-size: 0.875rem;">${meeting.date} • ${meeting.participants.length} participants</p>
                </div>
                <div class="meeting-actions">
                    ${meeting.transcript && meeting.transcript.includes('[Live Transcription]') ?
                        '<span class="live-indicator" style="position: static; animation: none; padding: 0.25rem 0.75rem; font-size: 0.75rem;">LIVE</span>' : ''}
                    <span class="meeting-status ${meeting.transcript ? 'status-complete' : 'status-processing'}">
                        ${meeting.transcript ? 'Complete' : 'Processing'}
                    </span>
                    <button class="delete-btn" onclick="confirmDeleteMeeting(${meeting.id}, '${meeting.title.replace(/'/g, "\\'")}', event)">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading meetings:', error);
    }
}

// Show meeting detail
async function showMeetingDetail(meetingId) {
    try {
        const response = await fetch(`/api/meetings/${meetingId}`);
        const meeting = await response.json();

        const detailContainer = document.getElementById('meeting-detail');
        detailContainer.innerHTML = `
            <h2>${meeting.title}</h2>
            <p style="color: #64748b; margin-bottom: 1rem;">${meeting.date}</p>

            <div style="margin-bottom: 1.5rem;">
                <strong>Participants:</strong>
                ${meeting.participants.map(p => `<span class="participant-tag">${p}</span>`).join('')}
            </div>

            ${meeting.summary ? `
                <div style="margin-bottom: 1.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <h3>Summary</h3>
                        ${meeting.transcript && !meeting.transcript_georgian && !translationInProgress.has(meeting.id) ? `
                            <button class="btn btn-secondary" onclick="translateMeeting(${meeting.id})" style="font-size: 0.875rem; padding: 0.5rem 1rem;">
                                Translate to Georgian
                            </button>
                        ` : translationInProgress.has(meeting.id) ? `
                            <button class="btn btn-secondary" disabled style="font-size: 0.875rem; padding: 0.5rem 1rem;">
                                Translating...
                            </button>
                        ` : `
                            <button class="btn btn-secondary" disabled style="font-size: 0.875rem; padding: 0.5rem 1rem;">
                                Already Translated
                            </button>
                        `}
                    </div>
                    <div id="summary-content">
                        <p>${meeting.summary}</p>
                        ${meeting.summary_georgian ? `
                            <div style="margin-top: 1rem; padding: 1rem; background: #f1f5f9; border-radius: 8px;">
                                <h4 style="margin: 0 0 0.5rem 0; color: #475569;">Georgian Translation:</h4>
                                <p style="margin: 0;">${meeting.summary_georgian}</p>
                            </div>
                        ` : ''}
                    </div>
                </div>

                ${meeting.action_items && meeting.action_items.length > 0 ? `
                    <div style="margin-bottom: 1.5rem;">
                        <h3>Action Items</h3>
                        ${meeting.action_items.map(item => `
                            <div class="action-item">
                                <div class="action-item-task">${item.task}</div>
                                <span class="action-item-owner">${item.owner}</span>
                                ${item.deadline ? `<span class="action-item-deadline">${item.deadline}</span>` : ''}
                            </div>
                        `).join('')}
                    </div>
                ` : ''}

                ${meeting.visual_summary_path ? `
                    <div>
                        <h3>Visual Summary</h3>
                        <img src="/generated_images/${meeting.visual_summary_path}" alt="Visual Summary" class="visual-summary">
                    </div>
                ` : ''}

                ${meeting.transcript ? `
                    <details style="margin-top: 2rem;">
                        <summary style="cursor: pointer; font-weight: 600;">Full Transcript</summary>
                        <div id="transcript-content" style="margin-top: 1rem; padding: 1rem; background: #f8fafc; border-radius: 8px;">
                            <p style="white-space: pre-wrap;">${meeting.transcript}</p>
                            ${meeting.transcript_georgian ? `
                                <div style="margin-top: 1rem; padding: 1rem; background: #f1f5f9; border-radius: 8px;">
                                    <h4 style="margin: 0 0 0.5rem 0; color: #475569;">Georgian Translation:</h4>
                                    <p style="white-space: pre-wrap; margin: 0;">${meeting.transcript_georgian}</p>
                                </div>
                            ` : ''}
                        </div>
                    </details>
                ` : ''}
            ` : `
                <div class="empty-state">
                    <div class="loading"></div>
                    <p>Meeting is being processed...</p>
                </div>
            `}
        `;

        // If translation is in progress, show the progress indicator
        if (translationInProgress.has(meetingId)) {
            showTranslationProgress(meetingId);
        }

        document.getElementById('meeting-modal').style.display = 'block';
    } catch (error) {
        console.error('Error loading meeting detail:', error);
    }
}

// Close modal
function closeMeetingModal() {
    document.getElementById('meeting-modal').style.display = 'none';
}

// Search meetings
async function searchMeetings() {
    const query = document.getElementById('search-input').value;
    if (!query) return;

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, limit: 5 })
        });

        const results = await response.json();
        const resultsContainer = document.getElementById('search-results');

        if (results.length === 0) {
            resultsContainer.innerHTML = '<p style="text-align: center; color: #94a3b8;">No matching meetings found</p>';
            return;
        }

        resultsContainer.innerHTML = `
            <h3>Search Results</h3>
            ${results.map(result => `
                <div class="meeting-item" onclick="showMeetingDetail(${result.id})" style="margin-bottom: 1rem;">
                    <div>
                        <h4>${result.title}</h4>
                        <p style="color: #64748b; font-size: 0.875rem;">${result.summary.substring(0, 150)}...</p>
                        <div style="display: flex; align-items: center; gap: 1rem; margin-top: 0.5rem;">
                            <p style="color: #667eea; font-size: 0.875rem;">Relevance: ${(result.similarity * 100).toFixed(1)}%</p>
                            ${result.matched_language ? `
                                <span style="padding: 0.25rem 0.5rem; background: ${result.matched_language === 'georgian' ? '#fef3c7' : '#e0e7ff'}; color: ${result.matched_language === 'georgian' ? '#92400e' : '#4338ca'}; border-radius: 4px; font-size: 0.75rem; font-weight: 500;">
                                    ${result.matched_language === 'georgian' ? '🇬🇪 Georgian' : '🇺🇸 English'}
                                </span>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `).join('')}
        `;
    } catch (error) {
        console.error('Error searching:', error);
    }
}

// Load insights
async function loadInsights() {
    try {
        const response = await fetch('/api/insights');
        const insights = await response.json();

        const container = document.getElementById('insights-content');
        container.innerHTML = `
            <div class="insights-grid">
                <div class="insight-card">
                    <div class="insight-number">${insights.total_action_items}</div>
                    <div class="insight-label">Total Action Items</div>
                </div>
                <div class="insight-card" style="background: linear-gradient(135deg, #f59e0b 0%, #dc2626 100%);">
                    <div class="insight-number">${insights.overdue_items}</div>
                    <div class="insight-label">Overdue Items</div>
                </div>
                <div class="insight-card" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
                    <div class="insight-number">${Object.keys(insights.owner_distribution).length}</div>
                    <div class="insight-label">Active Contributors</div>
                </div>
            </div>

            <h3>Key Insights</h3>
            <ul style="line-height: 2;">
                ${insights.insights.map(insight => `<li>${insight}</li>`).join('')}
            </ul>

            <h3 style="margin-top: 2rem;">Task Distribution</h3>
            <div style="margin-top: 1rem;">
                ${Object.entries(insights.owner_distribution).map(([owner, count]) => `
                    <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                        <span style="width: 150px;">${owner}</span>
                        <div style="flex: 1; background: #e2e8f0; height: 24px; border-radius: 12px; overflow: hidden;">
                            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 100%; width: ${(count / insights.total_action_items * 100)}%; transition: width 0.5s;"></div>
                        </div>
                        <span style="margin-left: 1rem; font-weight: 600;">${count}</span>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        console.error('Error loading insights:', error);
    }
}

// Modal close on outside click
window.onclick = function(event) {
    const modal = document.getElementById('meeting-modal');
    const deleteModal = document.getElementById('delete-confirm-modal');
    if (event.target == modal) {
        modal.style.display = 'none';
    }
    if (event.target == deleteModal) {
        deleteModal.style.display = 'none';
    }
}

// Delete meeting functionality
let meetingToDelete = null;

function confirmDeleteMeeting(meetingId, meetingTitle, event) {
    event.stopPropagation();
    meetingToDelete = meetingId;
    document.getElementById('delete-confirm-message').textContent =
        `Are you sure you want to delete "${meetingTitle}"? This action cannot be undone.`;
    document.getElementById('delete-confirm-modal').style.display = 'block';
}

function cancelDelete() {
    meetingToDelete = null;
    document.getElementById('delete-confirm-modal').style.display = 'none';
}

async function executeDelete() {
    if (!meetingToDelete) return;

    try {
        const response = await fetch(`/api/meetings/${meetingToDelete}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            document.getElementById('delete-confirm-modal').style.display = 'none';
            loadMeetings();
            alert('Meeting deleted successfully');
        } else {
            alert('Error deleting meeting');
        }
    } catch (error) {
        alert('Error deleting meeting: ' + error.message);
    } finally {
        meetingToDelete = null;
    }
}

// Global variable to track translation progress
let translationInProgress = new Set();

// Translate meeting to Georgian
async function translateMeeting(meetingId) {
    try {
        const button = event.target;
        const originalText = button.textContent;
        
        // Start translation progress
        translationInProgress.add(meetingId);
        button.textContent = 'Translating...';
        button.disabled = true;
        
        // Show progress indicator in the UI
        showTranslationProgress(meetingId);

        const response = await fetch(`/api/meetings/${meetingId}/translate`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            // Start polling for completion
            pollTranslationStatus(meetingId);
            alert('Translation to Georgian started! You can see the progress below. The page will update automatically when complete.');
        } else {
            // Reset on error
            translationInProgress.delete(meetingId);
            hideTranslationProgress(meetingId);
            button.textContent = originalText;
            button.disabled = false;
            alert('Error: ' + data.detail);
        }
    } catch (error) {
        // Reset on error
        translationInProgress.delete(meetingId);
        hideTranslationProgress(meetingId);
        event.target.textContent = 'Translate to Georgian';
        event.target.disabled = false;
        alert('Error starting translation: ' + error.message);
    }
}

// Show translation progress indicator
function showTranslationProgress(meetingId) {
    const summaryContent = document.getElementById('summary-content');
    if (summaryContent) {
        // Remove any existing progress indicator
        const existingProgress = summaryContent.querySelector('.translation-progress');
        if (existingProgress) {
            existingProgress.remove();
        }
        
        // Add progress indicator
        const progressDiv = document.createElement('div');
        progressDiv.className = 'translation-progress';
        progressDiv.innerHTML = `
            <div style="margin-top: 1rem; padding: 1rem; background: #fef3c7; border-radius: 8px; border-left: 4px solid #f59e0b;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <div class="loading" style="margin: 0;"></div>
                    <span style="color: #92400e; font-weight: 500;">Translating to Georgian...</span>
                </div>
                <div style="font-size: 0.875rem; color: #92400e; margin-top: 0.5rem;">
                    This may take a few minutes. The page will update automatically when complete.
                </div>
            </div>
        `;
        summaryContent.appendChild(progressDiv);
    }
}

// Hide translation progress indicator
function hideTranslationProgress(meetingId) {
    const progressIndicator = document.querySelector('.translation-progress');
    if (progressIndicator) {
        progressIndicator.remove();
    }
}

// Poll for translation completion
async function pollTranslationStatus(meetingId) {
    const maxAttempts = 60; // Poll for up to 5 minutes (5 second intervals)
    let attempts = 0;
    
    const poll = async () => {
        attempts++;
        
        try {
            const response = await fetch(`/api/meetings/${meetingId}`);
            const meeting = await response.json();
            
            // Check if translation is complete
            if (meeting.transcript_georgian) {
                // Translation is complete
                translationInProgress.delete(meetingId);
                hideTranslationProgress(meetingId);
                
                // Refresh the meeting detail display
                showMeetingDetail(meetingId);
                
                // Show success message
                const progressDiv = document.querySelector('.translation-progress');
                if (!progressDiv) {
                    const summaryContent = document.getElementById('summary-content');
                    if (summaryContent) {
                        const successDiv = document.createElement('div');
                        successDiv.innerHTML = `
                            <div style="margin-top: 1rem; padding: 1rem; background: #d1fae5; border-radius: 8px; border-left: 4px solid #10b981;">
                                <span style="color: #065f46; font-weight: 500;">✅ Translation completed successfully!</span>
                            </div>
                        `;
                        summaryContent.appendChild(successDiv);
                        
                        // Remove success message after 3 seconds
                        setTimeout(() => {
                            successDiv.remove();
                        }, 3000);
                    }
                }
                
                return; // Stop polling
            }
            
            // Continue polling if not complete and under max attempts
            if (attempts < maxAttempts && translationInProgress.has(meetingId)) {
                setTimeout(poll, 5000); // Poll every 5 seconds
            } else if (attempts >= maxAttempts) {
                // Timeout reached
                translationInProgress.delete(meetingId);
                hideTranslationProgress(meetingId);
                
                const summaryContent = document.getElementById('summary-content');
                if (summaryContent) {
                    const timeoutDiv = document.createElement('div');
                    timeoutDiv.innerHTML = `
                        <div style="margin-top: 1rem; padding: 1rem; background: #fef2f2; border-radius: 8px; border-left: 4px solid #ef4444;">
                            <span style="color: #dc2626; font-weight: 500;">Translation is taking longer than expected. Please refresh the page in a few minutes to check the status.</span>
                        </div>
                    `;
                    summaryContent.appendChild(timeoutDiv);
                }
            }
            
        } catch (error) {
            console.error('Error polling translation status:', error);
            // Continue polling unless max attempts reached
            if (attempts < maxAttempts && translationInProgress.has(meetingId)) {
                setTimeout(poll, 5000);
            }
        }
    };
    
    // Start polling after 5 seconds (give the background task time to start)
    setTimeout(poll, 5000);
}

const meetingDate = document.getElementById('meeting-date')
meetingDate.valueAsDate = new Date();