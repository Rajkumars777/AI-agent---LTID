# 🤖 NEXUS - Next-Gen AI Agent

A powerful AI-powered desktop automation and RPA (Robotic Process Automation) agent that understands natural language commands to control your computer, manage files, manipulate Excel spreadsheets, and more.

---

## ✨ Features

- 🗣️ **Natural Language Commands** - Just type or speak what you want to do
- 📁 **File Operations** - Open, move, rename, delete files with voice/text commands
- 📊 **Excel Manipulation** - Read, write, add rows, apply styles to spreadsheets
- 🖥️ **App Control** - Launch and close any application
- 🎤 **Voice Dictation** - Click mic, speak, verify, and execute (100% local & free)
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
├── src/                        # Python FastAPI Backend
│   ├── main.py                 # 🚀 Entry point - FastAPI app
│   ├── agent.py                # 🧠 Main agent logic & command routing
│   ├── requirements.txt        # Python dependencies
│   ├── .env                    # API keys (create this)
│   │
│   ├── capabilities/           # 🔧 Feature modules
│   │   ├── desktop.py          # File ops, app control, file search
│   │   ├── excel_manipulation.py # Excel read/write/style
│   │   ├── document.py         # PDF/Word extraction + conversions
│   │   ├── browser.py          # Web automation (Playwright)
│   │   ├── data.py             # Data processing (Polars)
│   │   ├── code_generator.py   # Dynamic code generation
│   │   ├── dictation.py        # Voice-to-text (Faster-Whisper)
│   │   ├── file_search_cache.py # Fast file search with caching
│   │   └── llm_general.py      # LLM utilities
│   │
│   ├── execution/              # 🔄 Workflow & NLU
│   │   ├── nlu.py              # Natural Language Understanding
│   │   ├── gemini_adapter.py   # Google Gemini LLM
│   │   ├── openrouter_adapter.py # OpenRouter multi-model
│   │   └── system_utils.py     # System utilities
│   │
│   ├── routers/                # 🌐 API Routes
│   │   ├── agent.py            # /agent/* endpoints
│   │   └── tools.py            # /tools/* endpoints
│   │
│   ├── api/                    # Voice API
│   │   └── dictation.py        # Voice transcription endpoint
│   │
│   └── tests/                  # 🧪 Test files
│       └── test_*.py
│
├── frontend/                   # Next.js React Frontend
│   ├── src/
│   │   ├── app/                # Next.js pages
│   │   │   └── page.tsx        # Main page
│   │   ├── components/         # React components
│   │   │   ├── InputConsole.tsx # Command input + mic
│   │   │   ├── TimelineFeed.tsx # Command history
│   │   │   └── ...
│   │   └── styles/             # CSS styles
│   ├── package.json
│   └── tailwind.config.js
│
└── README.md                   # This file
```

---

## 🎤 Voice Dictation

The app includes **FREE, LOCAL voice dictation** using Faster-Whisper:

1. **Click the mic button** (blue microphone icon)
2. **Speak your command** (records for up to 5 seconds)
3. **Text appears** in the input box
4. **Verify/edit** if needed
5. **Press Enter** to execute

✅ No API key needed - runs 100% locally!

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

### Voice not working

- Allow microphone permissions in browser
- Restart backend (first time downloads Whisper model)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

Made with ❤️ by Rajkumar
