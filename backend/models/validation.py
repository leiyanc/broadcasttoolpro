from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationIssue:
    rule_id: str
    severity: str
    message: str
    row: int | None = None
    field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationReport:
    score: int
    critical: int
    errors: int
    warnings: int
    auto_fixed: int
    issues: list[ValidationIssue]

    @classmethod
    def from_issues(
        cls,
        issues: list[ValidationIssue],
        auto_fixed: int = 0,
    ) -> "ValidationReport":
        critical = sum(issue.severity == "critical" for issue in issues)
        errors = sum(issue.severity == "error" for issue in issues)
        warnings = sum(issue.severity == "warning" for issue in issues)
        penalty = (critical * 25) + (errors * 10) + (warnings * 2)

        return cls(
            score=max(0, 100 - penalty),
            critical=critical,
            errors=errors,
            warnings=warnings,
            auto_fixed=auto_fixed,
            issues=issues,
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["ready_to_generate"] = self.critical == 0
        return result
