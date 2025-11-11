/**
 * User Fines Page Logic
 */

// Check authentication
if (!Auth.isAuthenticated()) {
  window.location.href = 'login.html';
}

// Page state
const finesState = {
  fines: [],
  totalAmount: 0
};

/**
 * Initialize fines page
 */
async function initFines() {
  await loadFines();
}

/**
 * Load fines
 */
async function loadFines() {
  const container = document.getElementById('finesContainer');
  showLoading(container);
  
  try {
    const response = await api.getFines();
    finesState.fines = response.items || [];
    // Ensure totalAmount is always a number (API may return Decimal as string)
    finesState.totalAmount = parseFloat(response.total_amount || 0) || 0;
    renderFines();
    updateSummary();
  } catch (error) {
    console.error('Error loading fines:', error);
    if (error.status === 401) {
      Auth.removeToken();
      window.location.href = 'login.html';
      return;
    }
    container.innerHTML = `
      <div class="alert alert-error">
        <strong>Error loading fines:</strong> ${error.message || 'Unknown error'}
      </div>
    `;
  }
}

/**
 * Update summary
 */
function updateSummary() {
  const pendingFines = finesState.fines.filter(f => f.status === 'pending');
  const paidFines = finesState.fines.filter(f => f.status === 'paid');
  
  // Ensure totalAmount is a number before calling toFixed
  const totalAmount = Number(finesState.totalAmount) || 0;
  document.getElementById('totalFines').textContent = `Rs ${totalAmount.toFixed(2)}`;
  document.getElementById('pendingCount').textContent = pendingFines.length;
  document.getElementById('paidCount').textContent = paidFines.length;
}

/**
 * Render fines
 */
function renderFines() {
  const container = document.getElementById('finesContainer');
  
  if (finesState.fines.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">💰</div>
        <p class="empty-state-title">No Fines</p>
        <p class="empty-state-description">You don't have any fines at the moment.</p>
      </div>
    `;
    return;
  }
  
  // Separate pending and paid fines
  const pendingFines = finesState.fines.filter(f => f.status === 'pending');
  const paidFines = finesState.fines.filter(f => f.status === 'paid');
  
  let html = '';
  
  if (pendingFines.length > 0) {
    html += `
      <h3 style="margin-bottom: var(--spacing-md);">Pending Fines</h3>
      <div class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th>Book Title</th>
              <th>Issue Date</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${pendingFines.map(fine => `
              <tr>
                <td><strong>${escapeHtml(fine.book_title)}</strong></td>
                <td><small>${formatDateTime(fine.issue_date)}</small></td>
                <td><strong>Rs ${Number(fine.amount || 0).toFixed(2)}</strong></td>
                <td><span class="badge badge-error">Pending</span></td>
                <td>
                  <button class="btn btn-sm btn-primary" onclick="payFine(${fine.fine_id})">Pay Fine</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }
  
  if (paidFines.length > 0) {
    html += `
      <h3 style="margin-top: var(--spacing-xl); margin-bottom: var(--spacing-md);">Paid Fines</h3>
      <div class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th>Book Title</th>
              <th>Issue Date</th>
              <th>Paid Date</th>
              <th>Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${paidFines.map(fine => `
              <tr>
                <td><strong>${escapeHtml(fine.book_title)}</strong></td>
                <td><small>${formatDateTime(fine.issue_date)}</small></td>
                <td><small>${fine.paid_date ? formatDateTime(fine.paid_date) : 'N/A'}</small></td>
                <td><strong>Rs ${Number(fine.amount || 0).toFixed(2)}</strong></td>
                <td><span class="badge badge-success">Paid</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }
  
  container.innerHTML = html;
}

/**
 * Pay a fine
 */
async function payFine(fineId) {
  const fine = finesState.fines.find(f => f.fine_id === fineId);
  if (!fine) {
    showToast('Fine not found', 'error');
    return;
  }
  
  if (!confirm(`Are you sure you want to pay the fine of Rs ${Number(fine.amount || 0).toFixed(2)} for "${fine.book_title}"?`)) {
    return;
  }
  
  try {
    const response = await api.payFine(fineId);
    
    if (response.success) {
      showToast('Fine paid successfully!', 'success');
      await loadFines();
    } else {
      showToast('Failed to pay fine', 'error');
    }
  } catch (error) {
    console.error('Error paying fine:', error);
    showToast('Failed to pay fine: ' + (error.message || 'Unknown error'), 'error');
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
window.loadFines = loadFines;
window.payFine = payFine;
window.handleLogout = handleLogout;

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initFines);
} else {
  initFines();
}

