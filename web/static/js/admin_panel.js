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
                    Notification.success('User created successfully!', 3000);
                    setTimeout(() => {
                        closeCreateUserModal();
                        location.reload();
                    }, 1500);
                } else {
                    Notification.error(result.message || 'Failed to create user');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = 'Create User';
                }
            } catch (error) {
                Notification.error('Network error: ' + error.message);
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
    const confirmed = await Modal.confirm({
        title: 'Delete User',
        message: `Are you sure you want to delete user "${username}"? This will also release their containers. This action cannot be undone.`,
        confirmText: 'Delete',
        cancelText: 'Cancel',
        type: 'danger',
        confirmColor: 'danger'
    });

    if (!confirmed) {
        return;
    }
    
    try {
        const response = await fetch(`/admin/user/${username}/delete`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            Notification.success('User deleted successfully!', 3000);
            setTimeout(() => {
            location.reload();
            }, 1500);
        } else {
            Notification.error(result.message || 'Failed to delete user');
        }
    } catch (error) {
        Notification.error('Network error: ' + error.message);
    }
}

async function toggleRole(username, currentRole) {
    const newRole = currentRole === 'admin' ? 'user' : 'admin';
    
    const confirmed = await Modal.confirm({
        title: 'Change User Role',
        message: `Change ${username}'s role from ${currentRole.toUpperCase()} to ${newRole.toUpperCase()}?`,
        confirmText: 'Change',
        cancelText: 'Cancel',
        type: 'info',
        confirmColor: 'primary'
    });

    if (!confirmed) {
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
            Notification.success('Role updated successfully!', 3000);
            setTimeout(() => {
            location.reload();
            }, 1500);
        } else {
            Notification.error(result.message || 'Failed to update role');
        }
    } catch (error) {
        Notification.error('Network error: ' + error.message);
    }
}

async function deleteReservation(reservationId, owner) {
    const confirmed = await Modal.confirm({
        title: 'Delete Reservation',
        message: `Delete reservation ${reservationId.substring(0, 8)}... for user "${owner}"? This will also release the containers.`,
        confirmText: 'Delete',
        cancelText: 'Cancel',
        type: 'warning',
        confirmColor: 'danger'
    });

    if (!confirmed) {
        return;
    }
    
    try {
        const response = await fetch(`/admin/reservation/${reservationId}/delete`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            Notification.success('Reservation deleted and containers released!', 3000);
            setTimeout(() => {
            location.reload();
            }, 1500);
        } else {
            Notification.error(result.message || 'Failed to delete reservation');
        }
    } catch (error) {
        Notification.error('Network error: ' + error.message);
    }
}

async function recoverPool() {
    const confirmed = await Modal.confirm({
        title: 'Recover Container Pool',
        message: 'Attempt to recover the container pool? This will check and restore any missing containers.',
        confirmText: 'Recover',
        cancelText: 'Cancel',
        type: 'warning',
        confirmColor: 'warning'
    });

    if (!confirmed) {
        return;
    }
    
    try {
        const response = await fetch('/admin/pool/recover', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            const output = result.output || 'Pool recovery initiated successfully.';
            await Modal.alert({
                title: 'Pool Recovery',
                message: output,
                type: 'success',
                buttonText: 'OK'
            });
            location.reload();
        } else {
            Notification.error(result.message || 'Failed to recover pool');
        }
    } catch (error) {
        Notification.error('Network error: ' + error.message);
    }
}
