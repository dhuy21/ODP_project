// Admin Overview Page JavaScript

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
    
    // Animate on scroll
    window.addEventListener('scroll', animateOnScroll);
    
    // Immediate animation for elements in viewport
    const elementsInView = document.querySelectorAll('.fade-in-up');
    elementsInView.forEach(element => {
        const elementTop = element.getBoundingClientRect().top;
        if (elementTop < window.innerHeight) {
            const delay = element.getAttribute('data-delay') || 0;
            setTimeout(() => {
                element.classList.add('animate');
            }, parseInt(delay));
        }
    });
    
    // Add hover effect to activity rows
    document.querySelectorAll('.activity-row').forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(4px)';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.transform = 'translateX(0)';
        });
    });
});
