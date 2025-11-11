/**
 * Dashboard Page Logic
 * Loads and displays dashboard statistics and recent pending entries
 */

// Dashboard state
const dashboardState = {
  stats: {
    totalBooks: 0,
    pendingCount: 0,
    todayCount: 0,
    availableCopies: 0
  },
  recentPending: [],
  autoRefreshInterval: null
};

/**
 * Initialize dashboard on page load
 */
async function initDashboard() {
  console.log('Initializing dashboard...');
  
  // Check admin authentication first
  if (!requireAdmin()) {
    // Redirect will happen in requireAdmin if not authorized
    return;
  }
  
  // Check backend connectivity
  try {
    const health = await api.checkHealth();
    console.log('Backend health:', health);
  } catch (error) {
    console.error('Health check failed:', error);
    showToast('Unable to connect to backend. Please ensure the server is running at ' + CONFIG.API_BASE_URL, 'error');
    // Don't return - try to load data anyway in case it's a transient error
  }
  
  // Load dashboard data
  await loadDashboardStats();
  await loadRecentPending();
  
  // Setup auto-refresh
  setupAutoRefresh();
}

/**
 * Load dashboard statistics
 */
async function loadDashboardStats() {
  try {
    console.log('Loading dashboard stats...');
    
    // Get total books count (using pagination to get just the count)
    try {
      const booksResponse = await api.getBooks({ page: 1, page_size: 1 });
      console.log('Books response:', booksResponse);
      dashboardState.stats.totalBooks = booksResponse.total || 0;
      document.getElementById('totalBooks').textContent = formatNumber(dashboardState.stats.totalBooks);
    } catch (error) {
      console.error('Error fetching books:', error);
      document.getElementById('totalBooks').textContent = '-';
      showToast('Failed to load books count: ' + (error.message || 'Unknown error'), 'error');
    }
    
    // Get pending count
    try {
      const pendingResponse = await api.getPending();
      console.log('Pending response:', pendingResponse);
      const pendingList = Array.isArray(pendingResponse) ? pendingResponse : [];
      dashboardState.stats.pendingCount = pendingList.filter(p => 
        p.status === 'awaiting_confirmation' || p.status === 'failed'
      ).length;
      document.getElementById('pendingCount').textContent = formatNumber(dashboardState.stats.pendingCount);
      
      // Calculate books added today
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      dashboardState.stats.todayCount = pendingList.filter(p => {
        const createdDate = new Date(p.created_at);
        createdDate.setHours(0, 0, 0, 0);
        return createdDate.getTime() === today.getTime() && p.status === 'completed';
      }).length;
      document.getElementById('todayCount').textContent = formatNumber(dashboardState.stats.todayCount);
    } catch (error) {
      console.error('Error fetching pending:', error);
      document.getElementById('pendingCount').textContent = '-';
      document.getElementById('todayCount').textContent = '0';
      showToast('Failed to load pending count: ' + (error.message || 'Unknown error'), 'error');
    }
    
    // Get more accurate available copies count
    try {
      const allBooks = await api.getBooks({ page: 1, page_size: 100 }); // Get first 100 for estimate
      const totalAvailable = allBooks.items.reduce((sum, book) => sum + (book.available_copies || 0), 0);
      // Extrapolate if we have more books
      if (allBooks.total > 100) {
        dashboardState.stats.availableCopies = Math.round((totalAvailable / allBooks.items.length) * allBooks.total);
      } else {
        dashboardState.stats.availableCopies = totalAvailable;
      }
      document.getElementById('availableCopies').textContent = formatNumber(dashboardState.stats.availableCopies);
    } catch (error) {
      console.error('Error fetching available copies:', error);
      // Fallback to 0 if can't get books
      document.getElementById('availableCopies').textContent = '0';
    }
    
    console.log('Dashboard stats loaded:', dashboardState.stats);
  } catch (error) {
    console.error('Error loading dashboard stats:', error);
    showError(error, 'Failed to load dashboard statistics');
  }
}

/**
 * Load recent pending entries
 */
async function loadRecentPending() {
  const container = document.getElementById('recentPending');
  
  try {
    console.log('Loading recent pending entries...');
    const pendingList = await api.getPending();
    console.log('Pending list received:', pendingList);
    
    // Filter and sort to get recent entries
    const recentEntries = (Array.isArray(pendingList) ? pendingList : [])
      .filter(p => p.status === 'awaiting_confirmation' || p.status === 'failed')
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      .slice(0, 5); // Get top 5
    
    dashboardState.recentPending = recentEntries;
    
    // Render table
    if (recentEntries.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📭</div>
          <p class="empty-state-title">No Pending Entries</p>
          <p class="empty-state-description">All books have been processed! Add a new book to get started.</p>
          <a href="add-book.html" class="btn btn-primary">Add Book</a>
        </div>
      `;
    } else {
      container.innerHTML = `
        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Title</th>
                <th>ISBN</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${recentEntries.map(entry => `
                <tr>
                  <td><strong>#${entry.id}</strong></td>
                  <td>${escapeHtml(truncate(entry.title || 'Untitled', 40))}</td>
                  <td>${entry.isbn_13 || entry.isbn_10 || entry.isbn || 'N/A'}</td>
                  <td>${getStatusBadge(entry.status)}</td>
                  <td><small>${getRelativeTime(entry.created_at)}</small></td>
                  <td>
                    <div class="table-actions">
                      <a href="pending.html?highlight=${entry.id}" class="btn btn-sm btn-outline">View</a>
                    </div>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
        <div style="text-align: center; margin-top: var(--spacing-lg);">
          <a href="pending.html" class="btn btn-outline">View All Pending Entries</a>
        </div>
      `;
    }
    
    console.log('Recent pending loaded:', recentEntries.length, 'entries');
  } catch (error) {
    console.error('Error loading recent pending:', error);
    console.error('Error details:', {
      message: error.message,
      status: error.status,
      data: error.data,
      stack: error.stack
    });
    container.innerHTML = `
      <div class="alert alert-error">
        <strong>Error loading pending entries:</strong> ${error.message || 'Unknown error'}
        <br><small>Status: ${error.status || 'N/A'}</small>
        <br><small>Check browser console (F12) for more details.</small>
      </div>
    `;
  }
}

// Helper function to escape HTML
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Setup auto-refresh interval
 */
function setupAutoRefresh() {
  // Clear any existing interval
  if (dashboardState.autoRefreshInterval) {
    clearInterval(dashboardState.autoRefreshInterval);
  }
  
  // Refresh every 30 seconds
  dashboardState.autoRefreshInterval = setInterval(async () => {
    console.log('Auto-refreshing dashboard...');
    await loadDashboardStats();
    await loadRecentPending();
  }, CONFIG.AUTO_REFRESH_INTERVAL);
  
  console.log('Auto-refresh enabled (every 30s)');
}

/**
 * Cleanup on page unload
 */
window.addEventListener('beforeunload', () => {
  if (dashboardState.autoRefreshInterval) {
    clearInterval(dashboardState.autoRefreshInterval);
  }
});

// Initialize dashboard when DOM is ready
// Wait for auth-admin.js to load first
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    // Small delay to ensure all scripts are loaded
    setTimeout(initDashboard, 100);
  });
} else {
  // DOM already loaded, wait a bit for scripts
  setTimeout(initDashboard, 100);
}

