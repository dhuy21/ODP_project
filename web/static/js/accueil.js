// ============================================
// ACCUEIL PAGE - INTERACTIVE ANIMATIONS
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Vanta.js Waves effect
    initVantaWaves();
    
    // Initialize entry animations first
    initEntryAnimations();
    
    // Initialize all other animations
    initScrollAnimations();
    initParallaxEffects();
    initSmoothScroll();
    initFeatureCardInteractions();
});

// ========== VANTA.JS WAVES EFFECT ==========
function initVantaWaves() {
    // Wait for Vanta to be available
    if (typeof VANTA !== 'undefined' && VANTA.WAVES) {
        const vantaEffect = VANTA.WAVES({
            el: "#vanta-waves",
            mouseControls: true,
            touchControls: true,
            gyroControls: false,
            minHeight: 200.00,
            minWidth: 200.00,
            scale: 1.00,
            scaleMobile: 1.00,
            color: 0x1a6429,
            shininess: 150.00,
            waveHeight: 40.00,
            waveSpeed: 1.45,
            zoom: 0.88
        });
        
        // Store reference for cleanup if needed
        window.vantaEffect = vantaEffect;
    } else {
        // Retry if Vanta is not loaded yet
        setTimeout(initVantaWaves, 100);
    }
}

// ========== ENTRY ANIMATIONS (Page Load) ==========
function initEntryAnimations() {
    // Get all elements with animation classes
    const animatedElements = document.querySelectorAll(
        '.fade-in, .fade-in-up, .fade-in-left, .fade-in-right, .fade-in-scale, .fade-in-rotate, .slide-in-bottom'
    );
    
    // Check which elements are in viewport on page load
    const viewportHeight = window.innerHeight;
    
    animatedElements.forEach((element, index) => {
        const rect = element.getBoundingClientRect();
        const isInViewport = rect.top < viewportHeight && rect.bottom > 0;
        
        if (isInViewport) {
            // Element is in viewport, animate it with delay
            const delay = parseInt(element.dataset.delay) || (index * 100);
            
            setTimeout(() => {
                element.classList.add('animate');
            }, delay);
        }
    });
}

// ========== SCROLL ANIMATIONS ==========
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                const delay = parseInt(element.dataset.delay) || 0;
                
                setTimeout(() => {
                    element.classList.add('animate');
                }, delay);
                
                observer.unobserve(element);
            }
        });
    }, observerOptions);

    // Observe all animated elements
    document.querySelectorAll(
        '.fade-in, .fade-in-up, .fade-in-left, .fade-in-right, .fade-in-scale, .fade-in-rotate, .slide-in-bottom'
    ).forEach(el => {
        // Only observe if not already animated
        if (!el.classList.contains('animate')) {
            observer.observe(el);
        }
    });
}

// ========== PARALLAX EFFECTS ==========
function initParallaxEffects() {
    let ticking = false;
    
    window.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(() => {
                const scrolled = window.pageYOffset;
                
                // Parallax for hero particles
                const particles = document.querySelector('.hero-particles');
                if (particles) {
                    particles.style.transform = `translateY(${scrolled * 0.5}px)`;
                }
                
                // Parallax for hero content
                const heroContent = document.querySelector('.hero-content');
                if (heroContent && scrolled < window.innerHeight) {
                    heroContent.style.transform = `translateY(${scrolled * 0.3}px)`;
                    heroContent.style.opacity = 1 - (scrolled / window.innerHeight);
                }
                
                ticking = false;
            });
            ticking = true;
        }
    });
}

// ========== SMOOTH SCROLL ==========
function initSmoothScroll() {
    const scrollIndicator = document.querySelector('.scroll-indicator');
    
    if (scrollIndicator) {
        scrollIndicator.addEventListener('click', () => {
            const featuresSection = document.querySelector('.features-section');
            if (featuresSection) {
                featuresSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    }
    
    // Smooth scroll for all anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// ========== FEATURE CARD INTERACTIONS ==========
function initFeatureCardInteractions() {
    const featureCards = document.querySelectorAll('.feature-card');
    
    featureCards.forEach(card => {
        // Add mouse move tilt effect
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const rotateX = (y - centerY) / 10;
            const rotateY = (centerX - x) / 10;
            
            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-10px)`;
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
        });
        
        // Add click ripple effect
        card.addEventListener('click', (e) => {
            const ripple = document.createElement('span');
            const rect = card.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            card.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

// ========== ADD RIPPLE STYLE ==========
const style = document.createElement('style');
style.textContent = `
    .feature-card {
        position: relative;
        overflow: hidden;
    }
    
    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(5, 150, 105, 0.3);
        transform: scale(0);
        animation: rippleAnimation 0.6s ease-out;
        pointer-events: none;
    }
    
    @keyframes rippleAnimation {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ========== DELAYED ANIMATIONS ==========
function applyDelayedAnimations() {
    document.querySelectorAll('[data-delay]').forEach(element => {
        const delay = parseInt(element.dataset.delay);
        element.style.animationDelay = delay + 'ms';
        element.style.transitionDelay = delay + 'ms';
    });
}

applyDelayedAnimations();

// ========== CURSOR EFFECT (Optional enhancement) ==========
function initCursorEffect() {
    const cursor = document.createElement('div');
    cursor.classList.add('custom-cursor');
    document.body.appendChild(cursor);
    
    let mouseX = 0;
    let mouseY = 0;
    let cursorX = 0;
    let cursorY = 0;
    
    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });
    
    function animateCursor() {
        cursorX += (mouseX - cursorX) * 0.1;
        cursorY += (mouseY - cursorY) * 0.1;
        
        cursor.style.left = cursorX + 'px';
        cursor.style.top = cursorY + 'px';
        
        requestAnimationFrame(animateCursor);
    }
    
    animateCursor();
    
    // Add hover effects
    document.querySelectorAll('a, button, .feature-card').forEach(el => {
        el.addEventListener('mouseenter', () => {
            cursor.classList.add('cursor-hover');
        });
        el.addEventListener('mouseleave', () => {
            cursor.classList.remove('cursor-hover');
        });
    });
}

// Uncomment to enable custom cursor
// initCursorEffect();

// ========== PERFORMANCE OPTIMIZATION ==========
// Throttle scroll events
function throttle(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Optimize scroll animations
const optimizedScrollHandler = throttle(() => {
    // Scroll-based animations here
}, 16); // ~60fps

window.addEventListener('scroll', optimizedScrollHandler);

// ========== CONSOLE MESSAGE ==========
console.log('%c🚀 ODP Project - IaC Platform', 'color: #059669; font-size: 20px; font-weight: bold;');
console.log('%cWelcome to our modern Infrastructure as Code platform!', 'color: #718096; font-size: 14px;');

