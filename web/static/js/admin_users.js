// Admin Users Page JavaScript

function openAddUserModal() {
    document.getElementById('addUserModal').classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

function editUser(userId) {
    // Implementation for editing user
    console.log('Edit user:', userId);
}

async function deleteUser(userId) {
    const confirmed = await Modal.confirm({
        title: 'Delete User',
        message: 'Are you sure you want to delete this user? This action cannot be undone.',
        confirmText: 'Delete',
        cancelText: 'Cancel',
        type: 'danger',
        confirmColor: 'danger'
    });

    if (confirmed) {
        // Implementation for deleting user
        console.log('Delete user:', userId);
    }
}
