"""
API routes for the Field Sales CRM.

All endpoints that the mobile app calls to sync data.
"""
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Vendedor, Cliente, Llamada, Visita
from app.schemas.schemas import (
    VendedorCreate, VendedorResponse,
    ClienteCreate, ClienteResponse, ClienteUpdate, ContactSyncRequest,
    LlamadaCreate, LlamadaResponse,
    VisitaCreate, VisitaResponse,
    EstadisticasResponse,
)
from app.services.openai_service import process_visit_audio

router = APIRouter(prefix="/api/v1")


# ============ VENDEDORES (Sales Reps) ============

@router.post("/vendedores/", response_model=VendedorResponse, tags=["vendedores"])
async def crear_vendedor(data: VendedorCreate, db: AsyncSession = Depends(get_db)):
    """Register a new sales rep."""
    vendedor = Vendedor(**data.model_dump())
    db.add(vendedor)
    await db.flush()
    await db.refresh(vendedor)
    return vendedor


@router.get("/vendedores/", response_model=list[VendedorResponse], tags=["vendedores"])
async def listar_vendedores(
    activo: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List all active sales reps."""
    result = await db.execute(
        select(Vendedor).where(Vendedor.activo == activo).order_by(Vendedor.nombre)
    )
    return result.scalars().all()


# ============ CLIENTES (Clients) ============

@router.get("/clientes/", response_model=list[ClienteResponse], tags=["clientes"])
async def listar_clientes(
    estado: str = None,
    zona: str = None,
    buscar: str = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List clients with optional filters."""
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
async def crear_cliente(data: ClienteCreate, db: AsyncSession = Depends(get_db)):
    """Create a new client."""
    # Check if phone already exists
    existing = await db.execute(
        select(Cliente).where(Cliente.telefono == data.telefono)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Client with this phone number already exists")

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
):
    """Update a client record."""
    result = await db.execute(select(Cliente).where(Cliente.id == cliente_id))
    cliente = result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(404, "Client not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cliente, field, value)

    cliente.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(cliente)
    return cliente


@router.post("/clientes/sync", tags=["clientes"])
async def sync_contactos(data: ContactSyncRequest, db: AsyncSession = Depends(get_db)):
    """
    Bulk sync contacts from a sales rep's phone.
    Creates new clients or skips if phone already exists.
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


# ============ LLAMADAS (Calls) ============

@router.post("/llamadas/", response_model=LlamadaResponse, tags=["llamadas"])
async def registrar_llamada(data: LlamadaCreate, db: AsyncSession = Depends(get_db)):
    """
    Log a call from a sales rep to a client.
    Also updates the client's status based on the call result.
    """
    llamada = Llamada(**data.model_dump())
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
    vendedor_id: int = None,
    cliente_id: int = None,
    fecha_desde: datetime = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List calls with optional filters."""
    query = select(Llamada)

    if vendedor_id:
        query = query.where(Llamada.vendedor_id == vendedor_id)
    if cliente_id:
        query = query.where(Llamada.cliente_id == cliente_id)
    if fecha_desde:
        query = query.where(Llamada.fecha >= fecha_desde)

    query = query.order_by(Llamada.fecha.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


# ============ VISITAS (Visits) ============

@router.post("/visitas/", response_model=VisitaResponse, tags=["visitas"])
async def crear_visita(data: VisitaCreate, db: AsyncSession = Depends(get_db)):
    """Create a new visit record (triggered by GPS geofence)."""
    visita = Visita(**data.model_dump())
    db.add(visita)
    await db.flush()
    await db.refresh(visita)
    return visita


@router.post("/visitas/{visita_id}/audio", tags=["visitas"])
async def subir_audio(
    visita_id: int,
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload the recorded audio for a visit.
    Saves to the audio storage directory.
    """
    result = await db.execute(select(Visita).where(Visita.id == visita_id))
    visita = result.scalar_one_or_none()
    if not visita:
        raise HTTPException(404, "Visit not found")

    # Validate file size
    content = await audio.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.max_audio_size_mb:
        raise HTTPException(413, f"Audio file too large ({size_mb:.1f}MB > {settings.max_audio_size_mb}MB)")

    # Save file
    ext = Path(audio.filename).suffix or ".m4a"
    filename = f"visita_{visita_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{ext}"
    file_path = settings.audio_dir / filename

    with open(file_path, "wb") as f:
        f.write(content)

    visita.audio_path = str(file_path)
    await db.flush()

    return {"message": "Audio uploaded", "path": str(file_path), "size_mb": round(size_mb, 2)}


@router.post("/visitas/{visita_id}/transcribir", response_model=VisitaResponse, tags=["visitas"])
async def transcribir_visita(visita_id: int, db: AsyncSession = Depends(get_db)):
    """
    Full AI pipeline: Transcribe audio → Extract CRM fields → Update visit + client.

    This is the core of the system — it replaces the manual phone call
    from the sales rep to the owner and the manual Excel data entry.
    """
    result = await db.execute(select(Visita).where(Visita.id == visita_id))
    visita = result.scalar_one_or_none()
    if not visita:
        raise HTTPException(404, "Visit not found")

    if not visita.audio_path:
        raise HTTPException(400, "No audio file uploaded for this visit")

    if visita.procesado:
        raise HTTPException(400, "Visit already processed")

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
    vendedor_id: int = None,
    cliente_id: int = None,
    procesado: bool = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List visits with optional filters."""
    query = select(Visita)

    if vendedor_id:
        query = query.where(Visita.vendedor_id == vendedor_id)
    if cliente_id:
        query = query.where(Visita.cliente_id == cliente_id)
    if procesado is not None:
        query = query.where(Visita.procesado == procesado)

    query = query.order_by(Visita.fecha.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


# ============ ESTADÍSTICAS (Dashboard Stats) ============

@router.get("/estadisticas/", response_model=EstadisticasResponse, tags=["estadisticas"])
async def obtener_estadisticas(db: AsyncSession = Depends(get_db)):
    """Dashboard statistics for the owner."""
    hoy = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_mes = hoy.replace(day=1)

    # Total counts
    total_clientes = (await db.execute(select(func.count(Cliente.id)))).scalar() or 0
    total_vendedores = (await db.execute(
        select(func.count(Vendedor.id)).where(Vendedor.activo == True)
    )).scalar() or 0

    # Today's activity
    llamadas_hoy = (await db.execute(
        select(func.count(Llamada.id)).where(Llamada.fecha >= hoy)
    )).scalar() or 0

    visitas_hoy = (await db.execute(
        select(func.count(Visita.id)).where(Visita.fecha >= hoy)
    )).scalar() or 0

    # Appointment rate (calls that resulted in appointments)
    total_llamadas_mes = (await db.execute(
        select(func.count(Llamada.id)).where(Llamada.fecha >= inicio_mes)
    )).scalar() or 0

    citas_mes = (await db.execute(
        select(func.count(Llamada.id)).where(
            and_(Llamada.fecha >= inicio_mes, Llamada.resultado == "cita")
        )
    )).scalar() or 0

    tasa_citas = (citas_mes / total_llamadas_mes * 100) if total_llamadas_mes > 0 else 0

    # Sales this month
    ventas_mes = (await db.execute(
        select(func.count(Llamada.id)).where(
            and_(Llamada.fecha >= inicio_mes, Llamada.resultado == "venta")
        )
    )).scalar() or 0

    # Clients by status
    status_query = await db.execute(
        select(Cliente.estado, func.count(Cliente.id)).group_by(Cliente.estado)
    )
    por_estado = {row[0]: row[1] for row in status_query.all()}

    # Top 5 sales reps (by visits this month)
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
