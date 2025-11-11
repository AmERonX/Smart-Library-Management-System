/**
 * Books Catalogue Page Logic
 * Handles browsing and searching all books in the catalogue
 */

// Check admin authentication
if (!initAdminPage()) {
  // Redirect will happen in initAdminPage if not authorized
}

// Page state
const catalogueState = {
  books: [],
  currentPage: 1,
  pageSize: 20,
  totalBooks: 0,
  viewMode: 'grid', // 'grid' or 'list'
  filters: {
    q: '',
    author: '',
    publisher: '',
    year: '',
    sort: 'created_desc'
  }
};

/**
 * Initialize catalogue page
 */
async function initCatalogue() {
  // Check admin authentication first
  if (!requireAdmin()) {
    // Redirect will happen in requireAdmin if not authorized
    return;
  }
  
  console.log('Admin authenticated, loading catalogue...');
  console.log('Initializing books catalogue...');
  
  // Setup event listeners
  document.getElementById('searchInput').addEventListener('input', debounce(handleSearchChange, 500));
  document.getElementById('authorFilter').addEventListener('input', debounce(handleFilterChange, 500));
  document.getElementById('publisherFilter').addEventListener('input', debounce(handleFilterChange, 500));
  document.getElementById('yearFilter').addEventListener('input', debounce(handleFilterChange, 500));
  document.getElementById('sortFilter').addEventListener('change', handleFilterChange);
  
  // Load books
  await loadBooks();
  
  console.log('Catalogue initialized');
}

/**
 * Load books from backend
 */
async function loadBooks() {
  const container = document.getElementById('booksContainer');
  showLoading(container);
  
  try {
    // Build query parameters
    const params = {
      page: catalogueState.currentPage,
      page_size: catalogueState.pageSize,
      sort: catalogueState.filters.sort
    };
    
    // Add filters if present
    if (catalogueState.filters.q) params.q = catalogueState.filters.q;
    if (catalogueState.filters.author) params.author = catalogueState.filters.author;
    if (catalogueState.filters.publisher) params.publisher = catalogueState.filters.publisher;
    if (catalogueState.filters.year) params.year = catalogueState.filters.year;
    
    // Call API
    const response = await api.getBooks(params);
    
    catalogueState.books = response.items || [];
    catalogueState.totalBooks = response.total || 0;
    catalogueState.currentPage = response.page || 1;
    
    console.log(`Loaded ${catalogueState.books.length} books (${catalogueState.totalBooks} total)`);
    
    // Update results count
    updateResultsCount();
    
    // Render books
    renderBooks();
    
    // Render pagination
    renderPagination();
    
  } catch (error) {
    console.error('Error loading books:', error);
    container.innerHTML = `
      <div class="alert alert-error">
        <strong>Error loading books:</strong> ${error.message}
      </div>
    `;
  }
}

/**
 * Update results count
 */
function updateResultsCount() {
  const count = document.getElementById('resultsCount');
  const start = (catalogueState.currentPage - 1) * catalogueState.pageSize + 1;
  const end = Math.min(start + catalogueState.books.length - 1, catalogueState.totalBooks);
  
  if (catalogueState.totalBooks === 0) {
    count.textContent = 'No books found';
  } else {
    count.textContent = `Showing ${start}-${end} of ${formatNumber(catalogueState.totalBooks)} books`;
  }
}

/**
 * Render books in current view mode
 */
function renderBooks() {
  const container = document.getElementById('booksContainer');
  
  if (catalogueState.books.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📚</div>
        <p class="empty-state-title">No Books Found</p>
        <p class="empty-state-description">
          ${Object.values(catalogueState.filters).some(v => v) 
            ? 'No books match your search criteria. Try adjusting your filters.' 
            : 'The catalogue is empty. Add books to get started!'}
        </p>
        ${Object.values(catalogueState.filters).some(v => v)
          ? '<button class="btn btn-outline" onclick="clearFilters()">Clear Filters</button>'
          : '<a href="add-book.html" class="btn btn-primary">Add Book</a>'}
      </div>
    `;
    return;
  }
  
  if (catalogueState.viewMode === 'grid') {
    renderGridView();
  } else {
    renderListView();
  }
}

/**
 * Render books in grid view
 */
function renderGridView() {
  const container = document.getElementById('booksContainer');
  
  container.innerHTML = `
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: var(--spacing-lg);">
      ${catalogueState.books.map(book => renderBookCard(book)).join('')}
    </div>
  `;
}

/**
 * Render single book card
 */
function renderBookCard(book) {
  const authors = book.authors && book.authors.length > 0 
    ? book.authors.join(', ') 
    : 'Unknown Author';
  const publisher = book.publisher || 'Unknown Publisher';
  const year = book.publication_year || 'N/A';
  const available = book.available_copies || 0;
  const total = book.total_copies || 0;
  
  return `
    <div class="card" style="cursor: pointer; transition: transform var(--transition-fast);" 
         onclick="viewBookDetail(${book.book_id})"
         onmouseover="this.style.transform='translateY(-4px)'"
         onmouseout="this.style.transform='translateY(0)'">
      <div class="card-body">
        <!-- Cover Image Placeholder -->
        <div style="background: var(--gray-100); height: 200px; display: flex; align-items: center; justify-content: center; margin-bottom: var(--spacing-md); border-radius: var(--radius-md);">
          <span style="font-size: 4rem;">📖</span>
        </div>
        
        <!-- Title -->
        <h3 style="font-size: var(--font-size-base); margin-bottom: var(--spacing-sm); height: 2.5em; overflow: hidden;">
          ${truncate(book.title, 60)}
        </h3>
        
        <!-- Authors -->
        <p class="text-muted" style="font-size: var(--font-size-sm); margin-bottom: var(--spacing-sm);">
          ${truncate(authors, 40)}
        </p>
        
        <!-- Publisher and Year -->
        <p class="text-muted" style="font-size: var(--font-size-xs); margin-bottom: var(--spacing-md);">
          ${truncate(publisher, 30)} • ${year}
        </p>
        
        <!-- Availability -->
        <div style="display: flex; justify-content: space-between; align-items: center; padding-top: var(--spacing-sm); border-top: 1px solid var(--gray-200);">
          <span class="text-muted" style="font-size: var(--font-size-sm);">Available:</span>
          <span class="font-semibold ${available > 0 ? 'text-success' : 'text-error'}">
            ${available} / ${total}
          </span>
        </div>
      </div>
    </div>
  `;
}

/**
 * Render books in list view
 */
function renderListView() {
  const container = document.getElementById('booksContainer');
  
  container.innerHTML = `
    <div class="table-container">
      <table class="table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Authors</th>
            <th>Publisher</th>
            <th>Year</th>
            <th>ISBN</th>
            <th>Available</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${catalogueState.books.map(book => renderBookRow(book)).join('')}
        </tbody>
      </table>
    </div>
  `;
}

/**
 * Render single book row
 */
function renderBookRow(book) {
  const authors = book.authors && book.authors.length > 0 
    ? book.authors.join(', ') 
    : 'Unknown Author';
  const publisher = book.publisher || 'Unknown Publisher';
  const year = book.publication_year || 'N/A';
  const isbn = book.isbn_13 || book.isbn_10 || book.isbn || 'N/A';
  const available = book.available_copies || 0;
  const total = book.total_copies || 0;
  
  return `
    <tr>
      <td><strong>${truncate(book.title, 50)}</strong></td>
      <td><small>${truncate(authors, 30)}</small></td>
      <td><small>${truncate(publisher, 20)}</small></td>
      <td><small>${year}</small></td>
      <td><small>${isbn}</small></td>
      <td>
        <span class="${available > 0 ? 'text-success' : 'text-error'}">
          ${available} / ${total}
        </span>
      </td>
      <td>
        <button class="btn btn-sm btn-outline" onclick="viewBookDetail(${book.book_id})">
          View
        </button>
      </td>
    </tr>
  `;
}

/**
 * Switch between grid and list view
 */
function switchView(mode) {
  catalogueState.viewMode = mode;
  
  // Update button states
  document.getElementById('gridViewBtn').classList.toggle('active', mode === 'grid');
  document.getElementById('listViewBtn').classList.toggle('active', mode === 'list');
  
  // Re-render books
  renderBooks();
  
  // Save preference to localStorage
  saveToStorage('catalogueViewMode', mode);
}

/**
 * View book detail
 */
function viewBookDetail(bookId) {
  window.location.href = `book-detail.html?id=${bookId}`;
}

/**
 * Handle search change
 */
function handleSearchChange(event) {
  catalogueState.filters.q = event.target.value.trim();
  catalogueState.currentPage = 1; // Reset to first page
  loadBooks();
}

/**
 * Handle filter change
 */
function handleFilterChange() {
  catalogueState.filters.author = document.getElementById('authorFilter').value.trim();
  catalogueState.filters.publisher = document.getElementById('publisherFilter').value.trim();
  catalogueState.filters.year = document.getElementById('yearFilter').value.trim();
  catalogueState.filters.sort = document.getElementById('sortFilter').value;
  
  catalogueState.currentPage = 1; // Reset to first page
  loadBooks();
}

/**
 * Clear all filters
 */
function clearFilters() {
  // Clear inputs
  document.getElementById('searchInput').value = '';
  document.getElementById('authorFilter').value = '';
  document.getElementById('publisherFilter').value = '';
  document.getElementById('yearFilter').value = '';
  document.getElementById('sortFilter').value = 'created_desc';
  
  // Reset state
  catalogueState.filters = {
    q: '',
    author: '',
    publisher: '',
    year: '',
    sort: 'created_desc'
  };
  catalogueState.currentPage = 1;
  
  // Reload
  loadBooks();
  
  showToast('Filters cleared', 'info');
}

/**
 * Render pagination
 */
function renderPagination() {
  const container = document.getElementById('paginationContainer');
  const totalPages = Math.ceil(catalogueState.totalBooks / catalogueState.pageSize);
  
  if (totalPages <= 1) {
    container.innerHTML = '';
    return;
  }
  
  const current = catalogueState.currentPage;
  
  container.innerHTML = `
    <button class="pagination-btn" ${current === 1 ? 'disabled' : ''} onclick="goToPage(1)">
      First
    </button>
    <button class="pagination-btn" ${current === 1 ? 'disabled' : ''} onclick="goToPage(${current - 1})">
      ◀
    </button>
    ${renderPageNumbers(totalPages)}
    <button class="pagination-btn" ${current === totalPages ? 'disabled' : ''} onclick="goToPage(${current + 1})">
      ▶
    </button>
    <button class="pagination-btn" ${current === totalPages ? 'disabled' : ''} onclick="goToPage(${totalPages})">
      Last
    </button>
  `;
}

/**
 * Render page numbers
 */
function renderPageNumbers(totalPages) {
  const current = catalogueState.currentPage;
  const pages = [];
  
  // Always show first page
  if (current > 3) {
    pages.push(1);
    if (current > 4) pages.push('...');
  }
  
  // Show pages around current
  for (let i = Math.max(1, current - 2); i <= Math.min(totalPages, current + 2); i++) {
    pages.push(i);
  }
  
  // Always show last page
  if (current < totalPages - 2) {
    if (current < totalPages - 3) pages.push('...');
    pages.push(totalPages);
  }
  
  return pages.map(page => {
    if (page === '...') {
      return '<span style="padding: 0 var(--spacing-sm);">...</span>';
    }
    return `
      <button class="pagination-btn ${page === current ? 'active' : ''}" onclick="goToPage(${page})">
        ${page}
      </button>
    `;
  }).join('');
}

/**
 * Go to specific page
 */
function goToPage(page) {
  const totalPages = Math.ceil(catalogueState.totalBooks / catalogueState.pageSize);
  if (page < 1 || page > totalPages) return;
  
  catalogueState.currentPage = page;
  loadBooks();
  
  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    // Restore view mode preference
    const savedViewMode = loadFromStorage('catalogueViewMode', 'grid');
    catalogueState.viewMode = savedViewMode;
    document.getElementById('gridViewBtn').classList.toggle('active', savedViewMode === 'grid');
    document.getElementById('listViewBtn').classList.toggle('active', savedViewMode === 'list');
    
    initCatalogue();
  });
} else {
  // Restore view mode preference
  const savedViewMode = loadFromStorage('catalogueViewMode', 'grid');
  catalogueState.viewMode = savedViewMode;
  document.getElementById('gridViewBtn').classList.toggle('active', savedViewMode === 'grid');
  document.getElementById('listViewBtn').classList.toggle('active', savedViewMode === 'list');
  
  initCatalogue();
}

