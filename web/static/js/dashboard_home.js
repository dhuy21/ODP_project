// Dashboard Home Page JavaScript

document.addEventListener('DOMContentLoaded', () => {
    // Refresh pool status
    async function refreshPoolStatus() {
        try {
            const response = await fetch('/pool/status');
            const data = await response.json();
            if (data.status === 'success') {
                const availableCount = document.getElementById('available-count');
                if (availableCount) {
                    availableCount.textContent = data.free;
                }
            }
        } catch (error) {
            console.error('Error refreshing pool status:', error);
        }
    }
    
    // Check for expired reservations
    async function checkExpiredReservations() {
        try {
            const response = await fetch('/check-my-reservations');
            const data = await response.json();
            
            if (data.has_expired) {
                alert('⚠️ One or more of your reservations has expired. Refreshing...');
                location.reload();
            }
        } catch (e) {
            console.error('Error checking reservations:', e);
        }
    }
    
    // Set intervals
    setInterval(refreshPoolStatus, 30000);
    setInterval(checkExpiredReservations, 30000);
});
