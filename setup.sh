#!/bin/bash

# PyBiorythm Django API Server Setup Script
# This script sets up the development environment and creates API tokens

set -e  # Exit on any error

echo "🚀 Setting up PyBiorythm Django API Server..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo "🔧 Creating virtual environment and installing dependencies..."
uv venv
source .venv/bin/activate
uv sync

echo "🗄️ Running database migrations..."
uv run python manage.py migrate

echo "👤 Creating superuser account..."
echo "Creating admin user with credentials:"
echo "Username: admin"
echo "Email: admin@example.com" 
echo "Password: admin123"
echo ""

# Create superuser non-interactively
DJANGO_SUPERUSER_PASSWORD=admin123 uv run python manage.py createsuperuser \
    --username admin \
    --email admin@example.com \
    --noinput || echo "Superuser already exists"

echo "🔑 Creating API token for admin user..."
uv run python manage.py shell -c "
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

try:
    user = User.objects.get(username='admin')
    token, created = Token.objects.get_or_create(user=user)
    print(f'API Token for admin: {token.key}')
    
    # Save token to file for easy access
    with open('auth_token.txt', 'w') as f:
        f.write(f'Admin API Token: {token.key}\n')
        f.write(f'Usage: Authorization: Token {token.key}\n')
    
    print('Token saved to auth_token.txt')
except Exception as e:
    print(f'Error creating token: {e}')
"

echo "📊 Loading sample biorhythm data..."
uv run python manage.py load_biorhythm_data \
    --name "API Demo User" \
    --birthdate "1990-06-15" \
    --days 180 \
    --email "demo@example.com" \
    --notes "Sample data for API demonstration"

echo "✅ Setup complete!"
echo ""
echo "🌐 To start the ASGI server:"
echo "   source .venv/bin/activate"
echo "   uv run daphne biorhythm_api.asgi:application -p 8001"
echo ""
echo "📋 Access the application:"
echo "   - API Root: http://127.0.0.1:8001/api/"
echo "   - Django Admin: http://127.0.0.1:8001/admin/"
echo "   - API Token: Check auth_token.txt file"
echo ""
echo "🔐 Admin credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📖 Test the API:"
echo "   curl -H \"Authorization: Token \$(cat auth_token.txt | grep Token | cut -d' ' -f4)\" http://127.0.0.1:8001/api/people/"