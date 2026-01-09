// ============================================
// MODERN DASHBOARD HOME - INTERACTIVE JAVASCRIPT
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initEntryAnimations();
    initOSSelection();
    initFormSubmission();
    initPoolStatusRefresh();
    initReservationUpdates();
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
// Make refreshPoolStatus available globally so it can be called from other functions
let poolStatusRefreshInterval = null;

async function refreshPoolStatus(skipAnimation = false) {
        try {
            const response = await fetch('/pool/status');
            const data = await response.json();
            if (data.status === 'success') {
                const availableCount = document.getElementById('available-count');
                if (availableCount) {
                    // Animate number change
                const oldValue = parseInt(availableCount.textContent) || 0;
                    const newValue = data.free;
                    
                if (oldValue !== newValue && !skipAnimation) {
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
    
async function initPoolStatusRefresh() {
    // Refresh immediately on page load
    refreshPoolStatus();
    
    // Then refresh every 30 seconds
    if (poolStatusRefreshInterval) {
        clearInterval(poolStatusRefreshInterval);
    }
    poolStatusRefreshInterval = setInterval(() => {
        refreshPoolStatus();
    }, 30000);
}

// ========== RESERVATION UPDATES ==========
function initReservationUpdates() {
    // Listen for WebSocket reservation_expired event
    if (typeof window.socket !== 'undefined') {
        window.socket.on('reservation_expired', function(data) {
            if (data && data.reservation_id) {
                // Wait a short moment to ensure database commit is complete
                // Then reload both active reservations AND pool status to keep them synchronized
                // This prevents UI showing stale data or removing reservations before database is ready
                // Both will update together with the same delay to maintain synchronization
                
                // Temporarily pause the pool status interval to prevent it from updating separately
                // We'll update it together with reservations to maintain sync
                const wasIntervalRunning = poolStatusRefreshInterval !== null;
                if (poolStatusRefreshInterval) {
                    clearInterval(poolStatusRefreshInterval);
                    poolStatusRefreshInterval = null;
                }
                
                setTimeout(() => {
                    // Update both active reservations and pool status together to maintain synchronization
                    Promise.all([
                        reloadActiveReservations(),
                        refreshPoolStatus(false) // Allow animation but sync timing
                    ]).then(() => {
                        // Restart the interval after sync update is complete
                        if (wasIntervalRunning) {
                            poolStatusRefreshInterval = setInterval(() => {
                                refreshPoolStatus();
                            }, 30000);
                        }
                    }).catch(error => {
                        console.error('Error updating dashboard data:', error);
                        // Restart interval even on error
                        if (wasIntervalRunning) {
                            poolStatusRefreshInterval = setInterval(() => {
                                refreshPoolStatus();
                            }, 30000);
                        }
                    });
                }, 300);
            }
        });
    }
    
    // Also check on page load if redirected from reservation_detail
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('refresh') === 'true') {
        // Reload immediately on page load if refresh flag is present
        setTimeout(() => {
            // Update both together to maintain synchronization
            Promise.all([
                reloadActiveReservations(),
                refreshPoolStatus(false) // Allow animation
            ]).catch(error => {
                console.error('Error updating dashboard data:', error);
            });
            // Clean up URL
            window.history.replaceState({}, document.title, window.location.pathname);
        }, 100);
    }
}

// Reload active reservations from API and update UI
// This function ensures data synchronization by getting latest data from API and updating UI once
async function reloadActiveReservations() {
    try {
        const gridElement = document.getElementById('active-reservations-grid');
        const sectionElement = document.getElementById('active-reservations-section');
        const countElement = document.getElementById('active-reservations-count');
        
        if (!gridElement || !sectionElement || !countElement) return;
        
        // Get current reservations from UI before updating
        const currentReservationIds = new Set();
        gridElement.querySelectorAll('[data-reservation-id]').forEach(card => {
            const id = card.getAttribute('data-reservation-id');
            if (id) currentReservationIds.add(id);
        });
        
        // Fetch latest data from API
        const response = await fetch('/api/reservations/active');
        const data = await response.json();
        
        if (data.status === 'success') {
            const activeReservations = data.active_reservations || [];
            const count = data.count || 0;
            
            // Get new reservation IDs from API response
            const newReservationIds = new Set(activeReservations.map(r => r.id));
            
            // Check if there are any differences
            const hasChanges = count !== currentReservationIds.size || 
                             ![...currentReservationIds].every(id => newReservationIds.has(id)) ||
                             ![...newReservationIds].every(id => currentReservationIds.has(id));
            
            // Only update UI if there are actual changes to avoid unnecessary re-renders
            if (!hasChanges) {
                // No changes, ensure count is correct
                const currentCount = parseInt(countElement.textContent) || 0;
                if (currentCount !== count) {
                    countElement.textContent = count;
                }
                return;
            }
            
            // Update active reservations count - single source of truth from API
            const oldValue = parseInt(countElement.textContent) || 0;
            if (oldValue !== count) {
                // Animate count change only if different
                countElement.style.transform = 'scale(1.2)';
                countElement.style.color = count < oldValue ? '#ef4444' : '#3b82f6';
                    setTimeout(() => {
                    countElement.textContent = count;
                    countElement.style.transform = 'scale(1)';
                    countElement.style.color = '';
                    }, 300);
            } else {
                countElement.textContent = count;
            }
            
            // Update UI with data from API - single update ensures synchronization
            if (count === 0) {
                // Hide section if no active reservations
                sectionElement.style.display = 'none';
                gridElement.innerHTML = '';
        } else {
                // Show section and update grid with fresh data from API
                sectionElement.style.display = 'block';
                
                // Generate HTML for active reservations from API data
                gridElement.innerHTML = activeReservations.map((reservation, index) => {
    const vmCount = reservation.vm_count || 1;
                    const reservationId = reservation.id || '';
    const duration = reservation.duration || reservation.duration_minutes || 0;
                    const packages = reservation.packages || [];
                    const packagesText = packages.length > 0 ? packages.join(', ') : 'None';
    
                    return `
                        <div class="reservation-card fade-in-up" data-delay="${index * 50}" data-reservation-id="${reservationId}">
        <div class="card-header">
            <div class="card-title-section">
                <div class="card-icon">
                    <i class="fas fa-server"></i>
                </div>
                <div>
                                        <h3>${vmCount} Virtual Machine${vmCount > 1 ? 's' : ''}</h3>
                                        <code class="reservation-id">${reservationId.substring(0, 12)}...</code>
                </div>
            </div>
            <span class="status-badge status-active">
                <i class="fas fa-circle"></i>
                Active
            </span>
        </div>
        <div class="card-body">
            <div class="detail-item">
                <i class="fas fa-clock"></i>
                <span class="detail-label">Duration:</span>
                <span class="detail-value">${duration} minutes</span>
            </div>
            <div class="detail-item">
                <i class="fas fa-box"></i>
                <span class="detail-label">Packages:</span>
                                    <span class="detail-value">${packagesText}</span>
            </div>
        </div>
        <div class="card-footer">
            <a href="/reservation/${reservationId}" class="btn btn-primary btn-card">
                <span>View Details</span>
                <i class="fas fa-arrow-right"></i>
            </a>
                            </div>
        </div>
    `;
                }).join('');
                
                // Re-init animations for new elements
                initEntryAnimations();
            }
        }
    } catch (error) {
        console.error('Error reloading active reservations:', error);
    }
}