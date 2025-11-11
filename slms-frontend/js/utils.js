/**
 * Utility Functions for SLMS Frontend
 * Common helpers used throughout the application
 */

// ============================================================================
// TOAST NOTIFICATIONS
// ============================================================================

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type: 'success', 'error', 'warning', 'info'
 */
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${getToastIcon(type)}</span>
    <span class="toast-message">${message}</span>
    <button class="toast-close" onclick="this.parentElement.remove()">×</button>
  `;
  
  document.body.appendChild(toast);
  
  // Trigger animation
  setTimeout(() => toast.classList.add('show'), 10);
  
  // Auto-remove after duration
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, CONFIG.TOAST_DURATION);
}

function getToastIcon(type) {
  const icons = {
    success: '✓',
    error: '✗',
    warning: '⚠',
    info: 'ℹ'
  };
  return icons[type] || icons.info;
}

// ============================================================================
// LOADING STATES
// ============================================================================

/**
 * Show loading spinner in a container
 */
function showLoading(container) {
  const element = typeof container === 'string' 
    ? document.getElementById(container) 
    : container;
    
  if (element) {
    element.innerHTML = `
      <div class="loading-spinner">
        <div class="spinner"></div>
        <p>Loading...</p>
      </div>
    `;
  }
}

/**
 * Hide loading spinner
 */
function hideLoading(container) {
  const element = typeof container === 'string'
    ? document.getElementById(container)
    : container;
    
  if (element) {
    const spinner = element.querySelector('.loading-spinner');
    if (spinner) spinner.remove();
  }
}

// ============================================================================
// VALIDATION
// ============================================================================

/**
 * Validate ISBN format (10 or 13 digits)
 */
function validateISBN(isbn) {
  if (!isbn) return false;
  const cleaned = isbn.replace(/[-\s]/g, '').toUpperCase();
  return CONFIG.ISBN_PATTERN.test(cleaned);
}

/**
 * Normalize ISBN (remove hyphens and spaces)
 */
function normalizeISBN(isbn) {
  if (!isbn) return '';
  return isbn.replace(/[-\s]/g, '').toUpperCase();
}

/**
 * Validate required field
 */
function validateRequired(value) {
  return value !== null && value !== undefined && value.toString().trim() !== '';
}

/**
 * Validate email format
 */
function validateEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
}

// ============================================================================
// FORMATTING
// ============================================================================

/**
 * Format date to readable string
 */
function formatDate(dateString, options = {}) {
  if (!dateString) return 'N/A';
  
  const date = new Date(dateString);
  const defaultOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    ...options
  };
  
  return date.toLocaleDateString('en-US', defaultOptions);
}

/**
 * Format datetime to readable string
 */
function formatDateTime(dateString) {
  if (!dateString) return 'N/A';
  
  const date = new Date(dateString);
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

/**
 * Get relative time (e.g., "2 hours ago")
 */
function getRelativeTime(dateString) {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  
  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
  if (diffHour < 24) return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
  if (diffDay < 7) return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
  
  return formatDate(dateString);
}

/**
 * Truncate text to specified length
 */
function truncate(text, length = 50) {
  if (!text) return '';
  return text.length > length ? text.substring(0, length) + '...' : text;
}

/**
 * Format number with commas
 */
function formatNumber(num) {
  if (num === null || num === undefined) return '0';
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// ============================================================================
// STATUS BADGES
// ============================================================================

/**
 * Get status badge HTML
 */
function getStatusBadge(status) {
  const label = CONFIG.STATUS_LABELS[status] || status;
  const color = CONFIG.STATUS_COLORS[status] || 'default';
  return `<span class="badge badge-${color}">${label}</span>`;
}

// ============================================================================
// URL HELPERS
// ============================================================================

/**
 * Get URL parameter by name
 */
function getURLParameter(name) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(name);
}

/**
 * Set URL parameter without reload
 */
function setURLParameter(name, value) {
  const url = new URL(window.location);
  url.searchParams.set(name, value);
  window.history.pushState({}, '', url);
}

/**
 * Navigate to page with parameters
 */
function navigateTo(page, params = {}) {
  const url = new URL(page, window.location.origin);
  Object.keys(params).forEach(key => {
    url.searchParams.set(key, params[key]);
  });
  window.location.href = url.toString();
}

// ============================================================================
// DEBOUNCE
// ============================================================================

/**
 * Debounce function execution
 */
function debounce(func, wait = CONFIG.SEARCH_DEBOUNCE_DELAY) {
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

// ============================================================================
// ARRAY HELPERS
// ============================================================================

/**
 * Paginate array
 */
function paginateArray(array, page, pageSize) {
  const start = (page - 1) * pageSize;
  const end = start + pageSize;
  return array.slice(start, end);
}

/**
 * Sort array by key
 */
function sortByKey(array, key, descending = false) {
  return array.sort((a, b) => {
    const aVal = a[key];
    const bVal = b[key];
    
    if (aVal < bVal) return descending ? 1 : -1;
    if (aVal > bVal) return descending ? -1 : 1;
    return 0;
  });
}

// ============================================================================
// LOCAL STORAGE
// ============================================================================

/**
 * Save to localStorage with JSON encoding
 */
function saveToStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (error) {
    console.error('Error saving to localStorage:', error);
    return false;
  }
}

/**
 * Load from localStorage with JSON decoding
 */
function loadFromStorage(key, defaultValue = null) {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch (error) {
    console.error('Error loading from localStorage:', error);
    return defaultValue;
  }
}

/**
 * Remove from localStorage
 */
function removeFromStorage(key) {
  try {
    localStorage.removeItem(key);
    return true;
  } catch (error) {
    console.error('Error removing from localStorage:', error);
    return false;
  }
}

// ============================================================================
// ERROR HANDLING
// ============================================================================

/**
 * Display error message
 */
function showError(error, fallbackMessage = 'An error occurred') {
  const message = error.message || fallbackMessage;
  showToast(message, 'error');
  console.error('Error:', error);
}

/**
 * Handle API error
 */
function handleAPIError(error, customMessage) {
  if (customMessage) {
    showError(new Error(customMessage));
  } else {
    showError(error);
  }
}

