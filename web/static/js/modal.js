// ============================================
// MODERN MODAL SYSTEM - CONFIRM DIALOGS
// ============================================

class ModalSystem {
    constructor() {
        this.activeModal = null;
    }

    confirm(options) {
        return new Promise((resolve) => {
            const {
                title = 'Confirm Action',
                message = 'Are you sure you want to proceed?',
                confirmText = 'Confirm',
                cancelText = 'Cancel',
                type = 'warning',
                confirmColor = 'danger'
            } = options;

            // Create modal overlay
            const overlay = document.createElement('div');
            overlay.className = 'modal-overlay';
            
            // Create modal
            const modal = document.createElement('div');
            modal.className = 'modal-dialog';
            
            // Icon based on type
            const icons = {
                warning: 'fa-exclamation-triangle',
                danger: 'fa-exclamation-circle',
                info: 'fa-info-circle',
                question: 'fa-question-circle'
            };

            modal.innerHTML = `
                <div class="modal-header">
                    <div class="modal-icon modal-icon-${type}">
                        <i class="fas ${icons[type] || icons.warning}"></i>
                    </div>
                    <h3 class="modal-title">${title}</h3>
                </div>
                <div class="modal-body">
                    <p>${message}</p>
                </div>
                <div class="modal-footer">
                    <button class="btn-modal btn-modal-cancel" data-action="cancel">
                        ${cancelText}
                    </button>
                    <button class="btn-modal btn-modal-${confirmColor}" data-action="confirm">
                        ${confirmText}
                    </button>
                </div>
            `;

            overlay.appendChild(modal);
            document.body.appendChild(overlay);

            // Show animation
            setTimeout(() => {
                overlay.classList.add('show');
            }, 10);

            // Handle button clicks
            const handleAction = (action) => {
                overlay.classList.remove('show');
                setTimeout(() => {
                    document.body.removeChild(overlay);
                    resolve(action === 'confirm');
                }, 300);
            };

            modal.querySelectorAll('[data-action]').forEach(btn => {
                btn.addEventListener('click', () => {
                    handleAction(btn.dataset.action);
                });
            });

            // Close on overlay click
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    handleAction('cancel');
                }
            });

            // Close on Escape key
            const handleEscape = (e) => {
                if (e.key === 'Escape') {
                    handleAction('cancel');
                    document.removeEventListener('keydown', handleEscape);
                }
            };
            document.addEventListener('keydown', handleEscape);

            this.activeModal = modal;
        });
    }

    alert(options) {
        return new Promise((resolve) => {
            const {
                title = 'Alert',
                message = '',
                buttonText = 'OK',
                type = 'info'
            } = options;

            const overlay = document.createElement('div');
            overlay.className = 'modal-overlay';
            
            const modal = document.createElement('div');
            modal.className = 'modal-dialog';
            
            const icons = {
                success: 'fa-check-circle',
                error: 'fa-exclamation-circle',
                warning: 'fa-exclamation-triangle',
                info: 'fa-info-circle'
            };

            modal.innerHTML = `
                <div class="modal-header">
                    <div class="modal-icon modal-icon-${type}">
                        <i class="fas ${icons[type] || icons.info}"></i>
                    </div>
                    <h3 class="modal-title">${title}</h3>
                </div>
                <div class="modal-body">
                    <p>${message}</p>
                </div>
                <div class="modal-footer">
                    <button class="btn-modal btn-modal-primary" data-action="ok">
                        ${buttonText}
                    </button>
                </div>
            `;

            overlay.appendChild(modal);
            document.body.appendChild(overlay);

            setTimeout(() => {
                overlay.classList.add('show');
            }, 10);

            const handleClose = () => {
                overlay.classList.remove('show');
                setTimeout(() => {
                    document.body.removeChild(overlay);
                    resolve();
                }, 300);
            };

            modal.querySelector('[data-action="ok"]').addEventListener('click', handleClose);
            
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    handleClose();
                }
            });

            const handleEscape = (e) => {
                if (e.key === 'Escape') {
                    handleClose();
                    document.removeEventListener('keydown', handleEscape);
                }
            };
            document.addEventListener('keydown', handleEscape);
        });
    }
}

// Initialize global modal system
const Modal = new ModalSystem();

// Export for use in other scripts
window.Modal = Modal;

// Convenience functions
window.showConfirm = (message, title = 'Confirm Action') => {
    return Modal.confirm({ message, title });
};

window.showAlert = (message, title = 'Alert', type = 'info') => {
    return Modal.alert({ message, title, type });
};

