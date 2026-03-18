"""
OpenAI services: Whisper transcription + GPT-4o-mini data extraction.

Whisper handles bilingual Spanish/English audio from field visits.
GPT extracts structured CRM fields from the transcription.
"""
import json
import logging
from pathlib import Path

from mutagen import File as MutagenFile
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


# ============ Audio duration (demo limits) ============

def get_audio_duration(audio_path: str) -> float:
    """Return audio duration in seconds using mutagen. Returns 0.0 if undetectable."""
    try:
        audio = MutagenFile(audio_path)
        if audio and audio.info:
            return float(audio.info.length)
    except Exception:
        pass
    return 0.0


# ============ WHISPER: Audio → Text ============

async def transcribe_audio(audio_path: str) -> dict:
    """
    Transcribe a visit audio file using OpenAI Whisper.

    Args:
        audio_path: Path to the .m4a/.wav audio file

    Returns:
        {"text": "full transcription", "language": "es"|"en"}
    """
    file_path = Path(audio_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    logger.info(f"Transcribing audio: {audio_path}")

    with open(file_path, "rb") as audio_file:
        # Use auto language detection for Spanish/English mix
        params = {
            "model": settings.whisper_model,
            "file": audio_file,
            "response_format": "verbose_json",
        }

        # If language is set to auto, let Whisper detect
        if settings.transcription_language != "auto":
            params["language"] = settings.transcription_language

        response = await client.audio.transcriptions.create(**params)

    return {
        "text": response.text,
        "language": getattr(response, "language", "unknown"),
    }


# ============ GPT: Transcription → CRM Fields ============

EXTRACTION_PROMPT = """You are a CRM data extraction assistant for a kitchen supplies distribution business in Long Island, NY.

Given a transcription of a sales visit conversation (in Spanish, English, or mixed), extract the following structured data for the CRM:

1. **notas_vendedor**: A concise summary of the conversation in Spanish (2-3 sentences). Include key points: what the client needs, their situation, any relevant details about their home/business.

2. **resultados**: The outcome of the visit in Spanish (1 sentence). Examples: "Venta cerrada de juego de ollas", "Cliente interesado, pedir seguimiento el sábado", "No le interesa por ahora".

3. **productos**: A list of products mentioned with details:
   - nombre: product name in Spanish
   - cantidad: quantity (integer, or null if not specified)
   - precio_cotizado: quoted price (number, or null if not discussed)

4. **nivel_interes**: Client's interest level: "alto" (wants to buy), "medio" (interested but undecided), "bajo" (not interested)

5. **objeciones**: Any objections the client raised, in Spanish. Null if none.

6. **siguiente_paso**: Recommended next action in Spanish. Examples: "Llamar el viernes para confirmar", "Enviar catálogo por WhatsApp", "No contactar más".

7. **estado_sugerido**: Suggested CRM status based on the conversation:
   - "venta" → sale was made
   - "cita" → follow-up appointment was set
   - "seguimiento" → needs follow-up but no firm date
   - "no_llamar" → client explicitly said don't call again
   - "equivocado" → wrong number or not the right person

Respond ONLY with a valid JSON object. No markdown, no explanation. Example:
{
  "notas_vendedor": "Clienta interesada en juego de ollas. Vive sola, cocina mucho. Pidió ver el catálogo completo.",
  "resultados": "Cita para el sábado para mostrar catálogo completo",
  "productos": [{"nombre": "Juego de ollas 12 piezas", "cantidad": 1, "precio_cotizado": 350}],
  "nivel_interes": "alto",
  "objeciones": "Precio un poco alto, quiere ver opciones más económicas",
  "siguiente_paso": "Visitar el sábado con catálogo y opciones de financiamiento",
  "estado_sugerido": "cita"
}"""


async def extract_crm_fields(transcription: str) -> dict:
    """
    Extract structured CRM fields from a visit transcription using GPT.

    Args:
        transcription: Full text transcription from Whisper

    Returns:
        Structured dict with CRM fields
    """
    logger.info(f"Extracting CRM fields from transcription ({len(transcription)} chars)")

    response = await client.chat.completions.create(
        model=settings.gpt_model,
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": f"Transcription:\n\n{transcription}"},
        ],
        temperature=0.1,  # Low temperature for consistent structured output
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse GPT response as JSON: {raw[:200]}")
        result = {
            "notas_vendedor": "Error al procesar transcripción",
            "resultados": "Requiere revisión manual",
            "productos": [],
            "nivel_interes": "medio",
            "objeciones": None,
            "siguiente_paso": "Revisar transcripción manualmente",
            "estado_sugerido": "seguimiento",
        }

    return result


# ============ Combined: Audio → CRM Fields ============

async def process_visit_audio(audio_path: str) -> dict:
    """
    Full pipeline: Audio file → Whisper transcription → GPT extraction.

    Args:
        audio_path: Path to the visit audio file

    Returns:
        {
            "transcription": "full text...",
            "language": "es",
            "extraction": { CRM fields }
        }
    """
    # Step 1: Transcribe
    transcription_result = await transcribe_audio(audio_path)

    # Step 2: Extract CRM fields
    extraction = await extract_crm_fields(transcription_result["text"])

    return {
        "transcription": transcription_result["text"],
        "language": transcription_result["language"],
        "extraction": extraction,
    }
