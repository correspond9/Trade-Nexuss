#!/bin/bash

# GitHub Setup Script for Broking Terminal V2
set -e

echo "🚀 Setting up GitHub repository for Broking Terminal V2..."

# Check if git is initialized
if [ ! -d .git ]; then
    echo "❌ Git repository not initialized. Please run 'git init' first."
    exit 1
fi

# Prompt for GitHub username
read -p "Enter your GitHub username: " USERNAME

if [ -z "$USERNAME" ]; then
    echo "❌ Username cannot be empty."
    exit 1
fi

# Repository name
REPO_NAME="broking-terminal-v2"

echo "📝 Creating remote repository: https://github.com/$USERNAME/$REPO_NAME.git"

# Add remote origin
git remote add origin "https://github.com/$USERNAME/$REPO_NAME.git" 2>/dev/null || {
    echo "⚠️  Remote 'origin' already exists. Updating..."
    git remote set-url origin "https://github.com/$USERNAME/$REPO_NAME.git"
}

# Push to GitHub
echo "📤 Pushing code to GitHub..."
git push -u origin main

echo "✅ Repository setup complete!"
echo ""
echo "🌐 Your repository is available at: https://github.com/$USERNAME/$REPO_NAME"
echo ""
echo "📋 Next steps:"
echo "1. Visit your repository on GitHub"
echo "2. Add repository description and topics"
echo "3. Enable GitHub Actions for CI/CD"
echo "4. Set up GitHub Secrets for environment variables"
echo "5. Follow the deployment guide in GITHUB_SETUP.md"
echo ""
echo "🎉 Happy coding!"
