# Meeting Intelligence Platform

A comprehensive web application that leverages OpenAI's APIs to transform meeting recordings into actionable insights. This platform integrates Whisper, GPT-4, Embeddings, and DALL-E APIs to provide transcription, analysis, semantic search, and visual summaries.

## 🌟 Features

### 1. **Audio Transcription** (Whisper API)
- Upload meeting recordings in MP3, WAV, or M4A format
- Automatic transcription of 20-30 minute audio files
- High-accuracy speech-to-text conversion

### 2. **Content Analysis** (GPT-4)
- Automated meeting summaries with key takeaways
- Extraction of action items with owner assignment
- Identification of key decisions made during meetings

### 3. **Semantic Search** (Embeddings API)
- Search across all meeting transcripts and summaries
- Find relevant discussions using natural language queries
- Cross-meeting insight discovery with similarity scoring

### 4. **Visual Summaries** (DALL-E 3)
- Auto-generated visual representations of meeting outcomes
- Professional infographic-style summaries for stakeholders
- Quick visual overview for non-attendees

### 5. **Fine-tuning Support**
- Pre-built dataset of company-specific terminology
- Export functionality for OpenAI fine-tuning format
- Examples covering technical terms, processes, and culture

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- OpenAI API key with access to GPT-4, Whisper, Embeddings, and DALL-E APIs

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd meeting-intelligence-platform
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

4. **Create required directories**
```bash
mkdir -p static uploads generated_images
```

5. **Copy the frontend file**
```bash
# Save the index.html content to static/index.html
```

### Running the Application

```bash
python app.py
```

The application will be available at `http://localhost:8000`

## 📋 API Documentation

### Meetings

#### Create Meeting
```http
POST /api/meetings
Content-Type: application/json

{
    "title": "Q3 Planning Session",
    "date": "2024-11-15",
    "participants": ["John Smith", "Sarah Johnson"]
}
```

#### Upload Audio
```http
POST /api/meetings/{meeting_id}/upload
Content-Type: multipart/form-data

file: <audio_file>
```

#### Get All Meetings
```http
GET /api/meetings
```

#### Get Single Meeting
```http
GET /api/meetings/{meeting_id}
```

### Search

#### Semantic Search
```http
POST /api/search
Content-Type: application/json

{
    "query": "discussion about KPI dashboard",
    "limit": 5
}
```

### Insights

#### Get Cross-Meeting Insights
```http
GET /api/insights
```

### Fine-tuning

#### Get Examples
```http
GET /api/fine-tuning/examples
```

#### Export Training Data
```http
POST /api/fine-tuning/export
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
pytest test_app.py -v
```

### Test Coverage
- **Unit Tests**: Individual API endpoints and functions
- **Integration Tests**: Complete workflow from upload to insights
- **Error Handling**: API failures and edge cases
- **Performance Tests**: Large file and dataset handling

## 🏗️ Architecture

### Backend (FastAPI)
- **Asynchronous Processing**: Non-blocking audio transcription and analysis
- **Background Tasks**: Long-running operations don't block the API
- **SQLite Database**: Lightweight storage for meetings and embeddings
- **Error Handling**: Graceful fallbacks for API failures

### Frontend (HTML/CSS/JavaScript)
- **Single Page Application**: Tab-based navigation
- **Real-time Updates**: Status indicators for processing
- **Responsive Design**: Works on desktop and mobile
- **Modern UI**: Gradient designs and smooth animations

### Database Schema

#### Meetings Table
- `id`: Primary key
- `title`: Meeting title
- `date`: Meeting date
- `participants`: JSON array of participant names
- `transcript`: Full meeting transcript
- `summary`: AI-generated summary
- `action_items`: JSON array of tasks
- `visual_summary_path`: Path to DALL-E generated image
- `embedding`: Vector embedding for semantic search
- `created_at`: Timestamp

#### Fine-tuning Examples Table
- `id`: Primary key
- `prompt`: User question/prompt
- `completion`: Expected response
- `category`: Type of example (technical, process, culture, etc.)

## 🔧 Configuration

### Environment Variables
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `PORT`: Server port (default: 8000)

### File Size Limits
- Maximum audio file size: 25MB (configurable in frontend)
- Supported formats: .mp3, .wav, .m4a, .mp4

## 📊 Sample Fine-tuning Dataset

The platform includes pre-built examples for company-specific terminology:

### Categories:
1. **Technical Terms**: KPI dashboard, RAPID framework, sprint retrospectives
2. **Company Products**: Project Phoenix, DataVault
3. **Meeting Patterns**: Quarterly planning, action item formats
4. **Company Culture**: Innovation Friday, remote-first policy

Export these examples in OpenAI's fine-tuning format for custom model training.

## 🚦 Performance Considerations

1. **Audio Processing**: 
   - Transcription happens asynchronously
   - 20-30 minute files typically process in 2-5 minutes

2. **Semantic Search**:
   - Uses cosine similarity for relevance scoring
   - Embedding generation cached per meeting

3. **Visual Generation**:
   - DALL-E images generated on-demand
   - Cached locally after generation

## 🔒 Security Notes

1. **API Key**: Store securely, never commit to version control
2. **File Uploads**: Validated for type and size
3. **Database**: Use parameterized queries to prevent SQL injection

## 🎯 Advanced Features Implemented

1. **Multi-API Integration**: Seamless coordination between 4 OpenAI APIs
2. **Semantic Search**: Vector similarity search across all meetings
3. **Visual Synthesis**: Auto-generated infographics for meeting summaries
4. **Fine-tuning Support**: Export data for custom model training
5. **Cross-Meeting Insights**: Analytics across entire meeting history

