/**
 * Add Book Page Logic
 * Handles book addition form with ISBN lookup and metadata fetching
 */

// Check admin authentication
if (!initAdminPage()) {
  // Redirect will happen in initAdminPage if not authorized
}

// Page state
const addBookState = {
  authorCount: 1,
  metadataFetched: null,
  isSubmitting: false
};

/**
 * Initialize add book page
 */
function initAddBook() {
  console.log('Initializing add book page...');
  
  // Check admin authentication first
  if (!requireAdmin()) {
    // Redirect will happen in requireAdmin if not authorized
    return;
  }
  
  console.log('Admin authenticated, setting up page...');
  
  // Setup event listeners
  document.getElementById('addBookForm').addEventListener('submit', handleFormSubmit);
  document.getElementById('fetchMetadataBtn').addEventListener('click', handleFetchMetadata);
  document.getElementById('addAuthorBtn').addEventListener('click', addAuthorField);
  document.getElementById('isbn').addEventListener('input', handleISBNInput);
  document.getElementById('isbn').addEventListener('blur', validateISBNField);
  document.getElementById('totalCopies').addEventListener('change', validateCopies);
  
  console.log('Add book page initialized');
}

/**
 * Handle ISBN input (real-time validation)
 */
function handleISBNInput(event) {
  const isbn = event.target.value.trim();
  const isbnError = document.getElementById('isbnError');
  const isbnSuccess = document.getElementById('isbnSuccess');
  
  // Clear previous messages
  isbnError.classList.add('hidden');
  isbnSuccess.classList.add('hidden');
  event.target.classList.remove('is-invalid', 'is-valid');
  
  if (isbn && isbn.length >= 10) {
    if (validateISBN(isbn)) {
      event.target.classList.add('is-valid');
      isbnSuccess.textContent = '✓ Valid ISBN format';
      isbnSuccess.classList.remove('hidden');
    }
  }
}

/**
 * Validate ISBN field on blur
 */
function validateISBNField() {
  const isbnInput = document.getElementById('isbn');
  const isbn = isbnInput.value.trim();
  const isbnError = document.getElementById('isbnError');
  const isbnSuccess = document.getElementById('isbnSuccess');
  
  // Clear previous messages
  isbnError.classList.add('hidden');
  isbnSuccess.classList.add('hidden');
  isbnInput.classList.remove('is-invalid', 'is-valid');
  
  if (isbn) {
    if (!validateISBN(isbn)) {
      isbnInput.classList.add('is-invalid');
      isbnError.textContent = 'Invalid ISBN format. Must be 10 or 13 digits.';
      isbnError.classList.remove('hidden');
      return false;
    } else {
      isbnInput.classList.add('is-valid');
      isbnSuccess.textContent = '✓ Valid ISBN format';
      isbnSuccess.classList.remove('hidden');
      return true;
    }
  }
  
  return true; // ISBN is optional
}

/**
 * Handle fetch metadata button click
 */
async function handleFetchMetadata(event) {
  // Prevent any form submission
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  
  const isbnInput = document.getElementById('isbn');
  const titleInput = document.getElementById('title');
  const isbn = isbnInput.value.trim();
  const title = titleInput.value.trim();
  
  // Validate ISBN if provided
  if (isbn && !validateISBNField()) {
    showToast('Please enter a valid ISBN', 'error');
    return;
  }
  
  // Need at least ISBN or title
  if (!isbn && !title) {
    showToast('Please enter an ISBN or title', 'warning');
    titleInput.focus();
    return;
  }
  
  // Get authors
  const authors = getAuthors();
  
  // Show loading state
  const fetchBtn = document.getElementById('fetchMetadataBtn');
  const originalText = fetchBtn.textContent;
  fetchBtn.disabled = true;
  fetchBtn.innerHTML = '<div class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></div> Fetching...';
  
  try {
    // Call backend API to fetch metadata only (no pending entry created)
    // Title is optional when ISBN is provided - don't send placeholder
    const response = await api.fetchMetadata({
      isbn: isbn || null,
      title: title || null,  // Send null if empty, not placeholder
      authors: authors.length > 0 ? authors : null,
      total_copies: 1 // Not used for metadata fetching
    });
    
    if (!response.success || !response.metadata_preview) {
      showToast(response.message || 'No metadata found', 'warning');
      hideMetadataPreview();
      return;
    }
    
    // Store fetched metadata
    addBookState.metadataFetched = response;
    
    // Display metadata preview
    displayMetadataPreview(response);
    
    showToast('Metadata fetched successfully!', 'success');
    
  } catch (error) {
    // Log full error for debugging
    console.error('Error fetching metadata:', error);
    console.error('Error details:', {
      message: error.message,
      detail: error.detail,
      status: error.status,
      data: error.data,
      stack: error.stack
    });
    
    // Extract error message properly
    let errorMessage = 'Failed to fetch metadata';
    if (error.message) {
      errorMessage += ': ' + error.message;
    } else if (error.detail) {
      errorMessage += ': ' + error.detail;
    } else if (error.data && error.data.detail) {
      errorMessage += ': ' + error.data.detail;
    } else if (typeof error === 'string') {
      errorMessage += ': ' + error;
    } else {
      errorMessage += '. Check browser console (F12) for details.';
    }
    
    showToast(errorMessage, 'error');
    hideMetadataPreview();
  } finally {
    // Restore button
    fetchBtn.disabled = false;
    fetchBtn.textContent = originalText;
  }
}

/**
 * Display metadata preview
 */
function displayMetadataPreview(response) {
  const preview = response.metadata_preview;
  
  if (!preview) {
    hideMetadataPreview();
    return;
  }
  
  const metadataDetails = document.getElementById('metadataDetails');
  metadataDetails.innerHTML = `
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: var(--spacing-md);">
      <div>
        <p class="text-muted" style="margin-bottom: var(--spacing-xs);"><strong>Title:</strong></p>
        <p>${preview.title || 'N/A'}</p>
      </div>
      <div>
        <p class="text-muted" style="margin-bottom: var(--spacing-xs);"><strong>Authors:</strong></p>
        <p>${preview.authors ? preview.authors.join(', ') : 'N/A'}</p>
      </div>
      <div>
        <p class="text-muted" style="margin-bottom: var(--spacing-xs);"><strong>Publisher:</strong></p>
        <p>${preview.publisher || 'N/A'}</p>
      </div>
      <div>
        <p class="text-muted" style="margin-bottom: var(--spacing-xs);"><strong>Year:</strong></p>
        <p>${preview.publication_year || 'N/A'}</p>
      </div>
      <div>
        <p class="text-muted" style="margin-bottom: var(--spacing-xs);"><strong>ISBN-10:</strong></p>
        <p>${preview.isbn_10 || 'N/A'}</p>
      </div>
      <div>
        <p class="text-muted" style="margin-bottom: var(--spacing-xs);"><strong>ISBN-13:</strong></p>
        <p>${preview.isbn_13 || 'N/A'}</p>
      </div>
    </div>
    <div style="margin-top: var(--spacing-md); padding-top: var(--spacing-md); border-top: 1px solid var(--gray-200);">
      <p class="text-muted"><strong>Source:</strong> ${preview.source || 'Unknown'}</p>
      ${response.pending_id ? `<p class="text-muted"><strong>Pending ID:</strong> ${response.pending_id}</p>` : ''}
    </div>
  `;
  
  // Always update form fields with fetched metadata (overwrite manual entries)
  const titleInput = document.getElementById('title');
  if (preview.title) {
    titleInput.value = preview.title;
  }
  
  // Always update authors if fetched (overwrite manual entries)
  if (preview.authors && preview.authors.length > 0) {
    const authorInputs = document.querySelectorAll('.author-input');
    
    // Clear existing author inputs
    authorInputs.forEach(input => input.value = '');
    
    // Set first author in first field
    if (authorInputs.length > 0) {
      authorInputs[0].value = preview.authors[0];
    }
    
    // Add additional authors if needed
    for (let i = 1; i < preview.authors.length; i++) {
      if (i < authorInputs.length) {
        authorInputs[i].value = preview.authors[i];
      } else {
        addAuthorField();
        const newInput = document.querySelector(`.author-input[data-index="${addBookState.authorCount - 1}"]`);
        if (newInput) {
          newInput.value = preview.authors[i];
        }
      }
    }
  }
  
  // Update ISBN fields if fetched and form field is empty
  const isbnInput = document.getElementById('isbn');
  if (preview.isbn_10 && !isbnInput.value.trim()) {
    isbnInput.value = preview.isbn_10;
  } else if (preview.isbn_13 && !isbnInput.value.trim()) {
    isbnInput.value = preview.isbn_13;
  }
  
  // Show preview
  document.getElementById('metadataPreview').classList.remove('hidden');
  
  // Scroll to preview
  document.getElementById('metadataPreview').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Hide metadata preview
 */
function hideMetadataPreview() {
  document.getElementById('metadataPreview').classList.add('hidden');
}

/**
 * Handle form submission
 */
async function handleFormSubmit(event) {
  event.preventDefault();
  
  if (addBookState.isSubmitting) {
    return;
  }
  
  // Get form data
  const isbn = document.getElementById('isbn').value.trim();
  let title = document.getElementById('title').value.trim();
  const authors = getAuthors();
  const totalCopies = parseInt(document.getElementById('totalCopies').value);
  
  // Clean up placeholder title if present
  if (title === 'Fetching title...') {
    title = '';
  }
  
  // Validate
  if (!validateForm(isbn, title, totalCopies)) {
    return;
  }
  
  // Show loading state
  addBookState.isSubmitting = true;
  const submitBtn = document.getElementById('submitBtn');
  const originalText = submitBtn.textContent;
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<div class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></div> Adding Book...';
  
  try {
    // Call API - use fetched metadata if available, otherwise use form values
    const response = await api.addBook({
      isbn: isbn || null,
      title: title || (addBookState.metadataFetched?.metadata_preview?.title || ''),
      authors: authors.length > 0 ? authors : (addBookState.metadataFetched?.metadata_preview?.authors || null),
      total_copies: totalCopies
    });
    
    console.log('Book added:', response);
    
    // Show success message
    showToast(`Book added successfully! Pending ID: ${response.pending_id}`, 'success');
    
    // Display metadata if available
    if (response.metadata_preview) {
      displayMetadataPreview(response);
    }
    
    // Ask user what to do next
    setTimeout(() => {
      if (confirm('Book added to pending catalogue!\n\nGo to Pending Catalogue to review?')) {
        window.location.href = `pending.html?highlight=${response.pending_id}`;
      } else {
        // Reset form for adding another book
        resetForm();
      }
    }, 1000);
    
  } catch (error) {
    console.error('Error adding book:', error);
    showToast('Failed to add book: ' + error.message, 'error');
  } finally {
    // Restore button
    addBookState.isSubmitting = false;
    submitBtn.disabled = false;
    submitBtn.textContent = originalText;
  }
}

/**
 * Validate form
 */
function validateForm(isbn, title, totalCopies) {
  let isValid = true;
  
  // Clear previous errors
  document.querySelectorAll('.form-error').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.form-control').forEach(el => el.classList.remove('is-invalid'));
  
  // Validate ISBN if provided
  if (isbn && !validateISBN(isbn)) {
    document.getElementById('isbn').classList.add('is-invalid');
    document.getElementById('isbnError').textContent = 'Invalid ISBN format';
    document.getElementById('isbnError').classList.remove('hidden');
    isValid = false;
  }
  
  // Validate title (required unless ISBN provided or metadata fetched)
  const hasFetchedMetadata = addBookState.metadataFetched?.metadata_preview?.title;
  if (!title && !isbn && !hasFetchedMetadata) {
    document.getElementById('title').classList.add('is-invalid');
    document.getElementById('titleError').textContent = 'Title is required (or provide ISBN)';
    document.getElementById('titleError').classList.remove('hidden');
    isValid = false;
  }
  
  // Validate total copies
  if (!totalCopies || totalCopies < 1) {
    document.getElementById('totalCopies').classList.add('is-invalid');
    document.getElementById('copiesError').textContent = 'Must be at least 1';
    document.getElementById('copiesError').classList.remove('hidden');
    isValid = false;
  }
  
  // Need at least ISBN or title or fetched metadata
  if (!isbn && !title && !hasFetchedMetadata) {
    showToast('Please enter either ISBN or title', 'warning');
    isValid = false;
  }
  
  return isValid;
}

/**
 * Get authors from input fields
 */
function getAuthors() {
  const authorInputs = document.querySelectorAll('.author-input');
  const authors = [];
  
  authorInputs.forEach(input => {
    const value = input.value.trim();
    if (value) {
      authors.push(value);
    }
  });
  
  return authors;
}

/**
 * Add author field
 */
function addAuthorField() {
  const container = document.getElementById('authorsContainer');
  const index = addBookState.authorCount;
  
  const fieldHTML = `
    <div class="input-group mb-1">
      <input 
        type="text" 
        class="form-control author-input" 
        placeholder="Author name"
        data-index="${index}"
      >
      <button type="button" class="btn btn-outline" onclick="removeAuthor(${index})">Remove</button>
    </div>
  `;
  
  container.insertAdjacentHTML('beforeend', fieldHTML);
  addBookState.authorCount++;
}

/**
 * Remove author field
 */
function removeAuthor(index) {
  const authorInputs = document.querySelectorAll('.author-input');
  
  // Don't remove if only one field left
  if (authorInputs.length <= 1) {
    showToast('At least one author field is required', 'warning');
    return;
  }
  
  // Find and remove the field
  const field = document.querySelector(`.author-input[data-index="${index}"]`);
  if (field) {
    field.closest('.input-group').remove();
  }
}

/**
 * Increment copies
 */
function incrementCopies() {
  const input = document.getElementById('totalCopies');
  const currentValue = parseInt(input.value) || 1;
  input.value = currentValue + 1;
}

/**
 * Decrement copies
 */
function decrementCopies() {
  const input = document.getElementById('totalCopies');
  const currentValue = parseInt(input.value) || 1;
  if (currentValue > 1) {
    input.value = currentValue - 1;
  }
}

/**
 * Validate copies
 */
function validateCopies() {
  const input = document.getElementById('totalCopies');
  const value = parseInt(input.value);
  
  if (!value || value < 1) {
    input.value = 1;
  }
}

/**
 * Reset form
 */
function resetForm() {
  document.getElementById('addBookForm').reset();
  document.getElementById('totalCopies').value = 1;
  
  // Clear validation states
  document.querySelectorAll('.form-control').forEach(el => {
    el.classList.remove('is-invalid', 'is-valid');
  });
  document.querySelectorAll('.form-error, .form-success').forEach(el => {
    el.classList.add('hidden');
  });
  
  // Reset authors to one field
  const container = document.getElementById('authorsContainer');
  container.innerHTML = `
    <div class="input-group mb-1">
      <input 
        type="text" 
        class="form-control author-input" 
        placeholder="Author name"
        data-index="0"
      >
      <button type="button" class="btn btn-outline" onclick="removeAuthor(0)">Remove</button>
    </div>
  `;
  addBookState.authorCount = 1;
  
  // Hide metadata preview
  hideMetadataPreview();
  
  // Reset state
  addBookState.metadataFetched = null;
  
  showToast('Form reset', 'info');
}

// Initialize on page load
// Wait for all scripts to load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initAddBook, 100);
  });
} else {
  setTimeout(initAddBook, 100);
}

