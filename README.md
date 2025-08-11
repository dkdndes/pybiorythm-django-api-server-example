# PyBiorythm Django API Server Example

A production-ready Django REST API server with ASGI/Daphne integration for serving biorhythm data from the [PyBiorythm](https://github.com/dkdndes/pybiorythm) library. Features token authentication, real-time calculations, and comprehensive API endpoints.

## 🌟 Features

- **Django REST Framework** with comprehensive API endpoints
- **ASGI Server** with Daphne for async request handling
- **Token Authentication** for secure API access
- **Real-time Biorhythm Calculations** using PyBiorythm library
- **Database Integration** with biorhythm data storage
- **CORS Support** for cross-origin requests
- **API Documentation** with browsable API interface
- **Filtering & Pagination** for efficient data access
- **Statistics Endpoints** for data analysis

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [API Endpoints](#api-endpoints)
- [Authentication](#authentication)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Testing](#testing)
- [Contributing](#contributing)

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/dkdndes/pybiorythm-django-api-server-example.git
   cd pybiorythm-django-api-server-example
   ```

2. **Set up virtual environment and install dependencies**
   ```bash
   # Install uv if you haven't already
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Create virtual environment and install dependencies
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv sync
   ```

3. **Run migrations**
   ```bash
   uv run python manage.py migrate
   ```

4. **Create superuser and API token**
   ```bash
   uv run python manage.py createsuperuser
   ```

5. **Load sample data**
   ```bash
   uv run python manage.py load_biorhythm_data --name "API Demo User" --birthdate "1990-01-15" --days 365
   ```

6. **Start the ASGI server**
   ```bash
   uv run daphne biorhythm_api.asgi:application -p 8001
   ```

7. **Access the API**
   - API Root: http://127.0.0.1:8001/api/
   - Admin Panel: http://127.0.0.1:8001/admin/
   - API Documentation: http://127.0.0.1:8001/api/docs/

## 📦 Installation

### Prerequisites

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation with uv

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync
```

### Dependencies

This project uses the following key dependencies:

- **Django** 5.2.5+ - Web framework
- **Django REST Framework** 3.14.0+ - REST API framework
- **Daphne** 4.0.0+ - ASGI server for async handling
- **Channels** 4.0.0+ - WebSocket and async support
- **PyBiorythm** - Real biorhythm calculations from GitHub
- **django-cors-headers** 4.0.0+ - CORS support for cross-origin requests
- **pandas** 2.0.0+ - Data analysis and statistics

## 🔌 API Endpoints

### Core Endpoints

#### People Management
```
GET    /api/people/                    # List all people
POST   /api/people/                    # Create new person
GET    /api/people/{id}/               # Get person details
PUT    /api/people/{id}/               # Update person
DELETE /api/people/{id}/               # Delete person
```

#### Biorhythm Data
```
GET    /api/people/{id}/biorhythm_data/    # Get biorhythm data for person
GET    /api/people/{id}/statistics/        # Get statistics for person
POST   /api/calculations/                  # Create new calculation
GET    /api/calculations/{id}/             # Get calculation details
```

#### Real-time Calculations
```
POST   /api/calculations/calculate/        # Calculate biorhythm data
```

### Advanced Endpoints

#### Filtering & Search
```bash
# Filter by date range
GET /api/people/1/biorhythm_data/?start_date=2024-01-01&end_date=2024-12-31

# Filter by critical days
GET /api/people/1/biorhythm_data/?is_physical_critical=true

# Search people
GET /api/people/?search=john

# Pagination
GET /api/people/?page=2&page_size=10
```

## 🔐 Authentication

### Token Authentication

1. **Create a user and get token**:
   ```bash
   # Via Django Admin
   uv run python manage.py createsuperuser
   
   # Get token via API
   curl -X POST http://127.0.0.1:8001/api-token-auth/ \
        -H "Content-Type: application/json" \
        -d '{"username": "your_username", "password": "your_password"}'
   ```

2. **Use token in requests**:
   ```bash
   curl -H "Authorization: Token your_token_here" \
        http://127.0.0.1:8001/api/people/
   ```

### API Token Management

```python
# Create token programmatically
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

user = User.objects.get(username='your_username')
token, created = Token.objects.get_or_create(user=user)
print(f"Token: {token.key}")
```

## 💻 Usage Examples

### Basic API Usage

#### Create a Person
```bash
curl -X POST http://127.0.0.1:8001/api/people/ \
     -H "Authorization: Token your_token" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "John Doe",
       "birthdate": "1985-03-15",
       "email": "john@example.com"
     }'
```

#### Calculate Biorhythm Data
```bash
curl -X POST http://127.0.0.1:8001/api/calculations/calculate/ \
     -H "Authorization: Token your_token" \
     -H "Content-Type: application/json" \
     -d '{
       "person_id": 1,
       "days": 30,
       "notes": "Monthly calculation"
     }'
```

#### Get Biorhythm Data
```bash
curl -H "Authorization: Token your_token" \
     "http://127.0.0.1:8001/api/people/1/biorhythm_data/?limit=10"
```

#### Get Statistics
```bash
curl -H "Authorization: Token your_token" \
     "http://127.0.0.1:8001/api/people/1/statistics/"
```

### Python Client Example

```python
import requests

# Setup
base_url = "http://127.0.0.1:8001/api"
headers = {"Authorization": "Token your_token_here"}

# Create person
person_data = {
    "name": "Alice Smith",
    "birthdate": "1992-07-20",
    "email": "alice@example.com"
}
response = requests.post(f"{base_url}/people/", json=person_data, headers=headers)
person = response.json()

# Calculate biorhythm data
calc_data = {
    "person_id": person["id"],
    "days": 365,
    "notes": "Annual calculation"
}
response = requests.post(f"{base_url}/calculations/calculate/", json=calc_data, headers=headers)
calculation = response.json()

# Get biorhythm data
response = requests.get(f"{base_url}/people/{person['id']}/biorhythm_data/", headers=headers)
biorhythm_data = response.json()

print(f"Calculated {calculation['data_points_created']} data points")
print(f"Retrieved {len(biorhythm_data['biorhythm_data'])} data points")
```

### JavaScript/Fetch Example

```javascript
const baseUrl = 'http://127.0.0.1:8001/api';
const token = 'your_token_here';

// Get people
async function getPeople() {
    const response = await fetch(`${baseUrl}/people/`, {
        headers: {
            'Authorization': `Token ${token}`,
            'Content-Type': 'application/json'
        }
    });
    return await response.json();
}

// Calculate biorhythm data
async function calculateBiorhythm(personId, days = 30) {
    const response = await fetch(`${baseUrl}/calculations/calculate/`, {
        method: 'POST',
        headers: {
            'Authorization': `Token ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            person_id: personId,
            days: days,
            notes: 'Client calculation'
        })
    });
    return await response.json();
}
```

## ⚙️ Configuration

### Django Settings

Key settings in `biorhythm_api/settings.py`:

```python
# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# CORS configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:8002",
]

# ASGI configuration
ASGI_APPLICATION = 'biorhythm_api.asgi.application'
```

### Environment Variables

Create a `.env` file:

```bash
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:8002

# Database (for production)
DATABASE_URL=postgresql://user:pass@localhost/dbname

# API Configuration
API_PAGE_SIZE=20
API_MAX_PAGE_SIZE=100
```

## 🐳 Deployment

### Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

COPY . .
RUN uv run python manage.py migrate
RUN uv run python manage.py collectstatic --noinput

EXPOSE 8001
CMD ["uv", "run", "daphne", "biorhythm_api.asgi:application", "-p", "8001", "-b", "0.0.0.0"]
```

#### Docker Compose
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8001:8001"
    environment:
      - DEBUG=0
      - DATABASE_URL=postgresql://biorhythm:password@db:5432/biorhythm
    depends_on:
      - db
      
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: biorhythm
      POSTGRES_USER: biorhythm
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Production Deployment

1. **Use PostgreSQL** for production database
2. **Configure Nginx** as reverse proxy
3. **Set up SSL/TLS** certificates
4. **Configure monitoring** and logging
5. **Set up backup** strategies

```bash
# Production setup
export DEBUG=False
export DATABASE_URL="postgresql://user:pass@localhost/biorhythm"
export SECRET_KEY="your-production-secret-key"

# Run with production server
uv run daphne biorhythm_api.asgi:application -p 8001 -b 0.0.0.0
```

## 🧪 Testing

### Run Tests

```bash
# Run all tests
uv run python manage.py test

# Run with coverage
uv run coverage run --source='.' manage.py test
uv run coverage report
uv run coverage html
```

### API Testing

```bash
# Install HTTPie for API testing
uv sync --extra dev

# Test endpoints
http GET http://127.0.0.1:8001/api/people/ "Authorization:Token your_token"
http POST http://127.0.0.1:8001/api/people/ name="Test User" birthdate="1990-01-01" "Authorization:Token your_token"
```

### Load Testing

```python
# Example load test script
import asyncio
import aiohttp
import time

async def test_api_endpoint():
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": "Token your_token"}
        
        start_time = time.time()
        tasks = []
        
        for i in range(100):  # 100 concurrent requests
            task = session.get(
                "http://127.0.0.1:8001/api/people/1/biorhythm_data/",
                headers=headers
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        print(f"100 requests completed in {end_time - start_time:.2f} seconds")
        print(f"Average response time: {(end_time - start_time) / 100:.3f} seconds")

# Run load test
asyncio.run(test_api_endpoint())
```

## 📊 Performance

### Optimization Features

- **Database Indexes** on frequently queried fields
- **Pagination** to limit response sizes
- **Async Request Handling** with Daphne/ASGI
- **Query Optimization** with select_related and prefetch_related
- **Caching** support for frequently accessed data

### Monitoring

```python
# Add to settings.py for monitoring
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'api.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Setup
```bash
# Install development dependencies
uv sync --extra dev

# Run tests before committing
uv run python manage.py test
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- **[PyBiorythm](https://github.com/dkdndes/pybiorythm)** - Core biorhythm calculation library
- **[PyBiorythm Django SQLite](https://github.com/dkdndes/pybiorythm-django-sqlite-example)** - Database integration example
- **[PyBiorythm Django Dashboard](https://github.com/dkdndes/pybiorythm-django-dashboard-example)** - Visualization dashboard example

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/dkdndes/pybiorythm-django-api-server-example/issues)
- **Documentation**: [API Documentation](https://github.com/dkdndes/pybiorythm-django-api-server-example/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/dkdndes/pybiorythm-django-api-server-example/discussions)

## 🙏 Acknowledgments

- **PyBiorythm Library** by [dkdndes](https://github.com/dkdndes)
- **Django REST Framework** by the DRF team
- **Daphne ASGI Server** by the Django Channels team

---

**Made with ❤️ for the PyBiorythm community**