from fastapi import FastAPI, HTTPException,Depends
from pydantic import BaseModel
from database import cursor
from llm import process_journal, analyze_only
import json
from collections import Counter
from fastapi.middleware.cors import CORSMiddleware
from middleware import get_current_user
from auth import router as auth_router

app = FastAPI(title="AI Journal API")
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # allow POST, GET, OPTIONS
    allow_headers=["*"],
)

app.include_router(auth_router)

class JournalRequest(BaseModel):
    userId: str
    ambience: str
    text: str

class AnalyzeRequest(BaseModel):
    text: str

@app.get("/health")
def health():
    return {"status": "ok"}

# ── POST /api/journal ─────────────────────────────
# Saves entry + calls LLM + saves analysis
@app.post("/api/journal")
def create_journal(data: JournalRequest, user=Depends(get_current_user)):
    print(data)
    result = process_journal(user["userId"], data.ambience, data.text)
    return result

# ── GET /api/journal/:userId ──────────────────────
# Return all entries for a user
@app.get("/api/journal/{user_id}")
def get_journals(user_id: str, user=Depends(get_current_user)):
    if user["userId"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    rows = cursor.execute(
        """SELECT j.id, j.user_id, j.ambience, j.text, j.created_at,
                  a.emotion, a.keywords, a.summary
           FROM journals j
           LEFT JOIN journal_analysis a ON j.id = a.journal_id
           WHERE j.user_id = ?
           ORDER BY j.created_at DESC""",
        (user_id,)
    ).fetchall()

    return [
        {
            "id":       row[0],
            "userId":   row[1],
            "ambience": row[2],
            "text":     row[3],
            "created_at": row[4],
            "emotion":  row[5],
            "keywords": json.loads(row[6]) if row[6] else [],
            "summary":  row[7],
        }
        for row in rows
    ]

# ── POST /api/journal/analyze ─────────────────────
# ONLY returns LLM response, no database saving
@app.post("/api/journal/analyze")
def analyze_journal(data: AnalyzeRequest):
    result = analyze_only(data.text)
    return result

# ── GET /api/journal/insights/:userId ────────────
@app.get("/api/journal/insights/{user_id}")
def get_insights(user_id: str,user=Depends(get_current_user)):
    if user["userId"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    # Total entries
    total = cursor.execute(
        "SELECT COUNT(*) FROM journals WHERE user_id = ?", (user_id,)
    ).fetchone()[0]

    if total == 0:
        raise HTTPException(status_code=404, detail="No entries found")

    # Top emotion
    emotions = [row[0] for row in cursor.execute(
        """SELECT ja.emotion FROM journal_analysis ja
           JOIN journals j ON ja.journal_id = j.id
           WHERE j.user_id = ? AND ja.emotion IS NOT NULL""",
        (user_id,)
    ).fetchall()]
    top_emotion = Counter(emotions).most_common(1)[0][0] if emotions else None

    # Most used ambience
    ambiences = [row[0] for row in cursor.execute(
        "SELECT ambience FROM journals WHERE user_id = ?", (user_id,)
    ).fetchall()]
    most_used_ambience = Counter(ambiences).most_common(1)[0][0] if ambiences else None

    # Recent keywords (last 5 entries)
    rows = cursor.execute(
        """SELECT ja.keywords FROM journal_analysis ja
           JOIN journals j ON ja.journal_id = j.id
           WHERE j.user_id = ? AND ja.keywords IS NOT NULL
           ORDER BY j.created_at DESC LIMIT 5""",
        (user_id,)
    ).fetchall()

    recent_keywords = []
    seen = set()
    for row in rows:
        for kw in json.loads(row[0]):
            if kw not in seen:
                seen.add(kw)
                recent_keywords.append(kw)

    return {
        "totalEntries":      total,
        "topEmotion":        top_emotion,
        "mostUsedAmbience":  most_used_ambience,
        "recentKeywords":    recent_keywords
    }
