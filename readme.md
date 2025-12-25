# PDF Chat Assistant with Generative UI & Citations

A full-stack RAG (Retrieval-Augmented Generation) chatbot that enables users to upload PDF documents, ask questions, and receive streaming responses with precise citations. The system features a modern, "Perplexity-style" UI with a split-screen PDF viewer that automatically scrolls to cited pages.

## Architecture Overview

The application follows a decoupled client-server architecture using Server-Sent Events (SSE) for real-time communication.


### Streaming Protocol
The backend uses **Server-Sent Events (SSE)** to push updates to the client in a single HTTP connection. The `/chat/pdf/stream` endpoint yields JSON chunks formatted as `data: {...}\n\n`.

Event types supported:
- `tool`: Status updates (e.g., "analyzing document").
- `text`: Incremental text tokens for the assistant's response.
- `sources`: JSON array of citations (Page number, snippet) sent once generation is complete.
- `done`: Signals completion and returns the `session_id`.
- `error`: Error messages.

## Setup Instructions

### Backend Setup

The backend is built with **FastAPI** and uses **Redis** for session management.

**Prerequisites:** Python 3.11+.

1.  **Navigate to backend root** (Assumed root based on description).
2. **Create Environment:**
    ```bash
    python -m venv venv
    ```
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Environment Variables:** Create a `.env` file:
    ```env
    DATABASE_URL=
    config_key_jwt = 
    config_token_expire_sec = 
    config_key_root = 
    config_gemini_key =
    config_redis_url=
    ```
4.  **Run Server:**
    ```bash
    uvicorn main:app --reload
    ```
    The server will start at `http://localhost:8000`.

### Frontend Setup

The frontend is built with **Next.js 16+** and **Tailwind CSS**.

1.  **Navigate to frontend directory** (`src` parent).
2.  **Install Dependencies:**
    ```bash
    npm install
    ```
3.  **Environment Variables:** Create `.env.local`:
    ```env
    NEXT_PUBLIC_API_BASE_URL=
    ```
4.  **Run Development Server:**
    ```bash
    npm run dev
    ```
    Access the app at `http://localhost:3000`.

## Features & Screenshots

- **Tool Call Streaming:** Real-time feedback ("Analyzing PDF...") before the text appears.
- **Generative UI:** Markdown rendering with support for structured data.
- **Interactive Citations:** Clicking a citation `[1]` opens the PDF panel and scrolls to page 1.

## Project Structure

### Backend
```
root/
├── main.py             # Entry point, app configuration
├── function.py         # Utility functions
├── package.py          # Shared imports/packages
├── controller/
│   ├── auth_controller.py  # Login/Signup logic
│   └── chat_controller.py  # Streaming logic, PDF processing
├── router/
│   ├── auth_router.py      # /login, /signup routes
│   └── chat_router.py      # /chat/pdf/stream route
└── schema/
    └── ...                 # Pydantic models for Input/Output validation
```

### Frontend (`src/`)
```
src/
├── app/
│   ├── chat/           # Chat interface page
│   ├── login/          # Login page
│   └── signup/         # Signup page
├── components/
│   ├── auth/           # LoginForm, SignUpForm, AuthProvider
│   ├── chat/           # ChatInput, MessageBubble, Sidebar, ChatLayout
│   └── pdf/            # PdfViewer (using react-pdf)
└── lib/
    ├── api/            # API services (authService, chatService)
    ├── hooks/          # Custom hooks (useAuth, useTheme)
    └── types/          # TypeScript interfaces
```

## Libraries Used

### Backend
- **FastAPI**: High-performance web framework for building APIs.
- **Uvicorn**: ASGI server.
- **PyPDF2**: Simple library for extracting text from PDFs to build context.
- **OpenAI SDK (Gemini Mount)**: Used to interface with Gemini models using the familiar OpenAI Client pattern.
- **Redis**: Key-value store used to persist chat session history (`messages`, `source_map`) between API calls.
- **PyJWT**: Handling JSON Web Token generation and validation for Authentication.

### Frontend
- **Next.js 16+**: React framework with App Router for server-side rendering and routing.
- **Tailwind CSS**: Utility-first CSS framework for rapid styling (Dark/Light mode support).
- **Framer Motion**: Animation library used for smooth message entry and transitions.
- **react-pdf**: Used for rendering PDF documents in the browser.
- **React Context**: Used for global state management (Authentication).

## Design Decisions

### Why Plain Redis?
We chose a plain **Redis** instance over a complex vector database or queue system (like Celery/RabbitMQ) for simplicity and speed. 
- **Session Management**: Redis is perfect for storing the linear chat history and `source_map` metadata with a TTL (Time-To-Live).
- **No Heavy Queue**: Since the chat interaction is synchronous (User waits for Stream), `StreamingResponse` in FastAPI coupled with an async generator provides a responsive experience without the operational overhead of a separate worker queue.

### Generative UI & Streaming
The UI handles a custom SSE protocol. Instead of just pushing text, we push typed events (`tool`, `sources`, `text`). This allows the frontend to be "smart" — rendering a loading spinner when the tool event arrives, and then seamlessly switching to text generation, finally appending interactive citation buttons when the `sources` event arrives.

### Citation -> PDF Viewer Transition
We implemented a split-panel layout. The `source_map` generated by the backend maps citation IDs (e.g., `[1]`) to specific Page Numbers. When the frontend receives the `sources` event, it renders clickable buttons. Clicking these updates the state of the `PdfViewer` component, triggering a re-render of the specific page, creating a seamless verification loop for the user.

### Trade-offs
- **PyPDF2 vs OCR**: We used `PyPDF2` for text extraction. It is fast but fails on scanned images. A trade-off made for speed and lack of external dependencies (like Tesseract).
- **In-Memory Context**: We inject the entire PDF text into the context window. For very large PDFs, this might hit token limits. A RAG approach with embeddings would be better for scalability but was omitted to keep the architecture simple for this iteration.
