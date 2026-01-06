// Login Page JavaScript

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    
    if (!loginForm) return;
    
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const resultDiv = document.getElementById('result');
        const submitBtn = form.querySelector('button[type="submit"]');
        
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="loading"></span> Signing in...';
        
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
                resultDiv.innerHTML = '<div class="alert success">✅ Login successful! Redirecting...</div>';
                setTimeout(() => {
                    window.location.href = '/home';
                }, 1000);
            } else {
                resultDiv.innerHTML = `<div class="alert error">❌ ${result.message}</div>`;
                submitBtn.disabled = false;
                submitBtn.innerHTML = '🚀 Sign In';
            }
        } catch (error) {
            resultDiv.innerHTML = `<div class="alert error">❌ ${error.message}</div>`;
            submitBtn.disabled = false;
            submitBtn.innerHTML = '🚀 Sign In';
        }
    });
});
