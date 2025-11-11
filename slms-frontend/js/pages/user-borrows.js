/**
 * User Borrows Page Logic
 */

// Check authentication
if (!Auth.isAuthenticated()) {
  window.location.href = 'login.html';
}

// Page state
const borrowsState = {
  currentTab: 'active',
  activeBorrows: [],
  borrowHistory: []
};

/**
 * Initialize borrows page
 */
async function initBorrows() {
  await loadActiveBorrows();
}

/**
 * Switch between tabs
 */
function switchTab(tab) {
  borrowsState.currentTab = tab;
  
  // Update tab buttons
  document.getElementById('activeTab').classList.toggle('active', tab === 'active');
  document.getElementById('historyTab').classList.toggle('active', tab === 'history');
  
  // Update tab styling
  const activeTab = document.getElementById('activeTab');
  const historyTab = document.getElementById('historyTab');
  
  if (tab === 'active') {
    activeTab.style.borderBottomColor = 'var(--primary-color)';
    historyTab.style.borderBottomColor = 'transparent';
    document.getElementById('activeBorrowsSection').style.display = 'block';
    document.getElementById('historySection').style.display = 'none';
  } else {
    activeTab.style.borderBottomColor = 'transparent';
    historyTab.style.borderBottomColor = 'var(--primary-color)';
    document.getElementById('activeBorrowsSection').style.display = 'none';
    document.getElementById('historySection').style.display = 'block';
  }
  
  // Load data for selected tab
  if (tab === 'active') {
    loadActiveBorrows();
  } else {
    loadBorrowHistory();
  }
}

/**
 * Load active borrows
 */
async function loadActiveBorrows() {
  const container = document.getElementById('activeBorrowsContainer');
  showLoading(container);
  
  try {
    const response = await api.getActiveBorrows();
    borrowsState.activeBorrows = response.items || [];
    renderActiveBorrows();
  } catch (error) {
    console.error('Error loading active borrows:', error);
    if (error.status === 401) {
      Auth.removeToken();
      window.location.href = 'login.html';
      return;
    }
    container.innerHTML = `
      <div class="alert alert-error">
        <strong>Error loading borrows:</strong> ${error.message || 'Unknown error'}
      </div>
    `;
  }
}

/**
 * Render active borrows
 */
function renderActiveBorrows() {
  const container = document.getElementById('activeBorrowsContainer');
  
  if (borrowsState.activeBorrows.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📖</div>
        <p class="empty-state-title">No Active Borrows</p>
        <p class="empty-state-description">You don't have any books borrowed at the moment.</p>
        <a href="user-browse.html" class="btn btn-primary">Browse Books</a>
      </div>
    `;
    return;
  }
  
  container.innerHTML = `
    <div class="table-container">
      <table class="table">
        <thead>
          <tr>
            <th>Book Title</th>
            <th>Borrowed Date</th>
            <th>Due Date</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${borrowsState.activeBorrows.map(borrow => `
            <tr class="${borrow.is_overdue ? 'table-row-error' : ''}">
              <td><strong>${escapeHtml(borrow.book_title)}</strong></td>
              <td><small>${formatDateTime(borrow.borrow_date)}</small></td>
              <td><small>${formatDateTime(borrow.due_date)}</small></td>
              <td>
                ${borrow.is_overdue ? 
                  '<span class="badge badge-error">Overdue</span>' : 
                  '<span class="badge badge-success">Active</span>'
                }
              </td>
              <td>
                <div class="table-actions">
                  <button class="btn btn-sm btn-primary" onclick="renewBorrow(${borrow.borrow_id})">Renew</button>
                  <button class="btn btn-sm btn-outline" onclick="returnBorrow(${borrow.borrow_id})">Return</button>
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

/**
 * Load borrow history
 */
async function loadBorrowHistory() {
  const container = document.getElementById('historyContainer');
  showLoading(container);
  
  try {
    const response = await api.getBorrowHistory();
    borrowsState.borrowHistory = response.items || [];
    renderBorrowHistory();
  } catch (error) {
    console.error('Error loading borrow history:', error);
    if (error.status === 401) {
      Auth.removeToken();
      window.location.href = 'login.html';
      return;
    }
    container.innerHTML = `
      <div class="alert alert-error">
        <strong>Error loading history:</strong> ${error.message || 'Unknown error'}
      </div>
    `;
  }
}

/**
 * Render borrow history
 */
function renderBorrowHistory() {
  const container = document.getElementById('historyContainer');
  
  if (borrowsState.borrowHistory.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📚</div>
        <p class="empty-state-title">No Borrow History</p>
        <p class="empty-state-description">You haven't borrowed any books yet.</p>
        <a href="user-browse.html" class="btn btn-primary">Browse Books</a>
      </div>
    `;
    return;
  }
  
  container.innerHTML = `
    <div class="table-container">
      <table class="table">
        <thead>
          <tr>
            <th>Book Title</th>
            <th>Borrowed Date</th>
            <th>Due Date</th>
            <th>Returned Date</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${borrowsState.borrowHistory.map(borrow => `
            <tr>
              <td><strong>${escapeHtml(borrow.book_title)}</strong></td>
              <td><small>${formatDateTime(borrow.borrow_date)}</small></td>
              <td><small>${formatDateTime(borrow.due_date)}</small></td>
              <td><small>${borrow.return_date ? formatDateTime(borrow.return_date) : 'Not returned'}</small></td>
              <td>
                ${borrow.return_date ? 
                  '<span class="badge badge-success">Returned</span>' : 
                  '<span class="badge badge-warning">Not Returned</span>'
                }
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

/**
 * Return a borrowed book
 */
async function returnBorrow(borrowId) {
  if (!confirm('Are you sure you want to return this book?')) {
    return;
  }
  
  try {
    const response = await api.returnBook(borrowId);
    
    if (response.success) {
      if (response.fine_created) {
        showToast(`Book returned successfully. Fine of Rs ${Number(response.fine_amount || 0).toFixed(2)} created due to overdue.`, 'warning');
      } else {
        showToast('Book returned successfully!', 'success');
      }
      await loadActiveBorrows();
    } else {
      showToast('Failed to return book', 'error');
    }
  } catch (error) {
    console.error('Error returning book:', error);
    showToast('Failed to return book: ' + (error.message || 'Unknown error'), 'error');
  }
}

/**
 * Renew a borrowed book
 */
async function renewBorrow(borrowId) {
  if (!confirm('Are you sure you want to renew this book? (14 days from today)')) {
    return;
  }
  
  try {
    const response = await api.renewBook(borrowId, {});
    
    if (response.success) {
      showToast(`Book renewed successfully! New due date: ${formatDateTime(response.new_due_date)}`, 'success');
      await loadActiveBorrows();
    } else {
      showToast('Failed to renew book', 'error');
    }
  } catch (error) {
    console.error('Error renewing book:', error);
    showToast('Failed to renew book: ' + (error.message || 'Unknown error'), 'error');
  }
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
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

// Make functions available globally
window.switchTab = switchTab;
window.loadActiveBorrows = loadActiveBorrows;
window.loadBorrowHistory = loadBorrowHistory;
window.returnBorrow = returnBorrow;
window.renewBorrow = renewBorrow;
window.handleLogout = handleLogout;

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initBorrows);
} else {
  initBorrows();
}

