/**
 * User Reservations Page Logic
 */

// Check authentication
if (!Auth.isAuthenticated()) {
  window.location.href = 'login.html';
}

// Page state
const reservationsState = {
  reservations: []
};

/**
 * Initialize reservations page
 */
async function initReservations() {
  await loadReservations();
}

/**
 * Load reservations
 */
async function loadReservations() {
  const container = document.getElementById('reservationsContainer');
  showLoading(container);
  
  try {
    const response = await api.getActiveReservations();
    reservationsState.reservations = response.items || [];
    renderReservations();
  } catch (error) {
    console.error('Error loading reservations:', error);
    if (error.status === 401) {
      Auth.removeToken();
      window.location.href = 'login.html';
      return;
    }
    container.innerHTML = `
      <div class="alert alert-error">
        <strong>Error loading reservations:</strong> ${error.message || 'Unknown error'}
      </div>
    `;
  }
}

/**
 * Render reservations
 */
function renderReservations() {
  const container = document.getElementById('reservationsContainer');
  
  if (reservationsState.reservations.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📌</div>
        <p class="empty-state-title">No Active Reservations</p>
        <p class="empty-state-description">You don't have any book reservations at the moment.</p>
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
            <th>Reservation Date</th>
            <th>Expiry Date</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${reservationsState.reservations.map(reservation => `
            <tr>
              <td><strong>${escapeHtml(reservation.book_title)}</strong></td>
              <td><small>${formatDateTime(reservation.reservation_date)}</small></td>
              <td><small>${reservation.expiry_date ? formatDateTime(reservation.expiry_date) : 'N/A'}</small></td>
              <td>
                <span class="badge badge-${reservation.status === 'active' ? 'success' : 'warning'}">
                  ${reservation.status === 'active' ? 'Active' : reservation.status}
                </span>
              </td>
              <td>
                <div class="table-actions">
                  <a href="user-book-detail.html?id=${reservation.book_id}" class="btn btn-sm btn-outline">View Book</a>
                  <button class="btn btn-sm btn-outline" onclick="cancelReservation(${reservation.reservation_id})">Cancel</button>
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
 * Cancel a reservation
 */
async function cancelReservation(reservationId) {
  if (!confirm('Are you sure you want to cancel this reservation?')) {
    return;
  }
  
  try {
    await api.cancelReservation(reservationId);
    showToast('Reservation cancelled successfully!', 'success');
    await loadReservations();
  } catch (error) {
    console.error('Error cancelling reservation:', error);
    showToast('Failed to cancel reservation: ' + (error.message || 'Unknown error'), 'error');
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
window.loadReservations = loadReservations;
window.cancelReservation = cancelReservation;
window.handleLogout = handleLogout;

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initReservations);
} else {
  initReservations();
}

