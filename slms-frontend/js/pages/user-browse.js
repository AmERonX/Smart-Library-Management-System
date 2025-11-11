/**
 * User Browse Books Page Logic
 */

// Check authentication
if (!Auth.isAuthenticated()) {
  window.location.href = 'login.html';
}

// Page state
const browseState = {
  currentPage: 1,
  pageSize: 20,
  searchQuery: '',
  sort: 'created_desc',
  searchMode: 'keyword',
  semanticMode: 'hybrid',
  semanticTopK: 10,
  semanticExpand: false,
  semanticMeta: null,
  books: [],
  total: 0,
  isLoading: false
};

/**
 * Initialize browse page
 */
async function initBrowse() {
  // Setup event listeners
  document.getElementById('searchInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      searchBooks();
    }
  });
  
  document.getElementById('sortSelect').addEventListener('change', (e) => {
    browseState.sort = e.target.value;
    loadBooks();
  });

  const searchTypeSelect = document.getElementById('searchTypeSelect');
  const semanticModeSelect = document.getElementById('semanticModeSelect');
  const semanticTopKInput = document.getElementById('semanticTopKInput');
  const semanticExpandCheckbox = document.getElementById('semanticExpandCheckbox');

  if (searchTypeSelect) {
    searchTypeSelect.addEventListener('change', (e) => {
      browseState.searchMode = e.target.value;
      browseState.currentPage = 1;
      browseState.semanticMeta = null;
      browseState.books = [];
      browseState.total = 0;
      updateSemanticOptionsVisibility();
      updateSearchStatus();
      if (browseState.searchMode === 'keyword') {
        loadBooks();
      } else if (!browseState.searchQuery) {
        renderBooks();
        renderPagination();
      }
    });
  }

  if (semanticModeSelect) {
    semanticModeSelect.addEventListener('change', (e) => {
      browseState.semanticMode = e.target.value;
      if (browseState.searchMode === 'semantic' && browseState.searchQuery) {
        loadBooks();
      }
    });
  }

  if (semanticTopKInput) {
    semanticTopKInput.addEventListener('change', (e) => {
      let value = parseInt(e.target.value, 10);
      if (Number.isNaN(value)) {
        value = 10;
      }
      value = Math.min(Math.max(value, 1), 20);
      browseState.semanticTopK = value;
      if (semanticTopKInput.value !== String(value)) {
        semanticTopKInput.value = value;
      }
      if (browseState.searchMode === 'semantic' && browseState.searchQuery) {
        loadBooks();
      }
    });
  }

  if (semanticExpandCheckbox) {
    semanticExpandCheckbox.addEventListener('change', (e) => {
      browseState.semanticExpand = e.target.checked;
      if (browseState.searchMode === 'semantic' && browseState.searchQuery) {
        loadBooks();
      }
    });
  }

  updateSemanticOptionsVisibility();
  updateSearchStatus();
  
  // Load books
  await loadBooks();
}

function updateSemanticOptionsVisibility() {
  const semanticOptions = document.getElementById('semanticOptions');
  if (!semanticOptions) return;
  semanticOptions.style.display = browseState.searchMode === 'semantic' ? 'flex' : 'none';
}

function setSearchStatus(message, type = 'info') {
  const statusEl = document.getElementById('searchStatus');
  if (!statusEl) return;

  if (!message) {
    statusEl.style.display = 'none';
    statusEl.textContent = '';
    return;
  }

  statusEl.style.display = 'block';
  statusEl.className = `alert alert-${type}`;
  statusEl.innerHTML = message;
}

function updateSearchStatus() {
  if (browseState.searchMode === 'semantic') {
    if (!browseState.searchQuery) {
      setSearchStatus('Enter a query to run semantic search (AI).', 'info');
      return;
    }

    if (browseState.isLoading) {
      setSearchStatus('Running semantic search…', 'info');
      return;
    }

    if (browseState.semanticMeta) {
      const meta = browseState.semanticMeta;
      const processed = escapeHtml(meta.query_processed || meta.query_raw || browseState.searchQuery);
      const modeLabel = meta.mode ? meta.mode.toUpperCase() : browseState.semanticMode.toUpperCase();
      setSearchStatus(
        `<strong>Semantic search</strong> · Mode: ${modeLabel} · Showing ${meta.resultCount} result${meta.resultCount === 1 ? '' : 's'}<br>` +
          `<em>Processed query:</em> ${processed}`,
        'info'
      );
      return;
    }

    setSearchStatus(null);
    return;
  }

  if (browseState.isLoading) {
    setSearchStatus('Loading books…', 'info');
    return;
  }

  if (browseState.searchQuery) {
    setSearchStatus(`Keyword search for “${escapeHtml(browseState.searchQuery)}”`, 'info');
    return;
  }

  setSearchStatus(null);
}

async function performSemanticSearch() {
  const payload = {
    query: browseState.searchQuery,
    mode: browseState.semanticMode,
    top_k: browseState.semanticTopK,
    normalize: true,
    expand: browseState.semanticExpand,
  };

  const response = await api.semanticSearch(payload);
  const hits = response.results || [];

  const detailedBooks = await Promise.all(
    hits.map(async (hit) => {
      try {
        const details = await api.getBookById(hit.book_id);
        return {
          ...details,
          __semantic: {
            score: hit.score,
            vectorType: hit.vector_type,
            original: hit,
            partial: false,
          },
        };
      } catch (error) {
        console.warn('Failed to load book details for semantic hit', hit.book_id, error);
        return {
          book_id: hit.book_id,
          title: hit.title || `Book ${hit.book_id}`,
          authors: hit.authors || [],
          publisher: hit.publisher,
          publication_year: hit.publication_year,
          available_copies: 0,
          cover_url: null,
          __semantic: {
            score: hit.score,
            vectorType: hit.vector_type,
            original: hit,
            partial: true,
          },
        };
      }
    })
  );

  return {
    books: detailedBooks,
    meta: {
      query_raw: response.query_raw,
      query_processed: response.query_processed,
      mode: response.mode,
      resultCount: hits.length,
    },
  };
}

/**
 * Load books
 */
async function loadBooks() {
  const container = document.getElementById('booksContainer');
  showLoading(container);
  browseState.isLoading = true;
  updateSearchStatus();
  
  try {
    if (browseState.searchMode === 'semantic' && !browseState.searchQuery) {
      browseState.books = [];
      browseState.total = 0;
      browseState.semanticMeta = null;
      container.innerHTML = '<p class="text-muted">Enter a query to run semantic search.</p>';
      renderPagination();
      return;
    }

    if (browseState.searchMode === 'semantic') {
      const { books, meta } = await performSemanticSearch();
      browseState.books = books;
      browseState.total = books.length;
      browseState.semanticMeta = meta;
    } else {
      const params = {
        page: browseState.currentPage,
        page_size: browseState.pageSize,
        sort: browseState.sort
      };
      
      if (browseState.searchQuery) {
        params.q = browseState.searchQuery;
      }
      
      const response = await api.getBooks(params);
      browseState.books = response.items || [];
      browseState.total = response.total || 0;
      browseState.semanticMeta = null;
    }

    renderBooks();
    renderPagination();
    updateSearchStatus();
  } catch (error) {
    console.error('Error loading books:', error);
    container.innerHTML = `
      <div class="alert alert-error">
        <strong>Error loading books:</strong> ${error.message}
      </div>
    `;
    browseState.semanticMeta = null;
    setSearchStatus(`Error loading books: ${escapeHtml(error.message || 'Unknown error')}`, 'error');
  } finally {
    browseState.isLoading = false;
    updateSearchStatus();
  }
}

/**
 * Render books grid
 */
function renderBooks() {
  const container = document.getElementById('booksContainer');
  const isSemantic = browseState.searchMode === 'semantic';
  
  if (browseState.books.length === 0) {
    container.innerHTML = isSemantic
      ? '<p class="text-muted">No semantic matches found. Try refining your query.</p>'
      : '<p class="text-muted">No books found</p>';
    return;
  }
  
  const cards = browseState.books.map((book) => {
    const availableCopies = typeof book.available_copies === 'number' ? book.available_copies : 0;
    const authors = book.authors && book.authors.length > 0
      ? book.authors.map(a => typeof a === 'string' ? a : a.full_name).join(', ')
      : 'Unknown Author';
    const publisher = book.publisher
      ? (typeof book.publisher === 'string' ? book.publisher : book.publisher.name)
      : null;
    const semanticInfo = isSemantic && book.__semantic
      ? `
        <div style="margin-top: var(--spacing-xs); display: flex; gap: var(--spacing-sm); flex-wrap: wrap;">
          <span class="badge badge-primary">Score ${(book.__semantic.score ?? 0).toFixed(3)}</span>
          ${book.__semantic.vectorType ? `<span class="badge badge-secondary">${book.__semantic.vectorType}</span>` : ''}
        </div>
      `
      : '';
    const partialNotice = isSemantic && book.__semantic && book.__semantic.partial
      ? '<p class="text-muted"><small>Limited details available for this match.</small></p>'
      : '';

    return `
      <div class="book-card">
        ${book.cover_url ? `<img src="${book.cover_url}" alt="${escapeHtml(book.title)}" class="book-cover">` : '<div class="book-cover-placeholder">📖</div>'}
        <div class="book-info">
          <h3>${escapeHtml(book.title)}</h3>
          <p class="text-muted">${escapeHtml(authors)}</p>
          ${publisher ? `<p class="text-muted"><small>${escapeHtml(publisher)}</small></p>` : ''}
          ${book.publication_year ? `<p class="text-muted"><small>${escapeHtml(String(book.publication_year))}</small></p>` : ''}
          ${semanticInfo}
          ${partialNotice}
          <div style="margin-top: var(--spacing-sm);">
            <span class="badge ${availableCopies > 0 ? 'badge-success' : 'badge-error'}">
              ${availableCopies > 0 ? `${availableCopies} available` : 'Unavailable'}
            </span>
          </div>
          <div style="margin-top: var(--spacing-md); display: flex; gap: var(--spacing-sm);">
            <a href="user-book-detail.html?id=${book.book_id}" class="btn btn-sm btn-outline" style="flex: 1;">View Details</a>
            ${availableCopies > 0 ? 
              `<button class="btn btn-sm btn-primary" style="flex: 1;" onclick="borrowBook(${book.book_id})">Borrow</button>` :
              `<button class="btn btn-sm btn-outline" style="flex: 1;" onclick="reserveBook(${book.book_id})">Reserve</button>`
            }
          </div>
        </div>
      </div>
    `;
  }).join('');

  container.innerHTML = `
    <div class="books-grid">
      ${cards}
    </div>
  `;
}

/**
 * Render pagination
 */
function renderPagination() {
  const container = document.getElementById('paginationContainer');
  if (browseState.searchMode === 'semantic') {
    container.innerHTML = '';
    return;
  }

  const totalPages = Math.ceil(browseState.total / browseState.pageSize);
  
  if (totalPages <= 1) {
    container.innerHTML = '';
    return;
  }
  
  container.innerHTML = `
    <div class="pagination-info">
      Showing ${(browseState.currentPage - 1) * browseState.pageSize + 1}-${Math.min(browseState.currentPage * browseState.pageSize, browseState.total)} of ${browseState.total}
    </div>
    <button class="pagination-btn" ${browseState.currentPage === 1 ? 'disabled' : ''} onclick="goToPage(1)">First</button>
    <button class="pagination-btn" ${browseState.currentPage === 1 ? 'disabled' : ''} onclick="goToPage(${browseState.currentPage - 1})">◀</button>
    <button class="pagination-btn active">${browseState.currentPage}</button>
    <button class="pagination-btn" ${browseState.currentPage === totalPages ? 'disabled' : ''} onclick="goToPage(${browseState.currentPage + 1})">▶</button>
    <button class="pagination-btn" ${browseState.currentPage === totalPages ? 'disabled' : ''} onclick="goToPage(${totalPages})">Last</button>
  `;
}

/**
 * Go to page
 */
function goToPage(page) {
  browseState.currentPage = page;
  loadBooks();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * Search books
 */
function searchBooks() {
  browseState.searchQuery = document.getElementById('searchInput').value.trim();
  browseState.currentPage = 1;
  browseState.semanticMeta = null;

  if (browseState.searchMode === 'semantic' && !browseState.searchQuery) {
    showToast('Enter a search term to run semantic search.', 'info');
  }

  loadBooks();
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
      await loadBooks(); // Refresh book list
    } else if (response.reserved) {
      showToast('Book not available. Reservation created.', 'info');
      await loadBooks(); // Refresh book list
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
    await loadBooks(); // Refresh book list
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

// Add escapeHtml to window if not already available
if (typeof window.escapeHtml === 'undefined') {
  window.escapeHtml = escapeHtml;
}

// Make functions available globally
window.goToPage = goToPage;
window.searchBooks = searchBooks;
window.borrowBook = borrowBook;
window.reserveBook = reserveBook;
window.handleLogout = function() {
  if (confirm('Are you sure you want to logout?')) {
    Auth.removeToken();
    localStorage.removeItem('user');
    window.location.href = 'login.html';
  }
};

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initBrowse);
} else {
  initBrowse();
}

