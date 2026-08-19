# Smart India Hackathon 2026 Submission | Internal Hackathon | Problem Statement ID: [IH-63]

## 🛠️ Tech Stack
- **Frontend**: React.js / Next.js (Located in `/frontend`)
- **Backend**: FastAPI (Python) (Located in `/backend`)
- **AI/Algorithm**: Google OR-Tools (MILP Solver), Python (Located in `/ai_pipeline`)
- **Database**: PostgreSQL (Located in `/database`)
- **Containerization**: Docker & Docker Compose

## 🏗️ Project Architecture
```text
├── ai_pipeline/       # AI models for tagging and parsing questions
├── backend/           # FastAPI application handling API requests & OR logic
├── database/          # PostgreSQL schemas, migrations, and seed data
├── docs/              # Additional project documentation
├── frontend/          # Web-based UI for blueprint creation and paper management
├── docker-compose.yml # Orchestration for all services
└── README.md          # Project documentation (You are here)
```

## 🚀 Getting Started

### Prerequisites
- [Docker](https://www.docker.com/get-started) and Docker Compose installed
- [Python 3.10+](https://www.python.org/downloads/) (for local development)

### Running the Application (Docker)
The easiest way to run the entire stack is using Docker Compose.

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd sih-question-paper-generator
   ```

2. **Start the services**:
   ```bash
   docker-compose up --build -d
   ```

3. **Access the application**:
   - **Frontend UI**: http://localhost:3000 (or as configured in frontend)
   - **Backend API Docs (Swagger)**: http://localhost:8000/docs
   - **Database**: Access via `localhost:5432`

### Local Development Setup
If you prefer running services locally without Docker:

**Backend Setup:**
```bash
cd backend
python -m venv .venv
# On Windows: .venv\Scriptsctivate
# On Unix: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend Setup:**
```bash
cd frontend
npm install
npm run dev
```