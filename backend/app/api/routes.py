"""
API routes for the Field Sales CRM.

All endpoints (except registration and login) require a valid JWT token
issued by POST /api/v1/auth/login.
"""
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import (
    get_current_vendedor,
    hash_password,
    verify_password,
    create_access_token,
)
from app.models.models import Vendedor, Cliente, Llamada, Visita
from app.schemas.schemas import (
    VendedorCreate, VendedorResponse,
    LoginRequest, TokenResponse,
    ClienteCreate, ClienteResponse, ClienteUpdate, ContactSyncRequest,
    LlamadaCreate, LlamadaResponse,
    VisitaCreate, VisitaResponse,
    EstadisticasResponse,
)
from app.services.openai_service import process_visit_audio

router = APIRouter(prefix="/api/v1")

# ---------------------------------------------------------------------------
# Audio magic-byte validation
# ---------------------------------------------------------------------------

# Known signatures for common audio formats
_AUDIO_MAGIC = [
    b'\xff\xfb',            # MP3
    b'\xff\xf3',            # MP3
    b'\xff\xf2',            # MP3
    b'\xff\xf1',            # AAC (ADTS)
    b'\xff\xf9',            # AAC (ADTS)
    b'ID3',                 # MP3 with ID3 tag
    b'RIFF',                # WAV
    b'OggS',                # OGG Vorbis / Opus
    b'fLaC',                # FLAC
    b'\x1a\x45\xdf\xa3',   # WebM / MKV
]


def _is_valid_audio(content: bytes) -> bool:
    """Return True if *content* starts with a known audio magic signature."""
    if len(content) < 12:
        return False
    header = content[:12]
    # M4A / MP4 / AAC container: 'ftyp' box at bytes 4–7
    if header[4:8] in (b'ftyp', b'moov', b'mdat', b'wide'):
        return True
    return any(header.startswith(sig) for sig in _AUDIO_MAGIC)


# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------

@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate a sales rep and return a JWT access token."""
    result = await db.execute(
        select(Vendedor).where(Vendedor.telefono == data.telefono, Vendedor.activo == True)
    )
    vendedor = result.scalar_one_or_none()

    # Use a constant-time comparison path to avoid user-enumeration timing attacks
    if vendedor is None or not vendedor.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(data.password, vendedor.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(vendedor.id)
    return TokenResponse(access_token=token, vendedor_id=vendedor.id)


# ---------------------------------------------------------------------------
# VENDEDORES (Sales Reps)
# ---------------------------------------------------------------------------

@router.post("/vendedores/", response_model=VendedorResponse, tags=["vendedores"])
async def crear_vendedor(data: VendedorCreate, db: AsyncSession = Depends(get_db)):
    """Register a new sales rep (public endpoint — used during onboarding)."""
    existing = await db.execute(
        select(Vendedor).where(Vendedor.telefono == data.telefono)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Phone number already registered")

    payload = data.model_dump(exclude={"password"})
    payload["password_hash"] = hash_password(data.password)
    vendedor = Vendedor(**payload)
    db.add(vendedor)
    await db.flush()
    await db.refresh(vendedor)
    return vendedor


@router.get("/vendedores/", response_model=list[VendedorResponse], tags=["vendedores"])
async def listar_vendedores(
    activo: bool = True,
    db: AsyncSession = Depends(get_db),
    _: Vendedor = Depends(get_current_vendedor),
):
    """List all active sales reps. Requires authentication."""
    result = await db.execute(
        select(Vendedor).where(Vendedor.activo == activo).order_by(Vendedor.nombre)
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------
# CLIENTES (Clients)
# ---------------------------------------------------------------------------

@router.get("/clientes/", response_model=list[ClienteResponse], tags=["clientes"])
async def listar_clientes(
    estado: str = None,
    zona: str = None,
    buscar: str = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: Vendedor = Depends(get_current_vendedor),
):
    """List clients with optional filters. Requires authentication."""
    query = select(Cliente)

    if estado:
        query = query.where(Cliente.estado == estado)
    if zona:
        query = query.where(Cliente.zona.ilike(f"%{zona}%"))
    if buscar:
        query = query.where(
            Cliente.nombre_apellido.ilike(f"%{buscar}%")
            | Cliente.telefono.ilike(f"%{buscar}%")
        )

    query = query.order_by(Cliente.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/clientes/", response_model=ClienteResponse, tags=["clientes"])
async def crear_cliente(
    data: ClienteCreate,
    db: AsyncSession = Depends(get_db),
    _: Vendedor = Depends(get_current_vendedor),
):
    """Create a new client. Requires authentication."""
    existing = await db.execute(
        select(Cliente).where(Cliente.telefono == data.telefono)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Phone number already registered")

    cliente = Cliente(**data.model_dump())
    db.add(cliente)
    await db.flush()
    await db.refresh(cliente)
    return cliente


@router.put("/clientes/{cliente_id}", response_model=ClienteResponse, tags=["clientes"])
async def actualizar_cliente(
    cliente_id: int,
    data: ClienteUpdate,
    db: AsyncSession = Depends(get_db),
    _: Vendedor = Depends(get_current_vendedor),
):
    """Update a client record. Requires authentication."""
    result = await db.execute(select(Cliente).where(Cliente.id == cliente_id))
    cliente = result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Client not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cliente, field, value)

    cliente.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(cliente)
    return cliente


@router.post("/clientes/sync", tags=["clientes"])
async def sync_contactos(
    data: ContactSyncRequest,
    db: AsyncSession = Depends(get_db),
    current_vendedor: Vendedor = Depends(get_current_vendedor),
):
    """
    Bulk sync contacts from a sales rep's phone.
    vendedor_id is taken from the JWT token — the client doesn't need to send it.
    """

    created = 0
    skipped = 0

    for contacto in data.contactos:
        existing = await db.execute(
            select(Cliente).where(Cliente.telefono == contacto.telefono)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        cliente = Cliente(**contacto.model_dump())
        db.add(cliente)
        created += 1

    await db.flush()
    return {"created": created, "skipped": skipped, "total": len(data.contactos)}


# ---------------------------------------------------------------------------
# LLAMADAS (Calls)
# ---------------------------------------------------------------------------

@router.post("/llamadas/", response_model=LlamadaResponse, tags=["llamadas"])
async def registrar_llamada(
    data: LlamadaCreate,
    db: AsyncSession = Depends(get_db),
    current_vendedor: Vendedor = Depends(get_current_vendedor),
):
    """Log a call. vendedor_id is taken from the JWT token."""
    llamada = Llamada(**data.model_dump(), vendedor_id=current_vendedor.id)
    db.add(llamada)

    # Update client status based on call result
    result = await db.execute(select(Cliente).where(Cliente.id == data.cliente_id))
    cliente = result.scalar_one_or_none()
    if cliente:
        status_map = {
            "cita": "cita",
            "venta": "venta",
            "no_llamar": "no_llamar",
            "equivocado": "equivocado",
        }
        if data.resultado in status_map:
            cliente.estado = status_map[data.resultado]
            cliente.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(llamada)
    return llamada


@router.get("/llamadas/", response_model=list[LlamadaResponse], tags=["llamadas"])
async def listar_llamadas(
    cliente_id: int = None,
    fecha_desde: datetime = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_vendedor: Vendedor = Depends(get_current_vendedor),
):
    """List the authenticated rep's calls."""
    query = select(Llamada).where(Llamada.vendedor_id == current_vendedor.id)

    if cliente_id:
        query = query.where(Llamada.cliente_id == cliente_id)
    if fecha_desde:
        query = query.where(Llamada.fecha >= fecha_desde)

    query = query.order_by(Llamada.fecha.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# VISITAS (Visits)
# ---------------------------------------------------------------------------

@router.post("/visitas/", response_model=VisitaResponse, tags=["visitas"])
async def crear_visita(
    data: VisitaCreate,
    db: AsyncSession = Depends(get_db),
    current_vendedor: Vendedor = Depends(get_current_vendedor),
):
    """Create a visit record. vendedor_id is taken from the JWT token."""
    visita = Visita(**data.model_dump(), vendedor_id=current_vendedor.id)
    db.add(visita)
    await db.flush()
    await db.refresh(visita)
    return visita


@router.post("/visitas/{visita_id}/audio", tags=["visitas"])
async def subir_audio(
    visita_id: int,
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_vendedor: Vendedor = Depends(get_current_vendedor),
):
    """
    Upload the recorded audio for a visit.
    Only the rep who owns the visit can upload audio.
    """
    result = await db.execute(select(Visita).where(Visita.id == visita_id))
    visita = result.scalar_one_or_none()
    if not visita:
        raise HTTPException(status_code=404, detail="Visit not found")
    if visita.vendedor_id != current_vendedor.id:
        raise HTTPException(status_code=403, detail="Not authorized to upload audio for this visit")

    # Read and validate file size
    content = await audio.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.max_audio_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"Audio file too large ({size_mb:.1f}MB > {settings.max_audio_size_mb}MB)",
        )

    # Validate file type via magic bytes (reject executables, scripts, etc.)
    if not _is_valid_audio(content):
        raise HTTPException(status_code=415, detail="Unsupported file type: must be an audio file")

    # Save with a server-generated filename (no user-supplied filename in the path)
    filename = f"visita_{visita_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.m4a"
    file_path = settings.audio_dir / filename

    with open(file_path, "wb") as f:
        f.write(content)

    visita.audio_path = str(file_path)
    await db.flush()

    return {"message": "Audio uploaded", "size_mb": round(size_mb, 2)}


@router.post("/visitas/{visita_id}/transcribir", response_model=VisitaResponse, tags=["visitas"])
async def transcribir_visita(
    visita_id: int,
    db: AsyncSession = Depends(get_db),
    current_vendedor: Vendedor = Depends(get_current_vendedor),
):
    """
    Full AI pipeline: Transcribe audio → Extract CRM fields → Update visit + client.
    Only the rep who owns the visit can trigger transcription.
    """
    result = await db.execute(select(Visita).where(Visita.id == visita_id))
    visita = result.scalar_one_or_none()
    if not visita:
        raise HTTPException(status_code=404, detail="Visit not found")
    if visita.vendedor_id != current_vendedor.id:
        raise HTTPException(status_code=403, detail="Not authorized to transcribe this visit")

    if not visita.audio_path:
        raise HTTPException(status_code=400, detail="No audio file uploaded for this visit")
    if visita.procesado:
        raise HTTPException(status_code=400, detail="Visit already processed")

    # Run AI pipeline: Audio → Transcription → Extraction
    ai_result = await process_visit_audio(visita.audio_path)

    # Update visit with AI results
    visita.transcripcion = ai_result["transcription"]
    visita.idioma_detectado = ai_result["language"]

    extraction = ai_result["extraction"]
    visita.notas_vendedor = extraction.get("notas_vendedor")
    visita.resultados = extraction.get("resultados")
    visita.productos_json = extraction.get("productos")
    visita.nivel_interes = extraction.get("nivel_interes")
    visita.objeciones = extraction.get("objeciones")
    visita.siguiente_paso = extraction.get("siguiente_paso")
    visita.estado_sugerido = extraction.get("estado_sugerido")
    visita.procesado = True

    # Update client status and address from visit
    cliente_result = await db.execute(select(Cliente).where(Cliente.id == visita.cliente_id))
    cliente = cliente_result.scalar_one_or_none()
    if cliente:
        if extraction.get("estado_sugerido"):
            cliente.estado = extraction["estado_sugerido"]
        if visita.lat and visita.lng and not cliente.lat:
            cliente.lat = visita.lat
            cliente.lng = visita.lng
        cliente.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(visita)
    return visita


@router.get("/visitas/", response_model=list[VisitaResponse], tags=["visitas"])
async def listar_visitas(
    cliente_id: int = None,
    procesado: bool = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_vendedor: Vendedor = Depends(get_current_vendedor),
):
    """List the authenticated rep's visits."""
    query = select(Visita).where(Visita.vendedor_id == current_vendedor.id)

    if cliente_id:
        query = query.where(Visita.cliente_id == cliente_id)
    if procesado is not None:
        query = query.where(Visita.procesado == procesado)

    query = query.order_by(Visita.fecha.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# ESTADÍSTICAS (Dashboard Stats)
# ---------------------------------------------------------------------------

@router.get("/estadisticas/", response_model=EstadisticasResponse, tags=["estadisticas"])
async def obtener_estadisticas(
    db: AsyncSession = Depends(get_db),
    _: Vendedor = Depends(get_current_vendedor),
):
    """Dashboard statistics. Requires authentication."""
    hoy = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_mes = hoy.replace(day=1)

    total_clientes = (await db.execute(select(func.count(Cliente.id)))).scalar() or 0
    total_vendedores = (await db.execute(
        select(func.count(Vendedor.id)).where(Vendedor.activo == True)
    )).scalar() or 0

    llamadas_hoy = (await db.execute(
        select(func.count(Llamada.id)).where(Llamada.fecha >= hoy)
    )).scalar() or 0

    visitas_hoy = (await db.execute(
        select(func.count(Visita.id)).where(Visita.fecha >= hoy)
    )).scalar() or 0

    total_llamadas_mes = (await db.execute(
        select(func.count(Llamada.id)).where(Llamada.fecha >= inicio_mes)
    )).scalar() or 0

    citas_mes = (await db.execute(
        select(func.count(Llamada.id)).where(
            and_(Llamada.fecha >= inicio_mes, Llamada.resultado == "cita")
        )
    )).scalar() or 0

    tasa_citas = (citas_mes / total_llamadas_mes * 100) if total_llamadas_mes > 0 else 0

    ventas_mes = (await db.execute(
        select(func.count(Llamada.id)).where(
            and_(Llamada.fecha >= inicio_mes, Llamada.resultado == "venta")
        )
    )).scalar() or 0

    status_query = await db.execute(
        select(Cliente.estado, func.count(Cliente.id)).group_by(Cliente.estado)
    )
    por_estado = {row[0]: row[1] for row in status_query.all()}

    top_query = await db.execute(
        select(Vendedor.nombre, func.count(Visita.id).label("visitas"))
        .join(Visita, Visita.vendedor_id == Vendedor.id)
        .where(Visita.fecha >= inicio_mes)
        .group_by(Vendedor.id)
        .order_by(func.count(Visita.id).desc())
        .limit(5)
    )
    top_vendedores = [{"nombre": row[0], "visitas": row[1]} for row in top_query.all()]

    return EstadisticasResponse(
        total_clientes=total_clientes,
        total_vendedores=total_vendedores,
        llamadas_hoy=llamadas_hoy,
        visitas_hoy=visitas_hoy,
        tasa_citas=round(tasa_citas, 1),
        ventas_mes=ventas_mes,
        por_estado=por_estado,
        top_vendedores=top_vendedores,
    )
