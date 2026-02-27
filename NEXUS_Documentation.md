# NEXUS - Next-Gen AI Agent

## Comprehensive Project Documentation

## 1. Introduction

NEXUS is a powerful AI-powered desktop automation and Robotic Process Automation (RPA) agent. It serves to empower users by allowing them to control their computer, manage files, manipulate spreadsheets, extract textual data from documents, and automate web operations through natural language commands or voice dictation.

## 2. Core Capabilities

NEXUS bridges the gap between natural language intention and computer operations. Its core capabilities include:

- **Natural Language & Voice Control**: Interpret spoken and typed commands locally using Faster-Whisper.
- **File System Management**: Execute CRUD operations natively (create, open, move, rename, delete files) with advanced semantic search.
- **Application Control**: Dynamically launch and manage closing of system applications and desktop software.
- **Spreadsheet Automation**: Interact with Excel directly, writing/reading data, formatting rows, and extracting content via `openpyxl` and `pandas`/`polars`.
- **Intelligent Web Automation**: Deploy agentic browsers using Playwright to search, extract data, and interact with web pages autonomously.
- **Document Processing**: Read and extract text from complex formats like PDF and Word files locally.

## 3. Technology Stack

### 3.1 Backend Architecture

The backend is built in **Python (3.10+)** leveraging modern async and AI frameworks:

- **API Framework**: `FastAPI` managed by `uvicorn` server for high-performance concurrent routing.
- **LLM Engine**: Integration via `langchain` and `langgraph` framework, supporting Google Gemini or OpenRouter pipelines.
- **Desktop APIs**: Built on `pyautogui`, `pygetwindow`, and `AppOpener`.
- **Data Engineering**: Data transformation powered by `pandas` and `polars`.

### 3.2 Frontend Architecture

The user interface is a web application constructed using **Node.js (18+)**:

- **Core Framework**: `Next.js` utilizing `React` components.
- **Styling UI**: `Tailwind CSS` for utility-based styling, enhanced visually with `Framer Motion` and stylized `lucide-react` icons.

## 4. System Architecture and Component Description

The application follows a decoupled client-server architecture:

### 4.1 Backend (`src/`)

- `main.py`: Initialization point for the FastAPI web server.
- `agent.py`: Brain of the agent logic handling command interpretation and routing.
- `capabilities/`: Subdirectory housing specialized domain controllers:
  - `desktop.py`: System file and window APIs.
  - `browser.py`: Playwright web controller instance.
  - `excel_manipulation.py`: Complex Excel sheet handling logic.
  - `dictation.py`: Local audio transcription node.
- `execution/`: Houses NLU (Natural Language Understanding) processing modules, system utils, and LLM specific adapters.

### 4.2 Frontend (`frontend/`)

- Handles the command input console, timeline feed visualization of the chat/command history, and active session interface.

## 5. Deployment and Setup

The setup requires isolated provisioning of the backend and frontend components.

### 5.1 Python Backend

1. Initialize a virtual environment in `src/`.
2. Install packages from `requirements.txt`.
3. Install browser dependencies globally via `playwright install`.
4. Store API Key tokens in `src/.env` (`OPENROUTER_API_KEY` or `GEMINI_API_KEY`).
5. Run the web server using `python main.py` at `http://localhost:8000`.

### 5.2 Node Frontend

1. Navigate to `frontend/`.
2. Execute dependency resolution via `npm install`.
3. Launch development instance via `npm run dev` running locally at `http://localhost:3000`.

## 6. End-User Workflow

1. Navigate to the web application at `localhost:3000`.
2. Provide commands through:
   - **Text Field**: Typing instructions manually.
   - **Voice**: By initializing the microphone interface, speaking locally up to 5 seconds, verifying the transcribed text, and committing the command for execution.
3. The server asynchronously executes user intents and returns the operative output.

## 7. Troubleshooting Guidelines

- **Port Conflict Errors**: Ensure ports `3000` or `8000` are not currently in use.
- **Missing Module Errors**: Reconfirm virtual environment is actively sourced before launching `main.py`. Ensure dependencies are successfully installed via requirements.
- **Voice Transcription**: Faster Whisper models are cached locally. The initial boot demands an active internet connection to securely fetch model weights locally. Permit microphone inputs inside the browser space.

---

**Version:** 1.0.0
