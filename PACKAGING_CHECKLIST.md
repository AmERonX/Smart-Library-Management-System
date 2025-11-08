# Packaging Checklist for SLMS

Use this checklist before sharing your codebase with others to ensure they can set it up successfully.

**Related Documents:**
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - What your users will follow
- [README.md](README.md) - First thing users see
- [verify_setup.py](verify_setup.py) - Users run this to verify setup

## Pre-Packaging Checklist

### 1. Documentation
- [ ] `README.md` is up to date with current features
- [ ] `SETUP_GUIDE.md` exists with step-by-step instructions
- [ ] `.env.example` exists with all required variables
- [ ] API documentation is complete in `docs/`
- [ ] All special setup requirements are documented

### 2. Dependencies
- [ ] `requirements.txt` is up to date
  ```bash
  pip freeze > requirements.txt
  ```
- [ ] All dependencies have version numbers
- [ ] No local/development-only packages in requirements.txt

### 3. Configuration Files
- [ ] `.env.example` exists (DO NOT include actual `.env`)
- [ ] `.env.example` has placeholder values
- [ ] `.gitignore` includes `.env` and sensitive files
- [ ] Database connection strings use placeholders

### 4. Database
- [ ] `db/Schema/db_files.sql` is complete and tested
- [ ] All migrations are in `db/migrations/` and numbered
- [ ] Schema creates all required tables
- [ ] No hardcoded credentials in SQL files

### 5. Code Quality
- [ ] No hardcoded passwords or API keys
- [ ] No absolute file paths (use relative paths)
- [ ] No machine-specific configurations
- [ ] All imports are from installed packages (not local system)
- [ ] No debug print statements or commented-out code

### 6. Testing
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Test database connection works
- [ ] Health endpoint returns correct status
- [ ] Sample API calls work as documented

### 7. Scripts
- [ ] Startup scripts work (`start_server.ps1`, etc.)
- [ ] Scripts use relative paths, not absolute
- [ ] Scripts handle missing dependencies gracefully

### 8. Files to EXCLUDE from Package
- [ ] `.env` (actual environment file)
- [ ] `__pycache__/` directories
- [ ] `.pytest_cache/`
- [ ] `venv/` or `env/` directories
- [ ] `.vscode/` or `.idea/` IDE settings
- [ ] `*.pyc` files
- [ ] `*.log` files
- [ ] `test.db` or other test databases
- [ ] `.git/` directory (if sharing as ZIP)

### 9. Files to INCLUDE in Package
- [x] `README.md`
- [x] `SETUP_GUIDE.md`
- [x] `PACKAGING_CHECKLIST.md` (this file)
- [x] `requirements.txt`
- [x] `.env.example`
- [x] `.gitignore`
- [x] All `.py` source files
- [x] All `db/` SQL files
- [x] All `docs/` documentation
- [x] `start_server.ps1` or startup scripts
- [x] `verify_setup.py` (setup verification script)

## Packaging Methods

### Method 1: ZIP File (Recommended for Beginners)

```bash
# Windows PowerShell
Compress-Archive -Path * -DestinationPath SLMS_checkpoint2.zip -Force

# Exclude unnecessary files
$exclude = @('venv', '.env', '__pycache__', '.pytest_cache', '.git', '*.pyc', '*.log', 'test.db')
Get-ChildItem -Exclude $exclude | Compress-Archive -DestinationPath SLMS_checkpoint2.zip
```

### Method 2: Git Repository (Recommended for Developers)

```bash
# Initialize git (if not already)
git init

# Add all files (respects .gitignore)
git add .

# Commit
git commit -m "Initial commit"

# Push to GitHub/GitLab
git remote add origin <your-repo-url>
git push -u origin main
```

## Testing the Package

### Before Sending to Others:

1. **Test in a clean environment:**
   ```bash
   # Create a test directory
   mkdir test_setup
   cd test_setup
   
   # Extract your ZIP or clone your repo
   unzip ../SLMS_checkpoint2.zip
   # OR
   git clone <your-repo-url> .
   
   # Follow SETUP_GUIDE.md exactly
   # Document any issues you encounter
   ```

2. **Run verification script:**
   ```bash
   python verify_setup.py
   ```

3. **Test the complete workflow:**
   ```bash
   # Start server
   .\start_server.ps1
   
   # In another terminal, test endpoints
   curl http://127.0.0.1:8000/health
   ```

### Ask a Friend to Test:

The best way to verify portability is to have someone else set it up:

1. Send them the ZIP/repo link
2. Send them `SETUP_GUIDE.md`
3. Ask them to document:
   - What worked
   - What didn't work
   - What was confusing
   - How long it took

## Common Issues to Prevent

### Issue 1: Missing Dependencies
**Prevention:** Always regenerate `requirements.txt` before packaging
```bash
pip freeze > requirements.txt
```

### Issue 2: Hardcoded Paths
**Prevention:** Use relative paths or environment variables
```python
# Bad
DB_PATH = "C:/Users/YourName/project/database.db"

# Good
DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")
```

### Issue 3: Missing .env.example
**Prevention:** Always include `.env.example` with placeholders
```env
# .env.example
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/slms
```

### Issue 4: Platform-Specific Code
**Prevention:** Use cross-platform libraries
```python
# Bad
os.system("cls")  # Windows only

# Good
import os
os.system('cls' if os.name == 'nt' else 'clear')
```

### Issue 5: Undocumented Setup Steps
**Prevention:** Document EVERYTHING in `SETUP_GUIDE.md`
- PostgreSQL installation
- Database creation
- Special character encoding in passwords
- Virtual environment activation

## Post-Packaging Verification

After creating your package, verify:

1. [ ] ZIP file size is reasonable (<50MB without venv)
2. [ ] All required files are present
3. [ ] No sensitive data included (.env, credentials)
4. [ ] README.md opens correctly
5. [ ] Can extract and follow SETUP_GUIDE.md successfully

## Sharing Checklist

Before sending to others:

- [ ] Package tested in clean environment
- [ ] Documentation reviewed and updated
- [ ] No sensitive data in package
- [ ] Setup time estimated and documented
- [ ] Contact information provided for support
- [ ] Known issues documented

## Support Information

When sharing with others, provide:

1. **Expected setup time:** ~15-20 minutes
2. **Prerequisites:** Python 3.10+, PostgreSQL 12+
3. **Contact:** Your email/Discord/Slack for questions
4. **Known issues:** List any current bugs or limitations
5. **Troubleshooting:** Link to SETUP_GUIDE.md

## Example Sharing Message

```
Hi! Here's the SLMS project.

Setup time: ~15-20 minutes
Prerequisites: Python 3.10+, PostgreSQL 12+

Steps:
1. Extract the ZIP file
2. Follow SETUP_GUIDE.md step-by-step
3. Run verify_setup.py to check your installation
4. Start the server with start_server.ps1

If you encounter issues:
- Check SETUP_GUIDE.md troubleshooting section
- Run verify_setup.py to diagnose problems
- Contact me at [your-email]

The health endpoint should return "operational" when setup is complete.
```

---

**Last Updated:** 2025-10-11
