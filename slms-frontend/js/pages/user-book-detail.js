/**
 * User Book Detail Page Logic
 */

// Check authentication
if (!Auth.isAuthenticated()) {
  window.location.href = 'login.html';
}

// Page state
const bookDetailState = {
  book: null,
  bookId: null
};

/**
 * Initialize book detail page
 */
async function initBookDetail() {
  // Get book ID from URL
  const urlParams = new URLSearchParams(window.location.search);
  bookDetailState.bookId = urlParams.get('id');
  
  if (!bookDetailState.bookId) {
    document.getElementById('bookDetailContainer').innerHTML = `
      <div class="alert alert-error">
        <strong>Error:</strong> No book ID provided
      </div>
    `;
    return;
  }
  
  await loadBookDetail();
}

/**
 * Load book detail
 */
async function loadBookDetail() {
  const container = document.getElementById('bookDetailContainer');
  showLoading(container);
  
  try {
    const book = await api.getBookById(bookDetailState.bookId);
    bookDetailState.book = book;
    renderBookDetail();
  } catch (error) {
    console.error('Error loading book detail:', error);
    if (error.status === 401) {
      Auth.removeToken();
      window.location.href = 'login.html';
      return;
    }
    container.innerHTML = `
      <div class="alert alert-error">
        <strong>Error loading book:</strong> ${error.message || 'Unknown error'}
      </div>
    `;
  }
}

/**
 * Render book detail
 */
function renderBookDetail() {
  const container = document.getElementById('bookDetailContainer');
  const book = bookDetailState.book;
  
  if (!book) {
    container.innerHTML = `
      <div class="alert alert-error">
        <strong>Error:</strong> Book not found
      </div>
    `;
    return;
  }
  
  const isAvailable = book.available_copies > 0;
  
  // Extract description from enhanced_metadata if available
  const description = book.enhanced_metadata?.description || null;
  const authorsList = book.authors ? book.authors.map(a => a.full_name || a) : [];
  const publisherName = book.publisher?.name || book.publisher || null;
  
  container.innerHTML = `
    <div class="card">
      <div class="card-body">
        <div style="display: grid; grid-template-columns: 200px 1fr; gap: var(--spacing-xl);">
          <!-- Book Cover -->
          <div>
            ${book.cover_url ? 
              `<img src="${book.cover_url}" alt="${book.title}" style="width: 100%; border-radius: var(--border-radius); box-shadow: 0 4px 8px rgba(0,0,0,0.1);">` : 
              `<div style="width: 100%; aspect-ratio: 3/4; background: var(--gray-200); border-radius: var(--border-radius); display: flex; align-items: center; justify-content: center; font-size: 4rem;">📖</div>`
            }
          </div>
          
          <!-- Book Info -->
          <div>
            <h1 style="margin-bottom: var(--spacing-md);">${escapeHtml(book.title)}</h1>
            
            <div style="margin-bottom: var(--spacing-lg);">
              ${authorsList.length > 0 ? 
                `<p><strong>Authors:</strong> ${authorsList.map(a => escapeHtml(a)).join(', ')}</p>` : 
                '<p><strong>Authors:</strong> Unknown</p>'
              }
              
              ${publisherName ? `<p><strong>Publisher:</strong> ${escapeHtml(publisherName)}</p>` : ''}
              
              ${book.publication_year ? `<p><strong>Year:</strong> ${book.publication_year}</p>` : ''}
              
              ${book.edition ? `<p><strong>Edition:</strong> ${escapeHtml(book.edition)}</p>` : ''}
              
              ${book.isbn_13 ? `<p><strong>ISBN-13:</strong> ${book.isbn_13}</p>` : ''}
              ${book.isbn_10 ? `<p><strong>ISBN-10:</strong> ${book.isbn_10}</p>` : ''}
              
              <p><strong>Available Copies:</strong> 
                <span class="badge ${isAvailable ? 'badge-success' : 'badge-error'}">
                  ${book.available_copies} of ${book.total_copies}
                </span>
              </p>
            </div>
            
            <!-- Actions -->
            <div style="display: flex; gap: var(--spacing-md); margin-top: var(--spacing-xl);">
              ${isAvailable ? 
                `<button class="btn btn-primary btn-lg" onclick="borrowBook(${book.book_id})">Borrow Book</button>` :
                `<button class="btn btn-outline btn-lg" onclick="reserveBook(${book.book_id})">Reserve Book</button>`
              }
            </div>
          </div>
        </div>
        
        <!-- Description -->
        ${description ? `
          <div style="margin-top: var(--spacing-xl); padding-top: var(--spacing-xl); border-top: 1px solid var(--gray-200);">
            <h2>Description</h2>
            <p style="white-space: pre-wrap; line-height: 1.8;">${escapeHtml(description)}</p>
          </div>
        ` : ''}
        
        <!-- Enhanced Metadata (Keywords, Categories) -->
        ${book.enhanced_metadata ? `
          <div style="margin-top: var(--spacing-xl); padding-top: var(--spacing-xl); border-top: 1px solid var(--gray-200);">
            ${book.enhanced_metadata.keywords && book.enhanced_metadata.keywords.length > 0 ? `
              <div style="margin-bottom: var(--spacing-md);">
                <h4>Keywords</h4>
                <div style="display: flex; flex-wrap: wrap; gap: var(--spacing-sm);">
                  ${book.enhanced_metadata.keywords.map(kw => `<span class="badge badge-primary">${escapeHtml(kw)}</span>`).join('')}
                </div>
              </div>
            ` : ''}
            ${book.enhanced_metadata.broad_categories && book.enhanced_metadata.broad_categories.length > 0 ? `
              <div>
                <h4>Categories</h4>
                <div style="display: flex; flex-wrap: wrap; gap: var(--spacing-sm);">
                  ${book.enhanced_metadata.broad_categories.map(cat => `<span class="badge badge-default">${escapeHtml(cat)}</span>`).join('')}
                </div>
              </div>
            ` : ''}
          </div>
        ` : ''}
      </div>
    </div>
  `;
}

/**
 * Borrow a book
 */
async function borrowBook(bookId) {
  if (!confirm('Are you sure you want to borrow this book?')) {
    return;
  }
  
  try {
    const response = await api.borrowBook({ book_id: bookId });
    
    if (response.success) {
      showToast('Book borrowed successfully!', 'success');
      await loadBookDetail(); // Refresh book details
    } else if (response.reserved) {
      showToast('Book not available. Reservation created.', 'info');
      await loadBookDetail(); // Refresh book details
    } else {
      showToast('Failed to borrow book', 'error');
    }
  } catch (error) {
    console.error('Error borrowing book:', error);
    showToast('Failed to borrow book: ' + (error.message || 'Unknown error'), 'error');
  }
}

/**
 * Reserve a book
 */
async function reserveBook(bookId) {
  if (!confirm('Are you sure you want to reserve this book?')) {
    return;
  }
  
  try {
    await api.createReservation({ book_id: bookId });
    showToast('Book reserved successfully!', 'success');
    await loadBookDetail(); // Refresh book details
  } catch (error) {
    console.error('Error reserving book:', error);
    showToast('Failed to reserve book: ' + (error.message || 'Unknown error'), 'error');
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
window.borrowBook = borrowBook;
window.reserveBook = reserveBook;
window.handleLogout = handleLogout;

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initBookDetail);
} else {
  initBookDetail();
}

