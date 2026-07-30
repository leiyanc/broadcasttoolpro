from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_render_staging_blueprint_is_isolated_and_persistent():
    blueprint = (PROJECT_ROOT / "render.yaml").read_text()

    assert "plan: starter" in blueprint
    assert "autoDeployTrigger: off" in blueprint
    assert "branch: feature/xmltv-generator" in blueprint
    assert "BTP_ALLOW_WEB_BOOTSTRAP" in blueprint
    assert 'value: "false"' in blueprint
    assert "BTP_DATA_DIR" in blueprint
    assert "mountPath: /opt/render/project/src/data" in blueprint
    assert "sizeGB: 1" in blueprint
    assert "initialDeployHook: python -m tools.bootstrap_admin" in blueprint
    assert "BTP_EMAIL_PROVIDER" in blueprint
    assert "value: disabled" in blueprint


def test_deployment_documentation_lists_required_secrets():
    documentation = (PROJECT_ROOT / "docs" / "DEPLOYMENT.md").read_text()

    assert "BTP_INITIAL_ADMIN_EMAIL" in documentation
    assert "BTP_INITIAL_ADMIN_PASSWORD" in documentation
    assert "remove `BTP_INITIAL_ADMIN_PASSWORD`" in documentation
