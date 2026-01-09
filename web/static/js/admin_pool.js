// Admin Pool Page JavaScript

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
    
    // Recover Pool button
    const recoverBtn = document.querySelector('.btn-warning[data-action="recover"]');
    if (recoverBtn) {
        recoverBtn.addEventListener('click', () => {
            recoverPool();
        });
        
        // Add loading animation
        recoverBtn.addEventListener('click', function() {
            const icon = this.querySelector('i');
            if (icon) {
                icon.classList.add('fa-spin');
                setTimeout(() => {
                    if (icon) icon.classList.remove('fa-spin');
                }, 3000);
            }
        });
    }
    
    // Refresh button
    const refreshBtn = document.querySelector('.btn-primary[data-action="refresh"]');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            const icon = refreshBtn.querySelector('i');
            if (icon) {
                icon.classList.add('fa-spin');
            }
            setTimeout(() => {
                location.reload();
            }, 300);
        });
    }
    
    // Container card interactions
    document.querySelectorAll('.container-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            const icon = this.querySelector('.container-icon');
            if (icon) {
                icon.style.transform = 'scale(1.1) rotate(5deg)';
            }
        });
        
        card.addEventListener('mouseleave', function() {
            const icon = this.querySelector('.container-icon');
            if (icon) {
                icon.style.transform = 'scale(1) rotate(0deg)';
            }
        });
    });
    
    // Add tooltips for container status
    document.querySelectorAll('.container-card').forEach(card => {
        const status = card.classList[1]; // Get status class
        if (status) {
            card.setAttribute('title', `Container status: ${status}`);
        }
    });
});
