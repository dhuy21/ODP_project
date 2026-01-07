// Reservation Detail Page JavaScript

let expiryTimestamp = 0;
let statsUpdateInterval;

// Initialize countdown timer
function initializeCountdown(expiresAt) {
    const countdownEl = document.getElementById('countdown');
    if (!countdownEl) return;

    function updateCountdown() {
        const now = Math.floor(Date.now() / 1000);
        const remaining = expiresAt - now;

        if (remaining <= 0) {
            countdownEl.textContent = 'EXPIRED';
            countdownEl.classList.add('warning');
            setTimeout(() => {
                alert('⚠️ Your reservation has expired!');
                window.location.href = countdownEl.dataset.redirectUrl || '/home';
            }, 2000);
            return;
        }

        const hours = Math.floor(remaining / 3600);
        const minutes = Math.floor((remaining % 3600) / 60);
        const seconds = remaining % 60;

        countdownEl.textContent = `${hours}h ${minutes}m ${seconds}s`;

        if (remaining < 300) { // Less than 5 minutes
            countdownEl.classList.add('warning');
        }
    }

    updateCountdown();
    setInterval(updateCountdown, 1000);
}

// Release reservation (internal function with unique name to avoid conflicts)
async function performReleaseReservation(username, reservationId, redirectUrl) {
    if (!confirm('Are you sure you want to release these resources?')) {
        return;
    }

    try {
        const response = await fetch(`/release/${username}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                reservation_id: reservationId
            })
        });

        const result = await response.json();

        if (result.status === 'success') {
            alert('✅ Resources released successfully!');
            window.location.href = redirectUrl || '/home';
        } else {
            alert('❌ Error: ' + result.message);
        }
    } catch (error) {
        alert('❌ Error: ' + error.message);
    }
}

// Update stats for all nodes
async function updateStats(reservationId) {
    try {
        const response = await fetch(`/stats/${reservationId}`);
        const data = await response.json();

        if (data.status === 'success') {
            Object.keys(data.stats).forEach(nodeName => {
                const stats = data.stats[nodeName];
                const cpuElem = document.getElementById(`cpu-${nodeName}`);
                const memElem = document.getElementById(`mem-${nodeName}`);
                const memPercElem = document.getElementById(`mem-perc-${nodeName}`);

                if (cpuElem) cpuElem.textContent = stats.cpu;
                if (memElem) memElem.textContent = stats.memory;
                if (memPercElem) memPercElem.textContent = stats.memory_percent;
            });
        }
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

// Initialize page
window.onload = function() {
    const countdownEl = document.getElementById('countdown');
    if (countdownEl) {
        const expiresAt = parseInt(countdownEl.dataset.expires);
        initializeCountdown(expiresAt);
    }

    // Get reservation ID from page
    const reservationIdMeta = document.querySelector('meta[name="reservation-id"]');
    if (reservationIdMeta) {
        const reservationId = reservationIdMeta.content;
        updateStats(reservationId); // Initial load
        statsUpdateInterval = setInterval(() => updateStats(reservationId), 3000);
    }
};

// Cleanup on page unload
window.onbeforeunload = function() {
    if (statsUpdateInterval) {
        clearInterval(statsUpdateInterval);
    }
};
