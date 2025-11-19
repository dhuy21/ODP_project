document.getElementById('provisionForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const submitButton = form.querySelector('button[type="submit"]');
    const resultDiv = document.getElementById('result');
    
    // Show loading state
    submitButton.disabled = true;
    submitButton.textContent = 'Creating Infrastructure...';
    resultDiv.innerHTML = '<div class="alert info">Creating your infrastructure, please wait...</div>';
    
    const data = {
        username: form.username.value,
        password: form.password.value,
        vm_count: form.vm_count.value,
        duration: form.duration.value,
        packages: form.packages.value
    };
    
    // Store credentials and duration for terminal use
    sessionStorage.setItem('username', data.username);
    sessionStorage.setItem('password', data.password);
    sessionStorage.setItem('duration', data.duration);
    
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
            resultDiv.innerHTML = '<div class="alert success">Infrastructure created successfully! Redirecting...</div>';
            window.location.href = result.redirect;
        } else {
            submitButton.disabled = false;
            submitButton.textContent = 'Create Infrastructure';
            resultDiv.innerHTML = `
                <div class="alert error">
                    ${result.message}
                </div>
            `;
        }
    } catch (error) {
        submitButton.disabled = false;
        submitButton.textContent = 'Create Infrastructure';
        resultDiv.innerHTML = `
            <div class="alert error">
                ${error.message}
            </div>
        `;
    }
});