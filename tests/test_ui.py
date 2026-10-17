from html.parser import HTMLParser

import pytest


class PageReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []
        self.ids = set()

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "script":
            self.sources.append(attrs.get("src", ""))
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.sources.append(attrs["href"])


def test_root_and_local_asset_contract(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Intentionally vulnerable" in response.text
    page = PageReferences()
    page.feed(response.text)
    assert page.sources == ["/assets/app.css", "/assets/app.js"]
    assert {
        "query",
        "run",
        "presets",
        "reset",
        "vulnerable-panel",
        "fixed-panel",
        "explanation",
    } <= page.ids
    for source in page.sources:
        assert client.get(source).status_code == 200
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_ui_source_contract_is_not_a_browser_test(client):
    script = client.get("/assets/app.js")
    assert script.headers["content-type"].startswith("text/javascript")
    assert "textContent" in script.text
    assert "innerHTML" not in script.text
    assert "window.confirm" in script.text
    assert "X-CSRF-Token" in script.text
    assert "Promise.allSettled" in script.text
    css = client.get("/assets/app.css")
    assert css.headers["content-type"].startswith("text/css")
    assert "grid-template-columns: 1fr" in css.text


@pytest.mark.parametrize(
    "path",
    ["/assets/unknown.js", "/assets/database.py", "/assets/%2e%2e%2fapp.py", "/docs", "/redoc"],
)
def test_no_arbitrary_assets_or_cdn_docs(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"
