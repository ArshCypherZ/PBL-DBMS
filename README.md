# AI-Native Database Management with Automated Audit Logging

**Team:** Metavoid (DBMS-V-T177)

## Team Members
- Arsh Javed (230211214) - Team Lead
- Shahab Salik (230111108)
- Amaan Khan (23021663)
- Nayan Kumar (230112207)

## Project Overview
Natural language interface for PostgreSQL with automated audit logging and rollback support.

## Setup

### Database Setup
```bash
psql -h localhost -U user -d mydb -f database/schema.sql
```

### Backend Setup
```bash
pip install -r requirements.txt
python backend/app.py
```

### Frontend Setup
```bash
streamlit run frontend/app.py
```

## Architecture
- Frontend: Streamlit
- Backend: FastAPI
- Database: PostgreSQL
