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

## Use Cases

### 1 — Sales Rep Onboarding (Register & Login)

```
Vendedor (Phone)               Backend API               SQLite (crm.db)
      │                             │                           │
      │  POST /api/v1/vendedores/   │                           │
      │  {nombre, telefono,         │                           │
      │   password}                 │                           │
      │ ─────────────────────────►  │                           │
      │                             │  SELECT vendedor          │
      │                             │  WHERE telefono = ?       │
      │                             │ ──────────────────────►   │
      │                             │  ◄──────────────────────  │
      │                             │  not found                │
      │                             │                           │
      │                             │  INSERT vendedor          │
      │                             │  (password_hash =         │
      │                             │   pbkdf2_sha256)          │
      │                             │ ──────────────────────►   │
      │                             │  ◄──────────────────────  │
      │  ◄─────────────────────────  │                           │
      │  201 {id, nombre, telefono} │                           │
      │                             │                           │
      │  POST /api/v1/auth/login    │                           │
      │  {telefono, password}       │                           │
      │ ─────────────────────────►  │                           │
      │                             │  SELECT vendedor WHERE    │
      │                             │  telefono = ? AND         │
      │                             │  activo = true            │
      │                             │ ──────────────────────►   │
      │                             │  ◄──────────────────────  │
      │                             │  vendedor record          │
      │                             │                           │
      │                             │  verify_password(pwd,     │
      │                             │  password_hash)           │
      │  ◄─────────────────────────  │                           │
      │  200 {access_token (JWT),   │                           │
      │       vendedor_id}          │                           │
      │                             │                           │
      │  [Token saved in phone      │                           │
      │   AsyncStorage — used on    │                           │
      │   all future requests]      │                           │
```

---

### 2 — Contact Sync from Phone

```
Vendedor (Phone)          Phone Contacts           Backend API             SQLite (crm.db)
      │                        │                        │                       │
      │  Request permission    │                        │                       │
      │ ─────────────────────► │                        │                       │
      │  ◄───────────────────  │                        │                       │
      │  [Contacts granted]    │                        │                       │
      │                        │                        │                       │
      │  Read all contacts     │                        │                       │
      │ ─────────────────────► │                        │                       │
      │  ◄───────────────────  │                        │                       │
      │  [{nombre, telefono}…] │                        │                       │
      │                        │                        │                       │
      │  POST /clientes/sync   │                        │                       │
      │  Authorization: Bearer │                        │                       │
      │  {contactos: [...]}    │                        │                       │
      │ ──────────────────────────────────────────────► │                       │
      │                        │                        │                       │
      │                        │  [for each contact]    │                       │
      │                        │                        │  SELECT cliente       │
      │                        │                        │  WHERE telefono = ?   │
      │                        │                        │ ─────────────────►    │
      │                        │                        │  ◄───────────────     │
      │                        │                        │  exists → skipped++   │
      │                        │                        │  not found →          │
      │                        │                        │  INSERT cliente       │
      │                        │                        │  created++            │
      │                        │                        │ ─────────────────►    │
      │                        │                        │                       │
      │  ◄────────────────────────────────────────────  │                       │
      │  200 {created: N,      │                        │                       │
      │       skipped: M,      │                        │                       │
      │       total: N+M}      │                        │                       │
      │                        │                        │                       │
      │  [New clients visible in owner's dashboard]     │                       │
```

---

### 3 — Logging a Call (Telemarketing)

```
Vendedor (Phone)            Backend API              SQLite (crm.db)
      │                          │                        │
      │  [Opens client card]     │                        │
      │  [Taps "Llamar"]         │                        │
      │  → Native phone dialer opens                      │
      │                          │                        │
      │  [Call ends]             │                        │
      │  [Selects outcome:       │                        │
      │   cita / no_cita /       │                        │
      │   no_contesta /          │                        │
      │   equivocado /           │                        │
      │   no_llamar / venta]     │                        │
      │                          │                        │
      │  POST /api/v1/llamadas/  │                        │
      │  Authorization: Bearer   │                        │
      │  {cliente_id,            │                        │
      │   resultado,             │                        │
      │   notas_telemarketing}   │                        │
      │ ───────────────────────► │                        │
      │                          │  Extract vendedor_id   │
      │                          │  from JWT              │
      │                          │                        │
      │                          │  INSERT INTO llamadas  │
      │                          │ ─────────────────────► │
      │                          │                        │
      │                          │  [if resultado maps    │
      │                          │   to a known status]   │
      │                          │  UPDATE clientes.estado│
      │                          │ ─────────────────────► │
      │                          │  ◄─────────────────── │
      │  ◄─────────────────────  │                        │
      │  201 {llamada_id, fecha} │  [Client card updates  │
      │                          │   status color]        │
```

---

### 4 — Field Visit with AI Processing (Core Flow)

```
Vendedor (Phone)     GPS / Mic      Backend API      OpenAI API       SQLite (crm.db)
      │                  │               │                │                 │
      │  [Opens Visita   │               │                │                 │
      │   tab, selects   │               │                │                 │
      │   client]        │               │                │                 │
      │                  │               │                │                 │
      │  Request GPS     │               │                │                 │
      │ ───────────────► │               │                │                 │
      │  ◄─────────────  │               │                │                 │
      │  {lat, lng}      │               │                │                 │
      │                  │               │                │                 │
      │  POST /visitas/  │               │                │                 │
      │  Authorization:  │               │                │                 │
      │  {cliente_id,    │               │                │                 │
      │   lat, lng}      │               │                │                 │
      │ ───────────────────────────────► │                │                 │
      │                  │               │  INSERT visita │                 │
      │                  │               │  (vendedor_id  │                 │
      │                  │               │   from token)  │                 │
      │                  │               │ ─────────────────────────────►   │
      │  ◄─────────────────────────────  │                │                 │
      │  {visita_id: 42} │               │                │                 │
      │                  │               │                │                 │
      │  Request mic     │               │                │                 │
      │  permission      │               │                │                 │
      │ ───────────────► │               │                │                 │
      │  [🔴 Recording  │               │                │                 │
      │   starts…]       │               │                │                 │
      │                  │               │                │                 │
      │  [Conversation   │               │                │                 │
      │   happens]       │               │                │                 │
      │                  │               │                │                 │
      │  [Taps STOP]     │               │                │                 │
      │ ───────────────► │               │                │                 │
      │  ◄─────────────  │               │                │                 │
      │  {uri, sizeMB}   │               │                │                 │
      │                  │               │                │                 │
      │  POST /visitas/42/audio          │                │                 │
      │  Authorization: Bearer           │                │                 │
      │  [.m4a binary upload]            │                │                 │
      │ ───────────────────────────────► │                │                 │
      │                  │               │  Validate magic│                 │
      │                  │               │  bytes, size   │                 │
      │                  │               │  Save to disk  │                 │
      │                  │               │  UPDATE visita │                 │
      │                  │               │  audio_path    │                 │
      │                  │               │ ─────────────────────────────►   │
      │  ◄─────────────────────────────  │                │                 │
      │  {message: "Audio uploaded"}     │                │                 │
      │                  │               │                │                 │
      │  POST /visitas/42/transcribir    │                │                 │
      │  Authorization: Bearer           │                │                 │
      │ ───────────────────────────────► │                │                 │
      │                  │               │                │                 │
      │                  │               │  Whisper API   │                 │
      │                  │               │  audio → text  │                 │
      │                  │               │ ─────────────► │                 │
      │                  │               │  ◄───────────  │                 │
      │                  │               │  {text, lang}  │                 │
      │                  │               │                │                 │
      │                  │               │  GPT-4o-mini   │                 │
      │                  │               │  text → CRM    │                 │
      │                  │               │ ─────────────► │                 │
      │                  │               │  ◄───────────  │                 │
      │                  │               │  {notas,       │                 │
      │                  │               │  resultados,   │                 │
      │                  │               │  productos,    │                 │
      │                  │               │  nivel_interes,│                 │
      │                  │               │  estado_suger} │                 │
      │                  │               │                │                 │
      │                  │               │  UPDATE visita │                 │
      │                  │               │  procesado=true│                 │
      │                  │               │  UPDATE cliente│                 │
      │                  │               │  estado, lat,  │                 │
      │                  │               │  lng           │                 │
      │                  │               │ ─────────────────────────────►   │
      │  ◄─────────────────────────────  │                │                 │
      │  {notas_vendedor,│               │                │                 │
      │   resultados,    │               │                │                 │
      │   nivel_interes, │               │                │                 │
      │   estado_suger…} │               │                │                 │
      │                  │               │                │                 │
      │  [Result screen  │               │                │                 │
      │   shows AI       │               │                │                 │
      │   summary]       │               │                │                 │
```

---

### 5 — Owner Views Real-Time Dashboard

```
Owner (Dashboard)           Streamlit (:8501)            Backend API             SQLite (crm.db)
      │                             │                          │                       │
      │  [Opens dashboard URL]      │                          │                       │
      │ ──────────────────────────► │                          │                       │
      │                             │  GET /api/v1/            │                       │
      │                             │  estadisticas/           │                       │
      │                             │  Authorization: Bearer   │                       │
      │                             │ ───────────────────────► │                       │
      │                             │                          │  COUNT clientes,      │
      │                             │                          │  vendedores activos   │
      │                             │                          │  COUNT llamadas /     │
      │                             │                          │  visitas hoy          │
      │                             │                          │  COUNT citas & ventas │
      │                             │                          │  este mes → tasa_citas│
      │                             │                          │  GROUP BY             │
      │                             │                          │  cliente.estado       │
      │                             │                          │  TOP 5 vendedores     │
      │                             │                          │  por visitas (mes)    │
      │                             │                          │ ─────────────────►    │
      │                             │                          │  ◄───────────────     │
      │                             │                          │  aggregated results   │
      │                             │  ◄─────────────────────  │                       │
      │                             │  EstadisticasResponse    │                       │
      │  ◄────────────────────────  │                          │                       │
      │  KPI cards + charts         │                          │                       │
      │  (tasa_citas, pipeline      │                          │                       │
      │   por estado, top reps)     │                          │                       │
      │                             │                          │                       │
      │  [Filter: estado=cita,      │                          │                       │
      │   zona=Brooklyn]            │                          │                       │
      │ ──────────────────────────► │                          │                       │
      │                             │  GET /api/v1/clientes/   │                       │
      │                             │  ?estado=cita            │                       │
      │                             │  &zona=Brooklyn          │                       │
      │                             │ ───────────────────────► │                       │
      │                             │                          │  SELECT clientes      │
      │                             │                          │  WHERE estado='cita'  │
      │                             │                          │  AND zona ILIKE       │
      │                             │                          │  '%Brooklyn%'         │
      │                             │                          │ ─────────────────►    │
      │                             │                          │  ◄───────────────     │
      │                             │  ◄─────────────────────  │  filtered list        │
      │                             │  ClienteResponse[]       │                       │
      │  ◄────────────────────────  │                          │                       │
      │  Filtered client table      │                          │                       │
      │  with visit history         │                          │                       │
```

---

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
| Backend API | FastAPI (Python) | REST API deployed on Fly.io (24/7) |
| Database | SQLite (WAL mode) | Zero-install, single file, persistent volume |
| Transcription | OpenAI Whisper API | Audio → text (Spanish + English) |
| Data Extraction | OpenAI GPT-4o-mini | Transcript → structured CRM fields |
| Dashboard | Streamlit | Real-time analytics (public URL on Fly.io) |
| Hosting | Fly.io | 24/7 cloud deployment, persistent volume |

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

### Backend Setup (local / development)

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
# Edit .env — required fields:
#   OPEN_API_KEY=sk-...
#   SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
#   DATABASE_PATH=C:/ventas/crm.db
#   AUDIO_STORAGE_PATH=C:/ventas/audios

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Backend Setup (Fly.io — production, 24/7)

```powershell
# Install flyctl — Windows PowerShell
iwr https://fly.io/install.ps1 -useb | iex

# Login
fly auth login

# From the backend/ directory
cd field-sales-crm/backend

# Create a 5GB persistent volume for SQLite DB + audio files
fly volumes create crm_data --region ewr --size 5

# Set secrets (one per command in PowerShell)
fly secrets set SECRET_KEY=<generate_with_python>
fly secrets set OPEN_API_KEY=sk-...
fly secrets set DATABASE_PATH=/data/crm.db
fly secrets set AUDIO_STORAGE_PATH=/data/audios
fly secrets set DEBUG=false
fly secrets set ACCESS_TOKEN_EXPIRE_MINUTES=43200

# Deploy
fly deploy

# Check it's running
fly status
fly logs
```

After deploy:

| Service | URL |
|---------|-----|
| **API** | `https://field-sales-crm.fly.dev` |
| **Dashboard** | `https://field-sales-crm.fly.dev:8501` |

### Mobile App Setup

```bash
cd mobile
npm install
npx expo start
```

The production API URL is already configured in `mobile/services/api.js`:
```javascript
: 'https://field-sales-crm.fly.dev'
```

### Dashboard

The dashboard runs automatically as part of the Fly.io deployment and is accessible at:
```
https://field-sales-crm.fly.dev:8501
```

For local development:
```bash
cd backend
streamlit run dashboard.py
```

## API Endpoints

Endpoints marked 🔒 require a `Authorization: Bearer <token>` header.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/vendedores/` | Public | Register a new sales rep (requires `password`) |
| `POST` | `/api/v1/auth/login` | Public | Login — returns JWT access token |
| `GET` | `/api/v1/vendedores/` | 🔒 | List active sales reps |
| `GET` | `/api/v1/clientes/` | 🔒 | List clients with optional filters |
| `POST` | `/api/v1/clientes/` | 🔒 | Create a new client |
| `PUT` | `/api/v1/clientes/{id}` | 🔒 | Update a client record |
| `POST` | `/api/v1/clientes/sync` | 🔒 | Bulk sync contacts from phone |
| `POST` | `/api/v1/llamadas/` | 🔒 | Log a call result (own rep only) |
| `GET` | `/api/v1/llamadas/` | 🔒 | List own call history |
| `POST` | `/api/v1/visitas/` | 🔒 | Create visit record (own rep only) |
| `POST` | `/api/v1/visitas/{id}/audio` | 🔒 | Upload visit audio (owner only) |
| `POST` | `/api/v1/visitas/{id}/transcribir` | 🔒 | Transcribe + extract CRM fields (owner only) |
| `GET` | `/api/v1/visitas/` | 🔒 | List own visits |
| `GET` | `/api/v1/estadisticas/` | 🔒 | Dashboard statistics |

### Authentication Flow

```bash
# 1. Register a rep (one-time)
curl -X POST /api/v1/vendedores/ \
  -d '{"nombre": "Ana López", "telefono": "+1631...", "password": "my_password"}'

# 2. Login to get a token
curl -X POST /api/v1/auth/login \
  -d '{"telefono": "+1631...", "password": "my_password"}'
# → {"access_token": "eyJ...", "token_type": "bearer", "vendedor_id": 1}

# 3. Use the token on all subsequent requests
curl -H "Authorization: Bearer eyJ..." /api/v1/clientes/
```

## Project Structure

```
field-sales-crm/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application, CORS, startup checks
│   │   ├── core/
│   │   │   ├── auth.py          # JWT tokens, password hashing, get_current_vendedor
│   │   │   ├── config.py        # Settings & environment variables
│   │   │   ├── database.py      # SQLite + SQLAlchemy async setup
│   │   │   └── init_db.py       # DB initialization & Excel import
│   │   ├── models/
│   │   │   └── models.py        # Vendedor, Cliente, Llamada, Visita
│   │   ├── schemas/
│   │   │   └── schemas.py       # Pydantic request/response schemas
│   │   ├── api/
│   │   │   └── routes.py        # All API routes with auth & ownership checks
│   │   └── services/
│   │       └── openai_service.py# Whisper + GPT-4o-mini integration
│   ├── dashboard.py             # Streamlit dashboard
│   ├── requirements.txt
│   ├── .env.example
│   └── tests/
│       ├── conftest.py          # In-memory DB + auth mock fixtures
│       ├── test_clientes.py
│       ├── test_llamadas_visitas.py
│       └── test_openai_service.py
├── mobile/                      # React Native + Expo app
│   ├── app/                     # Expo Router screens
│   ├── components/
│   ├── services/
│   └── package.json
├── README.md
└── LICENSE
```

## Security

| Feature | Status |
|---------|--------|
| JWT authentication on all endpoints | ✅ |
| Password hashing (pbkdf2_sha256) | ✅ |
| Ownership checks (reps access only their own data) | ✅ |
| Audio file validation via magic bytes | ✅ |
| CORS locked to configured origins | ✅ |
| API docs disabled in production | ✅ |
| `SECRET_KEY` enforced before production startup | ✅ |
| SQL injection in Streamlit dashboard | ⏳ Phase 2 |
| Rate limiting on transcription endpoint | ⏳ Phase 2 |
| Audit logging | ⏳ Phase 2 |

## Roadmap

- [x] Project architecture & documentation
- [x] **Phase 1**: Backend API (FastAPI + SQLite + models) + Security hardening
- [x] **Phase 2**: OpenAI integration (Whisper + GPT extraction)
- [x] **Phase 3**: Mobile app (contacts + calls + GPS + login/register)
- [x] **Phase 4**: Audio recording + upload + transcription
- [x] **Phase 5**: Streamlit dashboard (KPIs, charts, client history, vendor management, client ingestion)
- [x] **Phase 6**: Fly.io cloud deployment (24/7, persistent volume, public dashboard)
- [x] **Phase 7**: Client ingestion — manual form + CSV/Excel bulk import (dashboard) + mobile form
- [ ] **Phase 8**: Pilot with 5 reps → full rollout

## Cost Estimate (50 reps)

| Service | Monthly Cost |
|---------|-------------|
| OpenAI Whisper API | ~$15-30 |
| OpenAI GPT-4o-mini | ~$5-15 |
| Fly.io (shared CPU, 512MB RAM, 5GB volume) | ~$5-10 |
| **Total** | **$25-55/month** |

*vs. SaaS CRM for 50 users: $500-2,500/month*

## Legal Notice

This application records in-person sales conversations. In New York State, only **one-party consent** is required for recording conversations (NY Penal Law § 250.00). The sales rep (as a party to the conversation) provides that consent. However, it is recommended to inform clients that the conversation is being recorded as a best practice.

## License

MIT License — see [LICENSE](LICENSE) for details.

