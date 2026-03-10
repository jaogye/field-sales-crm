"""
Tests for OpenAI service — GPT extraction logic.
Uses mock to avoid real API calls during testing.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.openai_service import extract_crm_fields


SAMPLE_TRANSCRIPTION_ES = """
Hola buenas tardes, soy Carlos de la distribuidora de artículos de cocina.
Vengo a mostrarle nuestro catálogo. 
Sí claro pase adelante.
Mire tenemos este juego de ollas de 12 piezas, es de acero inoxidable,
muy resistente. El precio es de 350 dólares.
Ay qué bonito, pero 350 es un poco caro para mí.
Le puedo hacer un plan de pagos, 4 cuotas de 90 dólares.
Mmm déjeme pensarlo. ¿Puede venir el sábado? Mi esposo va a estar
y quiero que él lo vea también.
Claro que sí, el sábado vengo. ¿A qué hora le conviene?
Como a las 10 de la mañana.
Perfecto, aquí estaremos el sábado a las 10. Muchas gracias.
"""

SAMPLE_TRANSCRIPTION_MIXED = """
Hi, good afternoon. I'm here from the kitchen supplies company.
Ah sí, pase adelante. My friend told me about your products.
We have this beautiful 12-piece cookware set. Acero inoxidable, very durable.
How much is it?
Trescientos cincuenta dólares, but we have financing. Four payments of ninety.
That's not bad. Can you come back Saturday? My husband wants to see it too.
Of course, Saturday at 10am works for me.
Okay, see you then. Gracias.
"""


@pytest.mark.asyncio
async def test_extract_crm_fields_spanish():
    """Test GPT extraction with Spanish transcription (mocked API)."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "notas_vendedor": "Clienta interesada en juego de ollas 12 piezas. Precio le parece alto pero acepta plan de pagos. Quiere que su esposo lo vea.",
        "resultados": "Cita para el sábado a las 10am para mostrar productos al esposo",
        "productos": [{"nombre": "Juego de ollas 12 piezas", "cantidad": 1, "precio_cotizado": 350}],
        "nivel_interes": "alto",
        "objeciones": "Precio un poco alto, necesita aprobación del esposo",
        "siguiente_paso": "Visitar el sábado a las 10am",
        "estado_sugerido": "cita",
    })

    with patch("app.services.openai_service.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        result = await extract_crm_fields(SAMPLE_TRANSCRIPTION_ES)

    assert result["estado_sugerido"] == "cita"
    assert result["nivel_interes"] == "alto"
    assert len(result["productos"]) == 1
    assert result["productos"][0]["nombre"] == "Juego de ollas 12 piezas"
    assert result["productos"][0]["precio_cotizado"] == 350


@pytest.mark.asyncio
async def test_extract_crm_fields_mixed_language():
    """Test GPT extraction with mixed Spanish/English transcription."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "notas_vendedor": "Cliente referida por amiga. Interesada en juego de ollas. Esposo quiere verlo antes de decidir.",
        "resultados": "Cita para sábado a las 10am",
        "productos": [{"nombre": "Juego de ollas 12 piezas", "cantidad": 1, "precio_cotizado": 350}],
        "nivel_interes": "alto",
        "objeciones": "Necesita consultar con esposo",
        "siguiente_paso": "Visitar sábado 10am",
        "estado_sugerido": "cita",
    })

    with patch("app.services.openai_service.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        result = await extract_crm_fields(SAMPLE_TRANSCRIPTION_MIXED)

    assert result["estado_sugerido"] == "cita"
    assert "ollas" in result["productos"][0]["nombre"].lower()


@pytest.mark.asyncio
async def test_extract_crm_fields_invalid_json():
    """Test graceful handling when GPT returns invalid JSON."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is not valid JSON"

    with patch("app.services.openai_service.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        result = await extract_crm_fields("Some transcription text")

    # Should return fallback values
    assert result["estado_sugerido"] == "seguimiento"
    assert "error" in result["notas_vendedor"].lower() or "revisión" in result["resultados"].lower()


@pytest.mark.asyncio
async def test_extract_crm_fields_no_sale():
    """Test extraction when client is not interested."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "notas_vendedor": "Cliente no está interesada. Dice que ya tiene ollas nuevas y no necesita nada.",
        "resultados": "No le interesa. No volver a llamar.",
        "productos": [],
        "nivel_interes": "bajo",
        "objeciones": "Ya tiene productos similares, no necesita nada",
        "siguiente_paso": "No contactar más",
        "estado_sugerido": "no_llamar",
    })

    with patch("app.services.openai_service.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        result = await extract_crm_fields("No gracias, no me interesa...")

    assert result["estado_sugerido"] == "no_llamar"
    assert result["nivel_interes"] == "bajo"
    assert len(result["productos"]) == 0
