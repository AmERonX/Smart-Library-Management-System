/**
 * Pending Catalogue Page Logic
 * Handles pending entries table, filtering, sorting, and approval workflow
 */

// Page state
const pendingState = {
  allEntries: [],
  filteredEntries: [],
  currentPage: 1,
  pageSize: 10,
  sortColumn: 'created_at',
  sortDescending: true,
  filters: {
    search: '',
    status: 'awaiting_confirmation'
  },
  autoRefreshInterval: null,
  highlightId: null
};

/**
 * Initialize pending page
 */
async function initPending() {
  // Check admin authentication first
  if (!requireAdmin()) {
    // Redirect will happen in requireAdmin if not authorized
    return;
  }
  
  console.log('Admin authenticated, initializing pending catalogue page...');
  
  // Get highlight ID from URL
  pendingState.highlightId = getURLParameter('highlight');
  
  // Setup event listeners
  document.getElementById('searchInput').addEventListener('input', debounce(handleSearchChange, 300));
  document.getElementById('statusFilter').addEventListener('change', handleStatusFilterChange);
  document.getElementById('autoRefreshToggle').addEventListener('change', handleAutoRefreshToggle);
  
  // Load pending entries
  await loadPendingEntries();
  
  // Setup auto-refresh (enabled by default)
  setupAutoRefresh();
  
  console.log('Pending page initialized');
}

/**
 * Load pending entries from backend
 */
async function loadPendingEntries() {
  const container = document.getElementById('pendingTableContainer');
  showLoading(container);
  
  try {
    const response = await api.getPending();
    pendingState.allEntries = Array.isArray(response) ? response : [];
    
    console.log('Loaded pending entries:', pendingState.allEntries.length);
    
    // Apply filters and sort
    applyFiltersAndSort();
    
    // Render table
    renderPendingTable();
    
  } catch (error) {
    console.error('Error loading pending entries:', error);
    container.innerHTML = `
      <div class="alert alert-error" style="margin: var(--spacing-lg);">
        <strong>Error loading pending entries:</strong> ${error.message}
      </div>
    `;
  }
}

/**
 * Apply filters and sorting to entries
 */
function applyFiltersAndSort() {
  let entries = [...pendingState.allEntries];
  
  // Apply status filter
  if (pendingState.filters.status !== 'all') {
    entries = entries.filter(entry => entry.status === pendingState.filters.status);
  }
  
  // Apply search filter
  if (pendingState.filters.search) {
    const searchLower = pendingState.filters.search.toLowerCase();
    entries = entries.filter(entry => {
      return (entry.title && entry.title.toLowerCase().includes(searchLower)) ||
             (entry.isbn && entry.isbn.toLowerCase().includes(searchLower)) ||
             (entry.isbn_10 && entry.isbn_10.toLowerCase().includes(searchLower)) ||
             (entry.isbn_13 && entry.isbn_13.toLowerCase().includes(searchLower)) ||
             (entry.authors && JSON.stringify(entry.authors).toLowerCase().includes(searchLower));
    });
  }
  
  // Sort entries
  entries.sort((a, b) => {
    let aVal = a[pendingState.sortColumn];
    let bVal = b[pendingState.sortColumn];
    
    // Handle null values
    if (aVal === null || aVal === undefined) aVal = '';
    if (bVal === null || bVal === undefined) bVal = '';
    
    // Convert to comparable format
    if (typeof aVal === 'string') aVal = aVal.toLowerCase();
    if (typeof bVal === 'string') bVal = bVal.toLowerCase();
    
    if (aVal < bVal) return pendingState.sortDescending ? 1 : -1;
    if (aVal > bVal) return pendingState.sortDescending ? -1 : 1;
    return 0;
  });
  
  pendingState.filteredEntries = entries;
  pendingState.currentPage = 1; // Reset to first page when filtering
}

/**
 * Render pending table
 */
function renderPendingTable() {
  const container = document.getElementById('pendingTableContainer');
  const entries = pendingState.filteredEntries;
  
  // Update count
  document.getElementById('entryCount').textContent = `${entries.length} ${entries.length === 1 ? 'entry' : 'entries'}`;
  
  if (entries.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📭</div>
        <p class="empty-state-title">No Pending Entries</p>
        <p class="empty-state-description">
          ${pendingState.filters.search || pendingState.filters.status !== 'all' 
            ? 'No entries match your filters. Try adjusting your search.' 
            : 'All books have been processed! Add a new book to get started.'}
        </p>
        ${!pendingState.filters.search && pendingState.filters.status === 'all' 
          ? '<a href="add-book.html" class="btn btn-primary">Add Book</a>' 
          : '<button class="btn btn-outline" onclick="clearFilters()">Clear Filters</button>'}
      </div>
    `;
    document.getElementById('paginationContainer').innerHTML = '';
    return;
  }
  
  // Paginate
  const startIdx = (pendingState.currentPage - 1) * pendingState.pageSize;
  const endIdx = startIdx + pendingState.pageSize;
  const pageEntries = entries.slice(startIdx, endIdx);
  
  // Render table
  container.innerHTML = `
    <table class="table">
      <thead>
        <tr>
          <th class="sortable" onclick="handleSort('id')">
            ID ${getSortIndicator('id')}
          </th>
          <th class="sortable" onclick="handleSort('title')">
            Title ${getSortIndicator('title')}
          </th>
          <th>ISBN</th>
          <th>Authors</th>
          <th class="sortable" onclick="handleSort('status')">
            Status ${getSortIndicator('status')}
          </th>
          <th class="sortable" onclick="handleSort('created_at')">
            Created ${getSortIndicator('created_at')}
          </th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        ${pageEntries.map(entry => renderTableRow(entry)).join('')}
      </tbody>
    </table>
  `;
  
  // Render pagination
  renderPagination();
}

/**
 * Render single table row
 */
function renderTableRow(entry) {
  const isHighlighted = pendingState.highlightId && entry.id == pendingState.highlightId;
  const isbn = entry.isbn_13 || entry.isbn_10 || entry.isbn || 'N/A';
  const authors = entry.authors ? (Array.isArray(entry.authors) ? entry.authors.join(', ') : entry.authors) : 'N/A';
  
  return `
    <tr ${isHighlighted ? 'style="background-color: #fffbeb;"' : ''}>
      <td><strong>#${entry.id}</strong></td>
      <td>${truncate(entry.title, 50)}</td>
      <td><small>${isbn}</small></td>
      <td><small>${truncate(authors, 30)}</small></td>
      <td>${getStatusBadge(entry.status)}</td>
      <td><small>${getRelativeTime(entry.created_at)}</small></td>
      <td>
        <div class="table-actions">
          <button class="btn btn-sm btn-ghost" onclick="openReviewModal(${entry.id})" title="View Details">
            👁️
          </button>
          ${entry.status === 'awaiting_confirmation' || entry.status === 'failed' ? `
            <button class="btn btn-sm btn-primary" onclick="openEditModal(${entry.id})" title="Edit">
              ✏️
            </button>
            <button class="btn btn-sm btn-success" onclick="quickApprove(${entry.id})" title="Quick Approve">
              ✓
            </button>
            <button class="btn btn-sm btn-error" onclick="quickReject(${entry.id})" title="Quick Reject">
              ✗
            </button>
          ` : ''}
        </div>
      </td>
    </tr>
  `;
}

/**
 * Get sort indicator
 */
function getSortIndicator(column) {
  if (pendingState.sortColumn !== column) {
    return '';
  }
  return pendingState.sortDescending ? '↓' : '↑';
}

/**
 * Handle column sort
 */
function handleSort(column) {
  if (pendingState.sortColumn === column) {
    pendingState.sortDescending = !pendingState.sortDescending;
  } else {
    pendingState.sortColumn = column;
    pendingState.sortDescending = true;
  }
  
  applyFiltersAndSort();
  renderPendingTable();
}

/**
 * Render pagination
 */
function renderPagination() {
  const container = document.getElementById('paginationContainer');
  const totalPages = Math.ceil(pendingState.filteredEntries.length / pendingState.pageSize);
  
  if (totalPages <= 1) {
    container.innerHTML = '';
    return;
  }
  
  const startIdx = (pendingState.currentPage - 1) * pendingState.pageSize + 1;
  const endIdx = Math.min(startIdx + pendingState.pageSize - 1, pendingState.filteredEntries.length);
  
  container.innerHTML = `
    <div class="pagination-info">
      Showing ${startIdx}-${endIdx} of ${pendingState.filteredEntries.length}
    </div>
    <button class="pagination-btn" ${pendingState.currentPage === 1 ? 'disabled' : ''} onclick="goToPage(1)">
      First
    </button>
    <button class="pagination-btn" ${pendingState.currentPage === 1 ? 'disabled' : ''} onclick="goToPage(${pendingState.currentPage - 1})">
      ◀
    </button>
    ${renderPageNumbers(totalPages)}
    <button class="pagination-btn" ${pendingState.currentPage === totalPages ? 'disabled' : ''} onclick="goToPage(${pendingState.currentPage + 1})">
      ▶
    </button>
    <button class="pagination-btn" ${pendingState.currentPage === totalPages ? 'disabled' : ''} onclick="goToPage(${totalPages})">
      Last
    </button>
  `;
}

/**
 * Render page numbers
 */
function renderPageNumbers(totalPages) {
  const current = pendingState.currentPage;
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
 * Go to page
 */
function goToPage(page) {
  const totalPages = Math.ceil(pendingState.filteredEntries.length / pendingState.pageSize);
  if (page < 1 || page > totalPages) return;
  
  pendingState.currentPage = page;
  renderPendingTable();
  
  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * Handle search change
 */
function handleSearchChange(event) {
  pendingState.filters.search = event.target.value.trim();
  applyFiltersAndSort();
  renderPendingTable();
}

/**
 * Handle status filter change
 */
function handleStatusFilterChange(event) {
  pendingState.filters.status = event.target.value;
  applyFiltersAndSort();
  renderPendingTable();
}

/**
 * Clear filters
 */
function clearFilters() {
  document.getElementById('searchInput').value = '';
  document.getElementById('statusFilter').value = 'all';
  
  pendingState.filters.search = '';
  pendingState.filters.status = 'all';
  
  applyFiltersAndSort();
  renderPendingTable();
  
  showToast('Filters cleared', 'info');
}

/**
 * Refresh pending list
 */
async function refreshPendingList() {
  showToast('Refreshing...', 'info');
  await loadPendingEntries();
}

/**
 * Open review modal
 */
async function openReviewModal(pendingId) {
  const modal = document.getElementById('reviewModal');
  const modalBody = document.getElementById('reviewModalBody');
  const modalFooter = document.getElementById('reviewModalFooter');
  
  modal.classList.remove('hidden');
  
  // Show loading
  modalBody.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading...</p></div>';
  modalFooter.innerHTML = '';
  
  try {
    const entry = await api.getPendingById(pendingId);
    
    // Render entry details
    const metadata = entry.raw_metadata || {};
    const authors = entry.authors ? (Array.isArray(entry.authors) ? entry.authors.join(', ') : entry.authors) : 'N/A';
    
    modalBody.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: var(--spacing-lg);">
        <div>
          <p class="text-muted font-semibold">Pending ID</p>
          <p>${entry.id}</p>
        </div>
        <div>
          <p class="text-muted font-semibold">Status</p>
          <p>${getStatusBadge(entry.status)}</p>
        </div>
        <div>
          <p class="text-muted font-semibold">Title</p>
          <p>${entry.title}</p>
        </div>
        <div>
          <p class="text-muted font-semibold">Authors</p>
          <p>${authors}</p>
        </div>
        <div>
          <p class="text-muted font-semibold">ISBN</p>
          <p>${entry.isbn_13 || entry.isbn_10 || entry.isbn || 'N/A'}</p>
        </div>
        <div>
          <p class="text-muted font-semibold">Total Copies</p>
          <p>${entry.total_copies}</p>
        </div>
        ${metadata.publisher ? `
        <div>
          <p class="text-muted font-semibold">Publisher</p>
          <p>${metadata.publisher}</p>
        </div>
        ` : ''}
        ${metadata.publication_year ? `
        <div>
          <p class="text-muted font-semibold">Publication Year</p>
          <p>${metadata.publication_year}</p>
        </div>
        ` : ''}
      </div>
      
      ${metadata.description ? `
        <div style="margin-top: var(--spacing-lg);">
          <p class="text-muted font-semibold">Description</p>
          <p style="line-height: 1.6;">${metadata.description}</p>
        </div>
      ` : ''}
      
      <div style="margin-top: var(--spacing-lg); padding-top: var(--spacing-lg); border-top: 1px solid var(--gray-200);">
        <p class="text-muted"><small>Created: ${formatDateTime(entry.created_at)}</small></p>
        ${entry.updated_at ? `<p class="text-muted"><small>Updated: ${formatDateTime(entry.updated_at)}</small></p>` : ''}
      </div>
    `;
    
    // Render footer buttons based on status
    if (entry.status === 'awaiting_confirmation' || entry.status === 'failed') {
      modalFooter.innerHTML = `
        <button class="btn btn-outline" onclick="closeReviewModal()">Close</button>
        <button class="btn btn-error" onclick="rejectFromModal(${entry.id})">Reject</button>
        <button class="btn btn-success" onclick="approveFromModal(${entry.id})">Approve & Insert</button>
      `;
    } else {
      modalFooter.innerHTML = `
        <button class="btn btn-primary" onclick="closeReviewModal()">Close</button>
      `;
    }
    
  } catch (error) {
    console.error('Error loading entry:', error);
    modalBody.innerHTML = `
      <div class="alert alert-error">
        <strong>Error loading entry:</strong> ${error.message}
      </div>
    `;
    modalFooter.innerHTML = `
      <button class="btn btn-outline" onclick="closeReviewModal()">Close</button>
    `;
  }
}

/**
 * Close review modal
 */
function closeReviewModal() {
  document.getElementById('reviewModal').classList.add('hidden');
}

/**
 * Close modal on overlay click
 */
function closeModalOnOverlay(event) {
  if (event.target.classList.contains('modal-overlay')) {
    closeReviewModal();
  }
}

/**
 * Quick approve
 */
async function quickApprove(pendingId) {
  if (!confirm('Approve this book and insert into catalogue?')) {
    return;
  }
  
  try {
    // First confirm/approve
    const confirmResult = await api.confirmMetadata(pendingId, { approved: true });
    console.log('Approval successful:', confirmResult);
    
    // Small delay to ensure database transaction is committed
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Then insert
    const result = await api.insertBook(pendingId);
    console.log('Insertion successful:', result);
    
    showToast(`Book approved and inserted! Book ID: ${result.book_id}`, 'success');
    
    // Reload list
    await loadPendingEntries();
    
  } catch (error) {
    console.error('Error approving:', error);
    
    // Show more detailed error message
    let errorMessage = 'Failed to approve: ';
    if (error.message) {
      errorMessage += error.message;
    } else if (error.detail) {
      errorMessage += error.detail;
    } else {
      errorMessage += 'Unknown error occurred';
    }
    
    showToast(errorMessage, 'error');
    
    // Still reload to show updated status
    await loadPendingEntries();
  }
}

/**
 * Quick reject
 */
async function quickReject(pendingId) {
  const reason = prompt('Enter rejection reason:');
  if (!reason) return;
  
  try {
    await api.confirmMetadata(pendingId, { approved: false, reason });
    
    showToast('Book rejected', 'success');
    
    // Reload list
    await loadPendingEntries();
    
  } catch (error) {
    console.error('Error rejecting:', error);
    showToast('Failed to reject: ' + error.message, 'error');
  }
}

/**
 * Approve from modal
 */
async function approveFromModal(pendingId) {
  closeReviewModal();
  await quickApprove(pendingId);
}

/**
 * Reject from modal
 */
async function rejectFromModal(pendingId) {
  closeReviewModal();
  await quickReject(pendingId);
}

/**
 * Open edit modal
 */
async function openEditModal(pendingId) {
  const modal = document.getElementById('editModal');
  const modalBody = document.getElementById('editModalBody');
  const modalFooter = document.getElementById('editModalFooter');
  
  modal.classList.remove('hidden');
  
  // Show loading
  modalBody.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading...</p></div>';
  modalFooter.innerHTML = '';
  
  try {
    const entry = await api.getPendingById(pendingId);
    const metadata = entry.raw_metadata || {};
    const authors = entry.authors || [];
    
    // Render edit form
    modalBody.innerHTML = `
      <form id="editForm" onsubmit="saveEdit(event, ${pendingId})">
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--spacing-md);">
          <!-- Basic Info -->
          <div class="form-group">
            <label for="editTitle" class="form-label">Title *</label>
            <input type="text" id="editTitle" class="form-control" value="${escapeHtml(entry.title || '')}" required>
          </div>
          
          <div class="form-group">
            <label for="editTotalCopies" class="form-label">Total Copies *</label>
            <input type="number" id="editTotalCopies" class="form-control" value="${entry.total_copies || 1}" min="1" required>
          </div>
          
          <!-- ISBN Fields -->
          <div class="form-group">
            <label for="editIsbn" class="form-label">ISBN</label>
            <input type="text" id="editIsbn" class="form-control" value="${escapeHtml(entry.isbn || '')}" placeholder="ISBN-10 or ISBN-13">
          </div>
          
          <div class="form-group">
            <label for="editIsbn10" class="form-label">ISBN-10</label>
            <input type="text" id="editIsbn10" class="form-control" value="${escapeHtml(entry.isbn_10 || metadata.isbn_10 || '')}" placeholder="10 digits">
          </div>
          
          <div class="form-group">
            <label for="editIsbn13" class="form-label">ISBN-13</label>
            <input type="text" id="editIsbn13" class="form-control" value="${escapeHtml(entry.isbn_13 || metadata.isbn_13 || '')}" placeholder="13 digits">
          </div>
          
          <!-- Authors -->
          <div class="form-group" style="grid-column: span 2;">
            <label for="editAuthors" class="form-label">Authors</label>
            <div id="editAuthorsContainer">
              ${authors.length > 0 ? authors.map((author, idx) => `
                <div class="input-group mb-1">
                  <input type="text" class="form-control edit-author-input" value="${escapeHtml(author)}" placeholder="Author name">
                  ${idx > 0 ? `<button type="button" class="btn btn-outline" onclick="removeEditAuthor(this)">Remove</button>` : ''}
                </div>
              `).join('') : `
                <div class="input-group mb-1">
                  <input type="text" class="form-control edit-author-input" placeholder="Author name">
                </div>
              `}
            </div>
            <button type="button" class="btn btn-outline btn-sm mt-1" onclick="addEditAuthorField()">+ Add Author</button>
          </div>
          
          <!-- Metadata Fields -->
          <div class="form-group">
            <label for="editPublisher" class="form-label">Publisher</label>
            <input type="text" id="editPublisher" class="form-control" value="${escapeHtml(metadata.publisher || '')}" placeholder="Publisher name">
          </div>
          
          <div class="form-group">
            <label for="editPublicationYear" class="form-label">Publication Year</label>
            <input type="text" id="editPublicationYear" class="form-control" value="${escapeHtml(metadata.publication_year || '')}" placeholder="e.g., 2008">
          </div>
          
          <div class="form-group">
            <label for="editEdition" class="form-label">Edition</label>
            <input type="text" id="editEdition" class="form-control" value="${escapeHtml(metadata.edition || '')}" placeholder="e.g., 1st, 2nd">
          </div>
          
          <div class="form-group">
            <label for="editCoverUrl" class="form-label">Cover URL</label>
            <input type="url" id="editCoverUrl" class="form-control" value="${escapeHtml(metadata.cover_url || '')}" placeholder="https://...">
          </div>
          
          <!-- Description -->
          <div class="form-group" style="grid-column: span 2;">
            <label for="editDescription" class="form-label">Description</label>
            <textarea id="editDescription" class="form-control" rows="4" placeholder="Book description">${escapeHtml(metadata.description || '')}</textarea>
          </div>
          
          <!-- Categories -->
          <div class="form-group" style="grid-column: span 2;">
            <label for="editCategories" class="form-label">Categories</label>
            <input type="text" id="editCategories" class="form-control" value="${metadata.categories ? (Array.isArray(metadata.categories) ? metadata.categories.join(', ') : metadata.categories) : ''}" placeholder="Comma-separated categories">
          </div>
        </div>
      </form>
    `;
    
    // Render footer buttons
    modalFooter.innerHTML = `
      <button type="button" class="btn btn-outline" onclick="closeEditModal()">Cancel</button>
      <button type="button" class="btn btn-primary" onclick="saveEdit(null, ${pendingId})">Save Changes</button>
    `;
    
  } catch (error) {
    console.error('Error loading entry for editing:', error);
    modalBody.innerHTML = `
      <div class="alert alert-error">
        <strong>Error loading entry:</strong> ${error.message}
      </div>
    `;
    modalFooter.innerHTML = `
      <button type="button" class="btn btn-outline" onclick="closeEditModal()">Close</button>
    `;
  }
}

/**
 * Close edit modal
 */
function closeEditModal() {
  document.getElementById('editModal').classList.add('hidden');
}

/**
 * Close edit modal on overlay click
 */
function closeEditModalOnOverlay(event) {
  if (event.target.classList.contains('modal-overlay')) {
    closeEditModal();
  }
}

/**
 * Add author field in edit form
 */
function addEditAuthorField() {
  const container = document.getElementById('editAuthorsContainer');
  const fieldHTML = `
    <div class="input-group mb-1">
      <input type="text" class="form-control edit-author-input" placeholder="Author name">
      <button type="button" class="btn btn-outline" onclick="removeEditAuthor(this)">Remove</button>
    </div>
  `;
  container.insertAdjacentHTML('beforeend', fieldHTML);
}

/**
 * Remove author field from edit form
 */
function removeEditAuthor(button) {
  button.parentElement.remove();
}

/**
 * Save edited entry
 */
async function saveEdit(event, pendingId) {
  if (event) {
    event.preventDefault();
  }
  
  try {
    // Collect form data
    const title = document.getElementById('editTitle').value.trim();
    const totalCopies = parseInt(document.getElementById('editTotalCopies').value);
    const isbn = document.getElementById('editIsbn').value.trim() || null;
    const isbn10 = document.getElementById('editIsbn10').value.trim() || null;
    const isbn13 = document.getElementById('editIsbn13').value.trim() || null;
    
    // Collect authors
    const authorInputs = document.querySelectorAll('.edit-author-input');
    const authors = [];
    authorInputs.forEach(input => {
      const value = input.value.trim();
      if (value) {
        authors.push(value);
      }
    });
    
    // Collect metadata
    const publisher = document.getElementById('editPublisher').value.trim() || null;
    const publicationYear = document.getElementById('editPublicationYear').value.trim() || null;
    const edition = document.getElementById('editEdition').value.trim() || null;
    const coverUrl = document.getElementById('editCoverUrl').value.trim() || null;
    const description = document.getElementById('editDescription').value.trim() || null;
    
    // Get existing metadata and update it
    const entry = await api.getPendingById(pendingId);
    const existingMetadata = entry.raw_metadata || {};
    
    // Build raw_metadata object - preserve existing fields, update with new values
    const rawMetadata = { ...existingMetadata };
    
    // Always update title
    rawMetadata.title = title;
    
    // Update metadata fields (set to value or empty string to allow clearing)
    rawMetadata.publisher = publisher || '';
    rawMetadata.publication_year = publicationYear || '';
    rawMetadata.edition = edition || '';
    rawMetadata.cover_url = coverUrl || '';
    rawMetadata.description = description || '';
    rawMetadata.isbn_10 = isbn10 || '';
    rawMetadata.isbn_13 = isbn13 || '';
    
    // Handle categories
    const categoriesField = document.getElementById('editCategories');
    if (categoriesField) {
      const categoriesValue = categoriesField.value.trim();
      if (categoriesValue) {
        rawMetadata.categories = categoriesValue.split(',').map(c => c.trim()).filter(c => c);
      } else {
        rawMetadata.categories = [];
      }
    }
    
    // Clean up empty string values - convert to null for optional fields
    Object.keys(rawMetadata).forEach(key => {
      if (rawMetadata[key] === '' && key !== 'title' && key !== 'description') {
        delete rawMetadata[key];
      }
    });
    
    // Prepare update data
    const updateData = {
      title: title,
      total_copies: totalCopies,
      authors: authors.length > 0 ? authors : null,
      raw_metadata: rawMetadata
    };
    
    // Add ISBN fields (send null if empty to allow clearing)
    updateData.isbn = isbn || null;
    updateData.isbn_10 = isbn10 || null;
    updateData.isbn_13 = isbn13 || null;
    
    // Show saving state
    const modalFooter = document.getElementById('editModalFooter');
    const saveBtn = modalFooter.querySelector('.btn-primary');
    const originalText = saveBtn.textContent;
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';
    
    // Update entry
    await api.updatePending(pendingId, updateData);
    
    showToast('Book metadata updated successfully!', 'success');
    
    // Close modal and reload list
    closeEditModal();
    await loadPendingEntries();
    
  } catch (error) {
    console.error('Error saving edit:', error);
    
    let errorMessage = 'Failed to save changes: ';
    if (error.message) {
      errorMessage += error.message;
    } else if (error.detail) {
      errorMessage += error.detail;
    } else {
      errorMessage += 'Unknown error occurred';
    }
    
    showToast(errorMessage, 'error');
    
    // Restore button
    const modalFooter = document.getElementById('editModalFooter');
    const saveBtn = modalFooter.querySelector('.btn-primary');
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save Changes';
    }
  }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Setup auto-refresh
 */
function setupAutoRefresh() {
  if (pendingState.autoRefreshInterval) {
    clearInterval(pendingState.autoRefreshInterval);
  }
  
  if (document.getElementById('autoRefreshToggle').checked) {
    pendingState.autoRefreshInterval = setInterval(async () => {
      console.log('Auto-refreshing pending list...');
      await loadPendingEntries();
    }, CONFIG.AUTO_REFRESH_INTERVAL);
  }
}

/**
 * Handle auto-refresh toggle
 */
function handleAutoRefreshToggle() {
  setupAutoRefresh();
  
  const enabled = document.getElementById('autoRefreshToggle').checked;
  showToast(enabled ? 'Auto-refresh enabled' : 'Auto-refresh disabled', 'info');
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  if (pendingState.autoRefreshInterval) {
    clearInterval(pendingState.autoRefreshInterval);
  }
});

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPending);
} else {
  initPending();
}

