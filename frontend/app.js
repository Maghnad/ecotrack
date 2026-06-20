const API_BASE_URL = "";
let AUTH_TOKEN = "mock_token"; // fallback

// DOM Elements
const userEmailEl = document.getElementById('user-email');
const userLevelEl = document.getElementById('user-level');
const statXpEl = document.getElementById('stat-xp');
const statEmissionsEl = document.getElementById('stat-emissions');
const statBadgesEl = document.getElementById('stat-badges');

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
    } catch (err) {
        console.error("Failed to load profile:", err);
    }
}

function shareAchievement() {
    var userLevelEl = document.getElementById('user-level');
    var statEmissionsEl = document.getElementById('stat-emissions');
    
    var level = userLevelEl ? userLevelEl.innerText : "Eco Warrior";
    var saved = statEmissionsEl ? statEmissionsEl.innerText : "some carbon";
    
    var text = encodeURIComponent(`I'm officially a ${level} on EcoTrack! 🌍 I've achieved ${saved} so far! Track your footprint and offset your emissions with me.`);
    var url = encodeURIComponent(`https://ecotrack.example.com`);
    
    var twitterUrl = `https://twitter.com/intent/tweet?text=${text}&url=${url}`;
    window.open(twitterUrl, '_blank', 'noopener,noreferrer');
}

// --- Navigation ---
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(function(el) {
        el.classList.remove('active');
    });
    document.querySelectorAll('.sidebar li').forEach(function(el) {
        el.classList.remove('active');
    });

    var tabEl = document.getElementById('tab-' + tabId);
    if (tabEl) tabEl.classList.add('active');

    var navEl = document.getElementById('nav-' + tabId);
    if (navEl) navEl.classList.add('active');

    if (tabId === 'leaderboard') loadLeaderboard();
    if (tabId === 'challenges') loadChallenges();
    if (tabId === 'analytics') loadAnalytics();
}

// --- Chatbot Toggle ---
function toggleChat() {
    var body = document.getElementById('chatbot-body');
    var header = document.querySelector('.chatbot-header');
    body.classList.toggle('hidden');
    
    // Accessibility: Update aria-expanded and set focus
    var isExpanded = !body.classList.contains('hidden');
    header.setAttribute('aria-expanded', isExpanded);
    
    if (isExpanded) {
        document.getElementById('chat-input').focus();
    }
}

// --- Load Challenges ---
async function loadChallenges() {
    var container = document.getElementById('challenges-container');
    if (!container) return;
    container.innerHTML = '<p>Loading challenges...</p>';
    try {
        var data = await apiCall('/challenges');
        container.innerHTML = '';

        var allChallenges = [].concat(data.active_challenges, data.completed_challenges);
        if (allChallenges.length === 0) {
            container.innerHTML = '<p>No challenges available right now.</p>';
            return;
        }

        allChallenges.forEach(function(c) {
            var isDone = c.is_completed ? '✅ Completed' : '⏳ In Progress';
            container.innerHTML += '<div class="card glass challenge-card">' +
                '<h3>' + c.title + '</h3>' +
                '<p>' + c.description + '</p>' +
                '<div class="xp-reward">+' + c.xp_reward + ' XP</div>' +
                '<div><strong>Status:</strong> ' + isDone + '</div>' +
                '</div>';
        });
    } catch (err) {
        container.innerHTML = '<p>Failed to load challenges.</p>';
    }
}

// --- Load Leaderboard ---
async function loadLeaderboard() {
    var tbody = document.getElementById('leaderboard-body');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="4">Loading...</td></tr>';
    try {
        var data = await apiCall('/users/leaderboard');
        tbody.innerHTML = '';
        data.entries.forEach(function(entry) {
            var rankClass = entry.rank <= 3 ? 'rank-' + entry.rank : '';
            tbody.innerHTML += '<tr>' +
                '<td class="' + rankClass + '">#' + entry.rank + '</td>' +
                '<td>' + (entry.display_name || "Eco Warrior") + '</td>' +
                '<td>' + entry.level_name + '</td>' +
                '<td>' + entry.total_xp + ' XP</td>' +
                '</tr>';
        });
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="4">Failed to load leaderboard.</td></tr>';
    }
}

// --- Analytics & 3D ---
var emissionsChart = null;

async function loadAnalytics() {
    try {
        var history = await apiCall('/history?days=30');

        // Render Chart.js
        var canvas = document.getElementById('emissionsChart');
        if (!canvas) return;
        var ctx = canvas.getContext('2d');
        if (emissionsChart) emissionsChart.destroy();

        var totalDiet = 0, totalTransport = 0, totalEnergy = 0;
        history.daily_emissions.forEach(function(d) {
            totalDiet += d.diet_kg;
            totalTransport += d.transport_kg;
            totalEnergy += d.energy_kg;
        });

        var chartData = [totalDiet, totalTransport, totalEnergy];
        var chartColors = ['#4ade80', '#3b82f6', '#f59e0b'];
        var chartLabels = ['Diet', 'Transport', 'Energy'];

        if (totalDiet === 0 && totalTransport === 0 && totalEnergy === 0) {
            chartData = [1];
            chartColors = ['#334155'];
            chartLabels = ['No Actions Logged Yet'];
        }

        emissionsChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: chartLabels,
                datasets: [{
                    data: chartData,
                    backgroundColor: chartColors,
                    borderColor: '#0f172a'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#cbd5e1' }
                    }
                }
            }
        });

        var totalEmissions = totalDiet + totalTransport + totalEnergy;
        initThreeJS(totalEmissions);
        updateBudgetUI(totalEmissions);

    } catch (err) {
        console.error("Failed to load analytics:", err);
    }
}

function updateBudgetUI(totalEmissions) {
    var budgetUsedText = document.getElementById('budget-used-text');
    var budgetProgressBar = document.getElementById('budget-progress-bar');
    var budgetWarning = document.getElementById('budget-warning');
    
    if (!budgetUsedText || !budgetProgressBar) return;
    
    var budgetTotal = 200; // Hardcoded monthly budget goal for now
    var percentUsed = Math.min((totalEmissions / budgetTotal) * 100, 100);
    
    budgetUsedText.innerText = totalEmissions.toFixed(1) + " kg used";
    budgetProgressBar.style.width = percentUsed + "%";
    
    if (percentUsed >= 90) {
        budgetProgressBar.style.background = "#ef4444"; // Red
        if (budgetWarning) budgetWarning.style.display = "block";
    } else if (percentUsed >= 75) {
        budgetProgressBar.style.background = "#f59e0b"; // Orange
        if (budgetWarning) budgetWarning.style.display = "none";
    } else {
        budgetProgressBar.style.background = "#10b981"; // Green
        if (budgetWarning) budgetWarning.style.display = "none";
    }
}

// Global ThreeJS references
var threeScene, threeCamera, threeRenderer, ecoWorldMesh;

function initThreeJS(totalEmissions) {
    var container = document.getElementById('three-container');
    if (!container) return;
    if (container.children.length > 0) {
        updateThreeWorld(totalEmissions);
        return;
    }

    threeScene = new THREE.Scene();
    threeCamera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
    threeRenderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    threeRenderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(threeRenderer.domElement);

    var light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(1, 1, 1).normalize();
    threeScene.add(light);
    threeScene.add(new THREE.AmbientLight(0x404040));

    var geometry = new THREE.IcosahedronGeometry(2, 1);
    var material = new THREE.MeshPhongMaterial({ color: 0x4ade80, flatShading: true });
    ecoWorldMesh = new THREE.Mesh(geometry, material);
    threeScene.add(ecoWorldMesh);

    threeCamera.position.z = 5;

    updateThreeWorld(totalEmissions);

    function animate() {
        requestAnimationFrame(animate);
        ecoWorldMesh.rotation.x += 0.005;
        ecoWorldMesh.rotation.y += 0.005;
        threeRenderer.render(threeScene, threeCamera);
    }
    animate();
}

function updateThreeWorld(emissions) {
    if (!ecoWorldMesh) return;
    
    var statusEl = document.getElementById('eco-world-status');

    // Lowered thresholds for gamification/testing purposes so it changes quickly!
    if (emissions > 25) {
        ecoWorldMesh.material.color.setHex(0xef4444); // Reddish dying planet
        ecoWorldMesh.scale.set(0.8, 0.8, 0.8);
        if (statusEl) {
            statusEl.innerText = "Status: Critical (High Emissions)";
            statusEl.style.color = "#ef4444";
        }
    } else if (emissions > 10) {
        ecoWorldMesh.material.color.setHex(0xf59e0b); // Orange warning
        ecoWorldMesh.scale.set(0.9, 0.9, 0.9);
        if (statusEl) {
            statusEl.innerText = "Status: Warning (Moderate Emissions)";
            statusEl.style.color = "#f59e0b";
        }
    } else {
        ecoWorldMesh.material.color.setHex(0x4ade80); // Lush green
        ecoWorldMesh.scale.set(1, 1, 1);
        if (statusEl) {
            statusEl.innerText = "Status: Healthy (Low Emissions)";
            statusEl.style.color = "#4ade80";
        }
    }
}

// ============================================================
// Wire up all event listeners after DOM is ready
// ============================================================
document.addEventListener('DOMContentLoaded', function() {

    // --- Login Form ---
    var loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            var btn = loginForm.querySelector('button');
            var usernameInput = document.getElementById('login-username');
            var username = usernameInput.value.trim().replace(/\s+/g, '');
            if (!username) return;

            btn.disabled = true;
            btn.innerText = "Entering...";

            AUTH_TOKEN = 'mock_token_' + username;

            try {
                await apiCall('/users/me/display-name?display_name=' + username, { method: 'PATCH' });

                // Hide login overlay, show quiz overlay
                var loginOverlay = document.getElementById('login-overlay');
                loginOverlay.style.opacity = '0';
                setTimeout(function() {
                    loginOverlay.style.display = 'none';
                    var quizOverlay = document.getElementById('quiz-overlay');
                    if (quizOverlay) quizOverlay.classList.remove('hidden');
                }, 500);

                loadProfile();
            } catch (err) {
                alert("Failed to join. Is the backend running?");
                btn.disabled = false;
                btn.innerText = "Enter Game";
            }
        });
    }

    // --- Quiz Form ---
    var quizForm = document.getElementById('quiz-form');
    if (quizForm) {
        quizForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            var btn = quizForm.querySelector('button');
            btn.disabled = true;
            btn.innerText = "Calculating...";

            var diet = document.getElementById('quiz-diet').value;
            var commute = document.getElementById('quiz-commute').value;
            var energy = document.getElementById('quiz-energy').value;

            try {
                await apiCall('/footprint/baseline', {
                    method: 'POST',
                    body: JSON.stringify({ diet_type: diet, commute_method: commute, home_energy: energy })
                });
                var quizOverlay = document.getElementById('quiz-overlay');
                if (quizOverlay) quizOverlay.classList.add('hidden');
                loadProfile();
            } catch (err) {
                alert("Failed to save baseline.");
                btn.disabled = false;
                btn.innerText = "Calculate Baseline";
            }
        });
    }

    // --- Log Eco Action ---
    var actionForm = document.getElementById('action-form');
    if (actionForm) {
        actionForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            var btn = actionForm.querySelector('button');
            var resultBox = document.getElementById('action-result');
            var actionType = document.getElementById('action-type').value;

            btn.disabled = true;
            resultBox.classList.add('hidden');

            try {
                var result = await apiCall('/eco-actions', {
                    method: 'POST',
                    body: JSON.stringify({ action_type: actionType, quantity: 1 })
                });

                resultBox.innerHTML = '<h4 class="text-glow">+' + result.xp_awarded + ' XP Earned!</h4>' +
                    '<p>You saved ' + result.carbon_saved_kg + ' kg of CO₂.</p>' +
                    '<p class="text-sm" style="margin-top:0.5rem; color:#fca5a5;">' + result.fun_fact + '</p>';
                resultBox.classList.remove('hidden');
                loadProfile();
            } catch (err) {
                alert("Failed to log action.");
            } finally {
                btn.disabled = false;
            }
        });
    }

    // --- Log Daily Emission ---
    window.toggleEmissionInputs = function() {
        var category = document.getElementById('emission-category').value;
        document.querySelectorAll('.emission-inputs').forEach(function(el) {
            el.classList.add('hidden');
        });
        var target = document.getElementById('input-' + category);
        if (target) target.classList.remove('hidden');
    };

    var emissionForm = document.getElementById('emission-form');
    if (emissionForm) {
        emissionForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            var btn = emissionForm.querySelector('button');
            var resultBox = document.getElementById('emission-result');
            var category = document.getElementById('emission-category').value;
            
            btn.disabled = true;
            resultBox.classList.add('hidden');

            var endpoint = '';
            var body = {};

            if (category === 'diet') {
                endpoint = '/footprint/diet';
                body = {
                    meal_type: document.getElementById('emission-diet-type').value,
                    servings: 1,
                    date: new Date().toISOString().split('T')[0]
                };
            } else if (category === 'commute') {
                endpoint = '/footprint/commute';
                body = {
                    origin_address: 'Home',
                    destination_address: 'Work',
                    transport_mode: document.getElementById('emission-commute-mode').value,
                    date: new Date().toISOString().split('T')[0]
                };
            } else if (category === 'energy') {
                endpoint = '/footprint/energy';
                body = {
                    electricity_kwh: parseFloat(document.getElementById('emission-energy-elec').value || 0),
                    natural_gas_cubic_meters: 0,
                    date: new Date().toISOString().split('T')[0]
                };
            }

            try {
                var result = await apiCall(endpoint, {
                    method: 'POST',
                    body: JSON.stringify(body)
                });

                resultBox.innerHTML = '<h4 style="color:#ef4444;">+' + result.carbon_emissions_kg + ' kg CO₂ Emitted</h4>' +
                    '<p>+' + result.xp_awarded + ' XP Earned for logging.</p>';
                resultBox.classList.remove('hidden');
                loadProfile();
            } catch (err) {
                alert("Failed to log emission.");
            } finally {
                btn.disabled = false;
            }
        });
    }

    // --- AI Insights ---
    var insightBtn = document.getElementById('get-insight-btn');
    if (insightBtn) {
        insightBtn.addEventListener('click', async function() {
            var loading = document.getElementById('ai-loading');
            var box = document.getElementById('insight-box');

            insightBtn.disabled = true;
            if (loading) loading.classList.remove('hidden');
            if (box) box.classList.add('hidden');

            try {
                var category = document.getElementById('insight-category').value;
                var query = category ? '?category=' + category : '';
                var insight = await apiCall('/insights' + query);
                document.getElementById('ai-tip').innerText = insight.tips.length > 0 ? insight.tips[0] : "Great job staying green!";
                if (box) box.classList.remove('hidden');
            } catch (err) {
                alert("Failed to get insights.");
            } finally {
                insightBtn.disabled = false;
                if (loading) loading.classList.add('hidden');
            }
        });
    }

    // --- Chatbot Form ---
    var chatForm = document.getElementById('chat-form');
    if (chatForm) {
        chatForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            var input = document.getElementById('chat-input');
            var msg = input.value.trim();
            if (!msg) return;

            input.value = '';
            var messages = document.getElementById('chat-messages');
            messages.innerHTML += '<div class="msg user">' + msg + '</div>';
            messages.scrollTop = messages.scrollHeight;

            try {
                var result = await apiCall('/insights/chat', {
                    method: 'POST',
                    body: JSON.stringify({ message: msg })
                });
                messages.innerHTML += '<div class="msg ai">' + result.reply + '</div>';
                if (result.carbon_emissions_kg > 0) {
                    messages.innerHTML += '<div class="msg ai" style="background: #1e293b; font-weight:bold;">✅ Logged ' + result.carbon_emissions_kg + ' kg CO₂!</div>';
                    loadProfile();
                }
            } catch (err) {
                messages.innerHTML += '<div class="msg ai">Connection error.</div>';
            }
            messages.scrollTop = messages.scrollHeight;
        });
    }

    // --- Initial profile load ---
    loadProfile();

    // --- Keyboard Navigation (a11y) ---
    // Make tabs keyboard accessible
    var tabs = document.querySelectorAll('li[role="tab"]');
    tabs.forEach(function(tab) {
        tab.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                tab.click();
            }
        });
    });

    // Make chatbot header keyboard accessible
    var chatbotHeader = document.querySelector('.chatbot-header');
    if (chatbotHeader) {
        chatbotHeader.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleChat();
            }
        });
    }

});
