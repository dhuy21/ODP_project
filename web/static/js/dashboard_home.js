// Dashboard Home Page JavaScript

document.addEventListener('DOMContentLoaded', () => {
    // Handle provision form submission
    const form = document.getElementById('provisionForm');
    
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitButton = form.querySelector('button[type="submit"]');
            const resultDiv = document.getElementById('result');
            
            // Show loading state
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="loading"></span> Creating reservation...';
            resultDiv.innerHTML = '<div class="alert info">Creating your reservation, please wait...</div>';
            
            const data = {
                password: form.password.value,
                vm_count: parseInt(form.vm_count.value),
                duration: parseInt(form.duration.value),
                packages: form.packages.value
            };
            
            // Validation
            if (data.vm_count < 1 || data.vm_count > 5) {
                resultDiv.innerHTML = '<div class="alert error">❌ Please request between 1 and 5 VMs</div>';
                submitButton.disabled = false;
                submitButton.innerHTML = '🚀 Create Reservation';
                return;
            }
            
            // Store password for terminal use
            sessionStorage.setItem('password', data.password);
            
            try {
                const response = await fetch('/provision', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    resultDiv.innerHTML = `
                        <div class="alert success">
                            ✅ Reservation created successfully!<br>
                            <small>Redirecting to your resources...</small>
                        </div>
                    `;
                    
                    setTimeout(() => {
                        window.location.href = result.redirect;
                    }, 1500);
                } else {
                    resultDiv.innerHTML = `<div class="alert error">❌ ${result.message}</div>`;
                    
                    // Re-enable form
                    submitButton.disabled = false;
                    submitButton.innerHTML = '🚀 Create Reservation';
                    form.querySelectorAll('input, select').forEach(el => el.disabled = false);
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="alert error">❌ Network error: ${error.message}</div>`;
                
                // Re-enable form
                submitButton.disabled = false;
                submitButton.innerHTML = '🚀 Create Reservation';
                form.querySelectorAll('input, select').forEach(el => el.disabled = false);
            }
        });
    }
    
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
