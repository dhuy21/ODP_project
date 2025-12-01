document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('provisionForm');
    
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitButton = form.querySelector('button[type="submit"]');
            const resultDiv = document.getElementById('result');
            
            // Show loading state
            submitButton.disabled = true;
            submitButton.textContent = 'Creating Reservation...';
            resultDiv.innerHTML = '<div class="alert info">Creating your reservation, please wait...</div>';
            
            const data = {
                password: form.password.value,
                vm_count: form.vm_count.value,
                duration: form.duration.value,
                packages: form.packages.value
            };
            
            // Store password for terminal use
            sessionStorage.setItem('password', data.password);
            
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
                    resultDiv.innerHTML = '<div class="alert success">Reservation created successfully! Redirecting...</div>';
                    setTimeout(() => {
                        window.location.href = result.redirect;
                    }, 1000);
                } else {
                    submitButton.disabled = false;
                    submitButton.textContent = 'Create Reservation';
                    resultDiv.innerHTML = `
                        <div class="alert error">
                            ${result.message}
                        </div>
                    `;
                }
            } catch (error) {
                submitButton.disabled = false;
                submitButton.textContent = 'Create Reservation';
                resultDiv.innerHTML = `
                    <div class="alert error">
                        ${error.message}
                    </div>
                `;
            }
        });
    }
});