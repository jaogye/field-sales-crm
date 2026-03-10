"""
Tests for Vendedores and Clientes API endpoints.
"""
import pytest
from httpx import AsyncClient


# ============ VENDEDORES ============

class TestVendedores:

    @pytest.mark.asyncio
    async def test_crear_vendedor(self, client: AsyncClient):
        response = await client.post("/api/v1/vendedores/", json={
            "nombre": "Carlos Martinez",
            "telefono": "+1 (631) 555-0101",
            "zona": "Long Island",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "Carlos Martinez"
        assert data["telefono"] == "+1 (631) 555-0101"
        assert data["activo"] is True

    @pytest.mark.asyncio
    async def test_listar_vendedores(self, client: AsyncClient):
        # Create two reps
        await client.post("/api/v1/vendedores/", json={
            "nombre": "Ana López", "telefono": "+1 (631) 555-0201"
        })
        await client.post("/api/v1/vendedores/", json={
            "nombre": "Pedro Ruiz", "telefono": "+1 (631) 555-0202"
        })

        response = await client.get("/api/v1/vendedores/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


# ============ CLIENTES ============

class TestClientes:

    @pytest.mark.asyncio
    async def test_crear_cliente(self, client: AsyncClient):
        response = await client.post("/api/v1/clientes/", json={
            "nombre_apellido": "Doña Helena",
            "telefono": "+1 (631) 871-0368",
            "zona": "Hampton Bays",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["nombre_apellido"] == "Doña Helena"
        assert data["estado"] == "nuevo"

    @pytest.mark.asyncio
    async def test_crear_cliente_duplicado(self, client: AsyncClient):
        payload = {
            "nombre_apellido": "Don Ramon",
            "telefono": "+1 (631) 702-5509",
        }
        await client.post("/api/v1/clientes/", json=payload)
        response = await client.post("/api/v1/clientes/", json=payload)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_actualizar_cliente(self, client: AsyncClient):
        # Create
        create_resp = await client.post("/api/v1/clientes/", json={
            "nombre_apellido": "Esperanza Buestan",
            "telefono": "+1 (631) 268-8538",
        })
        cliente_id = create_resp.json()["id"]

        # Update
        response = await client.put(f"/api/v1/clientes/{cliente_id}", json={
            "estado": "cita",
            "direccion": "3691 Noyack Rd, Sag Harbor",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "cita"
        assert data["direccion"] == "3691 Noyack Rd, Sag Harbor"

    @pytest.mark.asyncio
    async def test_buscar_cliente(self, client: AsyncClient):
        await client.post("/api/v1/clientes/", json={
            "nombre_apellido": "Doña Amparo Farmacia",
            "telefono": "+1 (718) 219-0071",
            "zona": "Brooklyn",
        })
        await client.post("/api/v1/clientes/", json={
            "nombre_apellido": "Doña Julia Clases",
            "telefono": "+1 (631) 896-3373",
            "zona": "Hampton Bays",
        })

        # Search by name
        response = await client.get("/api/v1/clientes/", params={"buscar": "Amparo"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["nombre_apellido"] == "Doña Amparo Farmacia"

        # Filter by zone
        response = await client.get("/api/v1/clientes/", params={"zona": "Hampton"})
        data = response.json()
        assert len(data) == 1

    @pytest.mark.asyncio
    async def test_sync_contactos(self, client: AsyncClient):
        # Create a rep first
        rep_resp = await client.post("/api/v1/vendedores/", json={
            "nombre": "Maria Garcia", "telefono": "+1 (631) 555-9999"
        })
        rep_id = rep_resp.json()["id"]

        response = await client.post("/api/v1/clientes/sync", json={
            "vendedor_id": rep_id,
            "contactos": [
                {"nombre_apellido": "Cliente A", "telefono": "+1 (631) 100-0001"},
                {"nombre_apellido": "Cliente B", "telefono": "+1 (631) 100-0002"},
                {"nombre_apellido": "Cliente C", "telefono": "+1 (631) 100-0003"},
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 3
        assert data["skipped"] == 0

        # Sync again — should skip all
        response = await client.post("/api/v1/clientes/sync", json={
            "vendedor_id": rep_id,
            "contactos": [
                {"nombre_apellido": "Cliente A", "telefono": "+1 (631) 100-0001"},
                {"nombre_apellido": "Cliente B", "telefono": "+1 (631) 100-0002"},
            ]
        })
        data = response.json()
        assert data["created"] == 0
        assert data["skipped"] == 2
