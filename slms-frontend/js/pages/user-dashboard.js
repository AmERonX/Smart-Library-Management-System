/**
 * User Dashboard Page Logic
 */

// Check authentication on page load
if (!Auth.isAuthenticated()) {
  window.location.href = 'login.html';
}

/**
 * Initialize dashboard
 */
async function initDashboard() {
  try {
    // Get user info
    const userStr = localStorage.getItem('user');
    if (userStr) {
      const user = JSON.parse(userStr);
      document.getElementById('userName').textContent = user.username;
    }
    
    // Load dashboard data
    await loadDashboardData();
    
  } catch (error) {
    console.error('Error initializing dashboard:', error);
    if (error.status === 401) {
      // Token expired or invalid
      Auth.removeToken();
      window.location.href = 'login.html';
    }
  }
}

/**
 * Load dashboard data
 */
async function loadDashboardData() {
  try {
    const summary = await api.getUserSummary();
    
    // Update stats
    document.getElementById('activeBorrows').textContent = summary.active_borrows;
    document.getElementById('activeReservations').textContent = summary.active_reservations;
    document.getElementById('pendingFines').textContent = summary.pending_fines;
    document.getElementById('overdueBooks').textContent = summary.overdue_books;
    
    // Load recent borrows
    await loadRecentBorrows();
    
  } catch (error) {
    console.error('Error loading dashboard data:', error);
    showToast('Failed to load dashboard data', 'error');
  }
}

/**
 * Load recent borrows
 */
async function loadRecentBorrows() {
  const container = document.getElementById('recentBorrows');
  
  try {
    const response = await api.getActiveBorrows();
    const borrows = response.items.slice(0, 5); // Show only first 5
    
    if (borrows.length === 0) {
      container.innerHTML = '<p class="text-muted">No active borrows</p>';
      return;
    }
    
    container.innerHTML = `
      <table class="table">
        <thead>
          <tr>
            <th>Book</th>
            <th>Borrowed</th>
            <th>Due Date</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${borrows.map(borrow => `
            <tr>
              <td>${borrow.book_title}</td>
              <td><small>${formatDateTime(borrow.borrow_date)}</small></td>
              <td><small>${formatDateTime(borrow.due_date)}</small></td>
              <td>${borrow.is_overdue ? '<span class="badge badge-error">Overdue</span>' : '<span class="badge badge-success">Active</span>'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
    
  } catch (error) {
    console.error('Error loading recent borrows:', error);
    container.innerHTML = '<p class="text-muted">Failed to load borrows</p>';
  }
}

/**
 * Handle logout
 */
function handleLogout() {
  if (confirm('Are you sure you want to logout?')) {
    Auth.removeToken();
    localStorage.removeItem('user');
    window.location.href = 'login.html';
  }
}

// Make handleLogout available globally
window.handleLogout = handleLogout;

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDashboard);
} else {
  initDashboard();
}

