from typing import Any


PRICING_CATALOG = {
    "programming_suite": {
        "name": "Programming Suite",
        "monthly_cents": 3900,
    },
    "traffic_operations": {
        "name": "Traffic Operations",
        "monthly_cents": 6000,
    },
    "stream_monitoring": {
        "name": "Stream Monitoring",
        "monthly_cents": 5900,
    },
    "enterprise": {
        "name": "Enterprise",
        "monthly_cents": 24900,
    },
}


def commercial_pricing(
    plan: str,
    entitlements: dict[str, Any],
    billing_cycle: str = "monthly",
) -> dict[str, Any]:
    enabled_addons = {
        addon["code"]
        for addon in entitlements.get("addons", [])
        if addon.get("enabled")
    }

    if plan == "enterprise":
        display_name = "Enterprise"
        base = PRICING_CATALOG["enterprise"]
        addons: list[dict[str, Any]] = []
    else:
        base = PRICING_CATALOG["programming_suite"]
        addons = [
            {
                "code": code,
                **PRICING_CATALOG[code],
            }
            for code in ("traffic_operations", "stream_monitoring")
            if code in enabled_addons
        ]
        display_name = (
            "Professional"
            if "traffic_operations" in enabled_addons
            else "Programming Suite"
        )

    monthly_total = base["monthly_cents"] + sum(
        addon["monthly_cents"]
        for addon in addons
    )
    cycle_multiplier = 12 if billing_cycle == "annual" else 1

    return {
        "currency": "USD",
        "display_name": display_name,
        "billing_cycle": billing_cycle,
        "base": base,
        "addons": addons,
        "monthly_total_cents": monthly_total,
        "billing_total_cents": monthly_total * cycle_multiplier,
        "billing_period": "year" if billing_cycle == "annual" else "month",
    }
