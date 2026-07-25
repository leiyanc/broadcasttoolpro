from xml.etree import ElementTree


def add_text_element(
    parent: ElementTree.Element,
    tag: str,
    value,
    **attributes: str,
) -> ElementTree.Element | None:
    if value is None or value == "":
        return None

    element = ElementTree.SubElement(parent, tag, attributes)
    element.text = str(value)
    return element


def add_programme_metadata(
    element: ElementTree.Element,
    programme: dict,
    primary_language: str,
    original_language: str,
    rating_system: str,
) -> None:
    add_text_element(
        element,
        "title",
        programme["program_title"],
        lang=primary_language,
    )

    original_title = programme.get("original_title")
    if original_title and original_title != programme["program_title"]:
        add_text_element(
            element,
            "title",
            original_title,
            lang=original_language,
        )

    add_text_element(
        element,
        "sub-title",
        programme.get("original_episode_title"),
        lang=original_language,
    )
    add_text_element(
        element,
        "desc",
        programme.get("program_description"),
        lang=primary_language,
    )

    cast = programme.get("cast") or []
    if cast:
        credits = ElementTree.SubElement(element, "credits")
        for actor in cast:
            add_text_element(credits, "actor", actor)

    add_text_element(element, "date", programme.get("production_year"))
    add_text_element(
        element,
        "category",
        programme.get("genre"),
        lang=primary_language,
    )
    add_text_element(
        element,
        "country",
        programme.get("country_of_production"),
    )

    season = programme.get("season_number")
    episode = programme.get("episode_number")

    if season is not None and episode is not None:
        add_text_element(
            element,
            "episode-num",
            f"{season - 1}.{episode - 1}.",
            system="xmltv_ns",
        )
        add_text_element(
            element,
            "episode-num",
            f"S{season:02d}E{episode:02d}",
            system="onscreen",
        )

    rating = programme.get("parental_rating")
    if rating:
        rating_element = ElementTree.SubElement(
            element,
            "rating",
            {"system": rating_system},
        )
        add_text_element(rating_element, "value", rating)

    if programme.get("premiere"):
        ElementTree.SubElement(element, "premiere")

    if programme.get("live"):
        ElementTree.SubElement(element, "live")

    if programme.get("new"):
        ElementTree.SubElement(element, "new")


def generate_xmltv(
    programmes: list[dict],
    channel_id: str,
    channel_name: str,
    primary_language: str = "en",
    original_language: str = "en",
    rating_system: str = "VCHIP",
) -> bytes:
    root = ElementTree.Element(
        "tv",
        {"generator-info-name": "Broadcast Tool Pro"},
    )
    channel = ElementTree.SubElement(root, "channel", {"id": channel_id})
    add_text_element(
        channel,
        "display-name",
        channel_name,
        lang=primary_language,
    )

    for programme in programmes:
        element = ElementTree.SubElement(
            root,
            "programme",
            {
                "start": programme["xmltv_start"],
                "stop": programme["xmltv_stop"],
                "channel": channel_id,
            },
        )
        add_programme_metadata(
            element,
            programme,
            primary_language,
            original_language,
            rating_system,
        )

    ElementTree.indent(root, space="  ")
    return ElementTree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )
