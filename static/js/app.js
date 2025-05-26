document.addEventListener('DOMContentLoaded', function() {
    // Initialize the application
    initializeApp();
});

function initializeApp() {
    // Auto-hide flash messages after 5 seconds
    setTimeout(() => {
        const flashMessages = document.querySelectorAll('.flash-message');
        flashMessages.forEach(message => {
            message.style.transition = 'opacity 0.5s ease-out';
            message.style.opacity = '0';
            setTimeout(() => {
                if (message.parentNode) {
                    message.parentNode.removeChild(message);
                }
            }, 500);
        });
    }, 5000);

    // Initialize tooltips
    initializeTooltips();
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize responsive tables
    initializeResponsiveTables();
}

// Tooltip functionality
function initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(event) {
    const element = event.target;
    const tooltipText = element.getAttribute('data-tooltip');
    
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = tooltipText;
    tooltip.style.cssText = `
        position: absolute;
        background: #333;
        color: white;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 14px;
        z-index: 1000;
        opacity: 0;
        transition: opacity 0.3s ease;
        pointer-events: none;
    `;
    
    document.body.appendChild(tooltip);
    
    const rect = element.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.bottom + 8 + 'px';
    
    // Fade in
    setTimeout(() => {
        tooltip.style.opacity = '1';
    }, 10);
    
    element._tooltip = tooltip;
}

function hideTooltip(event) {
    const element = event.target;
    if (element._tooltip) {
        element._tooltip.style.opacity = '0';
        setTimeout(() => {
            if (element._tooltip && element._tooltip.parentNode) {
                document.body.removeChild(element._tooltip);
            }
            delete element._tooltip;
        }, 300);
    }
}

// Form validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    
    forms.forEach(form => {
        form.addEventListener('submit', validateForm);
        
        // Real-time validation
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('blur', validateField);
            input.addEventListener('input', clearFieldError);
        });
    });
}

function validateForm(event) {
    const form = event.target;
    let isValid = true;
    
    // Clear previous errors
    const errorElements = form.querySelectorAll('.field-error');
    errorElements.forEach(el => el.remove());
    
    // Validate required fields
    const requiredFields = form.querySelectorAll('[required]');
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            showFieldError(field, 'This field is required');
            isValid = false;
        }
    });
    
    // Validate email fields
    const emailFields = form.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
        if (field.value && !isValidEmail(field.value)) {
            showFieldError(field, 'Please enter a valid email address');
            isValid = false;
        }
    });
    
    // Validate number fields
    const numberFields = form.querySelectorAll('input[type="number"]');
    numberFields.forEach(field => {
        if (field.value && isNaN(field.value)) {
            showFieldError(field, 'Please enter a valid number');
            isValid = false;
        }
    });
    
    if (!isValid) {
        event.preventDefault();
        
        // Focus on first error field
        const firstError = form.querySelector('.field-error');
        if (firstError) {
            const field = firstError.previousElementSibling;
            if (field) {
                field.focus();
                field.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    }
}

function validateField(event) {
    const field = event.target;
    clearFieldError(field);
    
    if (field.hasAttribute('required') && !field.value.trim()) {
        showFieldError(field, 'This field is required');
    } else if (field.type === 'email' && field.value && !isValidEmail(field.value)) {
        showFieldError(field, 'Please enter a valid email address');
    } else if (field.type === 'number' && field.value && isNaN(field.value)) {
        showFieldError(field, 'Please enter a valid number');
    }
}

function clearFieldError(event) {
    const field = event.target;
    const errorElement = field.parentNode.querySelector('.field-error');
    if (errorElement) {
        errorElement.remove();
    }
    field.classList.remove('error');
}

function showFieldError(field, message) {
    // Remove existing error
    const existingError = field.parentNode.querySelector('.field-error');
    if (existingError) {
        existingError.remove();
    }
    
    // Add error class
    field.classList.add('error');
    
    // Create error element
    const errorElement = document.createElement('div');
    errorElement.className = 'field-error';
    errorElement.textContent = message;
    errorElement.style.cssText = `
        color: #ef4444;
        font-size: 0.875rem;
        margin-top: 0.25rem;
        display: block;
    `;
    
    // Insert after field
    field.parentNode.insertBefore(errorElement, field.nextSibling);
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Responsive tables
function initializeResponsiveTables() {
    const tables = document.querySelectorAll('table');
    
    tables.forEach(table => {
        if (!table.parentNode.classList.contains('table-responsive')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            wrapper.style.overflowX = 'auto';
            
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });
}

// Invoice-specific functions
function addInvoiceItem() {
    const container = document.getElementById('invoice-items');
    const template = container.querySelector('.invoice-item');
    const newItem = template.cloneNode(true);
    
    // Clear input values
    newItem.querySelectorAll('input').forEach(input => {
        if (input.name === 'quantity[]') {
            input.value = '1';
        } else {
            input.value = '';
        }
    });
    
    // Add remove functionality
    const removeBtn = newItem.querySelector('.remove-item');
    if (removeBtn) {
        removeBtn.addEventListener('click', function() {
            removeInvoiceItem(this);
        });
    }
    
    container.appendChild(newItem);
    
    // Focus on description field
    const descriptionField = newItem.querySelector('input[name="description[]"]');
    if (descriptionField) {
        descriptionField.focus();
    }
    
    // Add animation
    newItem.style.opacity = '0';
    newItem.style.transform = 'translateY(20px)';
    newItem.offsetHeight; // Force reflow
    newItem.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    newItem.style.opacity = '1';
    newItem.style.transform = 'translateY(0)';
}

function removeInvoiceItem(button) {
    const container = document.getElementById('invoice-items');
    const item = button.closest('.invoice-item');
    
    if (container.children.length > 1) {
        // Add animation
        item.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        item.style.opacity = '0';
        item.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            if (item.parentNode) {
                item.parentNode.removeChild(item);
                calculateInvoiceTotals();
            }
        }, 300);
    } else {
        showNotification('You must have at least one item in the invoice', 'warning');
    }
}

function calculateLineTotal(input) {
    const row = input.closest('.invoice-item');
    const quantity = parseFloat(row.querySelector('input[name="quantity[]"]').value) || 0;
    const rate = parseFloat(row.querySelector('input[name="rate[]"]').value) || 0;
    const total = quantity * rate;
    
    const totalField = row.querySelector('.line-total');
    if (totalField) {
        totalField.value = ' + total.toFixed(2);
    }
    
    calculateInvoiceTotals();
}

function calculateInvoiceTotals() {
    let subtotal = 0;
    
    document.querySelectorAll('.invoice-item').forEach(row => {
        const quantity = parseFloat(row.querySelector('input[name="quantity[]"]').value) || 0;
        const rate = parseFloat(row.querySelector('input[name="rate[]"]').value) || 0;
        subtotal += quantity * rate;
    });
    
    const taxRate = parseFloat(document.getElementById('tax_rate')?.value) || 0;
    const taxAmount = subtotal * (taxRate / 100);
    const total = subtotal + taxAmount;
    
    // Update display
    const subtotalElement = document.getElementById('subtotal');
    const taxAmountElement = document.getElementById('tax-amount');
    const totalElement = document.getElementById('total');
    
    if (subtotalElement) subtotalElement.textContent = ' + subtotal.toFixed(2);
    if (taxAmountElement) taxAmountElement.textContent = ' + taxAmount.toFixed(2);
    if (totalElement) totalElement.textContent = ' + total.toFixed(2);
}

// Notification system
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()" class="notification-close">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-width: 300px;
        max-width: 500px;
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
    `;
    
    // Set colors based on type
    const colors = {
        success: { bg: '#d1fae5', color: '#065f46', border: '#a7f3d0' },
        error: { bg: '#fee2e2', color: '#991b1b', border: '#fca5a5' },
        warning: { bg: '#fef3c7', color: '#92400e', border: '#fde68a' },
        info: { bg: '#dbeafe', color: '#1e40af', border: '#93c5fd' }
    };
    
    const typeColors = colors[type] || colors.info;
    notification.style.backgroundColor = typeColors.bg;
    notification.style.color = typeColors.color;
    notification.style.border = `1px solid ${typeColors.border}`;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    }, 10);
    
    // Auto remove
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, duration);
}

// Loading states
function showLoading(element, text = 'Loading...') {
    const originalContent = element.innerHTML;
    element.setAttribute('data-original-content', originalContent);
    element.innerHTML = `
        <span class="spinner"></span>
        <span style="margin-left: 8px;">${text}</span>
    `;
    element.disabled = true;
    element.classList.add('loading');
}

function hideLoading(element) {
    const originalContent = element.getAttribute('data-original-content');
    if (originalContent) {
        element.innerHTML = originalContent;
        element.removeAttribute('data-original-content');
    }
    element.disabled = false;
    element.classList.remove('loading');
}

// AJAX helpers
function makeRequest(url, options = {}) {
    const defaults = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'same-origin'
    };
    
    const config = { ...defaults, ...options };
    
    return fetch(url, config)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error('Request failed:', error);
            showNotification('An error occurred. Please try again.', 'error');
            throw error;
        });
}

// Invoice status update
function updateInvoiceStatus(invoiceId, status) {
    const button = event.target;
    showLoading(button, 'Updating...');
    
    makeRequest(`/invoice/${invoiceId}/status`, {
        method: 'POST',
        body: JSON.stringify({ status: status })
    })
    .then(data => {
        if (data.success) {
            showNotification('Invoice status updated successfully!', 'success');
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            throw new Error(data.message || 'Update failed');
        }
    })
    .catch(error => {
        showNotification('Failed to update invoice status', 'error');
    })
    .finally(() => {
        hideLoading(button);
    });
}

// Copy to clipboard
function copyToClipboard(text, successMessage = 'Copied to clipboard!') {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text)
            .then(() => showNotification(successMessage, 'success'))
            .catch(() => fallbackCopyToClipboard(text, successMessage));
    } else {
        fallbackCopyToClipboard(text, successMessage);
    }
}

function fallbackCopyToClipboard(text, successMessage) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showNotification(successMessage, 'success');
    } catch (err) {
        showNotification('Failed to copy to clipboard', 'error');
    }
    
    document.body.removeChild(textArea);
}

// Format currency
function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

// Format date
function formatDate(date, options = {}) {
    const defaults = {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    };
    
    const formatOptions = { ...defaults, ...options };
    return new Intl.DateTimeFormat('en-US', formatOptions).format(date);
}

// Debounce function
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
    };
}

// Search functionality
function initializeSearch() {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(performSearch, 300));
    }
}

function performSearch(event) {
    const query = event.target.value.toLowerCase();
    const searchableElements = document.querySelectorAll('[data-searchable]');
    
    searchableElements.forEach(element => {
        const searchText = element.getAttribute('data-searchable').toLowerCase();
        const row = element.closest('tr') || element.closest('.card') || element;
        
        if (searchText.includes(query)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
    
    // Show "no results" message if needed
    const visibleResults = Array.from(searchableElements).filter(el => {
        const row = el.closest('tr') || el.closest('.card') || el;
        return row.style.display !== 'none';
    });
    
    const noResultsMessage = document.getElementById('no-results');
    if (noResultsMessage) {
        noResultsMessage.style.display = visibleResults.length === 0 ? 'block' : 'none';
    }
}

// Keyboard shortcuts
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(event) {
        // Ctrl/Cmd + K for search
        if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
            event.preventDefault();
            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Ctrl/Cmd + N for new invoice
        if ((event.ctrlKey || event.metaKey) && event.key === 'n') {
            event.preventDefault();
            const newInvoiceLink = document.querySelector('a[href*="create-invoice"]');
            if (newInvoiceLink) {
                window.location.href = newInvoiceLink.href;
            }
        }
        
        // Escape to close modals/notifications
        if (event.key === 'Escape') {
            const modals = document.querySelectorAll('.modal:not([style*="display: none"])');
            const notifications = document.querySelectorAll('.notification');
            
            modals.forEach(modal => modal.style.display = 'none');
            notifications.forEach(notification => notification.remove());
        }
    });
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeSearch();
    initializeKeyboardShortcuts();
    
    // Add smooth scrolling to anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
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
    
    // Add click handlers for copy buttons
    document.querySelectorAll('[data-copy]').forEach(button => {
        button.addEventListener('click', function() {
            const textToCopy = this.getAttribute('data-copy');
            copyToClipboard(textToCopy);
        });
    });
    
    // Initialize invoice calculations if on create/edit page
    if (document.getElementById('invoice-items')) {
        document.addEventListener('input', function(event) {
            if (event.target.matches('input[name="quantity[]"], input[name="rate[]"], #tax_rate')) {
                if (event.target.matches('input[name="quantity[]"], input[name="rate[]"]')) {
                    calculateLineTotal(event.target);
                } else {
                    calculateInvoiceTotals();
                }
            }
        });
        
        // Initial calculation
        calculateInvoiceTotals();
    }
});