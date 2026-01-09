// Admin Reservations Page JavaScript

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
    
    // Delete reservation buttons
    document.querySelectorAll('[data-action="delete-reservation"]').forEach(btn => {
        btn.addEventListener('click', () => {
            const reservationId = btn.getAttribute('data-reservation-id');
            const owner = btn.getAttribute('data-owner');
            deleteReservation(reservationId, owner);
        });
        
        // Add loading state
        btn.addEventListener('click', function() {
            const icon = this.querySelector('i');
            if (icon) {
                icon.classList.add('fa-spin');
                setTimeout(() => {
                    if (icon) icon.classList.remove('fa-spin');
                }, 2000);
            }
        });
    });
    
    // Add hover animations to table rows
    document.querySelectorAll('table tbody tr').forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transition = 'all 0.2s ease';
        });
    });
    
    // Animate status badges
    document.querySelectorAll('.badge-status').forEach(badge => {
        if (badge.classList.contains('badge-success')) {
            const icon = badge.querySelector('i');
            if (icon) {
                setInterval(() => {
                    icon.style.opacity = icon.style.opacity === '0.5' ? '1' : '0.5';
                }, 1000);
            }
        }
    });
});
