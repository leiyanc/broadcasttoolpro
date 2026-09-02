from xml.etree import ElementTree

from backend.services.xmltv.validator import parse_duration


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
) -> None:
    add_text_element(
        element,
        "title",
        programme["program_title"],
        lang=primary_language,
    )

    original_title = programme.get("original_title")
    if original_title and original_title != programme["program_title"]:
        original_attributes = {}
        if programme.get("original_language"):
            original_attributes["lang"] = programme["original_language"]
        add_text_element(
            element,
            "title",
            original_title,
            **original_attributes,
        )

    original_attributes = {}
    if programme.get("original_language"):
        original_attributes["lang"] = programme["original_language"]
    add_text_element(
        element,
        "sub-title",
        programme.get("original_episode_title"),
        **original_attributes,
    )
    add_text_element(
        element,
        "desc",
        programme.get("episode_description")
        or programme.get("program_description"),
        lang=primary_language,
    )
    add_text_element(element, "language", primary_language)
    add_text_element(
        element,
        "orig-language",
        programme.get("original_language"),
    )

    cast = programme.get("cast") or []
    if cast:
        credits = ElementTree.SubElement(element, "credits")
        for actor in cast:
            add_text_element(credits, "actor", actor)

    original_air_date = programme.get("original_air_date")
    if original_air_date:
        add_text_element(
            element,
            "date",
            original_air_date.replace("-", ""),
        )
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

    duration = programme.get("duration")
    if duration:
        total_seconds = int(parse_duration(duration).total_seconds())
        add_text_element(
            element,
            "length",
            total_seconds,
            units="seconds",
        )

    icon_url = programme.get("icon_url")
    if icon_url:
        attributes = {"src": icon_url}
        if programme.get("icon_width") is not None:
            attributes["width"] = str(programme["icon_width"])
        if programme.get("icon_height") is not None:
            attributes["height"] = str(programme["icon_height"])
        ElementTree.SubElement(element, "icon", attributes)

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

    add_text_element(
        element,
        "episode-num",
        programme.get("asset_id"),
        system="assetID",
    )

    rating = programme.get("parental_rating")
    rating_system = programme.get("rating_system")
    if rating and rating_system:
        rating_element = ElementTree.SubElement(
            element,
            "rating",
            {"system": rating_system},
        )
        add_text_element(rating_element, "value", rating)

    if programme.get("premiere"):
        ElementTree.SubElement(element, "premiere")

    if programme.get("previously_shown"):
        ElementTree.SubElement(element, "previously-shown")

    if programme.get("live"):
        ElementTree.SubElement(element, "live")

    if programme.get("new"):
        ElementTree.SubElement(element, "new")

    for keyword in programme.get("keywords") or []:
        add_text_element(element, "keyword", keyword)


def generate_xmltv(
    programmes: list[dict],
    channel_id: str,
    channel_name: str,
    primary_language: str = "en",
    timestamp_format: str = "xmltv",
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
        if timestamp_format == "iso8601":
            start_value = programme["iso_start"]
            stop_value = programme["iso_stop"]
        else:
            start_value = programme["xmltv_start"]
            stop_value = programme["xmltv_stop"]
        element = ElementTree.SubElement(
            root,
            "programme",
            {
                "start": start_value,
                "stop": stop_value,
                "channel": channel_id,
            },
        )
        add_programme_metadata(
            element,
            programme,
            primary_language,
        )

    ElementTree.indent(root, space="  ")
    return ElementTree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )
