"""Liveness and OpenAPI smoke tests."""


def test_root_landing_page(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "GardenShare" in response.text
    assert "/docs" in response.text


def test_health_endpoint(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "gardenshare"}


def test_members_html_page(client) -> None:
    client.post("/members", json={"name": "Alice Green", "email": "alice@example.com"})
    response = client.get("/members", headers={"accept": "text/html"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Alice Green" in response.text
    assert "<table" in response.text


def test_openapi_available(client) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    body = response.json()
    assert body["info"]["title"] == "GardenShare"
    assert "/members" in body["paths"]
    assert "/seeds" in body["paths"]
