/**
 * Book Detail Page Logic
 * Displays complete information about a single book
 */

// Check admin authentication
if (!initAdminPage()) {
  // Redirect will happen in initAdminPage if not authorized
}

// Page state
const bookDetailState = {
  bookId: null,
  book: null
};

/**
 * Initialize book detail page
 */
async function initBookDetail() {
  // Check admin authentication first
  if (!requireAdmin()) {
    // Redirect will happen in requireAdmin if not authorized
    return;
  }
  
  console.log('Admin authenticated, loading book details...');
  console.log('Initializing book detail page...');
  
  // Get book ID from URL
  bookDetailState.bookId = getURLParameter('id');
  
  if (!bookDetailState.bookId) {
    showError(new Error('No book ID provided'));
    displayError('Book ID is missing. Please select a book from the catalogue.');
    return;
  }
  
  // Load book details
  await loadBookDetail();
  
  console.log('Book detail initialized');
}

/**
 * Load book details from backend
 */
async function loadBookDetail() {
  const container = document.getElementById('bookDetailContainer');
  showLoading(container);
  
  try {
    const book = await api.getBookById(bookDetailState.bookId);
    bookDetailState.book = book;
    
    console.log('Loaded book:', book);
    
    // Render book details
    renderBookDetail(book);
    
  } catch (error) {
    console.error('Error loading book:', error);
    displayError(`Failed to load book: ${error.message}`);
  }
}

/**
 * Render book detail
 */
function renderBookDetail(book) {
  const container = document.getElementById('bookDetailContainer');
  
  // Prepare data
  const authors = book.authors && book.authors.length > 0
    ? book.authors.map(a => a.full_name).join(', ')
    : 'Unknown Author';
  const publisher = book.publisher ? book.publisher.name : 'Unknown Publisher';
  const year = book.publication_year || 'N/A';
  const edition = book.edition || 'N/A';
  const isbn10 = book.isbn_10 || 'N/A';
  const isbn13 = book.isbn_13 || 'N/A';
  const available = book.available_copies || 0;
  const total = book.total_copies || 0;
  const enhanced = book.enhanced_metadata || {};
  
  container.innerHTML = `
    <!-- Main Book Info Card -->
    <div class="card">
      <div class="card-body">
        <div style="display: grid; grid-template-columns: 200px 1fr; gap: var(--spacing-2xl);">
          <!-- Cover Image -->
          <div>
            <div style="background: var(--gray-100); width: 200px; height: 280px; display: flex; align-items: center; justify-content: center; border-radius: var(--radius-lg); box-shadow: var(--shadow-md);">
              ${book.cover_url 
                ? `<img src="${book.cover_url}" alt="Book cover" style="max-width: 100%; max-height: 100%; border-radius: var(--radius-lg);">`
                : '<span style="font-size: 5rem;">📖</span>'}
            </div>
          </div>
          
          <!-- Book Info -->
          <div>
            <h1 style="margin-bottom: var(--spacing-sm);">${book.title}</h1>
            <p class="text-muted" style="font-size: var(--font-size-lg); margin-bottom: var(--spacing-md);">
              by ${authors}
            </p>
            <p class="text-muted" style="margin-bottom: var(--spacing-lg);">
              ${publisher} • ${year} ${edition !== 'N/A' ? `• ${edition}` : ''}
            </p>
            
            <!-- Availability -->
            <div style="background: ${available > 0 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)'}; padding: var(--spacing-md); border-radius: var(--radius-md); margin-bottom: var(--spacing-lg);">
              <p style="margin: 0;">
                <span class="font-semibold">Availability:</span>
                <span class="${available > 0 ? 'text-success' : 'text-error'}" style="font-size: var(--font-size-xl); font-weight: 700;">
                  ${available} of ${total} copies available
                </span>
              </p>
            </div>
            
            <!-- ISBN Info -->
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--spacing-md); margin-bottom: var(--spacing-lg);">
              <div>
                <p class="text-muted" style="font-size: var(--font-size-sm); margin-bottom: var(--spacing-xs);">ISBN-10</p>
                <p class="font-semibold">${isbn10}</p>
              </div>
              <div>
                <p class="text-muted" style="font-size: var(--font-size-sm); margin-bottom: var(--spacing-xs);">ISBN-13</p>
                <p class="font-semibold">${isbn13}</p>
              </div>
            </div>
            
            <!-- Action Buttons -->
            <div class="btn-group">
              ${available > 0 
                ? '<button class="btn btn-primary" disabled>Borrow (Coming Soon)</button>'
                : '<button class="btn btn-outline" disabled>Reserve (Coming Soon)</button>'}
              <button class="btn btn-outline" onclick="window.print()">Print Details</button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Description -->
    ${enhanced.description ? `
    <div class="card mt-3">
      <div class="card-header">
        <h2>Description</h2>
      </div>
      <div class="card-body">
        <p style="line-height: 1.8; white-space: pre-wrap;">${enhanced.description}</p>
      </div>
    </div>
    ` : ''}
    
    <!-- Enhanced Metadata -->
    ${enhanced.keywords || enhanced.broad_categories || enhanced.sub_disciplines ? `
    <div class="card mt-3">
      <div class="card-header">
        <h2>Enhanced Metadata</h2>
        <span class="badge badge-info">AI-Generated</span>
      </div>
      <div class="card-body">
        ${enhanced.keywords && enhanced.keywords.length > 0 ? `
          <div style="margin-bottom: var(--spacing-lg);">
            <h4 style="font-size: var(--font-size-base); margin-bottom: var(--spacing-sm);">Keywords</h4>
            <div style="display: flex; flex-wrap: wrap; gap: var(--spacing-sm);">
              ${enhanced.keywords.map(keyword => `
                <span class="badge badge-primary">${keyword}</span>
              `).join('')}
            </div>
          </div>
        ` : ''}
        
        ${enhanced.broad_categories && enhanced.broad_categories.length > 0 ? `
          <div style="margin-bottom: var(--spacing-lg);">
            <h4 style="font-size: var(--font-size-base); margin-bottom: var(--spacing-sm);">Categories</h4>
            <div style="display: flex; flex-wrap: wrap; gap: var(--spacing-sm);">
              ${enhanced.broad_categories.map(cat => `
                <span class="badge badge-default">${cat}</span>
              `).join('')}
            </div>
          </div>
        ` : ''}
        
        ${enhanced.sub_disciplines && enhanced.sub_disciplines.length > 0 ? `
          <div>
            <h4 style="font-size: var(--font-size-base); margin-bottom: var(--spacing-sm);">Disciplines</h4>
            <div style="display: flex; flex-wrap: wrap; gap: var(--spacing-sm);">
              ${enhanced.sub_disciplines.map(disc => `
                <span class="badge badge-default">${disc}</span>
              `).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    </div>
    ` : ''}
    
    <!-- Metadata -->
    <div class="card mt-3">
      <div class="card-header">
        <h2>Catalogue Information</h2>
      </div>
      <div class="card-body">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--spacing-lg);">
          <div>
            <p class="text-muted font-semibold">Book ID</p>
            <p>${book.book_id}</p>
          </div>
          <div>
            <p class="text-muted font-semibold">Publisher</p>
            <p>${publisher}</p>
          </div>
          <div>
            <p class="text-muted font-semibold">Publication Year</p>
            <p>${year}</p>
          </div>
          <div>
            <p class="text-muted font-semibold">Edition</p>
            <p>${edition}</p>
          </div>
          <div>
            <p class="text-muted font-semibold">Total Copies</p>
            <p>${total}</p>
          </div>
          <div>
            <p class="text-muted font-semibold">Available Copies</p>
            <p class="${available > 0 ? 'text-success' : 'text-error'} font-semibold">${available}</p>
          </div>
          <div>
            <p class="text-muted font-semibold">Added</p>
            <p>${formatDate(book.created_at)}</p>
          </div>
          ${book.updated_at ? `
          <div>
            <p class="text-muted font-semibold">Last Updated</p>
            <p>${formatDate(book.updated_at)}</p>
          </div>
          ` : ''}
        </div>
      </div>
    </div>
  `;
  
  // Update page title
  document.title = `${book.title} - SLMS`;
}

/**
 * Display error message
 */
function displayError(message) {
  const container = document.getElementById('bookDetailContainer');
  container.innerHTML = `
    <div class="alert alert-error">
      <strong>Error:</strong> ${message}
    </div>
    <div style="text-align: center; margin-top: var(--spacing-lg);">
      <a href="catalogue.html" class="btn btn-primary">Back to Catalogue</a>
    </div>
  `;
}

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initBookDetail);
} else {
  initBookDetail();
}

