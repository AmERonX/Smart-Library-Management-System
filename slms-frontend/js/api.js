/**
 * API Client for SLMS Backend
 * Handles all HTTP requests to the FastAPI backend
 */

class APIClient {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  /**
   * Generic request handler
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    // Prepare headers
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    
    // Prepare config - ensure body is properly set
    const config = {
      method: options.method || 'GET',
      headers: headers,
    };
    
    // Only add body for methods that support it
    if (options.body && ['POST', 'PUT', 'PATCH'].includes(config.method)) {
      // If body is already a string (JSON.stringify), use it directly
      // Otherwise, stringify it
      config.body = typeof options.body === 'string' ? options.body : JSON.stringify(options.body);
    }
    
    // Add any other options (like credentials, cache, etc.)
    if (options.credentials) config.credentials = options.credentials;
    if (options.cache) config.cache = options.cache;
    if (options.mode) config.mode = options.mode;

    try {
      // Log request details (don't log full response object as it's not serializable)
      console.log(`[API] ${config.method} ${url}`, {
        headers: Object.fromEntries(Object.entries(config.headers || {})),
        hasBody: !!config.body
      });
      
      const response = await fetch(url, config);
      console.log(`[API] Response: ${response.status} ${response.statusText} for ${config.method} ${url}`);
      
      // Try to parse JSON response
      let data;
      try {
        const text = await response.text();
        data = text ? JSON.parse(text) : {};
        if (response.ok && Object.keys(data).length > 0) {
          console.log(`[API] Response data (first 200 chars):`, JSON.stringify(data).substring(0, 200));
        }
      } catch (parseError) {
        console.error(`[API] Failed to parse response as JSON:`, parseError);
        // If parsing fails, create error object
        data = { detail: `Server returned non-JSON response: ${response.statusText}` };
      }
      
      if (!response.ok) {
        // Extract error message from response
        // FastAPI returns validation errors as array in detail field
        let errorMsg = '';
        if (Array.isArray(data.detail)) {
          // Format FastAPI validation errors (Pydantic validation errors)
          errorMsg = data.detail.map(err => {
            const field = err.loc && err.loc.length > 1 ? err.loc.slice(1).join('.') : (err.loc && err.loc[0] ? err.loc[0] : 'field');
            const msg = err.msg || err.message || 'validation error';
            const type = err.type || '';
            return `${field}: ${msg}${type ? ` (${type})` : ''}`;
          }).join('; ');
        } else if (typeof data.detail === 'string') {
          errorMsg = data.detail;
        } else if (data.detail && typeof data.detail === 'object') {
          // Handle nested error objects
          errorMsg = JSON.stringify(data.detail);
        } else if (data.message) {
          errorMsg = data.message;
        } else if (data.error) {
          errorMsg = data.error;
        } else {
          errorMsg = `HTTP ${response.status}: ${response.statusText}`;
        }
        
        // If error message is still empty, provide a default
        if (!errorMsg || errorMsg.trim() === '') {
          errorMsg = `Request failed with status ${response.status}`;
        }
        
        const error = new Error(errorMsg);
        error.status = response.status;
        error.data = data;
        throw error;
      }
      
      return data;
    } catch (error) {
      // If it's already our error object, re-throw it
      if (error.status) {
        throw error;
      }
      // Network or other errors
      console.error('API Error:', error);
      throw new Error(`Network error: ${error.message}`);
    }
  }

  // ============================================================================
  // HEALTH & STATUS
  // ============================================================================

  async checkHealth() {
    return this.request('/health');
  }

  async getRoot() {
    return this.request('/');
  }

  // ============================================================================
  // CATALOGUE MANAGEMENT
  // ============================================================================

  /**
   * Fetch metadata without creating a pending entry (preview only)
   * POST /catalogue/fetch-metadata
   */
  async fetchMetadata(data) {
    return this.request('/catalogue/fetch-metadata', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Add a new book to pending catalogue
   * POST /catalogue/add
   */
  async addBook(data) {
    return this.request('/catalogue/add', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Get all pending catalogue entries
   * GET /catalogue/pending
   */
  async getPending() {
    return this.request('/catalogue/pending');
  }

  /**
   * Get a specific pending entry by ID
   * GET /catalogue/pending/{id}
   */
  async getPendingById(id) {
    return this.request(`/catalogue/pending/${id}`);
  }

  /**
   * Update a pending entry
   * PATCH /catalogue/pending/{id}
   */
  async updatePending(id, data) {
    return this.request(`/catalogue/pending/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  /**
   * Confirm (approve/reject) book metadata
   * POST /catalogue/confirm/{id}
   */
  async confirmMetadata(id, data) {
    return this.request(`/catalogue/confirm/${id}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Insert approved book into main catalogue
   * POST /catalogue/insert/{id}
   */
  async insertBook(id) {
    return this.request(`/catalogue/insert/${id}`, {
      method: 'POST',
    });
  }

  /**
   * Get audit logs for a pending entry
   * GET /catalogue/audit/{id}
   */
  async getAuditLogs(id) {
    return this.request(`/catalogue/audit/${id}`);
  }

  // ============================================================================
  // BOOKS CATALOGUE
  // ============================================================================

  /**
   * Get books with filters and pagination
   * GET /books
   */
  async getBooks(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const endpoint = queryString ? `/books?${queryString}` : '/books';
    return this.request(endpoint);
  }

  /**
   * Get a specific book by ID
   * GET /books/{id}
   */
  async getBookById(id) {
    return this.request(`/books/${id}`);
  }

  // ============================================================================
  // SEMANTIC SEARCH
  // ============================================================================

  /**
   * Perform semantic search
   * POST /search/semantic
   */
  async semanticSearch(data) {
    return this.request('/search/semantic', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ============================================================================
  // AUTHENTICATION
  // ============================================================================

  /**
   * Register a new user
   * POST /auth/register
   */
  async register(data) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Login user
   * POST /auth/login
   */
  async login(data) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ============================================================================
  // USER ENDPOINTS (require authentication)
  // ============================================================================

  /**
   * Get current user profile
   * GET /users/me
   */
  async getCurrentUser() {
    return this.request('/users/me');
  }

  /**
   * Get user dashboard summary
   * GET /users/me/summary
   */
  async getUserSummary() {
    return this.request('/users/me/summary');
  }

  /**
   * Borrow a book
   * POST /users/borrows
   */
  async borrowBook(data) {
    return this.request('/users/borrows', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Get active borrows
   * GET /users/borrows/active
   */
  async getActiveBorrows() {
    return this.request('/users/borrows/active');
  }

  /**
   * Get borrow history
   * GET /users/borrows/history
   */
  async getBorrowHistory() {
    return this.request('/users/borrows/history');
  }

  /**
   * Return a book
   * POST /users/borrows/{id}/return
   */
  async returnBook(borrowId) {
    return this.request(`/users/borrows/${borrowId}/return`, {
      method: 'POST',
    });
  }

  /**
   * Renew a book
   * POST /users/borrows/{id}/renew
   */
  async renewBook(borrowId, data) {
    return this.request(`/users/borrows/${borrowId}/renew`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Create a reservation
   * POST /users/reservations
   */
  async createReservation(data) {
    return this.request('/users/reservations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Get active reservations
   * GET /users/reservations/active
   */
  async getActiveReservations() {
    return this.request('/users/reservations/active');
  }

  /**
   * Cancel a reservation
   * DELETE /users/reservations/{id}
   */
  async cancelReservation(reservationId) {
    return this.request(`/users/reservations/${reservationId}`, {
      method: 'DELETE',
    });
  }

  /**
   * Get fines
   * GET /users/fines
   */
  async getFines() {
    return this.request('/users/fines');
  }

  /**
   * Pay a fine
   * POST /users/fines/{id}/pay
   */
  async payFine(fineId) {
    return this.request(`/users/fines/${fineId}/pay`, {
      method: 'POST',
    });
  }
}

// Create global API instance
const api = new APIClient(CONFIG.API_BASE_URL);

// Authentication helper functions
const Auth = {
  /**
   * Store authentication token
   */
  setToken(token) {
    localStorage.setItem('auth_token', token);
  },

  /**
   * Get authentication token
   */
  getToken() {
    return localStorage.getItem('auth_token');
  },

  /**
   * Remove authentication token
   */
  removeToken() {
    localStorage.removeItem('auth_token');
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated() {
    return !!this.getToken();
  },

  /**
   * Get authorization header
   */
  getAuthHeader() {
    const token = this.getToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }
};

// Update API client to include auth token in requests
const originalRequest = api.request.bind(api);
api.request = function(endpoint, options = {}) {
  const authHeader = Auth.getAuthHeader();
  options.headers = {
    ...options.headers,
    ...authHeader,
  };
  return originalRequest(endpoint, options);
};

