from backend.services.xmltv.parser import (
    build_programme,
    normalize_rating_system,
)


def test_channel_rating_system_applies_only_when_parental_rating_exists():
    row = {
        "Air Date": "2026-07-18",
        "Start Time": "08:00:00",
        "Program Title": "Morning News",
        "Parental Rating (Optional)": "TV-PG",
    }
    programme = build_programme(row, 5, channel_rating_system="VCHIP")
    assert programme.rating_system == "VCHIP"

    row["Parental Rating (Optional)"] = None
    programme = build_programme(row, 5, channel_rating_system="VCHIP")
    assert programme.rating_system is None


def test_parental_rating_without_channel_rating_system_is_omitted():
    row = {
        "Air Date": "2026-07-18",
        "Start Time": "08:00:00",
        "Program Title": "Feature Film",
        "Parental Rating (Optional)": "12",
    }
    programme = build_programme(row, 5)
    assert programme.rating_system is None


def test_known_rating_system_variants_are_normalized():
    fixes = []

    assert normalize_rating_system("vchip", 5, fixes) == "VCHIP"
    assert normalize_rating_system("V-CHIP", 6, fixes) == "VCHIP"
    assert normalize_rating_system("mpaa", 7, fixes) == "MPA"
    assert normalize_rating_system("oflc nz", 8, fixes) == "OFLC-NZ"
    assert normalize_rating_system(
        "VCHIP — TV Parental Guidelines (United States)", 9, fixes
    ) == "VCHIP"
    assert len(fixes) == 5


def test_unlisted_rating_authority_is_preserved_for_global_use():
    fixes = []

    assert normalize_rating_system("My Authority", 5, fixes) == "My Authority"
    assert fixes == []
