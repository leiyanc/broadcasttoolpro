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
        "monthly_cents": 19900,
    },
}

ADDITIONAL_CHANNEL_CENTS = {
    "programming_suite": 2500,
    "professional": 4900,
    "enterprise": 7900,
}

COMMERCIAL_PLANS = [
    {
        "code": "programming_suite",
        "name": "Programming Suite",
        "monthly_cents": 3900,
        "description": "Create, validate, repair, and present programming.",
        "features": [
            "XMLTV Generator",
            "XMLTV Validator",
            "XMLTV Repair",
            "Programming Grid",
            "HLS Validator",
        ],
    },
    {
        "code": "professional",
        "name": "Professional",
        "monthly_cents": 9900,
        "description": "Programming and traffic workflows in one package.",
        "featured": True,
        "features": [
            "Everything in Programming Suite",
            "Pre Logs",
            "Post Logs",
            "Branded Excel and PDF reports",
            "Multi-format playlist and As-Run imports",
        ],
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "monthly_cents": 19900,
        "description": "Expanded scale, monitoring, and guided support.",
        "features": [
            "Everything in Professional",
            "Stream Monitoring included",
            "Media Loudness Compliance included",
            "Higher channel and user limits",
            "Advanced auditability",
            "Priority onboarding and support",
        ],
    },
]

COMMERCIAL_ADDONS = [
    {
        "code": "stream_monitoring",
        "name": "Stream Monitoring",
        "monthly_cents": 5900,
        "description": (
            "On-demand 5-, 10-, and 15-minute monitoring with SCTE-35, "
            "bandwidth analysis, and branded PDF reports."
        ),
    },
]


def commercial_pricing(
    plan: str,
    entitlements: dict[str, Any],
    billing_cycle: str = "monthly",
    channel_count: int = 1,
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

    plan_code = (
        "enterprise"
        if plan == "enterprise"
        else "professional"
        if "traffic_operations" in enabled_addons
        else "programming_suite"
    )
    channel_count = max(1, int(channel_count))
    additional_channel_count = max(0, channel_count - 1)
    additional_channel_cents = ADDITIONAL_CHANNEL_CENTS[plan_code]
    monthly_total = base["monthly_cents"] + sum(
        addon["monthly_cents"]
        for addon in addons
    ) + additional_channel_count * additional_channel_cents
    cycle_multiplier = 12 if billing_cycle == "annual" else 1

    return {
        "currency": "USD",
        "display_name": display_name,
        "plan_code": plan_code,
        "billing_cycle": billing_cycle,
        "base": base,
        "addons": addons,
        "monthly_total_cents": monthly_total,
        "channel_count": channel_count,
        "included_channel_count": 1,
        "additional_channel_count": additional_channel_count,
        "additional_channel_monthly_cents": additional_channel_cents,
        "billing_total_cents": monthly_total * cycle_multiplier,
        "billing_period": "year" if billing_cycle == "annual" else "month",
        "available_plans": COMMERCIAL_PLANS,
        "available_addons": COMMERCIAL_ADDONS,
    }
