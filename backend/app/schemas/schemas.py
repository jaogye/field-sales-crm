"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ============ Vendedor (Sales Rep) ============

class VendedorCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    telefono: str = Field(..., pattern=r"^\+?[\d\s\-\(\)]+$")
    zona: Optional[str] = None
    device_id: Optional[str] = None


class VendedorResponse(BaseModel):
    id: int
    nombre: str
    telefono: str
    zona: Optional[str]
    activo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ============ Cliente (Client) ============

class ClienteCreate(BaseModel):
    nombre_apellido: str = Field(..., min_length=1, max_length=200)
    telefono: str = Field(..., pattern=r"^\+?[\d\s\-\(\)]+$")
    fuente: Optional[str] = None
    zona: Optional[str] = None
    direccion: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class ClienteUpdate(BaseModel):
    nombre_apellido: Optional[str] = None
    telefono: Optional[str] = None
    fuente: Optional[str] = None
    zona: Optional[str] = None
    direccion: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    estado: Optional[str] = Field(
        None,
        pattern=r"^(nuevo|no_llamar|venta|equivocado|cita|seguimiento)$"
    )


class ClienteResponse(BaseModel):
    id: int
    nombre_apellido: str
    telefono: str
    fuente: Optional[str]
    zona: Optional[str]
    direccion: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    estado: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContactSyncRequest(BaseModel):
    """Bulk sync contacts from phone."""
    vendedor_id: int
    contactos: list[ClienteCreate]


# ============ Llamada (Call) ============

class LlamadaCreate(BaseModel):
    vendedor_id: int
    cliente_id: int
    duracion_seg: int = Field(0, ge=0)
    resultado: str = Field(
        ...,
        pattern=r"^(cita|no_cita|no_contesta|equivocado|no_llamar|venta)$"
    )
    notas_telemarketing: Optional[str] = None


class LlamadaResponse(BaseModel):
    id: int
    vendedor_id: int
    cliente_id: int
    fecha: datetime
    duracion_seg: int
    resultado: str
    notas_telemarketing: Optional[str]

    model_config = {"from_attributes": True}


# ============ Visita (Visit) ============

class VisitaCreate(BaseModel):
    vendedor_id: int
    cliente_id: int
    lat: Optional[float] = None
    lng: Optional[float] = None


class VisitaResponse(BaseModel):
    id: int
    vendedor_id: int
    cliente_id: int
    fecha: datetime
    lat: Optional[float]
    lng: Optional[float]
    audio_path: Optional[str]
    duracion_min: Optional[float]
    transcripcion: Optional[str]
    idioma_detectado: Optional[str]
    notas_vendedor: Optional[str]
    resultados: Optional[str]
    productos_json: Optional[dict]
    nivel_interes: Optional[str]
    objeciones: Optional[str]
    siguiente_paso: Optional[str]
    estado_sugerido: Optional[str]
    procesado: bool

    model_config = {"from_attributes": True}


# ============ AI Extraction Result ============

class ExtractionResult(BaseModel):
    """Structured data extracted by GPT from a visit transcription."""
    notas_vendedor: str = Field(..., description="Summary of the conversation for the CRM")
    resultados: str = Field(..., description="Visit outcome")
    productos: list[dict] = Field(
        default_factory=list,
        description="Products mentioned: [{nombre, cantidad, precio_cotizado}]"
    )
    nivel_interes: str = Field("medio", pattern=r"^(alto|medio|bajo)$")
    objeciones: Optional[str] = None
    siguiente_paso: Optional[str] = None
    estado_sugerido: str = Field(
        "seguimiento",
        pattern=r"^(no_llamar|venta|equivocado|cita|seguimiento)$"
    )


# ============ Statistics ============

class EstadisticasResponse(BaseModel):
    total_clientes: int
    total_vendedores: int
    llamadas_hoy: int
    visitas_hoy: int
    tasa_citas: float  # % of calls that result in appointments
    ventas_mes: int
    por_estado: dict[str, int]  # Count per status
    top_vendedores: list[dict]  # Top performers
