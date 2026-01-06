// Dashboard Page JavaScript

// Initialize expiry countdown
let expiryTimestamp = 0;

function initializeDashboard(timestamp) {
    expiryTimestamp = timestamp || 0;
    updateCountdown();
}

function updateCountdown() {
    if (expiryTimestamp === 0) return;
    
    const now = Math.floor(Date.now() / 1000);
    const remaining = expiryTimestamp - now;
    
    const countdownElement = document.getElementById('countdown');
    if (!countdownElement) return;
    
    if (remaining <= 0) {
        countdownElement.innerHTML = '<span style="color:red">EXPIRED - Your resources have been released</span>';
        setTimeout(() => window.location.href = '/', 3000);
        return;
    }
    
    const hours = Math.floor(remaining / 3600);
    const minutes = Math.floor((remaining % 3600) / 60);
    const seconds = remaining % 60;
    
    countdownElement.textContent = `${hours}h ${minutes}m ${seconds}s remaining`;
    
    setTimeout(updateCountdown, 1000);
}

async function releaseResources(username) {
    if (!confirm('Are you sure you want to release all resources?')) {
        return;
    }
    
    try {
        const response = await fetch(`/release/${username}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            alert('Resources released successfully!');
            window.location.href = '/';
        } else {
            alert('Error: ' + data.message);
        }
    } catch (error) {
        alert('Error releasing resources: ' + error.message);
    }
}
