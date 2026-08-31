from backend.main import app


def test_trial_email_preferences_are_not_exposed():
    paths = app.openapi()["paths"]

    assert "/api/auth/email-preferences" not in paths
