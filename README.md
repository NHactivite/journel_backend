# 🌿 AI-Assisted Journal System

An AI-powered journaling app where users write about nature sessions and get emotion analysis using a Large Language Model.

---

## Tech Stack

| Layer     | Technology               |
|-----------|--------------------------|
| Backend   | Python + FastAPI          |
| Frontend  | Next.js + Tailwind CSS    |
| Database  | SQLite                    |
| LLM       | HuggingFace (gpt-oss-20b) |
| Auth      | JWT (via httpOnly cookies)|

---

## Project Structure

```
├── backend/
│   ├── main.py           # FastAPI app + all routes
│   ├── auth.py           # Register, login, logout, /me
│   ├── llm.py            # LLM integration (analyze + process)
│   ├── database.py       # SQLite connection + table setup
│   ├── middleware.py     # JWT auth dependency
│   ├── .env              # Environment variables (not committed)
│   └── pyproject.toml    # uv dependencies
│
└── frontend/
    ├── app/
    │   ├── page.jsx               # Main journal page (protected)
    │   ├── login/page.jsx         # Login page
    │   ├── register/page.jsx      # Register page
    │   └── api/
    │       └── auth/
    │           ├── login/route.js
    │           ├── register/route.js
    │           ├── logout/route.js
    │           └── profile/route.js
    └── container/
        ├── Header.jsx
        ├── Write_tab.jsx
        ├── Analyze.jsx
        ├── TotalEntries.jsx
        └── Insight.jsx
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- HuggingFace account + API token

---

### Backend Setup

```bash
# 1. Go to backend folder
cd backend

# 2. Install dependencies with uv
uv sync

# 3. Create .env file
cp .env.example .env
# Fill in your values

# 4. Run the server
uv run uvicorn main:app --reload
```

> Or if your virtual environment is already activated:
> ```bash
> uvicorn main:app --reload
> ```

Backend runs at: `http://localhost:8000`  
Swagger docs at: `http://localhost:8000/docs`

### Environment Variables
```
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
EXPIRE_DAYS=7
HUGGINGFACEHUB_API_TOKEN=your-huggingface-token
```

> Generate a strong secret key:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

**frontend/.env.local**
```
NEXT_PUBLIC_SERVER=http://localhost:8000
```

---

## API Endpoints

### Auth
| Method | Endpoint           | Description        |
|--------|--------------------|--------------------|
| POST   | /api/auth/register | Register new user  |
| POST   | /api/auth/login    | Login + set cookie |
| POST   | /api/auth/logout   | Clear cookie       |
| GET    | /api/auth/me       | Get current user   |

### Journal
| Method | Endpoint                      | Description                   |
|--------|-------------------------------|-------------------------------|
| POST   | /api/journal                  | Save entry + run LLM analysis |
| GET    | /api/journal/:userId          | Get all entries for user      |
| POST   | /api/journal/analyze          | Analyze text (no DB save)     |
| GET    | /api/journal/insights/:userId | Get insights stats            |

---

## Features

- ✅ Write journal entries with nature ambience (forest, ocean, mountain)
- ✅ LLM emotion analysis — detects emotion, keywords, summary
- ✅ View all past entries with analysis results
- ✅ Insights dashboard — top emotion, favourite ambience, recent keywords
- ✅ JWT authentication via httpOnly cookies
- ✅ Protected routes — redirects to login if not authenticated

---

## Example API Usage

**Save a journal entry:**
```json
POST /api/journal
{
  "userId": "abc-123",
  "ambience": "forest",
  "text": "I felt calm today after listening to the rain."
}
```

**Analyze text:**
```json
POST /api/journal/analyze
{
  "text": "I felt calm today after listening to the rain."
}
```

**Response:**
```json
{
  "emotion": "calm",
  "keywords": ["rain", "nature", "peace", "listening", "calm"],
  "summary": "User experienced deep relaxation during a forest session."
}
```

---

## Testing the API

```bash
# Open Swagger UI
http://localhost:8000/docs

# Or use curl
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@test.com","password":"123456"}' \
  -c cookies.txt

# Analyze text
curl -X POST http://localhost:8000/api/journal/analyze \
  -H "Content-Type: application/json" \
  -d '{"text":"I felt peaceful walking through the forest today."}'
```

---

## Adding Dependencies

```bash
# Add a new package
uv add <package-name>

# Remove a package
uv remove <package-name>

# Sync all dependencies
uv sync
```
