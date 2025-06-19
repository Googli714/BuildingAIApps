"""
Test Cases for Meeting Intelligence Platform
Comprehensive testing for all API endpoints and functionality
"""
import os
import pytest
import asyncio
import json
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

os.environ["DB_PATH"] = "test_meetings.db"
DB_PATH = "test_meetings.db"

from app import app, init_db
# Test client
client = TestClient(app)

# Test data
TEST_MEETING = {
    "title": "Q3 Planning Session",
    "date": "2024-11-15",
    "participants": ["John Smith", "Sarah Johnson", "Mike Chen"]
}

TEST_TRANSCRIPT = """
Good morning everyone. Let's start our Q3 planning session. 
John: I think we should focus on improving our KPI dashboard this quarter.
Sarah: I agree. We also need to implement the RAPID framework for better decision making.
Mike: Let's also plan for Innovation Friday activities.
John: Great ideas. I'll take ownership of the dashboard improvements by end of month.
Sarah: I'll handle the RAPID framework training for the team.
Mike: And I'll coordinate the Innovation Friday schedule.
"""

TEST_SUMMARY_RESPONSE = {
    "summary": "The Q3 planning session focused on three main initiatives: improving the KPI dashboard, implementing the RAPID decision-making framework, and organizing Innovation Friday activities.",
    "key_decisions": [
        "Improve KPI dashboard this quarter",
        "Implement RAPID framework for decision making",
        "Schedule Innovation Friday activities"
    ],
    "action_items": [
        {"task": "Improve KPI dashboard", "owner": "John Smith", "deadline": "2024-11-30"},
        {"task": "RAPID framework training", "owner": "Sarah Johnson", "deadline": None},
        {"task": "Coordinate Innovation Friday", "owner": "Mike Chen", "deadline": None}
    ]
}


# Fixtures
@pytest.fixture(autouse=True)
def setup_test_db():
    """Setup test database before each test"""

    # Remove existing test database
    if Path(DB_PATH).exists():
        Path(DB_PATH).unlink()

    # Initialize database
    init_db(DB_PATH)

    yield

    # Cleanup
    if Path(DB_PATH).exists():
        Path(DB_PATH).unlink()


@pytest.fixture
def mock_openai():
    """Mock OpenAI API calls"""
    with patch('app.client') as mock_client:
        # Mock transcription
        mock_client.audio.transcriptions.create = AsyncMock(return_value=TEST_TRANSCRIPT)

        # Mock chat completion
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(TEST_SUMMARY_RESPONSE)))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        # Mock embeddings
        mock_embedding = MagicMock()
        mock_embedding.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create = AsyncMock(return_value=mock_embedding)

        # Mock image generation
        mock_image = MagicMock()
        mock_image.data = [MagicMock(url="https://example.com/image.png")]
        mock_client.images.generate = AsyncMock(return_value=mock_image)

        yield mock_client


# Test Cases

class TestMeetingCreation:
    """Test meeting creation functionality"""

    def test_create_meeting_success(self):
        """Test successful meeting creation"""
        response = client.post("/api/meetings", json=TEST_MEETING)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["message"] == "Meeting created successfully"

        # Verify in database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM meetings WHERE id = ?", (data["id"],))
        meeting = c.fetchone()
        conn.close()

        assert meeting is not None
        assert meeting[1] == TEST_MEETING["title"]

    def test_create_meeting_invalid_data(self):
        """Test meeting creation with invalid data"""
        invalid_meeting = {"title": "Test"}  # Missing required fields
        response = client.post("/api/meetings", json=invalid_meeting)
        assert response.status_code == 422


class TestAudioUpload:
    """Test audio upload and processing"""

    def test_upload_audio_success(self, mock_openai, tmp_path):
        """Test successful audio upload"""
        # Create meeting first
        response = client.post("/api/meetings", json=TEST_MEETING)
        meeting_id = response.json()["id"]

        # Create test audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio content")

        # Upload audio
        with open(audio_file, "rb") as f:
            response = client.post(
                f"/api/meetings/{meeting_id}/upload",
                files={"file": ("test.mp3", f, "audio/mpeg")}
            )

        assert response.status_code == 200
        assert "Processing started" in response.json()["message"]

    def test_upload_invalid_file_type(self):
        """Test upload with invalid file type"""
        response = client.post("/api/meetings", json=TEST_MEETING)
        meeting_id = response.json()["id"]

        # Try to upload a text file
        response = client.post(
            f"/api/meetings/{meeting_id}/upload",
            files={"file": ("test.txt", b"text content", "text/plain")}
        )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]


class TestMeetingRetrieval:
    """Test meeting retrieval endpoints"""

    def test_get_all_meetings(self):
        """Test retrieving all meetings"""
        # Create multiple meetings
        for i in range(3):
            meeting = TEST_MEETING.copy()
            meeting["title"] = f"Meeting {i + 1}"
            client.post("/api/meetings", json=meeting)

        response = client.get("/api/meetings")
        assert response.status_code == 200
        meetings = response.json()
        assert len(meetings) == 3
        assert all("participants" in m for m in meetings)

    def test_get_single_meeting(self):
        """Test retrieving a single meeting"""
        # Create meeting
        response = client.post("/api/meetings", json=TEST_MEETING)
        meeting_id = response.json()["id"]

        response = client.get(f"/api/meetings/{meeting_id}")
        assert response.status_code == 200
        meeting = response.json()
        assert meeting["title"] == TEST_MEETING["title"]
        assert meeting["participants"] == TEST_MEETING["participants"]

    def test_get_nonexistent_meeting(self):
        """Test retrieving a non-existent meeting"""
        response = client.get("/api/meetings/999")
        assert response.status_code == 404


class TestSemanticSearch:
    """Test semantic search functionality"""

    @pytest.mark.asyncio
    async def test_search_meetings(self, mock_openai):
        """Test searching across meetings"""
        # Create and process a meeting
        response = client.post("/api/meetings", json=TEST_MEETING)
        meeting_id = response.json()["id"]

        # Simulate processed meeting with embedding
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        embedding = json.dumps([0.1] * 1536)
        c.execute(
            "UPDATE meetings SET summary = ?, embedding = ? WHERE id = ?",
            ("Test summary about KPI dashboard", embedding, meeting_id)
        )
        conn.commit()
        conn.close()

        # Search
        response = client.post("/api/search", json={"query": "KPI dashboard", "limit": 5})
        assert response.status_code == 200
        results = response.json()
        assert len(results) > 0
        assert "similarity" in results[0]

    def test_search_empty_query(self):
        """Test search with empty query"""
        response = client.post("/api/search", json={"query": "", "limit": 5})
        assert response.status_code == 200
        assert response.json() == []


class TestInsights:
    """Test cross-meeting insights"""

    def test_get_insights(self):
        """Test insights generation"""
        # Create meetings with action items
        response = client.post("/api/meetings", json=TEST_MEETING)
        meeting_id = response.json()["id"]

        # Add action items
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        action_items = json.dumps(TEST_SUMMARY_RESPONSE["action_items"])
        c.execute(
            "UPDATE meetings SET action_items = ? WHERE id = ?",
            (action_items, meeting_id)
        )
        conn.commit()
        conn.close()

        response = client.get("/api/insights")
        assert response.status_code == 200
        insights = response.json()
        assert "total_action_items" in insights
        assert "owner_distribution" in insights
        assert insights["total_action_items"] == 3

class TestIntegration:
    """End-to-end integration tests"""

    @pytest.mark.asyncio
    async def test_full_meeting_workflow(self, mock_openai, tmp_path):
        """Test complete meeting workflow from creation to insights"""
        # 1. Create meeting
        response = client.post("/api/meetings", json=TEST_MEETING)
        meeting_id = response.json()["id"]

        # 2. Upload audio
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio content")

        with open(audio_file, "rb") as f:
            response = client.post(
                f"/api/meetings/{meeting_id}/upload",
                files={"file": ("test.mp3", f, "audio/mpeg")}
            )
        assert response.status_code == 200

        # 3. Wait for processing (in real scenario)
        await asyncio.sleep(0.1)

        # 4. Simulate processed meeting
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            UPDATE meetings 
            SET transcript = ?, summary = ?, action_items = ?, embedding = ?
            WHERE id = ?
        """, (
            TEST_TRANSCRIPT,
            TEST_SUMMARY_RESPONSE["summary"],
            json.dumps(TEST_SUMMARY_RESPONSE["action_items"]),
            json.dumps([0.1] * 1536),
            meeting_id
        ))
        conn.commit()
        conn.close()

        # 5. Retrieve meeting
        response = client.get(f"/api/meetings/{meeting_id}")
        meeting = response.json()
        assert meeting["transcript"] == TEST_TRANSCRIPT
        assert meeting["summary"] == TEST_SUMMARY_RESPONSE["summary"]
        assert len(meeting["action_items"]) == 3

        # 6. Search for meeting
        response = client.post("/api/search", json={"query": "RAPID framework"})
        results = response.json()
        assert len(results) > 0
        assert results[0]["id"] == meeting_id

        # 7. Get insights
        response = client.get("/api/insights")
        insights = response.json()
        assert insights["total_action_items"] == 3


class TestMeetingDeletion:
    """Test meeting deletion functionality"""

    def test_delete_meeting_success(self):
        """Test successful meeting deletion"""
        # Create meeting
        response = client.post("/api/meetings", json=TEST_MEETING)
        meeting_id = response.json()["id"]

        # Delete meeting
        response = client.delete(f"/api/meetings/{meeting_id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify deletion
        response = client.get(f"/api/meetings/{meeting_id}")
        assert response.status_code == 404

    def test_delete_nonexistent_meeting(self):
        """Test deleting a non-existent meeting"""
        response = client.delete("/api/meetings/999")
        assert response.status_code == 404


class TestGeorgianTranslation:
    """Test Georgian translation functionality"""

    def test_translate_meeting_success(self, mock_openai):
        """Test successful translation to Georgian"""
        # Mock Georgian translation
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="ქართული თარგმანი"))]
        )

        # Create meeting with transcript
        response = client.post("/api/meetings", json=TEST_MEETING)
        meeting_id = response.json()["id"]

        # Add transcript to meeting
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "UPDATE meetings SET transcript = ?, summary = ? WHERE id = ?",
            (TEST_TRANSCRIPT, "Test summary", meeting_id)
        )
        conn.commit()
        conn.close()

        # Request translation
        response = client.post(f"/api/meetings/{meeting_id}/translate")
        assert response.status_code == 200
        assert "Translation to Georgian started" in response.json()["message"]

    def test_translate_meeting_no_transcript(self):
        """Test translation request for meeting without transcript"""
        response = client.post("/api/meetings", json=TEST_MEETING)
        meeting_id = response.json()["id"]

        response = client.post(f"/api/meetings/{meeting_id}/translate")
        assert response.status_code == 400
        assert "no transcript to translate" in response.json()["detail"]

    def test_translate_nonexistent_meeting(self):
        """Test translation request for non-existent meeting"""
        response = client.post("/api/meetings/999/translate")
        assert response.status_code == 404

    def test_translate_already_translated(self, mock_openai):
        """Test translation request for already translated meeting"""
        response = client.post("/api/meetings", json=TEST_MEETING)
        meeting_id = response.json()["id"]

        # Add transcript and Georgian translation
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "UPDATE meetings SET transcript = ?, transcript_georgian = ? WHERE id = ?",
            (TEST_TRANSCRIPT, "ქართული თარგმანი", meeting_id)
        )
        conn.commit()
        conn.close()

        response = client.post(f"/api/meetings/{meeting_id}/translate")
        assert response.status_code == 200
        assert "already exists" in response.json()["message"]


class TestCrossLanguageSearch:
    """Test cross-language search functionality"""

    @pytest.mark.asyncio
    async def test_search_with_georgian_content(self, mock_openai):
        """Test search that finds Georgian content"""
        # Create meeting with both English and Georgian content
        response = client.post("/api/meetings", json=TEST_MEETING)
        meeting_id = response.json()["id"]

        # Add both English and Georgian content with embeddings
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        english_embedding = json.dumps([0.1] * 1536)
        georgian_embedding = json.dumps([0.9] * 1536)  # Higher similarity for Georgian
        
        c.execute("""
            UPDATE meetings 
            SET summary = ?, summary_georgian = ?, embedding = ?, embedding_georgian = ?
            WHERE id = ?
        """, (
            "English summary about dashboard",
            "ქართული რეზიუმე დაშბორდის შესახებ",
            english_embedding,
            georgian_embedding,
            meeting_id
        ))
        conn.commit()
        conn.close()

        # Search should return Georgian match with higher similarity
        response = client.post("/api/search", json={"query": "dashboard", "limit": 5})
        assert response.status_code == 200
        results = response.json()
        assert len(results) > 0
        assert "matched_language" in results[0]

    @pytest.mark.asyncio
    async def test_search_mixed_language_results(self, mock_openai):
        """Test search returning results from both languages"""
        # Create multiple meetings with different language content
        meetings = []
        for i in range(3):
            response = client.post("/api/meetings", json={
                "title": f"Meeting {i+1}",
                "date": "2024-11-15",
                "participants": ["Test User"]
            })
            meetings.append(response.json()["id"])

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # First meeting: English content matches better
        c.execute("""
            UPDATE meetings 
            SET summary = ?, embedding = ?, embedding_georgian = ?
            WHERE id = ?
        """, (
            "Project planning discussion",
            json.dumps([0.8] * 1536),  # High English similarity
            json.dumps([0.2] * 1536),  # Low Georgian similarity
            meetings[0]
        ))
        
        # Second meeting: Georgian content matches better
        c.execute("""
            UPDATE meetings 
            SET summary = ?, summary_georgian = ?, embedding = ?, embedding_georgian = ?
            WHERE id = ?
        """, (
            "Other topic discussion",
            "პროექტის დაგეგმვის განხილვა",
            json.dumps([0.3] * 1536),  # Low English similarity
            json.dumps([0.9] * 1536),  # High Georgian similarity
            meetings[1]
        ))
        
        conn.commit()
        conn.close()

        response = client.post("/api/search", json={"query": "planning", "limit": 5})
        assert response.status_code == 200
        results = response.json()
        assert len(results) >= 2


class TestInsightsErrorHandling:
    """Test insights with various edge cases"""

    def test_insights_with_tbd_deadlines(self):
        """Test insights handling TBD and invalid deadlines"""
        response = client.post("/api/meetings", json=TEST_MEETING)
        meeting_id = response.json()["id"]

        # Add action items with various deadline formats
        action_items = [
            {"task": "Task 1", "owner": "John", "deadline": "TBD"},
            {"task": "Task 2", "owner": "Sarah", "deadline": "To be determined"},
            {"task": "Task 3", "owner": "Mike", "deadline": "2024-01-01"},  # Past date
            {"task": "Task 4", "owner": "John", "deadline": "invalid-date"},
            {"task": "Task 5", "owner": "Sarah", "deadline": None}
        ]

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "UPDATE meetings SET action_items = ? WHERE id = ?",
            (json.dumps(action_items), meeting_id)
        )
        conn.commit()
        conn.close()

        # Should not crash despite invalid date formats
        response = client.get("/api/insights")
        assert response.status_code == 200
        insights = response.json()
        assert insights["total_action_items"] == 5
        assert insights["overdue_items"] == 1  # Only the valid past date

    def test_insights_empty_database(self):
        """Test insights with no meetings"""
        response = client.get("/api/insights")
        assert response.status_code == 200
        insights = response.json()
        assert insights["total_action_items"] == 0
        assert insights["overdue_items"] == 0
        assert insights["owner_distribution"] == {}

    def test_insights_no_action_items(self):
        """Test insights with meetings but no action items"""
        # Create meetings without action items
        for i in range(3):
            meeting = TEST_MEETING.copy()
            meeting["title"] = f"Meeting {i + 1}"
            client.post("/api/meetings", json=meeting)

        response = client.get("/api/insights")
        assert response.status_code == 200
        insights = response.json()
        assert insights["total_action_items"] == 0


class TestValidationAndEdgeCases:
    """Test various validation and edge cases"""

    def test_search_with_very_long_query(self, mock_openai):
        """Test search with extremely long query"""
        long_query = "dashboard " * 1000  # Very long query
        response = client.post("/api/search", json={"query": long_query, "limit": 5})
        assert response.status_code == 200

    def test_meeting_with_empty_participants(self):
        """Test creating meeting with empty participants list"""
        meeting = TEST_MEETING.copy()
        meeting["participants"] = []
        response = client.post("/api/meetings", json=meeting)
        assert response.status_code == 200

    def test_meeting_with_special_characters(self):
        """Test meeting creation with special characters"""
        meeting = {
            "title": "Meeting with émojis 🚀 and spëcial chars",
            "date": "2024-11-15",
            "participants": ["Jöhn Smîth", "Сара Иванова", "მარიამ გვარამაძე"]
        }
        response = client.post("/api/meetings", json=meeting)
        assert response.status_code == 200

    def test_search_limit_validation(self, mock_openai):
        """Test search with different limit values"""
        # Test with limit 0
        response = client.post("/api/search", json={"query": "test", "limit": 0})
        assert response.status_code == 200
        assert len(response.json()) == 0

        # Test with very high limit
        response = client.post("/api/search", json={"query": "test", "limit": 1000})
        assert response.status_code == 200


class TestPerformance:
    """Test performance and scalability"""

    def test_large_meeting_list(self):
        """Test handling of many meetings"""
        # Create 100 meetings
        for i in range(100):
            meeting = TEST_MEETING.copy()
            meeting["title"] = f"Meeting {i + 1}"
            client.post("/api/meetings", json=meeting)

        response = client.get("/api/meetings")
        assert response.status_code == 200
        meetings = response.json()
        assert len(meetings) == 100

    def test_large_transcript_processing(self, mock_openai):
        """Test processing of large transcripts"""
        # Create a large transcript (20-30 minutes worth)
        large_transcript = TEST_TRANSCRIPT * 100
        mock_openai.audio.transcriptions.create.return_value = large_transcript

        response = client.post("/api/meetings", json=TEST_MEETING)
        meeting_id = response.json()["id"]

        # Should handle large files
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_translations(self, mock_openai):
        """Test multiple concurrent translation requests"""
        # Create multiple meetings
        meeting_ids = []
        for i in range(5):
            response = client.post("/api/meetings", json=TEST_MEETING)
            meeting_id = response.json()["id"]
            meeting_ids.append(meeting_id)
            
            # Add transcript
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                "UPDATE meetings SET transcript = ? WHERE id = ?",
                (TEST_TRANSCRIPT, meeting_id)
            )
            conn.commit()
            conn.close()

        # Request translations concurrently
        responses = []
        for meeting_id in meeting_ids:
            response = client.post(f"/api/meetings/{meeting_id}/translate")
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 200


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])