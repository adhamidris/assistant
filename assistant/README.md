# AI Personal Business Assistant - Backend

A Django-based backend for an AI-powered business assistant that handles customer inquiries through a chat portal with features like audio transcription, knowledge base search, intent classification, and appointment booking.

## Features

- **Session & Identity Management**: Phone number-based customer identification
- **Real-time Messaging**: Text, audio, and file message support
- **AI Processing Pipeline**: OpenAI integration for transcription, embeddings, and text generation
- **Knowledge Base System**: Vector-based document search using pgvector
- **Response Mode Management**: Automatic or manual approval of AI responses
- **Calendar Integration**: Google Calendar appointment booking
- **Owner Dashboard**: Conversation management and analytics

## Tech Stack

- **Backend**: Django 5.2.5 + Django REST Framework
- **Database**: PostgreSQL with pgvector extension
- **Background Tasks**: Celery with Redis
- **File Storage**: MinIO (S3-compatible)
- **AI Services**: OpenAI API (Whisper, GPT, Embeddings)

## Quick Start

### 1. Environment Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup

Start the required services using Docker Compose:

```bash
docker-compose up -d
```

This starts:
- PostgreSQL with pgvector extension (port 5432)
- Redis (port 6379)
- MinIO (port 9000, console 9001)

### 3. Environment Configuration

Create a `.env` file based on `env.example`:

```bash
cp env.example .env
```

Update the `.env` file with your API keys:
- `OPENAI_API_KEY`: Your OpenAI API key
- `GOOGLE_OAUTH_CLIENT_ID` & `GOOGLE_OAUTH_CLIENT_SECRET`: For calendar integration

### 4. Database Migration

```bash
# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Set up demo data
python manage.py setup_demo_data
```

### 5. Start Development Server

```bash
# Start Django development server
python manage.py runserver

# In another terminal, start Celery worker
celery -A assistant worker --loglevel=info
```

## API Endpoints

### Core Endpoints
- `POST /api/v1/core/session/create/` - Create customer session
- `POST /api/v1/core/session/validate/` - Validate session token
- `GET /api/v1/core/conversations/` - List conversations
- `GET /api/v1/core/workspaces/` - Manage workspaces

### Messaging Endpoints
- `GET /api/v1/messaging/messages/` - List messages
- `POST /api/v1/messaging/upload-audio/` - Upload audio message
- `POST /api/v1/messaging/upload-file/` - Upload file attachment
- `POST /api/v1/messaging/generate-response/` - Generate AI response

### Knowledge Base Endpoints
- `POST /api/v1/knowledge-base/upload/` - Upload document
- `POST /api/v1/knowledge-base/search/` - Search knowledge base
- `GET /api/v1/knowledge-base/documents/` - List documents

### Calendar Endpoints
- `GET /api/v1/calendar/available-slots/` - Get available time slots
- `POST /api/v1/calendar/book-appointment/` - Book appointment
- `GET /api/v1/calendar/google-auth/` - Google Calendar OAuth

## Database Schema

### Core Models
- **Workspace**: Business account with settings
- **Contact**: Customer identity with phone number
- **Session**: Chat session tracking
- **Conversation**: Conversation thread

### Messaging Models
- **Message**: Individual messages (text/audio/file)
- **AudioTranscription**: Whisper transcription results
- **MessageDraft**: Draft responses for manual approval

### Knowledge Base Models
- **KBDocument**: Uploaded documents
- **KBChunk**: Searchable text chunks with embeddings
- **SearchQuery**: Query analytics

### Calendar Models
- **Appointment**: Calendar bookings
- **AvailabilitySlot**: Available time slots
- **GoogleCalendarSync**: Sync tracking

## Background Tasks

Celery tasks handle:
- Audio transcription using OpenAI Whisper
- Document processing and embedding generation
- AI response generation with RAG
- Google Calendar synchronization

## Security Features

- Phone number masking in logs and admin
- Session-based authentication
- Input validation and sanitization
- Rate limiting on API endpoints
- Secure file uploads with pre-signed URLs

## Development

### Running Tests
```bash
python manage.py test
```

### Code Quality
```bash
# Format code
black .

# Lint code
flake8 .
```

### Database Management
```bash
# Reset database
python manage.py flush

# Create new migration
python manage.py makemigrations app_name

# Show migration status
python manage.py showmigrations
```

## Production Deployment

1. Set `DEBUG=False` in environment
2. Configure proper database credentials
3. Set up SSL certificates
4. Configure Redis for production
5. Set up file storage (AWS S3 or similar)
6. Configure Celery with proper broker
7. Set up monitoring and logging

## Environment Variables

See `env.example` for all available configuration options.

## License

This project is part of the AI Personal Business Assistant system.

