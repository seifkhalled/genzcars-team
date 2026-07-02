# Cars Marketplace Chatbot

Intelligent AI assistant for the cars marketplace, built with **LangGraph** + **Groq (LLaMA 3.3 70B)** + **Qdrant** vector search.

## Architecture

The chatbot is a standalone FastAPI service (port 8001) using a LangGraph state machine with 7 specialized nodes:

```
User Message
    │
    ▼
preference_extractor ──► router
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
   search_node       advisor_node        seller_node
   (find listings)   (car analysis)      (selling help)
         │                  │                  │
         ▼                  ▼                  ▼
   guide_node         general_node
   (how-to FAQ)       (open chat)
         │                  │                  │
         └──────────────────┼──────────────────┘
                            ▼
                     responder_node
                     (streams tokens + data to SSE queue)
                            │
                         DB persist
                    (messages, preferences)
```

### Nodes

| Node | Purpose |
|------|---------|
| `preference_extractor` | Extracts car preferences (budget, brands, body type, etc.) from user messages using LLM |
| `router` | Classifies intent: search / advisor / seller / guide / general |
| `search_node` | Searches Qdrant vector DB for matching car listings |
| `advisor_node` | Analyzes a specific car listing (price, specs, market context) |
| `seller_node` | Helps sellers with listing optimization, pricing tips |
| `guide_node` | Answers how-to questions (buying process, financing, etc.) |
| `general_node` | Handles open-domain chat |
| `responder_node` | Streams response tokens via SSE, emits car data / price analysis, persists conversation to DB |

### Data Flow

1. **SSE streaming** — tokens, car listings, price analysis, and status events are pushed to a per-session `asyncio.Queue` consumed by the HTTP SSE response
2. **Persistence** — `responder_node` fire-and-forgets `insert_chat_message` and `upsert_user_preferences` to Supabase PostgreSQL via asyncpg
3. **Memory** — session history reloads from DB on reconnection; preferences accumulate across turns

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI + Uvicorn |
| Orchestration | LangGraph with MemorySaver checkpointer |
| LLM | Groq — openai/gpt-oss-120b |
| Vector DB | Qdrant (384-dim cosine, all-MiniLM-L6-v2 embeddings) |
| Database | Supabase PostgreSQL (asyncpg) |
| Streaming | Server-Sent Events |
| Embeddings | fastembed (sentence-transformers/all-MiniLM-L6-v2) |

## Setup

### Prerequisites

- Python 3.11+
- Groq API key
- Qdrant instance (cloud or local)
- PostgreSQL database (Supabase recommended)

### Environment

Copy `.env.example` or use the root `.env`:

```env
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b

DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

QDRANT_URL=https://your-instance.qdrant.io
QDRANT_API_KEY=eyJ...
QDRANT_COLLECTION=cars_ads

ENVIRONMENT=development
CHATBOT_PORT=8001
```

### Install & Run

```bash
cd Chatbot
pip install -r requirements.txt
uvicorn app.main:app --port 8001
```

### Docker

```bash
docker build -t cars-chatbot .
docker run -p 8001:8001 --env-file .env cars-chatbot
```

## API

### `POST /message`

Send a message to the chatbot. Returns an SSE stream.

```json
{
  "session_token": "abc123...",
  "message": "Show me SUVs under 500k EGP",
  "user_id": "uuid-or-null",
  "context_ad_id": "uuid-or-null"
}
```

#### SSE Event Types

| Type | Content | Description |
|------|---------|-------------|
| `token` | `string` | Response text token (streamed word by word) |
| `status` | `string` | Status update (e.g. "Searching listings...") |
| `cars` | `Ad[]` | Retrieved car listings matching the query |
| `similar_cars` | `Ad[]` | Similar cars to a specific listing |
| `price_analysis` | `object` | Price comparison data |
| `new_match` | `Ad[]` | New listings matching saved preferences |
| `done` | `null` | Signal that the response is complete |
| `error` | `string` | Error message |

### `GET /history/{session_token}`

Returns full conversation history and preferences for a session.

## Database Tables

Created automatically by the Backend service on startup:

- **`chat_sessions`** — tracks active sessions per user
- **`chat_messages`** — stores individual messages (role, content, node, referenced ads)
- **`user_preferences`** — accumulated preference state per session

## Clients

The Backend service (`localhost:8000`) proxies chat requests to the chatbot:

```
POST /api/v1/chat/session    → creates/resumes a session
POST /api/v1/chat/message    → proxies to chatbot /message (SSE)
GET  /api/v1/chat/history/{token} → proxies to chatbot /history
```

The Frontend (`useChat` hook) connects to the Backend API with SSE parsing and session persistence via localStorage.
