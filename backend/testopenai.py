"""
Test si una API key de OpenAI sigue activa.
Uso: python test_openai_key.py <tu_api_key>
  o: OPEN_API_KEY=sk-... python test_openai_key.py
"""

import sys
import os

try:
    import requests
except ImportError:
    print("Instalando requests...")
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests


def test_openai_key(api_key: str) -> dict:
    """Prueba una API key de OpenAI haciendo una llamada mínima."""

    result = {"key": f"{api_key[:8]}...{api_key[-4:]}", "active": False, "details": ""}

    # 1. Verificar formato básico
    if not api_key.startswith(("sk-", "sess-")):
        result["details"] = "Formato inválido: la key debe empezar con 'sk-' o 'sess-'"
        return result

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # 2. Listar modelos (endpoint ligero, no consume tokens)
    print("Consultando /v1/models ...")
    try:
        resp = requests.get(
            "https://api.openai.com/v1/models",
            headers=headers,
            timeout=15,
        )
    except requests.RequestException as e:
        result["details"] = f"Error de conexión: {e}"
        return result

    if resp.status_code == 200:
        models = [m["id"] for m in resp.json().get("data", [])]
        gpt_models = sorted([m for m in models if "gpt" in m])
        result["active"] = True
        result["details"] = "Key válida y activa"
        result["models_gpt"] = gpt_models
        result["total_models"] = len(models)
        return result

    # Interpretar errores comunes
    error_map = {
        401: "Key inválida o revocada (401 Unauthorized)",
        403: "Acceso denegado (403 Forbidden) — posible restricción de IP o permisos",
        429: "Rate limit alcanzado (429) — la key existe pero tiene límite excedido",
    }
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    error_msg = body.get("error", {}).get("message", resp.text[:200])

    result["details"] = error_map.get(resp.status_code, f"HTTP {resp.status_code}")
    result["error_message"] = error_msg

    # 429 significa que la key sí existe
    if resp.status_code == 429:
        result["active"] = True

    return result


def main():
    # Obtener key de argumento o variable de entorno
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        api_key = os.environ.get("OPEN_API_KEY", "")

    if not api_key:
        print("Uso:")
        print(f"  python {sys.argv[0]} <tu_api_key>")
        print(f"  OPEN_API_KEY=sk-... python {sys.argv[0]}")
        sys.exit(1)

    print(f"Probando key: {api_key[:8]}...{api_key[-4:]}\n")

    result = test_openai_key(api_key)

    # Mostrar resultados
    status = "✅ ACTIVA" if result["active"] else "❌ INACTIVA"
    print(f"Estado:  {status}")
    print(f"Detalle: {result['details']}")

    if result.get("error_message"):
        print(f"Error:   {result['error_message']}")

    if result.get("models_gpt"):
        print(f"\nModelos GPT disponibles ({len(result['models_gpt'])}):")
        for m in result["models_gpt"]:
            print(f"  - {m}")
        print(f"\nTotal modelos accesibles: {result['total_models']}")


if __name__ == "__main__":
    main()