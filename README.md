# 📱 Field Sales CRM — AI-Powered Mobile CRM for Field Sales Teams

> Transform field sales operations: from manual Excel tracking to an AI-powered mobile CRM that automatically records visits, transcribes conversations, and fills your CRM — hands-free.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![React Native](https://img.shields.io/badge/React%20Native-Expo-blueviolet.svg)](https://expo.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![SQLite](https://img.shields.io/badge/SQLite-3.40+-orange.svg)](https://sqlite.org)

## The Problem

A kitchen supplies distribution business has **50 field sales reps** visiting clients daily. Currently:

- ❌ Reps **call the owner by phone** after each visit to report results
- ❌ The owner **manually types notes into an Excel spreadsheet**
- ❌ Critical details are **lost in translation** between verbal report and typed notes
- ❌ **No analytics** — no way to know conversion rates, best performers, or pipeline health
- ❌ The owner becomes a **bottleneck** receiving 50+ calls per day

## The Solution

A mobile app that **automates the entire reporting cycle**:

```
📱 Syncs phone contacts → 📞 Tracks calls (got appointment? y/n)
    → 📍 GPS detects arrival at client → 🎙️ Records the conversation
    → 🤖 AI transcribes & extracts structured data → 🗄️ Updates CRM automatically
```

The owner sees everything in real-time on their laptop dashboard — **zero phone calls needed**.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    📱 MOBILE APP (per rep)                   │
│            React Native + Expo (iOS & Android)               │
│                                                              │
│  expo-contacts ─── expo-linking ─── expo-location ─── expo-av│
│       │                │                │              │     │
│   Sync phone      Track calls      Geofencing      Record    │
│   contacts       (appointment?)   (detect arrival)   audio   │
│                                                              │
│              WatermelonDB (offline SQLite sync)              │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTP sync when online
┌──────────────────────▼───────────────────────────────────────┐
│              💻 BACKEND (owner's Windows laptop)             │
│                    FastAPI + SQLite                          │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │  REST API   │  │ Whisper API  │  │   GPT-4o-mini API   │  │
│  │  /api/v1/*  │  │ Audio → Text │  │ Text → JSON fields  │  │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│         ▼                ▼                     ▼             │
│    ┌─────────────────────────────────────────────────┐       │
│    │              SQLite (crm.db)                    │       │
│    │  vendedores │ clientes │ llamadas │ visitas     │       │
│    └─────────────────────────────────────────────────┘       │
│                          │                                   │
│              Streamlit Dashboard (localhost:8501)            │
└──────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Mobile App | React Native + Expo | Cross-platform (Android + iPhone), single codebase |
| Contacts | expo-contacts | Read phone's native contacts |
| Call Tracking | expo-linking + call logs | Initiate calls, log outcomes |
| GPS/Geofencing | expo-location | Detect arrival at client location |
| Audio Recording | expo-av | Record visit conversations |
| Offline Storage | WatermelonDB | SQLite on device, syncs when online |
| Backend API | FastAPI (Python) | REST API on owner's laptop |
| Database | SQLite (WAL mode) | Zero-install, single file, portable |
| Transcription | OpenAI Whisper API | Audio → text (Spanish + English) |
| Data Extraction | OpenAI GPT-4o-mini | Transcript → structured CRM fields |
| Dashboard | Streamlit | Real-time analytics on localhost |
| Tunnel | Cloudflare Tunnel | Expose laptop API to internet (free) |

## Database Schema

The schema maps directly to the client's existing Excel spreadsheet:

| Excel Column | DB Field | Table | Auto-filled? |
|---|---|---|---|
| Row # | `id` | clientes | ✅ Auto |
| Col B: Nombre y apellido | `nombre_apellido` | clientes | ✅ From contacts |
| Col C: Teléfono | `telefono` | clientes | ✅ From contacts |
| Col D: Fuente | `fuente` | clientes | Manual |
| Col E: Zona | `zona` | clientes | Manual |
| Col F: Dirección | `direccion` + `lat/lng` | clientes | ✅ GPS |
| Col G: Notas del vendedor | `notas_vendedor` | visitas | ✅ AI extraction |
| Col H: Notas Telemarketing | `notas_telemarketing` | llamadas | Manual |
| Col I: Resultados | `resultados` | visitas | ✅ AI extraction |
| Row color (legend) | `estado` | clientes | ✅ AI extraction |

**States** (from Excel color legend): `no_llamar` (red), `venta` (green), `equivocado` (yellow), `cita` (purple), `seguimiento` (blue)

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for mobile app)
- OpenAI API key
- Windows 10/11 (backend) — also works on macOS/Linux

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/jaogye/field-sales-crm.git
cd field-sales-crm/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your OpenAI API key

# Initialize database
python -m app.core.init_db

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Mobile App Setup

```bash
cd mobile
npm install
npx expo start
```

### Dashboard

```bash
cd backend
streamlit run dashboard.py
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/vendedores/` | Register a new sales rep |
| `GET` | `/api/v1/clientes/` | List all clients |
| `POST` | `/api/v1/clientes/sync` | Sync contacts from phone |
| `POST` | `/api/v1/llamadas/` | Log a call result |
| `POST` | `/api/v1/visitas/` | Create visit record |
| `POST` | `/api/v1/visitas/{id}/audio` | Upload visit audio |
| `POST` | `/api/v1/visitas/{id}/transcribir` | Transcribe + extract CRM fields |
| `GET` | `/api/v1/estadisticas/` | Dashboard statistics |

## Project Structure

```
field-sales-crm/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── core/
│   │   │   ├── config.py        # Settings & environment
│   │   │   ├── database.py      # SQLite + SQLAlchemy setup
│   │   │   └── init_db.py       # DB initialization & Excel import
│   │   ├── models/
│   │   │   ├── vendedor.py      # Sales rep model
│   │   │   ├── cliente.py       # Client model
│   │   │   ├── llamada.py       # Call log model
│   │   │   └── visita.py        # Visit + transcription model
│   │   ├── schemas/
│   │   │   ├── vendedor.py      # Pydantic schemas
│   │   │   ├── cliente.py
│   │   │   ├── llamada.py
│   │   │   └── visita.py
│   │   ├── api/
│   │   │   ├── vendedores.py    # Sales rep endpoints
│   │   │   ├── clientes.py      # Client endpoints
│   │   │   ├── llamadas.py      # Call tracking endpoints
│   │   │   ├── visitas.py       # Visit + audio endpoints
│   │   │   └── estadisticas.py  # Dashboard stats
│   │   └── services/
│   │       ├── transcription.py # Whisper API integration
│   │       ├── extraction.py    # GPT extraction logic
│   │       └── sync.py          # Mobile sync logic
│   ├── dashboard.py             # Streamlit dashboard
│   ├── requirements.txt
│   ├── .env.example
│   └── tests/
├── mobile/                      # React Native + Expo app
│   ├── app/                     # Expo Router screens
│   ├── components/
│   ├── services/
│   └── package.json
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   └── DEPLOYMENT.md
├── scripts/
│   ├── import_excel.py          # Import existing Excel data
│   └── setup_tunnel.py          # Cloudflare Tunnel setup
├── README.md
└── LICENSE
```

## Roadmap

- [x] Project architecture & documentation
- [ ] **Phase 1**: Backend API (FastAPI + SQLite + models)
- [ ] **Phase 2**: OpenAI integration (Whisper + GPT extraction)
- [ ] **Phase 3**: Mobile app (contacts + calls + GPS)
- [ ] **Phase 4**: Audio recording + upload + transcription
- [ ] **Phase 5**: Streamlit dashboard
- [ ] **Phase 6**: Pilot with 5 reps → full rollout

## Cost Estimate (50 reps)

| Service | Monthly Cost |
|---------|-------------|
| OpenAI Whisper API | ~$15-30 |
| OpenAI GPT-4o-mini | ~$5-15 |
| SQLite | $0 (local file) |
| FastAPI | $0 (runs on laptop) |
| Cloudflare Tunnel | $0 (free tier) |
| **Total** | **$20-45/month** |

*vs. SaaS CRM for 50 users: $500-2,500/month*

## Legal Notice

This application records in-person sales conversations. In New York State, only **one-party consent** is required for recording conversations (NY Penal Law § 250.00). The sales rep (as a party to the conversation) provides that consent. However, it is recommended to inform clients that the conversation is being recorded as a best practice.

## License

MIT License — see [LICENSE](LICENSE) for details.

## Author

Built by [Juan Alvarado](https://www.linkedin.com/in/juan-alvarado-71a5a629/) — PhD Computer Science, independent contractor specializing in data engineering and AI systems.
