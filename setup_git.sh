#!/bin/bash
# Git setup script for Unexpected Vibe Trader

echo "🚀 Setting up Git repository..."

# Initialize git if not already done
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
fi

# Add remote
echo "Adding GitHub remote..."
git remote add origin https://github.com/UnexpectedIteminbagginarea/Unexpected_vibe_trader.git

# Verify remote
echo "Verifying remote..."
git remote -v

# Create initial commit if needed
if [ -z "$(git log 2>/dev/null)" ]; then
    echo "Creating initial commit..."
    git add .
    git commit -m "Initial commit: Vibe Trader for Aster Competition"
fi

# Show status
echo "Git status:"
git status

echo ""
echo "✅ Git setup complete!"
echo ""
echo "To push to GitHub, run:"
echo "  git branch -M main"
echo "  git push -u origin main"
