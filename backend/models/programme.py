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
    rating_system: str | None
    program_description: str | None
    original_title: str | None
    original_language: str | None
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
    asset_id: str | None = None
    original_air_date: str | None = None
    icon_url: str | None = None
    icon_width: int | None = None
    icon_height: int | None = None
    keywords: list[str] | None = None
    previously_shown: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
