// Register Page JavaScript

document.addEventListener('DOMContentLoaded', () => {
    const passwordInput = document.getElementById('password');
    const registerForm = document.getElementById('registerForm');
    
    if (!passwordInput || !registerForm) return;
    
    // Password strength indicator
    passwordInput.addEventListener('input', (e) => {
        const password = e.target.value;
        const bar = document.getElementById('strengthBar');
        
        if (!bar) return;
        
        let strength = 0;
        if (password.length >= 8) strength++;
        if (password.match(/[a-z]/) && password.match(/[A-Z]/)) strength++;
        if (password.match(/[0-9]/)) strength++;
        if (password.match(/[^a-zA-Z0-9]/)) strength++;
        
        bar.className = 'password-strength-bar';
        if (strength === 1 || strength === 2) {
            bar.classList.add('strength-weak');
        } else if (strength === 3) {
            bar.classList.add('strength-medium');
        } else if (strength >= 4) {
            bar.classList.add('strength-strong');
        }
    });
    
    // Form submission
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const resultDiv = document.getElementById('result');
        const submitBtn = form.querySelector('button[type="submit"]');
        
        // Validate password match
        if (form.password.value !== form.confirm_password.value) {
            resultDiv.innerHTML = '<div class="alert error">❌ Passwords do not match</div>';
            return;
        }
        
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="loading"></span> Creating account...';
        
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
                resultDiv.innerHTML = '<div class="alert success">✅ Account created! Redirecting to login...</div>';
                setTimeout(() => {
                    window.location.href = '/login';
                }, 1500);
            } else {
                resultDiv.innerHTML = `<div class="alert error">❌ ${result.message}</div>`;
                submitBtn.disabled = false;
                submitBtn.innerHTML = '✨ Create Account';
            }
        } catch (error) {
            resultDiv.innerHTML = `<div class="alert error">❌ ${error.message}</div>`;
            submitBtn.disabled = false;
            submitBtn.innerHTML = '✨ Create Account';
        }
    });
});
