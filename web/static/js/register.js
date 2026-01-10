// ============================================
// MODERN REGISTER PAGE - SIMPLE & CLEAN
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initEntryAnimations();
    initPasswordToggles();
    initPasswordStrength();
    initFormSubmission();
});

// ========== PASSWORD TOGGLES ==========
function initPasswordToggles() {
    const passwordToggle = document.getElementById('passwordToggle');
    const passwordInput = document.getElementById('password');
    const confirmToggle = document.getElementById('confirmPasswordToggle');
    const confirmInput = document.getElementById('confirm_password');
    
    if (passwordToggle && passwordInput) {
        passwordToggle.addEventListener('click', () => {
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            const icon = passwordToggle.querySelector('i');
            icon.classList.toggle('fa-eye');
            icon.classList.toggle('fa-eye-slash');
        });
    }
    
    if (confirmToggle && confirmInput) {
        confirmToggle.addEventListener('click', () => {
            const type = confirmInput.getAttribute('type') === 'password' ? 'text' : 'password';
            confirmInput.setAttribute('type', type);
            const icon = confirmToggle.querySelector('i');
            icon.classList.toggle('fa-eye');
            icon.classList.toggle('fa-eye-slash');
        });
    }
}

// ========== PASSWORD STRENGTH ==========
function initPasswordStrength() {
    const passwordInput = document.getElementById('password');
    const strengthBar = document.getElementById('strengthBar');
    
    if (!passwordInput || !strengthBar) return;
    
    passwordInput.addEventListener('input', (e) => {
        const password = e.target.value;
        let strength = 0;
        
        if (password.length >= 8) strength++;
        if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
        if (/[0-9]/.test(password)) strength++;
        if (/[^a-zA-Z0-9]/.test(password)) strength++;
        
        strengthBar.className = 'password-strength-bar';
        
        if (password.length === 0) {
            strengthBar.style.width = '0%';
        } else if (strength <= 1) {
            strengthBar.classList.add('strength-weak');
        } else if (strength === 2 || strength === 3) {
            strengthBar.classList.add('strength-medium');
        } else if (strength >= 4) {
            strengthBar.classList.add('strength-strong');
        }
    });
}

// ========== FORM SUBMISSION ==========
function initFormSubmission() {
    const form = document.getElementById('registerForm');
    if (!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const resultDiv = document.getElementById('result');
        const submitBtn = form.querySelector('.btn-submit');
        const btnText = submitBtn.querySelector('.btn-text');
        const btnIcon = submitBtn.querySelector('i');
        
        if (form.password.value !== form.confirm_password.value) {
            Notification.error('Passwords do not match');
            return;
        }
        
        submitBtn.disabled = true;
        btnText.textContent = 'Creating account...';
        btnIcon.style.display = 'none';
        
        const loading = document.createElement('span');
        loading.className = 'loading';
        submitBtn.insertBefore(loading, btnText);
        
        try {
            const response = await fetch('/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: form.username.value,
                    email: form.email.value,
                    password: form.password.value
                })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                Notification.success('Account created! Redirecting...', 2000);
                setTimeout(() => {
                    window.location.href = '/login';
                }, 1500);
            } else {
                Notification.error(result.message || 'Registration failed. Please try again.');
                submitBtn.disabled = false;
                btnText.textContent = 'Create Account';
                btnIcon.style.display = 'inline-block';
                if (submitBtn.querySelector('.loading')) {
                    submitBtn.querySelector('.loading').remove();
                }
            }
        } catch (error) {
            Notification.error('Network error. Please try again.');
            submitBtn.disabled = false;
            btnText.textContent = 'Create Account';
            btnIcon.style.display = 'inline-block';
            if (submitBtn.querySelector('.loading')) {
                submitBtn.querySelector('.loading').remove();
            }
        }
    });
}