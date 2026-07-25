from pathlib import Path

from backend.main import FRONTEND_DIR, home


def test_frontend_files_exist():
    assert (FRONTEND_DIR / "index.html").is_file()
    assert (FRONTEND_DIR / "styles.css").is_file()
    assert (FRONTEND_DIR / "app.js").is_file()


def test_home_returns_frontend():
    response = home()

    assert Path(response.path) == FRONTEND_DIR / "index.html"


def test_frontend_uses_xmltv_endpoints():
    javascript = (FRONTEND_DIR / "app.js").read_text()

    assert "/api/xmltv/import" in javascript
    assert "/api/xmltv/generate" in javascript
