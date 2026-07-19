import pytest


class TestGatewayHealth:
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["system"] == "Project Monolith"

    @pytest.mark.asyncio
    async def test_health_has_services(self, client):
        response = await client.get("/health")
        data = response.json()
        assert "services" in data
        assert isinstance(data["services"], dict)

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, client):
        response = await client.get("/")
        assert "X-Content-Type-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers

    @pytest.mark.asyncio
    async def test_security_headers_present(self, client):
        response = await client.get("/health")
        headers = response.headers
        assert headers.get("x-content-type-options") == "nosniff"
        assert "max-age=31536000" in headers.get("strict-transport-security", "")
