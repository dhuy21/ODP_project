// Admin Panel JavaScript

document.addEventListener('DOMContentLoaded', () => {
    // Smooth scroll to sections
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const target = document.querySelector(item.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                
                // Update active state
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
            }
        });
    });
    
    // Create user form
    const createUserForm = document.getElementById('createUserForm');
    if (createUserForm) {
        createUserForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            const resultDiv = document.getElementById('createUserResult');
            const submitBtn = form.querySelector('button[type="submit"]');
            
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="loading"></span> Creating...';
            
            const data = {
                username: form.username.value,
                email: form.email.value,
                password: form.password.value,
                role: form.role.value
            };
            
            try {
                const response = await fetch('/admin/user/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    resultDiv.innerHTML = '<div class="alert success">✅ User created successfully!</div>';
                    setTimeout(() => {
                        closeCreateUserModal();
                        location.reload();
                    }, 1500);
                } else {
                    resultDiv.innerHTML = `<div class="alert error">❌ ${result.message}</div>`;
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = 'Create User';
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="alert error">❌ ${error.message}</div>`;
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Create User';
            }
        });
    }
    
    // Close modal when clicking outside
    const modal = document.getElementById('createUserModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                closeCreateUserModal();
            }
        });
    }
});

function showCreateUserModal() {
    document.getElementById('createUserModal').classList.add('active');
}

function closeCreateUserModal() {
    document.getElementById('createUserModal').classList.remove('active');
    document.getElementById('createUserForm').reset();
    document.getElementById('createUserResult').innerHTML = '';
}

async function deleteUser(username) {
    if (!confirm(`Are you sure you want to delete user ${username}? This will also release their containers.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/admin/user/${username}/delete`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            alert('✅ User deleted successfully!');
            location.reload();
        } else {
            alert('❌ Error: ' + result.message);
        }
    } catch (error) {
        alert('❌ Error: ' + error.message);
    }
}

async function toggleRole(username, currentRole) {
    const newRole = currentRole === 'admin' ? 'user' : 'admin';
    
    if (!confirm(`Change ${username}'s role from ${currentRole} to ${newRole}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/admin/user/${username}/role`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({role: newRole})
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            alert('✅ Role updated successfully!');
            location.reload();
        } else {
            alert('❌ Error: ' + result.message);
        }
    } catch (error) {
        alert('❌ Error: ' + error.message);
    }
}

async function deleteReservation(reservationId, owner) {
    if (!confirm(`Delete reservation ${reservationId.substring(0, 8)}... for user ${owner}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/admin/reservation/${reservationId}/delete`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            alert('✅ Reservation deleted and containers released!');
            location.reload();
        } else {
            alert('❌ Error: ' + result.message);
        }
    } catch (error) {
        alert('❌ Error: ' + error.message);
    }
}

async function recoverPool() {
    if (!confirm('Attempt to recover the container pool?')) {
        return;
    }
    
    try {
        const response = await fetch('/admin/pool/recover', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            alert('✅ Pool recovery initiated!\n\n' + result.output);
            location.reload();
        } else {
            alert('❌ Error: ' + result.message);
        }
    } catch (error) {
        alert('❌ Error: ' + error.message);
    }
}
