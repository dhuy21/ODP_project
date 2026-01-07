// ============================================
// MODERN LOGIN PAGE - SIMPLE & CLEAN
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initEntryAnimations();
    initPasswordToggle();
    initFormSubmission();
});

// ========== ENTRY ANIMATIONS ==========
function initEntryAnimations() {
    const elements = document.querySelectorAll('.fade-in-scale, .fade-in-up, .fade-in');
    
    elements.forEach((element, index) => {
        const delay = parseInt(element.dataset.delay) || (index * 100);
        
        setTimeout(() => {
            element.classList.add('animate');
        }, delay);
    });
}

// ========== PASSWORD TOGGLE ==========
function initPasswordToggle() {
    const toggle = document.getElementById('passwordToggle');
    const input = document.getElementById('password');
    
    if (toggle && input) {
        toggle.addEventListener('click', () => {
            const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
            input.setAttribute('type', type);
            
            const icon = toggle.querySelector('i');
            icon.classList.toggle('fa-eye');
            icon.classList.toggle('fa-eye-slash');
        });
    }
}

// ========== FORM SUBMISSION ==========
function initFormSubmission() {
    const form = document.getElementById('loginForm');
    if (!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const resultDiv = document.getElementById('result');
        const submitBtn = form.querySelector('.btn-submit');
        const btnText = submitBtn.querySelector('.btn-text');
        const btnIcon = submitBtn.querySelector('i');
        
        submitBtn.disabled = true;
        btnText.textContent = 'Signing in...';
        btnIcon.style.display = 'none';
        
        const loading = document.createElement('span');
        loading.className = 'loading';
        submitBtn.insertBefore(loading, btnText);
        
        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: form.username.value,
                    password: form.password.value
                })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                Notification.success('Login successful! Redirecting...', 2000);
                setTimeout(() => {
                    window.location.href = '/home';
                }, 1000);
            } else {
                Notification.error(result.message || 'Login failed. Please try again.');
                submitBtn.disabled = false;
                btnText.textContent = 'Sign In';
                btnIcon.style.display = 'inline-block';
                if (submitBtn.querySelector('.loading')) {
                    submitBtn.querySelector('.loading').remove();
                }
            }
        } catch (error) {
            Notification.error('Network error. Please try again.');
            submitBtn.disabled = false;
            btnText.textContent = 'Sign In';
            btnIcon.style.display = 'inline-block';
            if (submitBtn.querySelector('.loading')) {
                submitBtn.querySelector('.loading').remove();
            }
        }
    });
}