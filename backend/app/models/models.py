"""
SQLAlchemy models — maps directly to the client's Excel spreadsheet.

Excel legend colors → estado field:
  Red    = no_llamar    (do not call)
  Green  = venta        (sale completed)
  Yellow = equivocado   (wrong number)
  Purple = cita         (appointment set)
  Blue   = seguimiento  (follow-up needed)
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Boolean,
    ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Vendedor(Base):
    """Sales rep — one of the 50 field sellers."""
    __tablename__ = "vendedores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200), nullable=False)
    telefono = Column(String(20), unique=True, nullable=False)
    zona = Column(String(100), nullable=True)
    activo = Column(Boolean, default=True)
    device_id = Column(String(100), nullable=True)  # Mobile device identifier
    password_hash = Column(String(200), nullable=True)  # bcrypt hash
    is_demo = Column(Boolean, default=False, nullable=False, server_default="0")
    demo_segundos_usados = Column(Integer, default=0, nullable=False, server_default="0")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    llamadas = relationship("Llamada", back_populates="vendedor")
    visitas = relationship("Visita", back_populates="vendedor")

    def __repr__(self):
        return f"<Vendedor {self.nombre}>"


class Cliente(Base):
    """
    Client record — maps to one row in the Excel spreadsheet.

    Excel mapping:
      Col B → nombre_apellido
      Col C → telefono
      Col D → fuente
      Col E → zona
      Col F → direccion
      Row color → estado
    """
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # From Excel columns B, C
    nombre_apellido = Column(String(200), nullable=False)
    telefono = Column(String(20), unique=True, nullable=False, index=True)

    # From Excel columns D, E, F
    fuente = Column(String(100), nullable=True)          # Col D: lead source
    zona = Column(String(100), nullable=True)             # Col E: zone
    direccion = Column(Text, nullable=True)               # Col F: address

    # GPS coordinates (auto-filled from visit)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    # From Excel row color legend
    estado = Column(
        String(20),
        default="nuevo",
        nullable=False,
        index=True
    )
    # Valid: nuevo, no_llamar, venta, equivocado, cita, seguimiento

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    llamadas = relationship("Llamada", back_populates="cliente")
    visitas = relationship("Visita", back_populates="cliente")

    __table_args__ = (
        Index("ix_clientes_estado_zona", "estado", "zona"),
    )

    def __repr__(self):
        return f"<Cliente {self.nombre_apellido} [{self.estado}]>"


class Llamada(Base):
    """
    Call log — tracks every call from a rep to a client.

    Excel mapping:
      Col H → notas_telemarketing (e.g., "04-06 NC")
    """
    __tablename__ = "llamadas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vendedor_id = Column(Integer, ForeignKey("vendedores.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)

    fecha = Column(DateTime, default=datetime.utcnow, index=True)
    duracion_seg = Column(Integer, default=0)  # Duration in seconds

    # Call outcome
    resultado = Column(String(20), nullable=False)
    # Valid: cita, no_cita, no_contesta, equivocado, no_llamar, venta

    # From Excel Col H
    notas_telemarketing = Column(Text, nullable=True)

    # Relationships
    vendedor = relationship("Vendedor", back_populates="llamadas")
    cliente = relationship("Cliente", back_populates="llamadas")

    def __repr__(self):
        return f"<Llamada {self.vendedor_id}→{self.cliente_id} [{self.resultado}]>"


class Visita(Base):
    """
    Visit record — created when GPS detects rep arrived at client location.
    Audio is recorded, transcribed, and AI extracts structured CRM fields.

    Excel mapping:
      Col G → notas_vendedor  (auto-filled from AI extraction)
      Col I → resultados      (auto-filled from AI extraction)
    """
    __tablename__ = "visitas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vendedor_id = Column(Integer, ForeignKey("vendedores.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)

    fecha = Column(DateTime, default=datetime.utcnow, index=True)

    # GPS at arrival
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    # Audio recording
    audio_path = Column(String(500), nullable=True)  # Path to .m4a file
    duracion_min = Column(Float, nullable=True)

    # Whisper transcription
    transcripcion = Column(Text, nullable=True)
    idioma_detectado = Column(String(10), nullable=True)  # es, en, mixed

    # GPT-extracted fields (auto-fill CRM)
    notas_vendedor = Column(Text, nullable=True)     # Col G: summary of conversation
    resultados = Column(Text, nullable=True)          # Col I: outcome
    productos_json = Column(JSON, nullable=True)      # Extracted product interests
    nivel_interes = Column(String(10), nullable=True)  # alto, medio, bajo
    objeciones = Column(Text, nullable=True)          # Client objections
    siguiente_paso = Column(Text, nullable=True)      # Next action
    fecha_seguimiento = Column(DateTime, nullable=True)
    estado_sugerido = Column(String(20), nullable=True)  # AI-suggested status

    # Processing status
    procesado = Column(Boolean, default=False)

    # Relationships
    vendedor = relationship("Vendedor", back_populates="visitas")
    cliente = relationship("Cliente", back_populates="visitas")

    def __repr__(self):
        return f"<Visita {self.vendedor_id}→{self.cliente_id} [{self.fecha}]>"
