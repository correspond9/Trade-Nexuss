@echo off
REM Push to GitHub after manual repository creation

echo 🚀 Pushing Trade-Nexuss to GitHub...
echo.

REM Check if we're on master branch
git branch

REM Push to GitHub
echo 📤 Pushing code to GitHub...
git push -u origin master

echo.
echo ✅ Repository successfully pushed to GitHub!
echo.
echo 🌐 Your repository is available at: https://github.com/correspond9/Trade-Nexuss
echo.
echo 📋 Next steps:
echo 1. Visit your repository on GitHub
echo 2. Add repository description and topics
echo 3. Enable GitHub Actions for CI/CD
echo 4. Set up GitHub Secrets for environment variables
echo 5. Follow the deployment guide in GITHUB_SETUP.md
echo.
echo 🎉 Your project is now on GitHub!
