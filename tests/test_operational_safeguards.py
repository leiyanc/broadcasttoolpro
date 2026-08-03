from backend.core.operations import RequestRateLimiter


def test_sensitive_authentication_route_is_rate_limited():
    limiter = RequestRateLimiter()

    for attempt in range(10):
        allowed, retry_after = limiter.check(
            method="POST",
            path="/api/auth/login",
            client_key="198.51.100.10",
            now=float(attempt),
        )
        assert allowed is True
        assert retry_after == 0

    allowed, retry_after = limiter.check(
        method="POST",
        path="/api/auth/login",
        client_key="198.51.100.10",
        now=10.0,
    )

    assert allowed is False
    assert retry_after > 0


def test_rate_limit_is_isolated_by_client():
    limiter = RequestRateLimiter()

    for attempt in range(5):
        limiter.check(
            method="POST",
            path="/api/auth/password-reset/request",
            client_key="198.51.100.10",
            now=float(attempt),
        )

    allowed, _ = limiter.check(
        method="POST",
        path="/api/auth/password-reset/request",
        client_key="203.0.113.20",
        now=5.0,
    )

    assert allowed is True


def test_regular_product_routes_are_not_limited():
    limiter = RequestRateLimiter()

    for attempt in range(100):
        allowed, retry_after = limiter.check(
            method="POST",
            path="/api/xmltv/validate",
            client_key="198.51.100.10",
            now=float(attempt),
        )
        assert allowed is True
        assert retry_after == 0


def test_rate_limiter_keeps_bounded_client_state():
    limiter = RequestRateLimiter(max_clients=2)

    for client_number in range(3):
        limiter.check(
            method="POST",
            path="/api/auth/login",
            client_key=f"198.51.100.{client_number}",
            now=1.0,
        )

    assert len(limiter._requests) == 2
