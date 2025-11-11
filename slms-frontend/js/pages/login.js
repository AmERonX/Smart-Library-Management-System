/**
 * Login/Register Page Logic
 */

/**
 * Switch between login and register tabs
 */
function switchTab(tab) {
  // Update tab buttons
  document.querySelectorAll('.login-tab').forEach(btn => {
    btn.classList.remove('active');
  });
  event.target.classList.add('active');
  
  // Update forms
  document.getElementById('loginForm').classList.toggle('active', tab === 'login');
  document.getElementById('registerForm').classList.toggle('active', tab === 'register');
}

/**
 * Handle login form submission
 */
async function handleLogin(event) {
  event.preventDefault();
  
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;
  
  const submitBtn = event.target.querySelector('button[type="submit"]');
  const originalText = submitBtn.textContent;
  submitBtn.disabled = true;
  submitBtn.textContent = 'Logging in...';
  
  try {
    // Validate input
    if (!username || !password) {
      showToast('Please enter both username and password', 'error');
      submitBtn.disabled = false;
      submitBtn.textContent = originalText;
      return;
    }
    
    console.log('Logging in user:', username);
    
    const response = await api.login({ 
      username: username.trim(), 
      password: password 
    });
    
    // Store token
    Auth.setToken(response.access_token);
    
    // Store user info
    localStorage.setItem('user', JSON.stringify(response.user));
    
    showToast('Login successful!', 'success');
    
    // Redirect based on user role
    const userRole = response.user.role;
    setTimeout(() => {
      if (userRole === 'admin' || userRole === 'librarian') {
        // Admin/Librarian goes to librarian dashboard
        window.location.href = 'index.html';
      } else {
        // Student goes to user dashboard
        window.location.href = 'user-dashboard.html';
      }
    }, 1000);
    
  } catch (error) {
    console.error('Login error:', error);
    console.error('Error details:', {
      message: error.message,
      status: error.status,
      data: error.data
    });
    
    // Extract detailed error message
    let errorMessage = 'Login failed';
    if (error.message) {
      errorMessage = error.message;
    } else if (error.data && error.data.detail) {
      if (Array.isArray(error.data.detail)) {
        errorMessage = error.data.detail.map(err => {
          const field = err.loc ? err.loc.slice(1).join('.') : 'field';
          return `${field}: ${err.msg}`;
        }).join('; ');
      } else {
        errorMessage = error.data.detail;
      }
    }
    
    showToast(errorMessage, 'error');
    submitBtn.disabled = false;
    submitBtn.textContent = originalText;
  }
}

/**
 * Handle register form submission
 */
async function handleRegister(event) {
  event.preventDefault();
  
  const username = document.getElementById('registerUsername').value.trim();
  const email = document.getElementById('registerEmail').value.trim();
  const password = document.getElementById('registerPassword').value;
  const role = document.getElementById('registerRole').value;
  
  const submitBtn = event.target.querySelector('button[type="submit"]');
  const originalText = submitBtn.textContent;
  submitBtn.disabled = true;
  submitBtn.textContent = 'Registering...';
  
  try {
    // Validate input before sending
    if (!username || username.length < 3) {
      showToast('Username must be at least 3 characters', 'error');
      return;
    }
    if (!email || !validateEmail(email)) {
      showToast('Please enter a valid email address', 'error');
      return;
    }
    if (!password || password.length < 6) {
      showToast('Password must be at least 6 characters', 'error');
      return;
    }
    if (role && !['student', 'admin', 'librarian'].includes(role)) {
      showToast('Invalid role selected', 'error');
      return;
    }
    
    // Prepare request data
    const requestData = {
      username: username.trim(),
      email: email.trim().toLowerCase(),
      password: password,
      role: role || 'student'
    };
    
    console.log('Registering user with data:', { ...requestData, password: '***' });
    
    const response = await api.register(requestData);
    
    showToast('Registration successful! Please login.', 'success');
    
    // Switch to login tab
    setTimeout(() => {
      document.querySelector('.login-tab').click();
      document.getElementById('loginUsername').value = username;
      document.getElementById('loginPassword').focus();
    }, 1500);
    
  } catch (error) {
    console.error('Registration error:', error);
    console.error('Error details:', {
      message: error.message,
      status: error.status,
      data: error.data
    });
    
    // Extract detailed error message
    let errorMessage = 'Registration failed';
    if (error.message) {
      errorMessage = error.message;
    } else if (error.data && error.data.detail) {
      if (Array.isArray(error.data.detail)) {
        errorMessage = error.data.detail.map(err => {
          const field = err.loc ? err.loc.slice(1).join('.') : 'field';
          return `${field}: ${err.msg}`;
        }).join('; ');
      } else {
        errorMessage = error.data.detail;
      }
    }
    
    showToast(errorMessage, 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = originalText;
  }
}

