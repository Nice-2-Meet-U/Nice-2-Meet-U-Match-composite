// Configuration
const API_BASE_URL = 'https://user-matches-service-870022169527.us-central1.run.app';

// Utility Functions
function generateUUID() {
    const uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
    document.getElementById('userId').value = uuid;
    showMessage('poolInfo', `Generated new UUID: ${uuid}`, 'success');
}

function getUserId() {
    const userId = document.getElementById('userId').value.trim();
    if (!userId) {
        alert('Please enter or generate a User ID first');
        return null;
    }
    return userId;
}

function showMessage(elementId, message, type = 'info') {
    const element = document.getElementById(elementId);
    element.innerHTML = `<div class="${type}">${message}</div>`;
    element.style.display = 'block';
}

function showJSON(elementId, data, type = 'success') {
    const element = document.getElementById(elementId);
    element.innerHTML = `<pre class="${type}">${JSON.stringify(data, null, 2)}</pre>`;
    element.style.display = 'block';
}

function showError(elementId, error) {
    const element = document.getElementById(elementId);
    element.innerHTML = `<div class="error">Error: ${error}</div>`;
    element.style.display = 'block';
}

// API Functions
async function joinPool() {
    const userId = getUserId();
    if (!userId) return;

    const location = document.getElementById('location').value.trim();
    const coordXInput = document.getElementById('coordX').value.trim();
    const coordYInput = document.getElementById('coordY').value.trim();

    if (!location) {
        showError('poolInfo', 'Please enter a location');
        return;
    }

    // Build payload - only include coordinates if they're provided
    const payload = { location };
    
    if (coordXInput && coordYInput) {
        const coordX = parseFloat(coordXInput);
        const coordY = parseFloat(coordYInput);
        
        if (isNaN(coordX) || isNaN(coordY)) {
            showError('poolInfo', 'Invalid coordinate values');
            return;
        }
        
        payload.coord_x = coordX;
        payload.coord_y = coordY;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}/pool`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to join pool');
        }

        const data = await response.json();
        showJSON('poolInfo', data, 'success');
    } catch (error) {
        showError('poolInfo', error.message);
    }
}

async function getPoolInfo() {
    const userId = getUserId();
    if (!userId) return;

    try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}/pool`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get pool info');
        }

        const data = await response.json();
        showJSON('poolInfo', data, 'success');
    } catch (error) {
        showError('poolInfo', error.message);
    }
}

async function getPoolMembers() {
    const userId = getUserId();
    if (!userId) return;

    try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}/pool/members`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get pool members');
        }

        const data = await response.json();
        
        // Format the members list nicely
        let html = `<div class="success">
            <h3>Pool Members (${data.members_count})</h3>
            <div style="margin-top: 15px;">`;
        
        data.members.forEach((member, index) => {
            html += `<div class="match-item">
                <p><strong>Member ${index + 1}</strong></p>
                <p>User ID: ${member.user_id}</p>
                <p>Coordinates: (${member.coord_x}, ${member.coord_y})</p>
            </div>`;
        });
        
        html += '</div></div>';
        document.getElementById('poolInfo').innerHTML = html;
        document.getElementById('poolInfo').style.display = 'block';
    } catch (error) {
        showError('poolInfo', error.message);
    }
}

async function leavePool() {
    const userId = getUserId();
    if (!userId) return;

    if (!confirm('Are you sure you want to leave the pool? This will also delete all your matches and decisions.')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}/pool`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to leave pool');
        }

        const data = await response.json();
        showJSON('poolInfo', data, 'success');
    } catch (error) {
        showError('poolInfo', error.message);
    }
}

async function generateMatches() {
    const userId = getUserId();
    if (!userId) return;

    try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}/matches`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate matches');
        }

        const data = await response.json();
        
        // Format the generated matches nicely
        let html = `<div class="success">
            <h3>${data.message}</h3>
            <p><strong>Pool ID:</strong> ${data.pool_id}</p>
            <p><strong>Matches Created:</strong> ${data.matches_created}</p>
            <div style="margin-top: 15px;">`;
        
        if (data.matches_created === 0) {
            html += '<p>No matches were created.</p>';
        } else {
            data.matches.forEach((match, index) => {
                html += `<div class="match-item">
                    <h4>Match ${index + 1}</h4>
                    <p><strong>Match ID:</strong> ${match.match_id}</p>
                    <p><strong>User 1:</strong> ${match.user1_id}</p>
                    <p><strong>User 2:</strong> ${match.user2_id}</p>
                    <p><strong>Status:</strong> ${match.status}</p>
                    <p><strong>Created:</strong> ${new Date(match.created_at).toLocaleString()}</p>
                </div>`;
            });
        }
        
        html += '</div></div>';
        document.getElementById('matchesInfo').innerHTML = html;
        document.getElementById('matchesInfo').style.display = 'block';
    } catch (error) {
        showError('matchesInfo', error.message);
    }
}

async function getMatches() {
    const userId = getUserId();
    if (!userId) return;

    try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}/matches`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get matches');
        }

        const data = await response.json();
        
        // Format the matches list nicely
        let html = `<div class="success">
            <h3>Your Matches (${data.matches_count})</h3>
            <div style="margin-top: 15px;">`;
        
        if (data.matches_count === 0) {
            html += '<p>No matches yet. Generate some matches to get started!</p>';
        } else {
            data.matches.forEach((match, index) => {
                html += `<div class="match-item">
                    <h4>Match ${index + 1}</h4>
                    <p><strong>Match ID:</strong> ${match.match_id}</p>
                    <p><strong>User 1:</strong> ${match.user1_id}</p>
                    <p><strong>User 2:</strong> ${match.user2_id}</p>
                    <p><strong>Status:</strong> ${match.status}</p>
                    <p><strong>Created:</strong> ${new Date(match.created_at).toLocaleString()}</p>
                </div>`;
            });
        }
        
        html += '</div></div>';
        document.getElementById('matchesInfo').innerHTML = html;
        document.getElementById('matchesInfo').style.display = 'block';
    } catch (error) {
        showError('matchesInfo', error.message);
    }
}

async function getDecisions() {
    const userId = getUserId();
    if (!userId) return;

    try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}/decisions`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get decisions');
        }

        const data = await response.json();
        
        // Format the decisions list nicely
        let html = `<div class="success">
            <h3>Your Decisions (${data.decisions_count})</h3>
            <div style="margin-top: 15px;">`;
        
        if (data.decisions_count === 0) {
            html += '<p>No decisions yet. Make some decisions on your matches!</p>';
        } else {
            data.decisions.forEach((decision, index) => {
                const decisionClass = decision.decision === 'accept' ? 'btn-success' : 'btn-danger';
                html += `<div class="match-item">
                    <h4>Decision ${index + 1}</h4>
                    <p><strong>Match ID:</strong> ${decision.match_id}</p>
                    <p><strong>User ID:</strong> ${decision.user_id}</p>
                    <p><strong>Decision:</strong> <span class="${decisionClass}" style="display: inline-block; padding: 5px 10px; border-radius: 5px; font-size: 0.9em;">${decision.decision.toUpperCase()}</span></p>
                    <p><strong>Decided At:</strong> ${new Date(decision.decided_at).toLocaleString()}</p>
                </div>`;
            });
        }
        
        html += '</div></div>';
        document.getElementById('decisionsInfo').innerHTML = html;
        document.getElementById('decisionsInfo').style.display = 'block';
    } catch (error) {
        showError('decisionsInfo', error.message);
    }
}

async function makeDecision(decision) {
    const userId = getUserId();
    if (!userId) return;

    const matchId = document.getElementById('matchId').value.trim();
    if (!matchId) {
        showError('decisionResult', 'Please enter a Match ID');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}/matches/${matchId}/decisions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                decision: decision
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to submit decision');
        }

        const data = await response.json();
        showJSON('decisionResult', data, 'success');
        
        // Clear the match ID field
        document.getElementById('matchId').value = '';
    } catch (error) {
        showError('decisionResult', error.message);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Nice 2 Meet U Match Service - Frontend Ready!');
    console.log('API Base URL:', API_BASE_URL);
});
// Updated: Fri Dec  5 07:22:20 EST 2025
