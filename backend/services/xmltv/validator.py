from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime, timedelta

from backend.models.programme import Programme
from backend.models.validation import ValidationIssue, ValidationReport


def programme_start(programme: Programme) -> datetime:
    return datetime.fromisoformat(
        f"{programme.air_date}T{programme.start_time}"
    )


def parse_duration(value: str) -> timedelta:
    parts = value.split(":")

    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError

    hours, minutes, seconds = (int(part) for part in parts)

    if minutes > 59 or seconds > 59:
        raise ValueError

    duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)

    if duration <= timedelta(0):
        raise ValueError

    return duration


class ValidationRule(ABC):
    rule_id: str

    @abstractmethod
    def validate(
        self,
        programmes: list[Programme],
    ) -> list[ValidationIssue]:
        raise NotImplementedError


class ProductionYearRule(ValidationRule):
    rule_id = "VAL-006"

    def validate(
        self,
        programmes: list[Programme],
    ) -> list[ValidationIssue]:
        return [
            ValidationIssue(
                rule_id=self.rule_id,
                severity="warning",
                row=programme.source_row,
                field="Production Year",
                message="Production Year must be between 1900 and 2100.",
            )
            for programme in programmes
            if programme.production_year is not None
            and not 1900 <= programme.production_year <= 2100
        ]


class DurationRule(ValidationRule):
    rule_id = "VAL-007"

    def validate(
        self,
        programmes: list[Programme],
    ) -> list[ValidationIssue]:
        issues = []

        for programme in programmes:
            if programme.duration is None:
                continue

            try:
                parse_duration(programme.duration)
            except ValueError:
                issues.append(
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity="critical",
                        row=programme.source_row,
                        field="Duration (Optional)",
                        message="Duration must use a positive HH:MM:SS value.",
                    )
                )

        return issues


class ChronologicalOrderRule(ValidationRule):
    rule_id = "VAL-004"

    def validate(
        self,
        programmes: list[Programme],
    ) -> list[ValidationIssue]:
        issues = []
        previous_by_channel: dict[str, datetime] = {}

        for programme in programmes:
            channel = programme.channel or "__default__"
            start = programme_start(programme)
            previous = previous_by_channel.get(channel)

            if previous is not None and start < previous:
                issues.append(
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity="error",
                        row=programme.source_row,
                        field="Start Time",
                        message="Programme rows are not in chronological order.",
                    )
                )

            previous_by_channel[channel] = start

        return issues


class DuplicateStartRule(ValidationRule):
    rule_id = "VAL-005"

    def validate(
        self,
        programmes: list[Programme],
    ) -> list[ValidationIssue]:
        seen: dict[tuple[str, datetime], int] = {}
        issues = []

        for programme in programmes:
            key = (
                programme.channel or "__default__",
                programme_start(programme),
            )

            if key in seen:
                issues.append(
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity="critical",
                        row=programme.source_row,
                        field="Start Time",
                        message=(
                            "Duplicate programme start time; "
                            f"it also appears on row {seen[key]}."
                        ),
                    )
                )
            else:
                seen[key] = programme.source_row

        return issues


class OverlapRule(ValidationRule):
    rule_id = "VAL-008"

    def validate(
        self,
        programmes: list[Programme],
    ) -> list[ValidationIssue]:
        by_channel: dict[str, list[Programme]] = defaultdict(list)
        issues = []

        for programme in programmes:
            by_channel[programme.channel or "__default__"].append(programme)

        for channel_programmes in by_channel.values():
            ordered = sorted(channel_programmes, key=programme_start)

            for current, following in zip(ordered, ordered[1:]):
                if current.duration is None:
                    continue

                try:
                    current_stop = (
                        programme_start(current)
                        + parse_duration(current.duration)
                    )
                except ValueError:
                    continue

                if current_stop > programme_start(following):
                    issues.append(
                        ValidationIssue(
                            rule_id=self.rule_id,
                            severity="critical",
                            row=following.source_row,
                            field="Start Time",
                            message=(
                                "Programme overlaps the previous programme "
                                f"on row {current.source_row}."
                            ),
                        )
                    )

        return issues


class StopTimeRule(ValidationRule):
    rule_id = "VAL-009"

    def validate(
        self,
        programmes: list[Programme],
    ) -> list[ValidationIssue]:
        by_channel: dict[str, list[Programme]] = defaultdict(list)
        issues = []

        for programme in programmes:
            by_channel[programme.channel or "__default__"].append(programme)

        for channel_programmes in by_channel.values():
            final_programme = max(channel_programmes, key=programme_start)

            if final_programme.duration is None:
                issues.append(
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity="critical",
                        row=final_programme.source_row,
                        field="Duration (Optional)",
                        message=(
                            "The final programme requires a duration because "
                            "its stop time cannot be inferred."
                        ),
                    )
                )

        return issues


DEFAULT_RULES: tuple[ValidationRule, ...] = (
    ProductionYearRule(),
    DurationRule(),
    ChronologicalOrderRule(),
    DuplicateStartRule(),
    OverlapRule(),
    StopTimeRule(),
)


class ValidationEngine:
    def __init__(
        self,
        rules: tuple[ValidationRule, ...] = DEFAULT_RULES,
    ) -> None:
        self.rules = rules

    def validate(
        self,
        programmes: list[Programme],
        initial_issues: list[ValidationIssue] | None = None,
        auto_fixed: int = 0,
    ) -> ValidationReport:
        issues = list(initial_issues or [])

        for rule in self.rules:
            issues.extend(rule.validate(programmes))

        return ValidationReport.from_issues(
            issues,
            auto_fixed=auto_fixed,
        )
