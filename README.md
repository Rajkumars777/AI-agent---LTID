# NEXUS - Next-Gen AI Agent

A powerful AI-powered desktop automation and RPA (Robotic Process Automation) agent that understands natural language commands to control your computer, manage files, manipulate Excel spreadsheets, and more.

---

## Features

- 🗣️ **Natural Language Commands** - Just type or speak what you want to do
- 📁 **File Operations** - Open, move, rename, delete files with voice/text commands
- 📊 **Excel Manipulation** - Read, write, add rows, apply styles to spreadsheets
- 🖥️ **App Control** - Launch and close any application
- 🔍 **Smart File Search** - Fast cached search across your system
- 📄 **Document Processing** - Extract text from PDF/Word, convert formats
- 🌐 **AI Web Automation** - Agent can browse, search, and extract data from the web using Playwright

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version |
| ----------- | ------- |
| Python      | 3.10+   |
| Node.js     | 18+     |
| npm         | 9+      |

### Step 1: Clone the Repository

```powershell
git clone https://github.com/Rajkumars777/AI-agent---LTID.git
cd AI-agent---LTID
```

### Step 2: Setup Backend

```powershell
# Navigate to src
cd src

# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers (for web automation)
playwright install
```

### Step 3: Configure Environment

Create a `.env` file in the `src/` folder:

```env
# Required: Choose ONE LLM provider

# Option 1: OpenRouter (Recommended - works with many models)
OPENROUTER_API_KEY=your_openrouter_api_key

# Option 2: Google Gemini
GEMINI_API_KEY=your_gemini_api_key
```

Get your API key:

- **OpenRouter**: https://openrouter.ai/keys (supports GPT-4, Claude, Llama, etc.)
- **Gemini**: https://makersuite.google.com/app/apikey

### Step 4: Run Backend

```powershell
cd src
python main.py
```

✅ Backend runs on: `http://localhost:8000`

### Step 5: Setup & Run Frontend

Open a **new terminal**:

```powershell
cd frontend

# Install Node dependencies
npm install

# Start development server
npm run dev
```

✅ Frontend runs on: `http://localhost:3000`

### Step 6: Use the App

1. Open `http://localhost:3000` in your browser
2. Type or click the mic to speak commands like:
   - `"open notepad"`
   - `"delete sample.xlsx"`
   - `"rename old.txt to new.txt"`
   - `"add a row to budget.xlsx with name John and amount 500"`

---

## 📦 Dependencies

### Backend (Python)

| Package            | Purpose                    |
| ------------------ | -------------------------- |
| `fastapi`        | Web framework for API      |
| `uvicorn`        | ASGI server                |
| `python-dotenv`  | Environment variables      |
| `pyautogui`      | Desktop automation         |
| `pygetwindow`    | Window management          |
| `openpyxl`       | Excel read/write           |
| `pandas`         | Data manipulation          |
| `polars`         | Fast data processing       |
| `pymupdf`        | PDF text extraction        |
| `python-docx`    | Word document handling     |
| `playwright`     | Browser automation         |
| `faster-whisper` | Local voice-to-text (free) |
| `send2trash`     | Safe file deletion         |
| `AppOpener`      | Application launching      |
| `langchain`      | LLM framework              |
| `langgraph`      | Agent workflows            |

### Frontend (Node.js)

| Package           | Purpose         |
| ----------------- | --------------- |
| `next`          | React framework |
| `react`         | UI library      |
| `tailwindcss`   | Styling         |
| `framer-motion` | Animations      |
| `lucide-react`  | Icons           |
| `axios`         | API calls       |

---

## 📂 Project Structure

```
AI-agent---LTID/
├── src/                             # Python FastAPI Backend
│   ├── main.py                      # 🚀 Entry point - FastAPI app
│   │
│   ├── api/                         # 🌐 API layer
│   │   └── routers/
│   │       ├── agent.py             # /agent/* endpoints
│   │       ├── events.py            # SSE event streaming
│   │       ├── tools.py             # /tools/* endpoints
│   │       └── voice.py             # Voice transcription endpoint
│   │
│   ├── core/                        # 🧠 AI brain
│   │   ├── agent.py                 # Main agent routing logic
│   │   ├── execution/               # Task planning & execution
│   │   │   ├── orchestrator.py      # Unified task orchestrator
│   │   │   ├── multistep_planner.py # Multi-step task planner
│   │   │   ├── multistep_executor.py# Plan executor
│   │   │   ├── handlers.py          # Action handlers (DYNAMIC_CODE, etc.)
│   │   │   ├── nlu.py               # Natural Language Understanding
│   │   │   ├── confirmation_handler.py # User confirmation flow
│   │   │   ├── interaction.py       # Interaction manager
│   │   │   ├── system_utils.py      # System utility helpers
│   │   │   └── task_memory.py       # Task state memory
│   │   ├── intelligence/            # Code & report generation
│   │   │   ├── code_generator.py    # Dynamic Python code generation
│   │   │   ├── report_generator.py  # Report creation
│   │   │   └── app_templates.py     # App scaffolding templates
│   │   ├── llm/                     # LLM adapters
│   │   │   ├── agent_llm.py         # Core LLM interface
│   │   │   └── openrouter_adapter.py# OpenRouter multi-model adapter
│   │   └── security/                # Security & credential management
│   │       ├── manager.py           # Security manager
│   │       └── credential_handler.py# API key/credential handler
│   │
│   ├── models/                      # 📐 Data models
│   │   ├── document.py              # Document schema
│   │   └── report_schema.py         # Report schema
│   │
│   ├── services/                    # ⚙️ Feature services
│   │   ├── browser/                 # Web automation
│   │   │   ├── agent.py             # Browser agent
│   │   │   └── intelligent_web_automation.py
│   │   ├── data/                    # Data & file processing
│   │   │   ├── excel.py             # Excel read/write/style (openpyxl, polars)
│   │   │   ├── retriever.py         # Data retrieval (stocks, market data)
│   │   │   ├── document_ops.py      # PDF/Word operations
│   │   │   └── file_search.py       # Fast file search with caching
│   │   ├── desktop/                 # Desktop automation
│   │   │   ├── screen_agent.py      # Screen-based AI agent
│   │   │   ├── automation.py        # PyAutoGUI automation
│   │   │   ├── generative_agent.py  # Generative desktop agent
│   │   │   ├── ops.py               # Desktop operations
│   │   │   ├── file_index.py        # File indexing & cache
│   │   │   └── agent_s/             # Agent-S integration
│   │   │       └── integration.py
│   │   └── vision/                  # Vision/screen analysis
│   │       └── engine.py
│   │
│   ├── tools/                       # 🔧 Tool registry & generators
│   │   ├── core_tools.py            # Core built-in tools
│   │   ├── document_intelligence_tools.py # Document AI tools
│   │   ├── generator.py             # Dynamic tool generator
│   │   ├── registry.py              # Tool registry loader
│   │   ├── registry.json            # Tool metadata registry
│   │   └── generated/               # Auto-generated tool scripts
│   │       ├── open_excel_application.py
│   │       ├── compress_excel_file.py
│   │       └── ...
│   │
│   └── utils/                       # 🛠️ Shared utilities
│       └── utils/
│           └── resolver.py          # Path & target resolver
│
├── frontend/                        # Next.js React Frontend
│   └── src/
│       ├── app/                     # Next.js App Router pages
│       │   ├── page.tsx             # Main dashboard page
│       │   ├── layout.tsx           # Root layout
│       │   ├── globals.css          # Global CSS
│       │   └── overlay/             # Overlay UI route
│       │       ├── page.tsx
│       │       └── layout.tsx
│       ├── components/              # React components
│       │   ├── AriaAssistant.tsx    # 🎙️ Voice assistant UI (Aria)
│       │   ├── InputConsole.tsx     # Command input + mic button
│       │   ├── TimelineFeed.tsx     # Live task event timeline
│       │   ├── RecentsHistory.tsx   # Recent commands history
│       │   ├── ResultCard.tsx       # Task result display card
│       │   ├── VoiceControlPanel.tsx# Voice control panel
│       │   ├── VoiceMicIndicator.tsx# Mic status indicator
│       │   ├── VoiceWaveform.tsx    # Waveform animation
│       │   ├── WakeWordAnimation.tsx# Wake word visual feedback
│       │   ├── BrowserViewport.tsx  # Embedded browser view
│       │   ├── HeroSection.tsx      # Landing hero section
│       │   ├── TauriProvider.tsx    # Tauri desktop bridge
│       │   └── ui/                  # Reusable UI primitives
│       ├── hooks/                   # Custom React hooks
│       ├── lib/                     # Utility libraries
│       ├── styles/                  # Component styles
│       │   └── aria.css             # Aria assistant styles
│       └── types/                   # TypeScript type definitions
│
├── requirements.txt                 # Python dependencies
├── .env                             # API keys (create this)
├── .gitignore
└── README.md                        # This file
```

---

## 💡 Example Commands

| Command                                            | What it does                   |
| -------------------------------------------------- | ------------------------------ |
| `open notepad`                                   | Launches Notepad               |
| `open excel`                                     | Launches Microsoft Excel       |
| `close chrome`                                   | Closes Chrome browser          |
| `delete report.pdf`                              | Moves file to Recycle Bin      |
| `rename old.txt to new.txt`                      | Renames the file               |
| `move data.xlsx to Documents`                    | Moves file to Documents folder |
| `read sample.xlsx`                               | Shows Excel contents           |
| `add row to data.xlsx with name John and age 25` | Adds a new row                 |

---

## 🛠️ Troubleshooting

### Backend won't start

```powershell
# Make sure virtual environment is activated
.\venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Frontend errors

```powershell
# Clear npm cache and reinstall
rm -rf node_modules
npm install
```

### "API key not found" error

- Make sure `.env` file exists in `src/` folder
- Check that API key is correctly set (no extra spaces)
- ---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

Made with ❤️ by Rajkumar
