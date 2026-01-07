// ============================================
// RESERVATION HISTORY - INTERACTIVE JAVASCRIPT
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initEntryAnimations();
});

// ========== ENTRY ANIMATIONS ==========
function initEntryAnimations() {
    const elements = document.querySelectorAll('.fade-in, .fade-in-up');
    
    elements.forEach((element, index) => {
        const delay = parseInt(element.dataset.delay) || (index * 100);
        
        setTimeout(() => {
            element.classList.add('animate');
        }, delay);
    });
}

