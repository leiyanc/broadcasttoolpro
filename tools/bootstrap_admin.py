import os

from backend.services.identity_store import identity_store


def required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required for administrator bootstrap.")
    return value


def main() -> None:
    if identity_store.has_users():
        print("Administrator bootstrap skipped: users already exist.")
        return
    user, organization, _ = identity_store.bootstrap(
        organization_name=required_environment(
            "BTP_INITIAL_ORGANIZATION_NAME"
        ),
        display_name=required_environment("BTP_INITIAL_ADMIN_NAME"),
        email=required_environment("BTP_INITIAL_ADMIN_EMAIL"),
        password=required_environment("BTP_INITIAL_ADMIN_PASSWORD"),
    )
    print(
        "Administrator bootstrap completed for "
        f"{user['email']} in {organization['name']}."
    )


if __name__ == "__main__":
    main()
