# Sequence Diagrams — Field Sales CRM

---

### 1. Onboarding — New Sales Rep Registration

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

### 2. Contact Sync — Loading the Client List

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

### 3. Call Logging — Telemarketing Flow

```
Vendedor (Phone)            Backend API              SQLite (crm.db)
      │                          │                        │
      │  [Opens client card]     │                        │
      │  [Taps "Llamar"]         │                        │
      │  → Native phone dialer opens                      │
      │  → Call result modal appears                      │
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
      │   duracion_seg,          │                        │
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
      │                          │  ◄───────────────────  │
      │  ◄─────────────────────  │                        │
      │  201 {llamada_id, fecha} │  [Client card updates  │
      │  [Modal closes]          │   status color]        │
```

---

### 4. Field Visit — Core AI Pipeline

```
Vendedor (Phone)     GPS / Mic      Backend API      OpenAI API       SQLite (crm.db)
      │                  │               │                │                 │
      │  [Taps "Visita"  │               │                │                 │
      │   on client card]│               │                │                 │
      │  → Visit screen  │               │                │                 │
      │    opens         │               │                │                 │
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

### 5. Owner Views Real-Time Dashboard

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
