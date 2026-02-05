@echo off
REM GitHub Setup Script for Broking Terminal V2 (Windows)

echo 🚀 Setting up GitHub repository for Broking Terminal V2...

REM Check if git is initialized
if not exist .git (
    echo ❌ Git repository not initialized. Please run 'git init' first.
    exit /b 1
)

REM Prompt for GitHub username
set /p USERNAME="Enter your GitHub username: "

if "%USERNAME%"=="" (
    echo ❌ Username cannot be empty.
    exit /b 1
)

REM Repository name
set REPO_NAME=broking-terminal-v2

echo 📝 Creating remote repository: https://github.com/%USERNAME%/%REPO_NAME%.git

REM Add remote origin
git remote add origin "https://github.com/%USERNAME%/%REPO_NAME%.git" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Remote 'origin' already exists. Updating...
    git remote set-url origin "https://github.com/%USERNAME%/%REPO_NAME%.git"
)

REM Push to GitHub
echo 📤 Pushing code to GitHub...
git push -u origin main

echo ✅ Repository setup complete!
echo.
echo 🌐 Your repository is available at: https://github.com/%USERNAME%/%REPO_NAME%
echo.
echo 📋 Next steps:
echo 1. Visit your repository on GitHub
echo 2. Add repository description and topics  
echo 3. Enable GitHub Actions for CI/CD
echo 4. Set up GitHub Secrets for environment variables
echo 5. Follow the deployment guide in GITHUB_SETUP.md
echo.
echo 🎉 Happy coding!
