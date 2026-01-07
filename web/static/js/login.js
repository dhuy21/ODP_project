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
        
        resultDiv.innerHTML = '';
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
                resultDiv.innerHTML = `
                    <div class="alert success">
                        <i class="fas fa-check-circle"></i>
                        <span>Login successful! Redirecting...</span>
                    </div>
                `;
                setTimeout(() => {
                    window.location.href = '/home';
                }, 1000);
            } else {
                resultDiv.innerHTML = `
                    <div class="alert error">
                        <i class="fas fa-exclamation-circle"></i>
                        <span>${result.message || 'Login failed. Please try again.'}</span>
                    </div>
                `;
                submitBtn.disabled = false;
                btnText.textContent = 'Sign In';
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
            btnText.textContent = 'Sign In';
            btnIcon.style.display = 'inline-block';
            submitBtn.querySelector('.loading').remove();
        }
    });
}