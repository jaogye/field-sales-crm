# Field Sales CRM — Technical Architecture

**Option A — Recommended**

## React Native + FastAPI + SQLite

Everything runs on the owner's laptop. No external servers. No infrastructure costs.

---

## 1. Architecture

### 📱 Mobile Layer (each sales rep)

| Icon | Layer | Technology | Detail |
|------|-------|-----------|--------|
| 📱 | Mobile App | React Native + Expo | iOS and Android. Single codebase |
| 👤 | Contacts | expo-contacts | Reads contacts from the rep's phone |
| 📞 | Calls | expo-linking + call-log | Initiates calls, logs outcome |
| 📍 | GPS / Geofence | expo-location | Auto-detects arrival at client location |
| 🎙️ | Recording | expo-av | Records visit audio in background |
| 📴 | Offline sync | WatermelonDB (SQLite) | Local DB on device. Syncs when online |

### 💻 Backend Layer (owner's laptop)

| Icon | Layer | Technology | Detail |
|------|-------|-----------|--------|
| ⚙️ | REST API | FastAPI (Python) | Receives data from 50 reps. Validates and stores |
| 🗄️ | Database | SQLite | Single .db file on the owner's laptop |
| 🔗 | ORM | SQLAlchemy + aiosqlite | Async access to SQLite from FastAPI |
| 🗣️ | Transcription | OpenAI Whisper API | Audio → text in Spanish/English. ~$0.006/min |
| 🤖 | AI Extraction | OpenAI GPT-4o-mini | Transcription → JSON to fill CRM fields |
| 🌐 | Exposure | Cloudflare Tunnel / ngrok | Exposes laptop to internet without static IP |

### 📊 Dashboard Layer (owner's laptop)

| Icon | Layer | Technology | Detail |
|------|-------|-----------|--------|
| 📊 | Dashboard | Streamlit or React | Analytics panel for the owner |
| 📈 | Reports | Pandas + Matplotlib | Export to Excel for compatibility |

### 🔄 Data Flow

```
Rep's phone          → WatermelonDB (local SQLite)    Contacts + calls + GPS
WatermelonDB         → FastAPI (laptop)                HTTP sync when online
Audio .m4a           → Whisper API                     Upload → Spanish/English transcription
Transcription        → GPT-4o-mini                     Text → structured JSON
Extracted JSON       → SQLite (laptop)                 INSERT/UPDATE into crm.db
SQLite               → Streamlit Dashboard             SELECT live statistics
```

---

## 2. Database Schema

**File:** `C:\sales\crm.db` — A single SQLite file on the laptop. Fields marked **AUTO** are filled automatically by the app.

### sales_reps (5 fields)

| Field | Type | Excel Mapping | Source |
|-------|------|--------------|--------|
| id | INTEGER PK | | AUTO |
| nombre | TEXT | | MANUAL |
| telefono | TEXT | | MANUAL |
| zona | TEXT | | MANUAL |
| activo | BOOLEAN | | MANUAL |

### clients (10 fields)

| Field | Type | Excel Mapping | Source |
|-------|------|--------------|--------|
| id | INTEGER PK | | AUTO |
| nombre_apellido | TEXT | Excel Col B | AUTO |
| telefono | TEXT | Col C | AUTO |
| fuente | TEXT | Col D | MANUAL |
| zona | TEXT | Col E | MANUAL |
| direccion | TEXT | Col F | AUTO |
| lat | REAL | GPS | AUTO |
| lng | REAL | GPS | AUTO |
| estado | TEXT | Color legend | AUTO |
| fecha_creacion | DATETIME | | AUTO |

### calls (7 fields)

| Field | Type | Excel Mapping | Source |
|-------|------|--------------|--------|
| id | INTEGER PK | | AUTO |
| vendedor_id | FK → sales_reps | | AUTO |
| cliente_id | FK → clients | | AUTO |
| fecha | DATETIME | | AUTO |
| duracion_seg | INTEGER | | AUTO |
| resultado | TEXT | appointment/no_appt/nc/wrong | AUTO |
| notas_telemarketing | TEXT | Excel Col H | MANUAL |

### visits (14 fields)

| Field | Type | Excel Mapping | Source |
|-------|------|--------------|--------|
| id | INTEGER PK | | AUTO |
| vendedor_id | FK → sales_reps | | AUTO |
| cliente_id | FK → clients | | AUTO |
| fecha | DATETIME | | AUTO |
| lat | REAL | GPS on arrival | AUTO |
| lng | REAL | GPS on arrival | AUTO |
| audio_path | TEXT | Path to .m4a file | AUTO |
| duracion_min | REAL | | AUTO |
| transcripcion | TEXT | Full text (Whisper) | AUTO |
| notas_vendedor | TEXT | Excel Col G | AUTO |
| resultados | TEXT | Excel Col I | AUTO |
| productos_json | JSON | Extracted by AI | AUTO |
| nivel_interes | TEXT | high/medium/low | AUTO |
| siguiente_paso | TEXT | | AUTO |

### 📋 Excel → SQLite Mapping

| Excel Column | SQLite Field |
|-------------|-------------|
| Col B: Full name | clientes.nombre_apellido |
| Col C: Phone | clientes.telefono |
| Col D: Lead source | clientes.fuente |
| Col E: Zone | clientes.zona |
| Col F: Address | clientes.direccion + lat/lng |
| Col G: Sales rep notes | visitas.notas_vendedor |
| Col H: Telemarketing notes | llamadas.notas_telemarketing |
| Col I: Results | visitas.resultados |
| Row color (legend) | clientes.estado |
| Row number | clientes.id |

---

## 3. Why SQLite?

### Advantages

| | Advantage | Detail |
|---|----------|--------|
| ✅ | **Zero installation** | No DB server to install. Just a single .db file on the laptop |
| 💾 | **Portable** | Copy the file = full backup. Move to USB, Dropbox, etc. |
| ⚡ | **Enough for 50 reps** | SQLite handles thousands of writes/second. More than enough |
| 📊 | **Excel compatible** | Any table can be exported to .xlsx with a single line of code |
| 📱 | **WatermelonDB (mobile)** | The rep's offline DB also uses SQLite. Same technology |
| ⚙️ | **FastAPI async** | With aiosqlite, FastAPI reads/writes without blocking. WAL mode for concurrency |

### SQLite vs PostgreSQL for this use case

| Criteria | SQLite | PostgreSQL | Winner |
|----------|--------|-----------|--------|
| Installation | Zero. Comes with Python | Requires server installation | **SQLite** |
| Concurrency (50 reps) | OK with WAL mode | Better for 500+ users | **SQLite** |
| Backup | Copy .db file | pg_dump or pg_basebackup | **SQLite** |
| Portability | USB, Dropbox, email | Requires running server | **SQLite** |
| Maintenance | Zero | Vacuuming, tuning, updates | **SQLite** |
| JSON queries | json_extract() since 3.38 | JSONB (superior) | PostgreSQL |
| Full-text search | FTS5 (good) | GIN indexes (superior) | PostgreSQL |
| Future scalability | Up to ~1M records OK | Unlimited | PostgreSQL |

**Verdict:** For 50 reps and a single admin on a laptop, SQLite wins on simplicity. If the business grows to 500+ reps, migrating to PostgreSQL is straightforward with SQLAlchemy (just change the connection string).

### FastAPI + SQLite config

```python
# database.py
from sqlalchemy.ext.asyncio import create_async_engine

# Single .db file on the laptop
DATABASE_URL = "sqlite+aiosqlite:///C:/sales/crm.db"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    # WAL mode: allows concurrent reads
    # while a rep is writing
)

# Future migration to PostgreSQL (if needed):
# DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/crm"
```

---

## 4. Monthly Cost Breakdown

| Service | Cost | Detail | Frequency |
|---------|------|--------|-----------|
| Whisper API | $15-30 | 50 reps × 5 visits/day × 10 min audio | /mo |
| GPT-4o-mini API | $5-15 | Field extraction from 250 transcriptions/day | /mo |
| SQLite | $0 | Free. Local file on the laptop | FREE |
| FastAPI + Python | $0 | Open source. Runs on the owner's laptop | FREE |
| Cloudflare Tunnel | $0 | Free tier. Exposes laptop to the internet | FREE |
| Expo (builds) | $0-99 | Free for development. $99/mo for production builds | /mo |
| Domain (optional) | $10 | sales.yourbusiness.com for dashboard access | /yr |

### Estimated monthly total

> **$20 - $145/mo** for 50 reps, ~250 visits/day
>
> vs. SaaS CRM: $500-2,500/mo

### What the owner saves

- ✓ Daily hours receiving calls from 50 reps → $0 wasted time
- ✓ Manual transcription errors when typing into Excel → 100% accurate data
- ✓ No SaaS CRM license ($10-50/user/mo × 50 = $500-2,500/mo)
- ✓ No database server → SQLite is free on the laptop
- ✓ Backup = copy a 10MB file to USB or Dropbox
