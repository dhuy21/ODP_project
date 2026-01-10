// ============================================
// SHARED UTILITY FUNCTIONS
// ============================================

/**
 * Initialize entry animations for elements with animation classes
 * Supports: fade-in, fade-in-up, fade-in-left, fade-in-right, fade-in-scale, fade-in-rotate, slide-in-bottom
 */
function initEntryAnimations() {
    const elements = document.querySelectorAll(
        '.fade-in, .fade-in-up, .fade-in-left, .fade-in-right, .fade-in-scale, .fade-in-rotate, .slide-in-bottom'
    );
    
    elements.forEach((element, index) => {
        const delay = parseInt(element.dataset.delay) || (index * 100);
        
        setTimeout(() => {
            element.classList.add('animate');
        }, delay);
    });
}

