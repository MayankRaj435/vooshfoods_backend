# RAG News Chatbot - Backend

This repository contains the backend server for a Retrieval-Augmented Generation (RAG) chatbot. The application ingests news articles, stores them in a vector database, and uses a Large Language Model (LLM) to answer user questions based on the ingested content.

This backend is responsible for:
- Ingesting and processing news articles into a vector database.
- Handling real-time chat connections via WebSockets.
- Managing user sessions and chat history with Redis.
- Orchestrating the RAG pipeline: retrieving context and generating answers.

---

## Final Tech Stack

| Component             | Technology                                                              | Justification                                                                                             |
| --------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **Runtime**           | Node.js with Express.js                                                 | A robust and minimalist framework for building the REST API and WebSocket server.                         |
| **Real-time Chat**    | Socket.IO                                                               | Enables low-latency, bidirectional communication for streaming bot responses.                             |
| **LLM (Generation)**  | Gemini API (`gemini-pro`)                                               | A powerful and cost-effective LLM for generating high-quality, context-aware answers.                     |
| **Embeddings**        | Cohere API (`embed-english-v3.0`)                                       | Provides high-quality text embeddings necessary for the retrieval step of the RAG pipeline.               |
| **Vector Database**   | Qdrant                                                                  | A high-performance, open-source vector database for storing and searching text embeddings efficiently.    |
| **Cache & Sessions**  | Redis                                                                   | An in-memory data store used for fast access to session-specific chat histories.                          |
| **Deployment**        | Render.com                                                              | Offers a generous free tier for web services and Redis, making it ideal for hosting this project.         |

---

## Project Setup & Running Locally

### Prerequisites
- Node.js (v20.19+ recommended)
- Python
- Docker

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/news-rag-chatbot-backend.git
cd news-rag-chatbot-backend
```

### 2. Set Up Environment Variables
Create a `.env` file in the root of the project and add the following variables.

```ini
# .env

GEMINI_API_KEY="your_google_gemini_api_key_here"

# Get from Cohere Dashboard
COHERE_API_KEY="your_cohere_api_key_here"

# Local Docker URLs
QDRANT_URL="http://localhost:6333"
REDIS_URL="redis://localhost:6379"

# Server Configuration
PORT=3001
FRONTEND_URL="http://localhost:5173"
```

### 3. Start Local Databases with Docker
Run the following commands in your terminal to start local instances of Qdrant and Redis.
```bash
# Start Qdrant
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant

# Start Redis
docker run -p 6379:6379 -d redis/redis-stack-server:latest
```

### 4. Install Dependencies
Install both Python and Node.js dependencies.
```bash
# Install Python packages
pip install qdrant-client cohere requests beautifulsoup4 langchain python-dotenv lxml

# Install Node.js packages
npm install
```

### 5. Run the Data Ingestion Script
This script scrapes news articles, creates embeddings using the Cohere API, and stores them in your local Qdrant database. **This step is mandatory.**
```bash
python scripts/ingest.py
```

### 6. Start the Backend Server
```bash
node src/app.js
```
The server will start and listen on `http://localhost:3001`.

---

## Code Walkthrough & System Design

### End-to-End Flow
The application follows a classic Retrieval-Augmented Generation (RAG) pattern:

1.  **User Query:** The user sends a message from the frontend via a WebSocket connection.
2.  **Store & Embed:** The backend server receives the message, stores it in the Redis session history, and sends the query text to the Cohere API to generate a vector embedding.
3.  **Retrieve:** The resulting vector is used to search the Qdrant database. Qdrant performs a similarity search and returns the top-k most relevant text chunks from the ingested news articles.
4.  **Augment:** The retrieved text chunks (the "context") are combined with the original user query into a detailed prompt.
5.  **Generate:** This augmented prompt is sent to the Gemini API. Gemini generates a conversational answer based *only* on the provided context.
6.  **Stream Response:** The response from Gemini is streamed back to the frontend in real-time, creating a "typed-out" effect for the user.

### Redis Caching & Session Management
- **Purpose:** Redis is used as a high-speed, in-memory cache for session-specific data.
- **Mechanism:**
    - When a new user connects, a unique `sessionId` is generated.
    - Every message (both from the user and the bot) is stored in a Redis List associated with that `sessionId`.
    - A Time-To-Live (TTL) of 1 hour (`3600` seconds) is set on the session key. If the user is inactive for an hour, Redis automatically purges the chat history, keeping the database clean.
    - When a user reloads the page, their `sessionId` is retrieved from `localStorage`, and the chat history is fetched from Redis via a REST API endpoint (`/history/:sessionId`).

### Frontend/Backend Communication
- **REST API:** Used for stateless, one-off requests.
    - `POST /session`: Creates a new session and returns a `sessionId`.
    - `GET /history/:sessionId`: Fetches the chat history for a given session.
- **WebSockets (Socket.IO):** Used for persistent, real-time, bidirectional communication.
    - `join_session`: The client joins a dedicated "room" based on their `sessionId`.
    - `chat_message`: The client sends a new message to the server.
    - `bot_response_chunk`: The server streams parts of the AI's response back to the specific client in their room.
