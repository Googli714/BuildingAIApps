"""
Meeting Intelligence Platform - Backend API
Integrates OpenAI's Whisper, GPT-4, Embeddings, and DALL-E APIs
"""

import os
import json
import sqlite3
from collections import deque
from datetime import datetime
from typing import List, Optional, Any
from pathlib import Path
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import AsyncOpenAI
import aiofiles
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import tempfile
import subprocess
from typing import Dict


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Database setup
DB_PATH = os.getenv("DB_PATH", "meetings.db")
UPLOAD_DIR = Path("uploads")
IMAGES_DIR = Path("generated_images")
UPLOAD_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)


# Pydantic models
class MeetingCreate(BaseModel):
    title: str
    date: str
    participants: List[str]


class SearchQuery(BaseModel):
    query: str
    limit: int = 5


class Meeting(BaseModel):
    id: int
    title: str
    date: str
    participants: List[str]
    transcript: Optional[str] = None
    summary: Optional[str] = None
    action_items: Optional[List[Dict[str, str]]] = None
    visual_summary_path: Optional[str] = None
    created_at: str


class ActionItem(BaseModel):
    task: str
    owner: str
    deadline: Optional[str] = None

# Database initialization
def init_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Meetings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            participants TEXT NOT NULL,
            transcript TEXT,
            summary TEXT,
            action_items TEXT,
            visual_summary_path TEXT,
            embedding TEXT,
            language TEXT DEFAULT 'en',
            transcript_georgian TEXT,
            summary_georgian TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add columns to existing tables if they don't exist
    c.execute("PRAGMA table_info(meetings)")
    columns = [column[1] for column in c.fetchall()]
    if 'language' not in columns:
        c.execute("ALTER TABLE meetings ADD COLUMN language TEXT DEFAULT 'en'")
    if 'transcript_georgian' not in columns:
        c.execute("ALTER TABLE meetings ADD COLUMN transcript_georgian TEXT")
    if 'summary_georgian' not in columns:
        c.execute("ALTER TABLE meetings ADD COLUMN summary_georgian TEXT")
    if 'embedding_georgian' not in columns:
        c.execute("ALTER TABLE meetings ADD COLUMN embedding_georgian TEXT")

    conn.commit()
    conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db(DB_PATH)
    yield
    # Shutdown
    pass


# Initialize FastAPI app
app = FastAPI(title="Meeting Intelligence Platform", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/generated_images", StaticFiles(directory="generated_images"), name="generated_images")

# Helper functions
async def transcribe_audio(file_path: str, language: str = "en") -> str:
    """Transcribe audio using Whisper API with language support"""
    try:
        with open(file_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
                language=language
            )
        return str(transcript)
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


async def translate_text_to_georgian(text: str) -> str:
    """Translate text to Georgian using GPT-4"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional translator. Translate the provided text to Georgian language. Maintain the original formatting, structure, and meaning. Only return the translated text, nothing else."
                },
                {
                    "role": "user", 
                    "content": text
                }
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


async def generate_summary_and_actions(transcript: str, meeting_title: str) -> Dict[str, Any]:
    """Generate meeting summary and extract action items using GPT-4"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": """You are a meeting analyst. Analyze the transcript and provide:
                    1. A concise executive summary (2-3 paragraphs)
                    2. Key decisions made
                    3. Action items with owners and deadlines

                    Return the response in JSON format:
                    {
                        "summary": "executive summary text",
                        "key_decisions": ["decision 1", "decision 2"],
                        "action_items": [
                            {"task": "task description", "owner": "person name", "deadline": "date"}
                        ]
                    }"""
                },
                {
                    "role": "user",
                    "content": f"Meeting: {meeting_title}\n\nTranscript:\n{transcript}"
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )

        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Summary generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")


async def generate_embedding(text: str) -> List[float]:
    """Generate text embedding using OpenAI Embeddings API"""
    try:
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")


async def generate_visual_summary(summary: str, key_points: List[str]) -> str:
    """Generate visual summary using DALL-E 3"""
    try:
        # Create a prompt for DALL-E
        visual_prompt = f"""Create a professional infographic-style image that visually represents a meeting summary.
        Include abstract representations of these key points:
        {', '.join(key_points[:3])}
        Style: Clean, corporate, modern design with icons and minimal text.
        Color scheme: Professional blues and grays."""

        response = await client.images.generate(
            model="dall-e-3",
            prompt=visual_prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )

        # Download and save the image
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(response.data[0].url) as resp:
                if resp.status == 200:
                    filename = f"visual_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    file_path = IMAGES_DIR / filename
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(await resp.read())
                    return filename
    except Exception as e:
        logger.error(f"Visual generation error: {e}")
        # Return None if generation fails, don't break the entire process
        return None


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    a_np = np.array(a)
    b_np = np.array(b)
    return np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np))


# API Endpoints
@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.post("/api/meetings")
async def create_meeting(meeting: MeetingCreate):
    """Create a new meeting record"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        "INSERT INTO meetings (title, date, participants) VALUES (?, ?, ?)",
        (meeting.title, meeting.date, json.dumps(meeting.participants))
    )
    meeting_id = c.lastrowid
    conn.commit()
    conn.close()

    return {"id": meeting_id, "message": "Meeting created successfully"}


@app.post("/api/meetings/{meeting_id}/upload")
async def upload_audio(meeting_id: int, background_tasks: BackgroundTasks, file: UploadFile = File(...), language: str = Form("en")):
    """Upload and process audio file with language support"""
    # Validate file type
    if not file.filename.endswith(('.mp3', '.wav', '.m4a', ".mp4")):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .mp3, .wav, and .m4a are supported.")

    # Save uploaded file
    file_path = UPLOAD_DIR / f"meeting_{meeting_id}_{file.filename}"
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    # Update meeting with language preference
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE meetings SET language = ? WHERE id = ?", (language, meeting_id))
    conn.commit()
    conn.close()

    # Process in background
    background_tasks.add_task(process_meeting_audio, meeting_id, str(file_path))

    return {"message": "Audio uploaded. Processing started.", "meeting_id": meeting_id}


async def process_meeting_audio(meeting_id: int, file_path: str):
    """Background task to process meeting audio"""
    try:
        # Get meeting details including language preference
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT title, language FROM meetings WHERE id = ?", (meeting_id,))
        result = c.fetchone()
        meeting_title = result[0]
        language = result[1] if result[1] else "en"
        conn.close()

        # Step 1: Transcribe audio with specified language
        logger.info(f"Transcribing audio for meeting {meeting_id} in language: {language}")
        transcript = await transcribe_audio(file_path, language)

        # Step 2: Generate summary and extract action items
        logger.info(f"Generating summary for meeting {meeting_id}")

        analysis = await generate_summary_and_actions(transcript, meeting_title)

        # Step 3: Generate embedding for semantic search
        logger.info(f"Generating embedding for meeting {meeting_id}")
        embedding_text = f"{meeting_title} {analysis['summary']} {' '.join(analysis['key_decisions'])}"
        embedding = await generate_embedding(embedding_text)

        # Step 4: Generate visual summary
        logger.info(f"Generating visual summary for meeting {meeting_id}")
        visual_path = await generate_visual_summary(
            analysis['summary'],
            analysis['key_decisions']
        )

        # Step 5: Update database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            UPDATE meetings 
            SET transcript = ?, summary = ?, action_items = ?, 
                visual_summary_path = ?, embedding = ?
            WHERE id = ?
        """, (
            transcript,
            analysis['summary'],
            json.dumps(analysis['action_items']),
            visual_path,
            json.dumps(embedding),
            meeting_id
        ))
        conn.commit()
        conn.close()

        logger.info(f"Successfully processed meeting {meeting_id}")

    except Exception as e:
        logger.error(f"Error processing meeting {meeting_id}: {e}")


@app.get("/api/meetings")
async def get_meetings():
    """Get all meetings"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM meetings ORDER BY created_at DESC")
    meetings = []
    for row in c.fetchall():
        meeting = dict(row)
        meeting['participants'] = json.loads(meeting['participants'])
        if meeting['action_items']:
            meeting['action_items'] = json.loads(meeting['action_items'])
        meetings.append(meeting)

    conn.close()
    return meetings


@app.get("/api/meetings/{meeting_id}")
async def get_meeting(meeting_id: int):
    """Get a specific meeting"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
    row = c.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Meeting not found")

    meeting = dict(row)
    meeting['participants'] = json.loads(meeting['participants'])
    if meeting['action_items']:
        meeting['action_items'] = json.loads(meeting['action_items'])

    conn.close()
    return meeting


@app.post("/api/search")
async def search_meetings(query: SearchQuery):
    """Cross-language semantic search across all meetings"""
    # Generate embedding for search query
    query_embedding = await generate_embedding(query.query)

    # Search in database - include Georgian embeddings
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT id, title, summary, embedding, embedding_georgian, 
               summary_georgian
        FROM meetings WHERE embedding IS NOT NULL
    """)

    results = []
    for row in c.fetchall():
        # Calculate similarity with original content
        original_embedding = json.loads(row['embedding'])
        original_similarity = cosine_similarity(query_embedding, original_embedding)
        
        # Calculate similarity with Georgian content if available
        georgian_similarity = 0
        if row['embedding_georgian']:
            georgian_embedding = json.loads(row['embedding_georgian'])
            georgian_similarity = cosine_similarity(query_embedding, georgian_embedding)
        
        # Use the higher similarity score
        max_similarity = max(original_similarity, georgian_similarity)
        matched_language = 'georgian' if georgian_similarity > original_similarity else 'english'
        
        # Use Georgian summary if it matched better and exists
        display_summary = row['summary']
        if matched_language == 'georgian' and row['summary_georgian']:
            display_summary = row['summary_georgian']
        
        results.append({
            'id': row['id'],
            'title': row['title'],
            'summary': display_summary,
            'similarity': max_similarity,
            'matched_language': matched_language
        })

    # Sort by similarity and return top results
    results.sort(key=lambda x: x['similarity'], reverse=True)
    conn.close()

    return results[:query.limit]


@app.delete("/api/meetings/{meeting_id}")
async def delete_meeting(meeting_id: int):
    """Delete a meeting and its associated files"""

    conn = sqlite3.connect(DB_PATH)

    c = conn.cursor()

    # Get meeting details first to delete associated files

    c.execute("SELECT visual_summary_path FROM meetings WHERE id = ?", (meeting_id,))

    row = c.fetchone()

    if not row:
        conn.close()

        raise HTTPException(status_code=404, detail="Meeting not found")

    # Delete visual summary file if exists

    if row[0]:

        image_path = IMAGES_DIR / row[0]

        if image_path.exists():
            image_path.unlink()

    # Delete meeting from database

    c.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))

    conn.commit()

    conn.close()

    # Delete associated audio files

    for audio_file in UPLOAD_DIR.glob(f"meeting_{meeting_id}_*"):
        audio_file.unlink()

    return {"message": "Meeting deleted successfully"}


@app.post("/api/meetings/{meeting_id}/translate")
async def translate_meeting_to_georgian(meeting_id: int, background_tasks: BackgroundTasks):
    """Translate meeting transcript and summary to Georgian"""
    # Check if meeting exists and has transcript
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT transcript, summary FROM meetings WHERE id = ?", (meeting_id,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    transcript, summary = result
    
    if not transcript:
        conn.close()
        raise HTTPException(status_code=400, detail="Meeting has no transcript to translate")
    
    # Check if translation already exists
    c.execute("SELECT transcript_georgian, summary_georgian FROM meetings WHERE id = ?", (meeting_id,))
    existing = c.fetchone()
    conn.close()
    
    if existing and existing[0]:  # If Georgian translation already exists
        return {"message": "Georgian translation already exists", "meeting_id": meeting_id}
    
    # Start translation in background
    background_tasks.add_task(translate_meeting_content, meeting_id, transcript, summary)
    
    return {"message": "Translation to Georgian started", "meeting_id": meeting_id}


async def translate_meeting_content(meeting_id: int, transcript: str, summary: str):
    """Background task to translate meeting content to Georgian"""
    try:
        logger.info(f"Starting Georgian translation for meeting {meeting_id}")
        
        # Translate transcript
        logger.info(f"Translating transcript for meeting {meeting_id}")
        transcript_georgian = await translate_text_to_georgian(transcript)
        
        # Translate summary if it exists
        summary_georgian = None
        if summary:
            logger.info(f"Translating summary for meeting {meeting_id}")
            summary_georgian = await translate_text_to_georgian(summary)
        
        # Generate Georgian embedding for search
        logger.info(f"Generating Georgian embedding for meeting {meeting_id}")
        georgian_text = ""
        if summary_georgian:
            georgian_text += summary_georgian
        if transcript_georgian:
            georgian_text += " " + transcript_georgian
        
        embedding_georgian = None
        if georgian_text.strip():
            embedding_georgian = await generate_embedding(georgian_text)
        
        # Update database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            UPDATE meetings 
            SET transcript_georgian = ?, summary_georgian = ?, embedding_georgian = ?
            WHERE id = ?
        """, (transcript_georgian, summary_georgian, 
              json.dumps(embedding_georgian) if embedding_georgian else None, 
              meeting_id))
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully completed Georgian translation for meeting {meeting_id}")
        
    except Exception as e:
        logger.error(f"Error translating meeting {meeting_id}: {e}")


@app.get("/api/insights")
async def get_cross_meeting_insights():
    """Generate insights across all meetings"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Get all action items
    c.execute("SELECT action_items FROM meetings WHERE action_items IS NOT NULL")
    all_actions = []
    for row in c.fetchall():
        actions = json.loads(row[0])
        all_actions.extend(actions)

    # Analyze patterns
    owner_counts = {}
    overdue_count = 0

    for action in all_actions:
        owner = action.get('owner', 'Unassigned')
        owner_counts[owner] = owner_counts.get(owner, 0) + 1

        if action.get('deadline'):
            try:
                # Only try to parse if it's a valid date format, skip TBD and other text
                if action['deadline'] not in ['TBD', 'To be determined', '', None]:
                    deadline = datetime.strptime(action['deadline'], '%Y-%m-%d')
                    if deadline < datetime.now():
                        overdue_count += 1
            except ValueError:
                # Skip invalid date formats
                continue

    conn.close()

    return {
        'total_action_items': len(all_actions),
        'owner_distribution': owner_counts,
        'overdue_items': overdue_count,
        'insights': [
            f"Total of {len(all_actions)} action items across all meetings",
            f"{overdue_count} items are overdue",
            f"Top assignee: {max(owner_counts, key=owner_counts.get) if owner_counts else 'None'}"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)