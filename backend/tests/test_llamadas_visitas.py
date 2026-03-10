"""
Tests for Llamadas (calls) and Visitas (visits) API endpoints.
"""
import pytest
from httpx import AsyncClient


async def create_rep_and_client(client: AsyncClient) -> tuple[int, int]:
    """Helper: create a rep and a client, return (vendedor_id, cliente_id)."""
    rep = await client.post("/api/v1/vendedores/", json={
        "nombre": "Test Vendedor", "telefono": "+1 (631) 555-8888"
    })
    cli = await client.post("/api/v1/clientes/", json={
        "nombre_apellido": "Test Cliente", "telefono": "+1 (631) 555-7777"
    })
    return rep.json()["id"], cli.json()["id"]


# ============ LLAMADAS ============

class TestLlamadas:

    @pytest.mark.asyncio
    async def test_registrar_llamada_cita(self, client: AsyncClient):
        vid, cid = await create_rep_and_client(client)

        response = await client.post("/api/v1/llamadas/", json={
            "vendedor_id": vid,
            "cliente_id": cid,
            "duracion_seg": 120,
            "resultado": "cita",
            "notas_telemarketing": "04-06 Cita confirmada para sábado",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["resultado"] == "cita"
        assert data["duracion_seg"] == 120

        # Client status should be updated to "cita"
        cli_resp = await client.get("/api/v1/clientes/", params={"buscar": "Test Cliente"})
        assert cli_resp.json()[0]["estado"] == "cita"

    @pytest.mark.asyncio
    async def test_registrar_llamada_no_contesta(self, client: AsyncClient):
        vid, cid = await create_rep_and_client(client)

        response = await client.post("/api/v1/llamadas/", json={
            "vendedor_id": vid,
            "cliente_id": cid,
            "duracion_seg": 0,
            "resultado": "no_contesta",
            "notas_telemarketing": "04-06 NC",
        })
        assert response.status_code == 200

        # Status should remain "nuevo" (no_contesta doesn't change status)
        cli_resp = await client.get("/api/v1/clientes/", params={"buscar": "Test Cliente"})
        assert cli_resp.json()[0]["estado"] == "nuevo"

    @pytest.mark.asyncio
    async def test_registrar_llamada_venta(self, client: AsyncClient):
        vid, cid = await create_rep_and_client(client)

        await client.post("/api/v1/llamadas/", json={
            "vendedor_id": vid,
            "cliente_id": cid,
            "duracion_seg": 300,
            "resultado": "venta",
        })

        cli_resp = await client.get("/api/v1/clientes/", params={"buscar": "Test Cliente"})
        assert cli_resp.json()[0]["estado"] == "venta"

    @pytest.mark.asyncio
    async def test_listar_llamadas_por_vendedor(self, client: AsyncClient):
        vid, cid = await create_rep_and_client(client)

        # Make 3 calls
        for resultado in ["no_contesta", "no_contesta", "cita"]:
            await client.post("/api/v1/llamadas/", json={
                "vendedor_id": vid, "cliente_id": cid,
                "duracion_seg": 30, "resultado": resultado,
            })

        response = await client.get("/api/v1/llamadas/", params={"vendedor_id": vid})
        assert response.status_code == 200
        assert len(response.json()) == 3

    @pytest.mark.asyncio
    async def test_resultado_invalido(self, client: AsyncClient):
        vid, cid = await create_rep_and_client(client)

        response = await client.post("/api/v1/llamadas/", json={
            "vendedor_id": vid, "cliente_id": cid,
            "duracion_seg": 10, "resultado": "invalido",
        })
        assert response.status_code == 422  # Validation error


# ============ VISITAS ============

class TestVisitas:

    @pytest.mark.asyncio
    async def test_crear_visita(self, client: AsyncClient):
        vid, cid = await create_rep_and_client(client)

        response = await client.post("/api/v1/visitas/", json={
            "vendedor_id": vid,
            "cliente_id": cid,
            "lat": 40.8621,
            "lng": -72.6268,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["vendedor_id"] == vid
        assert data["cliente_id"] == cid
        assert data["lat"] == 40.8621
        assert data["procesado"] is False

    @pytest.mark.asyncio
    async def test_listar_visitas_no_procesadas(self, client: AsyncClient):
        vid, cid = await create_rep_and_client(client)

        await client.post("/api/v1/visitas/", json={
            "vendedor_id": vid, "cliente_id": cid,
        })

        response = await client.get("/api/v1/visitas/", params={"procesado": False})
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_transcribir_sin_audio(self, client: AsyncClient):
        vid, cid = await create_rep_and_client(client)

        visit_resp = await client.post("/api/v1/visitas/", json={
            "vendedor_id": vid, "cliente_id": cid,
        })
        visita_id = visit_resp.json()["id"]

        response = await client.post(f"/api/v1/visitas/{visita_id}/transcribir")
        assert response.status_code == 400
        assert "No audio" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_visita_no_encontrada(self, client: AsyncClient):
        response = await client.post("/api/v1/visitas/99999/transcribir")
        assert response.status_code == 404


# ============ ESTADÍSTICAS ============

class TestEstadisticas:

    @pytest.mark.asyncio
    async def test_estadisticas_vacias(self, client: AsyncClient):
        response = await client.get("/api/v1/estadisticas/")
        assert response.status_code == 200
        data = response.json()
        assert data["total_clientes"] == 0
        assert data["total_vendedores"] == 0
        assert data["tasa_citas"] == 0

    @pytest.mark.asyncio
    async def test_estadisticas_con_datos(self, client: AsyncClient):
        vid, cid = await create_rep_and_client(client)

        # Create calls
        await client.post("/api/v1/llamadas/", json={
            "vendedor_id": vid, "cliente_id": cid,
            "duracion_seg": 60, "resultado": "cita",
        })
        await client.post("/api/v1/llamadas/", json={
            "vendedor_id": vid, "cliente_id": cid,
            "duracion_seg": 30, "resultado": "no_contesta",
        })

        response = await client.get("/api/v1/estadisticas/")
        data = response.json()
        assert data["total_clientes"] == 1
        assert data["total_vendedores"] == 1
        assert data["tasa_citas"] == 50.0  # 1 cita out of 2 calls
