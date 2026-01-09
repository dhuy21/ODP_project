// Admin Users Page JavaScript

document.addEventListener('DOMContentLoaded', () => {
    // Animate elements on scroll
    const animateOnScroll = () => {
        const elements = document.querySelectorAll('.fade-in-up');
        
        elements.forEach(element => {
            const elementTop = element.getBoundingClientRect().top;
            const elementVisible = 150;
            
            if (elementTop < window.innerHeight - elementVisible) {
                const delay = element.getAttribute('data-delay') || 0;
                setTimeout(() => {
                    element.classList.add('animate');
                }, delay);
            }
        });
    };
    
    // Initial animation
    animateOnScroll();
    window.addEventListener('scroll', animateOnScroll);
    
    // Create User buttons
    document.querySelectorAll('[data-action="create-user"]').forEach(btn => {
        btn.addEventListener('click', () => {
            showCreateUserModal();
        });
        
        // Add ripple effect
        btn.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            this.appendChild(ripple);
            
            setTimeout(() => ripple.remove(), 600);
        });
    });
    
    // Close modal button
    const closeModalBtn = document.querySelector('[data-action="close-modal"]');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            closeCreateUserModal();
        });
    }
    
    // Toggle role buttons
    document.querySelectorAll('[data-action="toggle-role"]').forEach(btn => {
        btn.addEventListener('click', () => {
            const username = btn.getAttribute('data-username');
            const currentRole = btn.getAttribute('data-role');
            toggleRole(username, currentRole);
        });
        
        // Add loading state
        btn.addEventListener('click', function() {
            const icon = this.querySelector('i');
            if (icon) {
                icon.classList.add('fa-spin');
                setTimeout(() => icon.classList.remove('fa-spin'), 2000);
            }
        });
    });
    
    // Delete user buttons
    document.querySelectorAll('[data-action="delete-user"]').forEach(btn => {
        btn.addEventListener('click', () => {
            const username = btn.getAttribute('data-username');
            deleteUser(username);
        });
    });
    
    // Add hover animations to table rows
    document.querySelectorAll('table tbody tr').forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transition = 'all 0.2s ease';
        });
    });
});
