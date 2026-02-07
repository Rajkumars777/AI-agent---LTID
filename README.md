# AI-agent---LTID

Here is how you can run this application. It consists of a Python backend and a Next.js frontend.

Prerequisites
Python 3.10+ (for the backend)
Node.js 18+ & npm (for the frontend)
1. Run the Backend
Open a terminal in the project root:

powershell
cd backend
# Create a virtual environment (optional but recommended)
python -m venv venv
.\venv\Scripts\activate
# Install dependencies
pip install -r requirements.txt
playwright install  # Needed for browser capabilities
# Run the server
python main.py
The backend will start on http://localhost:8000.

2. Run the Frontend
Open a new terminal window in the project root:

powershell
cd frontend
# Install dependencies
npm install
# Start the dev server
npm run dev
The frontend will start on http://localhost:3000.

Once both are running, open your browser to http://localhost:3000.