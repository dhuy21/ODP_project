// ============================================
// MODERN DASHBOARD HOME - INTERACTIVE JAVASCRIPT
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initEntryAnimations();
    initOSSelection();
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

// ========== OS SELECTION ==========
function initOSSelection() {
    const osCards = document.querySelectorAll('.btn-os-select');
    const osGrid = document.getElementById('osGrid');
    const formContainer = document.getElementById('provisionFormContainer');
    const btnBack = document.getElementById('btnBackToOS');
    const selectedOSInput = document.getElementById('selectedOS');
    const selectedOSName = document.getElementById('selectedOSName');
    
    osCards.forEach(btn => {
        btn.addEventListener('click', () => {
            const os = btn.dataset.os;
            const osCard = btn.closest('.os-card');
            const osName = osCard.querySelector('h3').textContent;
            const osVersion = osCard.querySelector('.os-version').textContent;
            
            // Store selected OS
            selectedOSInput.value = os;
            selectedOSName.textContent = `${osName} ${osVersion}`;
            
            // Hide OS grid and show form
            osGrid.style.display = 'none';
            formContainer.style.display = 'block';
            
            // Scroll to form
            formContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });
    
    if (btnBack) {
        btnBack.addEventListener('click', () => {
            formContainer.style.display = 'none';
            osGrid.style.display = 'grid';
            osGrid.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }
}

// ========== FORM SUBMISSION ==========
function initFormSubmission() {
    const form = document.getElementById('provisionForm');
    if (!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitButton = form.querySelector('button[type="submit"]');
        const btnText = submitButton.querySelector('span');
        const btnIcon = submitButton.querySelector('i');
        
        // Validation
        const vmCount = parseInt(form.vm_count.value);
        if (vmCount < 1 || vmCount > 5) {
            Notification.error('Please request between 1 and 5 VMs');
            return;
        }
            
        // Show loading state
        submitButton.disabled = true;
        btnText.textContent = 'Creating reservation...';
        btnIcon.className = 'fas fa-spinner fa-spin';
        
        Notification.info('Creating your reservation, please wait...', 3000);
        
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
                Notification.success('Reservation created successfully! Redirecting...', 3000);
                setTimeout(() => {
                    window.location.href = result.redirect;
                }, 1500);
            } else {
                Notification.error(result.message || 'Failed to create reservation');
                
                // Re-enable form
                submitButton.disabled = false;
                btnText.textContent = 'Create Reservation';
                btnIcon.className = 'fas fa-rocket';
            }
        } catch (error) {
            Notification.error('Network error: ' + error.message);
            
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
                Notification.warning('One or more of your reservations has expired. Refreshing...', 3000);
                setTimeout(() => {
                    location.reload();
                }, 3000);
            }
        } catch (e) {
            console.error('Error checking reservations:', e);
        }
    }
    
    // Check every 30 seconds
    setInterval(checkExpiredReservations, 30000);
}