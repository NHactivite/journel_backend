from langchain_core.messages import HumanMessage, AIMessage
# from langchain_openai import ChatOpenAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
import json, datetime, uuid
from database import cursor, conn
from dotenv import load_dotenv
load_dotenv()

model = HuggingFaceEndpoint(
    repo_id="openai/gpt-oss-20b",
    task="text-generation"
)
llm = ChatHuggingFace(llm=model)

ANALYSIS_PROMPT = """You are an empathetic journaling assistant.

Analyze the journal entry below and return a JSON object with exactly these keys:
  - "emotion"  : the dominant emotion (one word, e.g. "anxious", "hopeful", "calm")
  - "keywords" : list of 5 important keywords / themes
  - "summary"  : one-sentence summary of the entry

Respond ONLY with valid JSON. No markdown, no extra text.

Journal entry:
{content}
"""

def analyze_with_llm(text: str) -> dict:
    """
    Call LLM and return emotion, keywords, summary.
    Used by BOTH process_journal and analyze_only.
    """
    prompt = ANALYSIS_PROMPT.format(content=text)
    try:
        response: AIMessage = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        parsed = json.loads(raw)
        return {
            "emotion":  parsed.get("emotion"),
            "keywords": parsed.get("keywords", []),
            "summary":  parsed.get("summary"),
            "error":    None
        }
    except Exception as e:
        return {"emotion": None, "keywords": [], "summary": None, "error": str(e)}


def process_journal(user_id: str, ambience: str, text: str) -> dict:
    """
    Called by POST /api/journal
    - Saves entry to journals table
    - Calls LLM
    - Saves analysis to journal_analysis table
    - Returns full result
    """
    journal_id = str(uuid.uuid4())

    # Step 1: Save journal entry
    cursor.execute(
        "INSERT INTO journals (id, user_id, ambience, text, created_at) VALUES (?, ?, ?, ?, ?)",
        (journal_id, user_id, ambience, text, datetime.datetime.utcnow().isoformat())
    )
    conn.commit()
    print(f"Saved journal {journal_id}")

    # Step 2: Call LLM
    analysis = analyze_with_llm(text)
    if analysis["error"]:
        print(f" LLM error: {analysis['error']}")
        return {"journal_id": journal_id, "saved": True, "analysis_saved": False, **analysis}

    # Step 3: Save analysis
    cursor.execute(
        """INSERT INTO journal_analysis (id, journal_id, emotion, keywords, summary, analyzed_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()),
            journal_id,
            analysis["emotion"],
            json.dumps(analysis["keywords"]),
            analysis["summary"],
            datetime.datetime.utcnow().isoformat()
        )
    )
    conn.commit()
    print(f" Analysis saved for journal {journal_id}")

    return {
        "journal_id":     journal_id,
        "saved":          True,
        "analysis_saved": True,
        "emotion":        analysis["emotion"],
        "keywords":       analysis["keywords"],
        "summary":        analysis["summary"],
        "error":          None
    }


def analyze_only(text: str) -> dict:
    """
    Called by POST /api/journal/analyze
    - ONLY calls LLM, no database saving
    """
    return analyze_with_llm(text)

