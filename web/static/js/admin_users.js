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

function deleteUser(userId) {
    if (confirm('Are you sure you want to delete this user?')) {
        // Implementation for deleting user
        console.log('Delete user:', userId);
    }
}
