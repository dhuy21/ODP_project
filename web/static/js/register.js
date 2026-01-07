// ============================================
// MODERN REGISTER PAGE - SIMPLE & CLEAN
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initEntryAnimations();
    initPasswordToggles();
    initPasswordStrength();
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
            resultDiv.innerHTML = `
                <div class="alert error">
                    <i class="fas fa-exclamation-circle"></i>
                    <span>Passwords do not match</span>
                </div>
            `;
            return;
        }
        
        resultDiv.innerHTML = '';
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
                resultDiv.innerHTML = `
                    <div class="alert success">
                        <i class="fas fa-check-circle"></i>
                        <span>Account created! Redirecting...</span>
                    </div>
                `;
                setTimeout(() => {
                    window.location.href = '/login';
                }, 1500);
            } else {
                resultDiv.innerHTML = `
                    <div class="alert error">
                        <i class="fas fa-exclamation-circle"></i>
                        <span>${result.message || 'Registration failed. Please try again.'}</span>
                    </div>
                `;
                submitBtn.disabled = false;
                btnText.textContent = 'Create Account';
                btnIcon.style.display = 'inline-block';
                submitBtn.querySelector('.loading').remove();
            }
        } catch (error) {
            resultDiv.innerHTML = `
                <div class="alert error">
                    <i class="fas fa-exclamation-circle"></i>
                    <span>Network error. Please try again.</span>
                </div>
            `;
            submitBtn.disabled = false;
            btnText.textContent = 'Create Account';
            btnIcon.style.display = 'inline-block';
            submitBtn.querySelector('.loading').remove();
        }
    });
}