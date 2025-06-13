# FastAPI Supabase SIP Management

A FastAPI application for managing Systematic Investment Plans (SIPs) using Supabase as the backend.

## Setup Instructions

1. Create a virtual environment and activate it:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Supabase:
   - Create a new project on [Supabase](https://supabase.com)
   - Create a new table called `sips` with the following columns:
     - `user_id` (text)
     - `scheme_name` (text)
     - `monthly_amount` (integer)
     - `start_date` (text)
   - Get your Supabase URL and keys from the project settings

4. Update the Supabase configuration in `fastapi-supabase-auth.py`:
```python
SUPABASE_URL = "your_supabase_project_url"
SUPABASE_ANON_KEY = "your_supabase_anon_key"
SUPABASE_SERVICE_KEY = "your_supabase_service_role_key"
```

5. Run the application:
```bash
uvicorn fastapi-supabase-auth:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Sign Up User
```http
POST /auth/signup
Content-Type: application/json

{
    "username": "testuser",
    "password": "testpass123"
}
```

### 2. Create SIP
```http
POST /auth/sip
Content-Type: application/json

{
    "user_id": "user_id_from_signup",
    "scheme_name": "Equity Fund SIP",
    "monthly_amount": 5000,
    "start_date": "2024-03-20"
}
```

### 3. Get SIP Summary
```http
GET /auth/sips/summary/{user_id}
```

Response:
```json
{
    "schemes": [
        {
            "scheme_name": "Equity Fund SIP",
            "total_investment": 5000,
            "months_invested": 1
        }
    ],
    "total_investment": 5000
}
```

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Error Handling

The API returns appropriate HTTP status codes and error messages:
- 201: Created successfully
- 400: Bad request
- 404: User not found
- 500: Internal server error

## Development

- The application uses FastAPI for the API framework
- Supabase for authentication and database
- Python 3.12+ is required
- Hot reload is enabled for development 