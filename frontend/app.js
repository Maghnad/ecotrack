const API_BASE_URL = "";
let AUTH_TOKEN = "mock_token"; // fallback

// DOM Elements
const userEmailEl = document.getElementById('user-email');
const userLevelEl = document.getElementById('user-level');
const statXpEl = document.getElementById('stat-xp');
const statEmissionsEl = document.getElementById('stat-emissions');
const statBadgesEl = document.getElementById('stat-badges');

// --- Simulated Login ---
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    const username = document.getElementById('login-username').value.trim().replace(/\s+/g, '');
    if (!username) return;

    btn.disabled = true;
    btn.innerText = "Entering...";
    
    // Set dynamic token
    AUTH_TOKEN = `mock_token_${username}`;
    
    // Create profile and set display name
    try {
        await apiCall(`/users/me/display-name?display_name=${username}`, { method: 'PATCH' });
        
        // Hide overlay and initialize dashboard
        document.getElementById('login-overlay').style.opacity = '0';
        setTimeout(() => document.getElementById('login-overlay').style.display = 'none', 500);
        
        loadProfile();
        if (document.getElementById('tab-challenges').classList.contains('active')) loadChallenges();
        if (document.getElementById('tab-leaderboard').classList.contains('active')) loadLeaderboard();
        
    } catch (e) {
        alert("Failed to join. Is the backend running?");
        btn.disabled = false;
        btn.innerText = "Enter Game";
    }
});

// --- Navigation ---
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.sidebar li').forEach(el => el.classList.remove('active'));
    
    document.getElementById(`tab-${tabId}`).classList.add('active');
    event.currentTarget.classList.add('active');

    if (tabId === 'leaderboard') loadLeaderboard();
    if (tabId === 'challenges') loadChallenges();
}

// --- API Helpers ---
async function apiCall(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${AUTH_TOKEN}`
    };
    const response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers });
    if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
    return await response.json();
}

// --- Load Profile ---
async function loadProfile() {
    try {
        const profile = await apiCall('/users/me');
        userEmailEl.innerText = profile.email || "Eco Warrior";
        userLevelEl.innerText = profile.level_name;
        statXpEl.innerText = profile.total_xp + " XP";
        statEmissionsEl.innerText = profile.total_carbon_saved_kg + " kg Saved";
        statBadgesEl.innerText = profile.badges.length;
    } catch (e) {
        console.error("Failed to load profile:", e);
    }
}

// --- Log Eco Action ---
document.getElementById('action-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    const resultBox = document.getElementById('action-result');
    const actionType = document.getElementById('action-type').value;
    
    btn.disabled = true;
    resultBox.classList.add('hidden');
    
    try {
        const result = await apiCall('/eco-actions', {
            method: 'POST',
            body: JSON.stringify({ action_type: actionType, quantity: 1 })
        });
        
        resultBox.innerHTML = `
            <h4 class="text-glow">+${result.xp_awarded} XP Earned!</h4>
            <p>You saved ${result.carbon_saved_kg} kg of CO₂.</p>
            <p class="text-sm" style="margin-top:0.5rem; color:#fca5a5;">${result.fun_fact}</p>
        `;
        resultBox.classList.remove('hidden');
        loadProfile(); // Refresh XP
    } catch (e) {
        alert("Failed to log action.");
    } finally {
        btn.disabled = false;
    }
});

// --- AI Insights ---
document.getElementById('get-insight-btn').addEventListener('click', async (e) => {
    const btn = e.target;
    const loading = document.getElementById('ai-loading');
    const box = document.getElementById('insight-box');
    
    btn.disabled = true;
    loading.classList.remove('hidden');
    box.classList.add('hidden');
    
    try {
        const insight = await apiCall('/insights');
        document.getElementById('ai-tip').innerText = insight.tips.length > 0 ? insight.tips[0] : "Great job staying green!";
        box.classList.remove('hidden');
    } catch (e) {
        alert("Failed to get insights.");
    } finally {
        btn.disabled = false;
        loading.classList.add('hidden');
    }
});

// --- Load Challenges ---
async function loadChallenges() {
    const container = document.getElementById('challenges-container');
    container.innerHTML = '<p>Loading challenges...</p>';
    try {
        const data = await apiCall('/challenges');
        container.innerHTML = '';
        
        const allChallenges = [...data.active_challenges, ...data.completed_challenges];
        if (allChallenges.length === 0) {
            container.innerHTML = '<p>No challenges available right now.</p>';
            return;
        }

        allChallenges.forEach(c => {
            const isDone = c.is_completed ? '✅ Completed' : '⏳ In Progress';
            container.innerHTML += `
                <div class="card glass challenge-card">
                    <h3>${c.title}</h3>
                    <p>${c.description}</p>
                    <div class="xp-reward">+${c.xp_reward} XP</div>
                    <div><strong>Status:</strong> ${isDone}</div>
                </div>
            `;
        });
    } catch (e) {
        container.innerHTML = '<p>Failed to load challenges.</p>';
    }
}

// --- Load Leaderboard ---
async function loadLeaderboard() {
    const tbody = document.getElementById('leaderboard-body');
    tbody.innerHTML = '<tr><td colspan="4">Loading...</td></tr>';
    try {
        const data = await apiCall('/users/leaderboard');
        tbody.innerHTML = '';
        data.entries.forEach(e => {
            let rankClass = e.rank <= 3 ? `rank-${e.rank}` : '';
            tbody.innerHTML += `
                <tr>
                    <td class="${rankClass}">#${e.rank}</td>
                    <td>${e.display_name || "Eco Warrior"}</td>
                    <td>${e.level_name}</td>
                    <td>${e.total_xp} XP</td>
                </tr>
            `;
        });
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4">Failed to load leaderboard.</td></tr>';
    }
}

// Initialize
loadProfile();
