/**
 * Admin Authentication Utilities
 * Checks if user is authenticated and has admin/librarian role
 */

/**
 * Check if current user is admin or librarian
 */
function isAdmin() {
  if (!Auth.isAuthenticated()) {
    return false;
  }
  
  const userStr = localStorage.getItem('user');
  if (!userStr) {
    return false;
  }
  
  try {
    const user = JSON.parse(userStr);
    return user.role === 'admin' || user.role === 'librarian';
  } catch (error) {
    console.error('Error parsing user data:', error);
    return false;
  }
}

/**
 * Require admin access - redirects to login if not admin
 */
function requireAdmin() {
  if (!Auth.isAuthenticated()) {
    // Not authenticated - redirect to login
    window.location.href = 'login.html';
    return false;
  }
  
  if (!isAdmin()) {
    // Not admin - redirect to user dashboard
    showToast('Access denied. Admin access required.', 'error');
    setTimeout(() => {
      window.location.href = 'user-dashboard.html';
    }, 1500);
    return false;
  }
  
  return true;
}

/**
 * Initialize admin page - call this at the top of admin page scripts
 */
function initAdminPage() {
  // Check authentication and admin role
  if (!requireAdmin()) {
    return false;
  }
  
  // Load user info
  const userStr = localStorage.getItem('user');
  if (userStr) {
    try {
      const user = JSON.parse(userStr);
      // You can use this to display admin name, etc.
      return user;
    } catch (error) {
      console.error('Error parsing user data:', error);
    }
  }
  
  return true;
}

/**
 * Handle admin logout
 */
function handleAdminLogout() {
  if (confirm('Are you sure you want to logout?')) {
    Auth.removeToken();
    localStorage.removeItem('user');
    window.location.href = 'login.html';
  }
}

// Make functions available globally
window.handleAdminLogout = handleAdminLogout;
window.isAdmin = isAdmin;
window.requireAdmin = requireAdmin;
window.initAdminPage = initAdminPage;

