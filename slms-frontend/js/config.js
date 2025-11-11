/**
 * Configuration constants for SLMS Frontend
 */

const CONFIG = {
  // Backend API Configuration
  API_BASE_URL: 'http://127.0.0.1:8000',
  API_TIMEOUT: 10000, // 10 seconds
  
  // Pagination
  ITEMS_PER_PAGE: 20,
  
  // Auto-refresh intervals (milliseconds)
  AUTO_REFRESH_INTERVAL: 30000, // 30 seconds
  
  // Toast notification duration
  TOAST_DURATION: 3000, // 3 seconds
  
  // ISBN validation pattern
  ISBN_PATTERN: /^(\d{9}[\dXx]|\d{13})$/,
  
  // Search debounce delay
  SEARCH_DEBOUNCE_DELAY: 500, // 0.5 seconds
  
  // Status configurations
  STATUS_LABELS: {
    pending: 'Pending',
    awaiting_confirmation: 'Awaiting Confirmation',
    approved: 'Approved',
    failed: 'Failed',
    rejected: 'Rejected',
    completed: 'Completed'
  },
  
  STATUS_COLORS: {
    pending: 'warning',
    awaiting_confirmation: 'info',
    approved: 'success',
    failed: 'error',
    rejected: 'error',
    completed: 'success'
  }
};

// Freeze config to prevent modifications
Object.freeze(CONFIG);

