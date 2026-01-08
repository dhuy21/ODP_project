// Reservation Detail Page JavaScript

let expiryTimestamp = 0;
let statsUpdateInterval;
let reservationStatus = 'active'; // Track reservation status
let isStatsUpdateActive = true; // Flag to control stats updates

// Initialize countdown timer
function initializeCountdown(expiresAt) {
    const countdownEl = document.getElementById('countdown');
    if (!countdownEl) return;

    let hasShownExpiredNotification = false; // Flag to prevent multiple notifications
    let countdownInterval = null; // Store interval ID

    function updateCountdown() {
        const now = Math.floor(Date.now() / 1000);
        const remaining = expiresAt - now;

        if (remaining <= 0) {
            countdownEl.textContent = 'EXPIRED';
            countdownEl.classList.add('warning');
            // Stop stats updates when expired
            stopStatsUpdates();
            reservationStatus = 'expired';
            
            // Stop countdown interval
            if (countdownInterval) {
                clearInterval(countdownInterval);
                countdownInterval = null;
            }
            
            // Only show notification once
            if (!hasShownExpiredNotification) {
                hasShownExpiredNotification = true;
                setTimeout(() => {
                    Notification.warning('Your reservation has expired!', 3000);
                    setTimeout(() => {
                        window.location.href = countdownEl.dataset.redirectUrl || '/home';
                    }, 3000);
                }, 2000);
            }
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
    countdownInterval = setInterval(updateCountdown, 1000);
}

// Stop stats updates
function stopStatsUpdates() {
    isStatsUpdateActive = false;
    if (statsUpdateInterval) {
        clearInterval(statsUpdateInterval);
        statsUpdateInterval = null;
    }
}

// Release reservation (internal function with unique name to avoid conflicts)
async function performReleaseReservation(username, reservationId, redirectUrl) {
    const confirmed = await Modal.confirm({
        title: 'Release Resources',
        message: 'Are you sure you want to release these resources? This action cannot be undone.',
        confirmText: 'Release',
        cancelText: 'Cancel',
        type: 'warning',
        confirmColor: 'danger'
    });

    if (!confirmed) {
        return;
    }

    // Get release button and set loading state
    const releaseBtn = document.getElementById('release-btn');
    if (releaseBtn) {
        releaseBtn.classList.add('loading');
        releaseBtn.disabled = true;
    }

    // Show loading notification (with very long duration, will be removed manually)
    const loadingNotification = Notification.info('Releasing resources...', 999999);

    // Stop stats updates immediately
    stopStatsUpdates();
    reservationStatus = 'released';

    try {
        const response = await fetch(`/release/${username}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                reservation_id: reservationId
            })
        });

        const result = await response.json();

        // Remove loading notification
        if (loadingNotification) {
            Notification.remove(loadingNotification);
        }

        if (result.status === 'success') {
            // Remove loading state
            if (releaseBtn) {
                releaseBtn.classList.remove('loading');
            }
            
            // Show success notification
            Notification.success('Resources released successfully!', 3000);
            
            // Redirect after a short delay
            setTimeout(() => {
                window.location.href = redirectUrl || '/home';
            }, 1500);
        } else {
            // Remove loading state on error
            if (releaseBtn) {
                releaseBtn.classList.remove('loading');
                releaseBtn.disabled = false;
            }
            
            Notification.error(result.message || 'Failed to release resources');
        }
    } catch (error) {
        // Remove loading notification on error
        if (loadingNotification) {
            Notification.remove(loadingNotification);
        }
        
        // Remove loading state on error
        if (releaseBtn) {
            releaseBtn.classList.remove('loading');
            releaseBtn.disabled = false;
        }
        
        Notification.error('Network error: ' + error.message);
    }
}

// Update stats for all nodes
async function updateStats(reservationId, forceLoad = false) {
    // Don't update if stats updates are stopped (unless forced for initial load)
    if (!isStatsUpdateActive && !forceLoad) {
        return;
    }

    try {
        const response = await fetch(`/stats/${reservationId}`);
        const data = await response.json();

        if (data.status === 'success') {
            // Display stats (either active or final saved stats)
            if (data.stats) {
                Object.keys(data.stats).forEach(nodeName => {
                    const stats = data.stats[nodeName];
                    const cpuElem = document.getElementById(`cpu-${nodeName}`);
                    const memElem = document.getElementById(`mem-${nodeName}`);
                    const memPercElem = document.getElementById(`mem-perc-${nodeName}`);

                    // Remove loading indicator and set stats
                    if (cpuElem) {
                        const loading = cpuElem.querySelector('.loading-stats');
                        if (loading) loading.remove();
                        cpuElem.textContent = stats.cpu || 'N/A';
                    }
                    if (memElem) {
                        const loading = memElem.querySelector('.loading-stats');
                        if (loading) loading.remove();
                        memElem.textContent = stats.memory || 'N/A';
                    }
                    if (memPercElem) {
                        const loading = memPercElem.querySelector('.loading-stats');
                        if (loading) loading.remove();
                        memPercElem.textContent = stats.memory_percent || 'N/A';
                    }
                });
            }
            
            // Check if reservation is still active
            if (data.reservation_status && data.reservation_status !== 'active') {
                // Reservation is no longer active, stop updates
                stopStatsUpdates();
                reservationStatus = data.reservation_status;
                return;
            }
        } else if (data.status === 'error') {
            // Reservation is not active or error occurred
            if (data.reservation_status && data.reservation_status !== 'active') {
                stopStatsUpdates();
                reservationStatus = data.reservation_status;
            }
            
            // Try to show error message or N/A
            const nodeCards = document.querySelectorAll('.node-card');
            nodeCards.forEach(card => {
                const nodeName = card.querySelector('.node-name')?.textContent.trim();
                if (nodeName) {
                    const cpuElem = document.getElementById(`cpu-${nodeName}`);
                    const memElem = document.getElementById(`mem-${nodeName}`);
                    const memPercElem = document.getElementById(`mem-perc-${nodeName}`);
                    
                    if (cpuElem && cpuElem.textContent.includes('Loading')) {
                        cpuElem.textContent = 'N/A';
                        cpuElem.parentElement.querySelector('.loading-stats')?.remove();
                    }
                    if (memElem && memElem.textContent.includes('Loading')) {
                        memElem.textContent = 'N/A';
                        memElem.parentElement.querySelector('.loading-stats')?.remove();
                    }
                    if (memPercElem && memPercElem.textContent.includes('Loading')) {
                        memPercElem.textContent = 'N/A';
                        memPercElem.parentElement.querySelector('.loading-stats')?.remove();
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

// Initialize page
window.onload = function() {
    // Get reservation status from page
    const statusBadge = document.querySelector('.badge');
    if (statusBadge) {
        const statusText = statusBadge.textContent.trim().toLowerCase();
        if (statusText !== 'active') {
            reservationStatus = statusText;
            isStatsUpdateActive = false;
        }
    }

    const countdownEl = document.getElementById('countdown');
    if (countdownEl) {
        const expiresAt = parseInt(countdownEl.dataset.expires);
        initializeCountdown(expiresAt);
    } else {
        // No countdown means reservation is not active
        isStatsUpdateActive = false;
    }

    // Get reservation ID from page
    const reservationIdMeta = document.querySelector('meta[name="reservation-id"]');
    if (reservationIdMeta) {
        const reservationId = reservationIdMeta.content;
        
        // Always load stats once (for active or final stats)
        updateStats(reservationId, true); // Initial load with force flag
        
        // Only start interval if reservation is active
        if (isStatsUpdateActive) {
            statsUpdateInterval = setInterval(() => updateStats(reservationId), 3000);
        }
    }
};

// Cleanup on page unload
window.onbeforeunload = function() {
    if (statsUpdateInterval) {
        clearInterval(statsUpdateInterval);
    }
};
