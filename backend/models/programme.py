from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Programme:
    source_row: int
    channel: str | None
    air_date: str
    start_time: str
    program_title: str
    duration: str | None
    parental_rating: str | None
    program_description: str | None
    original_title: str | None
    cast: list[str]
    season_number: int | None
    episode_number: int | None
    original_episode_title: str | None
    episode_description: str | None
    genre: str | None
    country_of_production: str | None
    production_year: int | None
    premiere: bool
    live: bool
    new: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
