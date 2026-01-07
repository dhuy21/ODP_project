// ============================================
// MODERN DASHBOARD HOME - INTERACTIVE JAVASCRIPT
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initEntryAnimations();
    initFormSubmission();
    initPoolStatusRefresh();
    initReservationCheck();
});

// ========== ENTRY ANIMATIONS ==========
function initEntryAnimations() {
    const elements = document.querySelectorAll('.fade-in, .fade-in-up');
    
    elements.forEach((element, index) => {
        const delay = parseInt(element.dataset.delay) || (index * 100);
        
        setTimeout(() => {
            element.classList.add('animate');
        }, delay);
    });
}

// ========== FORM SUBMISSION ==========
function initFormSubmission() {
    const form = document.getElementById('provisionForm');
    if (!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitButton = form.querySelector('button[type="submit"]');
        const resultDiv = document.getElementById('result');
        const btnText = submitButton.querySelector('span');
        const btnIcon = submitButton.querySelector('i');
        
        // Validation
        const vmCount = parseInt(form.vm_count.value);
        if (vmCount < 1 || vmCount > 5) {
            resultDiv.innerHTML = `
                <div class="alert error">
                    <i class="fas fa-exclamation-circle"></i>
                    <span>Please request between 1 and 5 VMs</span>
                </div>
            `;
            return;
        }
        
        // Show loading state
        submitButton.disabled = true;
        btnText.textContent = 'Creating reservation...';
        btnIcon.className = 'fas fa-spinner fa-spin';
        
        resultDiv.innerHTML = `
            <div class="alert info">
                <i class="fas fa-info-circle"></i>
                <span>Creating your reservation, please wait...</span>
            </div>
        `;
        
        const data = {
            password: form.password.value,
            vm_count: vmCount,
            duration: parseInt(form.duration.value),
            packages: form.packages.value
        };
        
        // Store password for terminal use
        sessionStorage.setItem('password', data.password);
        
        try {
            const response = await fetch('/provision', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                resultDiv.innerHTML = `
                    <div class="alert success">
                        <i class="fas fa-check-circle"></i>
                        <span>
                            Reservation created successfully!<br>
                            <small>Redirecting to your resources...</small>
                        </span>
                    </div>
                `;
                
                setTimeout(() => {
                    window.location.href = result.redirect;
                }, 1500);
            } else {
                resultDiv.innerHTML = `
                    <div class="alert error">
                        <i class="fas fa-exclamation-circle"></i>
                        <span>${result.message || 'Failed to create reservation'}</span>
                    </div>
                `;
                
                // Re-enable form
                submitButton.disabled = false;
                btnText.textContent = 'Create Reservation';
                btnIcon.className = 'fas fa-rocket';
            }
        } catch (error) {
            resultDiv.innerHTML = `
                <div class="alert error">
                    <i class="fas fa-exclamation-circle"></i>
                    <span>Network error: ${error.message}</span>
                </div>
            `;
            
            // Re-enable form
            submitButton.disabled = false;
            btnText.textContent = 'Create Reservation';
            btnIcon.className = 'fas fa-rocket';
        }
    });
}

// ========== POOL STATUS REFRESH ==========
async function initPoolStatusRefresh() {
    async function refreshPoolStatus() {
        try {
            const response = await fetch('/pool/status');
            const data = await response.json();
            if (data.status === 'success') {
                const availableCount = document.getElementById('available-count');
                if (availableCount) {
                    // Animate number change
                    const oldValue = parseInt(availableCount.textContent);
                    const newValue = data.free;
                    
                    if (oldValue !== newValue) {
                        availableCount.style.transform = 'scale(1.2)';
                        availableCount.style.color = '#10b981';
                        setTimeout(() => {
                            availableCount.textContent = newValue;
                            availableCount.style.transform = 'scale(1)';
                            availableCount.style.color = '';
                        }, 300);
                    } else {
                        availableCount.textContent = newValue;
                    }
                }
            }
        } catch (error) {
            console.error('Error refreshing pool status:', error);
        }
    }
    
    // Refresh immediately and then every 30 seconds
    refreshPoolStatus();
    setInterval(refreshPoolStatus, 30000);
}

// ========== RESERVATION CHECK ==========
async function initReservationCheck() {
    async function checkExpiredReservations() {
        try {
            const response = await fetch('/check-my-reservations');
            const data = await response.json();
            
            if (data.has_expired) {
                // Show notification instead of alert
                const notification = document.createElement('div');
                notification.className = 'alert warning';
                notification.style.position = 'fixed';
                notification.style.top = '20px';
                notification.style.right = '20px';
                notification.style.zIndex = '10000';
                notification.style.maxWidth = '400px';
                notification.innerHTML = `
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>One or more of your reservations has expired. Refreshing...</span>
                `;
                document.body.appendChild(notification);
                
                setTimeout(() => {
                    location.reload();
                }, 2000);
            }
        } catch (e) {
            console.error('Error checking reservations:', e);
        }
    }
    
    // Check every 30 seconds
    setInterval(checkExpiredReservations, 30000);
}