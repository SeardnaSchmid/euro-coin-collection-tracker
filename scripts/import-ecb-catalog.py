#!/usr/bin/env python3
"""Build the bundled circulation-coin catalogue from official ECB pages.

Requires the `requests` and `beautifulsoup4` Python packages available in the
development environment. The generated JSON and images are committed so the
deployed static site never depends on live ECB requests.
"""

from __future__ import annotations

import html
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "public" / "coins" / "ecb"
OUTPUT = ROOT / "src" / "data" / "coins.generated.json"
ECB = "https://www.ecb.europa.eu"

# These issues already appear in the ECB catalogue, but their image elements
# currently point to a generic "coming soon" graphic. Use the corresponding
# official Commission photographs instead of omitting the coins.
OFFICIAL_IMAGE_FALLBACKS = {
    (2024, "VA", "the-150th-anniversary-of-the-birth-of-guglielmo-marconi"): {
        "image": "https://economy-finance.ec.europa.eu/sites/default/files/2024-07/The-150Th-anniversary-of-the-birth-of-Guglielmo-Marconi.jpg?eurocase=1",
        "source": "https://economy-finance.ec.europa.eu/euro/euro-coins-and-notes/euro-coins/commemorative-coins/150th-anniversary-birth-guglielmo-marconi_en",
    },
    (2025, "VA", "the-550th-anniversary-of-the-birth-of-michelangelo"): {
        "image": "https://economy-finance.ec.europa.eu/sites/default/files/2026-06/vA_2025_Michelangelo.jpg?eurocase=1",
        "source": "https://economy-finance.ec.europa.eu/euro/euro-coins-and-notes/euro-coins/commemorative-coins/550th-anniversary-birth-michelangelo_en",
    },
    (2025, "VA", "sede-vacante-2025"): {
        "image": "https://economy-finance.ec.europa.eu/sites/default/files/2026-06/va_2025_Sede_vacante_small.jpg?eurocase=1",
        "source": "https://economy-finance.ec.europa.eu/euro/euro-coins-and-notes/euro-coins/commemorative-coins/sede-vacante-2025_en",
    },
    (2025, "VA", "jubilee-2025"): {
        "image": "https://economy-finance.ec.europa.eu/sites/default/files/2026-06/VA_2025_Jubilee.jpg?eurocase=1",
        "source": "https://economy-finance.ec.europa.eu/euro/euro-coins-and-notes/euro-coins/commemorative-coins/jubilee-2025-0_en",
    },
}

COUNTRIES = [
    ("AD", "Andorra", "🇦🇩", "ad"),
    ("AT", "Austria", "🇦🇹", "at"),
    ("BE", "Belgium", "🇧🇪", "be"),
    ("BG", "Bulgaria", "🇧🇬", "bg"),
    ("HR", "Croatia", "🇭🇷", "hr"),
    ("CY", "Cyprus", "🇨🇾", "cy"),
    ("EE", "Estonia", "🇪🇪", "et"),
    ("FI", "Finland", "🇫🇮", "fi"),
    ("FR", "France", "🇫🇷", "fr"),
    ("DE", "Germany", "🇩🇪", "de"),
    ("GR", "Greece", "🇬🇷", "gr"),
    ("IE", "Ireland", "🇮🇪", "ie"),
    ("IT", "Italy", "🇮🇹", "it"),
    ("LV", "Latvia", "🇱🇻", "lv"),
    ("LT", "Lithuania", "🇱🇹", "lt"),
    ("LU", "Luxembourg", "🇱🇺", "lu"),
    ("MT", "Malta", "🇲🇹", "mt"),
    ("MC", "Monaco", "🇲🇨", "mo"),
    ("NL", "Netherlands", "🇳🇱", "nl"),
    ("PT", "Portugal", "🇵🇹", "pt"),
    ("SM", "San Marino", "🇸🇲", "sm"),
    ("SK", "Slovakia", "🇸🇰", "sk"),
    ("SI", "Slovenia", "🇸🇮", "sl"),
    ("ES", "Spain", "🇪🇸", "es"),
    ("VA", "Vatican City", "🇻🇦", "va"),
]

COUNTRY_BY_CODE = {code: (code, name, flag, page) for code, name, flag, page in COUNTRIES}
COUNTRY_BY_PAGE = {page: COUNTRY_BY_CODE[code] for code, _, _, page in COUNTRIES}
COUNTRY_ALIASES = {
    "vatican": "VA",
    "vatican city": "VA",
    "vatican city state": "VA",
    "san marino": "SM",
    "the netherlands": "NL",
    "netherlands": "NL",
    "nederland": "NL",
}
COUNTRY_ALIASES.update({name.lower(): code for code, name, _, _ in COUNTRIES})

DENOMINATIONS = {
    "€2": (200, "€2"),
    "€1": (100, "€1"),
    "50 cent": (50, "50 cent"),
    "20 cent": (20, "20 cent"),
    "10 cent": (10, "10 cent"),
    "5 cent": (5, "5 cent"),
    "2 cent": (2, "2 cent"),
    "1 cent": (1, "1 cent"),
}

SERIES = {
    "BE": [
        ("first-series", "First series · Albert II"),
        ("second-series", "Second series · Albert II"),
        ("third-series", "Third series · Philippe"),
    ],
    "FR": [("first-series", "First series"), ("second-series", "Second series")],
    "LU": [("first-series", "Henri")],
    "MC": [
        ("first-series", "First series · Rainier III"),
        ("second-series", "Second series · Albert II"),
        ("third-series", "Third series · Albert II"),
    ],
    "NL": [
        ("first-series", "First series · Beatrix"),
        ("second-series", "Second series · Willem-Alexander"),
    ],
    "SM": [("first-series", "First series"), ("second-series", "Second series")],
    "ES": [
        ("first-series", "First series · Juan Carlos I"),
        ("modified-first-series", "Modified first series · Juan Carlos I"),
        ("third-series", "Third series · Felipe VI"),
    ],
    "VA": [
        ("john-paul-ii", "John Paul II"),
        ("sede-vacante-2005", "Sede vacante 2005"),
        ("benedict-xvi", "Benedict XVI"),
        ("francis-portrait", "Francis portrait"),
        ("francis-coat-of-arms", "Francis coat of arms"),
    ],
}

LU_GUILLAUME_SOURCE = "https://www.bcl.lu/en/Banknotes-and-Coins/billets_pieces/car_pieces/nouvelles-faces/"
LU_GUILLAUME_IMAGES = {
    200: "https://www.bcl.lu/fr/media_actualites/communiques/2025/09/nouvelles-faces/1-2-euro.png",
    100: "https://www.bcl.lu/fr/media_actualites/communiques/2025/09/nouvelles-faces/1-2-euro.png",
    50: "https://www.bcl.lu/fr/media_actualites/communiques/2025/09/nouvelles-faces/102050.png",
    20: "https://www.bcl.lu/fr/media_actualites/communiques/2025/09/nouvelles-faces/102050.png",
    10: "https://www.bcl.lu/fr/media_actualites/communiques/2025/09/nouvelles-faces/102050.png",
    5: "https://www.bcl.lu/fr/media_actualites/communiques/2025/09/nouvelles-faces/125-cents.png",
    2: "https://www.bcl.lu/fr/media_actualites/communiques/2025/09/nouvelles-faces/125-cents.png",
    1: "https://www.bcl.lu/fr/media_actualites/communiques/2025/09/nouvelles-faces/125-cents.png",
}
VA_LEO_SOURCE = "https://vaticanstate.va/en/news/4413-vatican-euro-coin-set-unveiles-new-color-and-design.html"
VA_LEO_IMAGE = "https://vaticanstate.va/images/news/Divisionale-8-9-pezzi.jpg"

MOTIFS = {
    "AD": {200: "Coat of arms", 100: "Casa de la Vall", 50: "Romanesque art", 20: "Romanesque art", 10: "Romanesque art", 5: "Pyrenean chamois", 2: "Pyrenean chamois", 1: "Pyrenean chamois"},
    "AT": {200: "Bertha von Suttner", 100: "Wolfgang Amadeus Mozart", 50: "Vienna Secession", 20: "Belvedere Palace", 10: "St Stephen’s Cathedral", 5: "Primrose", 2: "Edelweiss", 1: "Gentian"},
    "BE": {value: ["King Albert II", "King Albert II", "King Philippe"] for value in (200, 100, 50, 20, 10, 5, 2, 1)},
    "BG": {200: "Paisiy Hilendarski", 100: "St Ivan of Rila", 50: "Madara Rider", 20: "Madara Rider", 10: "Madara Rider", 5: "Madara Rider", 2: "Madara Rider", 1: "Madara Rider"},
    "HR": {200: "Map of Croatia", 100: "Marten", 50: "Nikola Tesla", 20: "Nikola Tesla", 10: "Nikola Tesla", 5: "Glagolitic HR", 2: "Glagolitic HR", 1: "Glagolitic HR"},
    "CY": {200: "Cruciform idol", 100: "Cruciform idol", 50: "Kyrenia ship", 20: "Kyrenia ship", 10: "Kyrenia ship", 5: "Cypriot mouflon", 2: "Cypriot mouflon", 1: "Cypriot mouflon"},
    "EE": {value: "Map of Estonia" for value in (200, 100, 50, 20, 10, 5, 2, 1)},
    "FI": {200: "Cloudberries", 100: "Flying swans", 50: "Heraldic lion", 20: "Heraldic lion", 10: "Heraldic lion", 5: "Heraldic lion", 2: "Heraldic lion", 1: "Heraldic lion"},
    "FR": {200: ["Tree of life", "Oak and olive tree"], 100: ["Tree of life", "Oak and olive tree"], 50: ["The Sower", "Marie Curie"], 20: ["The Sower", "Joséphine Baker"], 10: ["The Sower", "Simone Veil"], 5: "Marianne", 2: "Marianne", 1: "Marianne"},
    "DE": {200: "Federal eagle", 100: "Federal eagle", 50: "Brandenburg Gate", 20: "Brandenburg Gate", 10: "Brandenburg Gate", 5: "Oak twig", 2: "Oak twig", 1: "Oak twig"},
    "GR": {200: "Europa and Zeus", 100: "Athenian owl", 50: "Eleftherios Venizelos", 20: "Ioannis Capodistrias", 10: "Rigas Feraios", 5: "Modern tanker", 2: "Corvette", 1: "Athenian trireme"},
    "IE": {value: "Celtic harp" for value in (200, 100, 50, 20, 10, 5, 2, 1)},
    "IT": {200: "Dante Alighieri", 100: "Vitruvian Man", 50: "Marcus Aurelius", 20: "Unique Forms of Continuity", 10: "The Birth of Venus", 5: "Colosseum", 2: "Mole Antonelliana", 1: "Castel del Monte"},
    "LV": {200: "Latvian folk maiden", 100: "Latvian folk maiden", 50: "Large coat of arms", 20: "Large coat of arms", 10: "Large coat of arms", 5: "Small coat of arms", 2: "Small coat of arms", 1: "Small coat of arms"},
    "LT": {value: "Vytis" for value in (200, 100, 50, 20, 10, 5, 2, 1)},
    "LU": {value: "Grand Duke Henri" for value in (200, 100, 50, 20, 10, 5, 2, 1)},
    "MT": {200: "Maltese Cross", 100: "Maltese Cross", 50: "Coat of arms of Malta", 20: "Coat of arms of Malta", 10: "Coat of arms of Malta", 5: "Mnajdra temples", 2: "Mnajdra temples", 1: "Mnajdra temples"},
    "MC": {200: ["Prince Rainier III", "Prince Albert II", "Prince Albert II frontal portrait"], 100: ["Rainier III and Albert II", "Prince Albert II", "Prince Albert II frontal portrait"], 50: ["Prince’s seal", "Albert II monogram", "Albert II monogram"], 20: ["Prince’s seal", "Albert II monogram", "Albert II monogram"], 10: ["Prince’s seal", "Albert II monogram", "Albert II monogram"], 5: ["Grimaldi coat of arms", "Grimaldi coat of arms", "Grimaldi coat of arms"], 2: ["Grimaldi coat of arms", "Grimaldi coat of arms", "Grimaldi coat of arms"], 1: ["Grimaldi coat of arms", "Grimaldi coat of arms", "Grimaldi coat of arms"]},
    "NL": {value: ["Queen Beatrix", "King Willem-Alexander"] for value in (200, 100, 50, 20, 10, 5, 2, 1)},
    "PT": {200: "Royal seal of 1144", 100: "Royal seal of 1144", 50: "Royal seal of 1142", 20: "Royal seal of 1142", 10: "Royal seal of 1142", 5: "Royal seal of 1134", 2: "Royal seal of 1134", 1: "Royal seal of 1134"},
    "SM": {200: ["Palazzo Pubblico", "Saint Marinus"], 100: ["Coat of arms", "Second Tower"], 50: ["Three Towers", "Saint Marinus"], 20: ["Saint Marinus", "Mount Titano"], 10: ["Basilica of San Marino", "Church of St Francis"], 5: ["Guaita Tower", "Church of St Quirinus"], 2: ["Statue of Liberty", "City Gate"], 1: ["Montale Tower", "Coat of arms"]},
    "SK": {200: "Double cross", 100: "Double cross", 50: "Bratislava Castle", 20: "Bratislava Castle", 10: "Bratislava Castle", 5: "Mount Kriváň", 2: "Mount Kriváň", 1: "Mount Kriváň"},
    "SI": {200: "France Prešeren", 100: "Primož Trubar", 50: "Mount Triglav", 20: "Lipizzaner horses", 10: "Slovenian Parliament", 5: "The Sower", 2: "Prince’s Stone", 1: "Stork"},
    "ES": {200: ["King Juan Carlos I", "King Juan Carlos I", "King Felipe VI"], 100: ["King Juan Carlos I", "King Juan Carlos I", "King Felipe VI"], 50: "Miguel de Cervantes", 20: "Miguel de Cervantes", 10: "Miguel de Cervantes", 5: "Santiago de Compostela", 2: "Santiago de Compostela", 1: "Santiago de Compostela"},
    "VA": {value: ["Pope John Paul II", "Sede vacante", "Pope Benedict XVI", "Pope Francis", "Pope Francis coat of arms"] for value in (200, 100, 50, 20, 10, 5, 2, 1)},
}

def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def slug(value: str) -> str:
    value = value.casefold().replace("ß", "ss")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")[:90]


def absolute_url(page_url: str, asset_url: str) -> str:
    return urljoin(page_url, asset_url)


def extension_for(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp"} else ".jpg"


def series_for(code: str, index: int) -> tuple[str, str]:
    choices = SERIES.get(code, [("first-series", "Regular issue")])
    return choices[min(index, len(choices) - 1)]


def motif_for(code: str, value: int, index: int) -> str:
    motif = MOTIFS[code][value]
    if isinstance(motif, list):
        return motif[min(index, len(motif) - 1)]
    return motif


def image_candidates(box) -> list[str]:
    candidates = []
    for picture in box.select(".coins picture"):
        webp = picture.select_one('source[type="image/webp"]')
        image = picture.select_one("img[src]")
        source = clean_text(webp.get("srcset", "")) if webp else ""
        if not source and image:
            source = clean_text(image.get("src", ""))
        if source and "placeholder_coming_soon" not in source:
            candidates.append(source)
    return candidates


def field_text(box, label: str) -> str:
    for strong in box.select(".content-box strong"):
        if clean_text(strong.get_text(" ", strip=True)).rstrip(":").casefold() == label.casefold():
            parent = strong.parent
            text = clean_text(parent.get_text(" ", strip=True))
            return clean_text(re.sub(rf"^{re.escape(label)}\s*:\s*", "", text, flags=re.I))
    return ""


def regular_catalog(session: requests.Session) -> list[dict]:
    records = []
    for code, country, flag, page_code in COUNTRIES:
        page_url = f"{ECB}/euro/coins/html/{page_code}.en.html"
        response = session.get(page_url, timeout=40)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        boxes = soup.select("main .boxes > .box")
        if len(boxes) != 8:
            raise RuntimeError(f"Expected 8 denomination boxes for {country}, found {len(boxes)}")
        for box in boxes:
            heading = box.select_one("h3")
            denomination_key = clean_text(heading.get_text(" ", strip=True))
            value, denomination = DENOMINATIONS[denomination_key]
            images = image_candidates(box)
            content = box.select_one(".content-box")
            description = clean_text(content.get_text(" ", strip=True)) if content else ""
            description = clean_text(re.sub(rf"^{re.escape(denomination_key)}\s*", "", description))
            for index, image_path in enumerate(images):
                series_id, series_label = series_for(code, index)
                record_id = f"{code.lower()}-{series_id}-{value}"
                image_url = absolute_url(page_url, image_path)
                ext = extension_for(image_url)
                local = f"regular/{record_id}{ext}"
                records.append({
                    "id": record_id,
                    "country": country,
                    "countryCode": code,
                    "flag": flag,
                    "denomination": denomination,
                    "valueCents": value,
                    "motif": motif_for(code, value, index),
                    "series": series_label,
                    "kind": "regular",
                    "info": description,
                    "imagePath": f"coins/ecb/{local}",
                    "sourceUrl": page_url,
                    "imageSourceUrl": image_url,
                    "_local": local,
                })
    return records


def supplemental_regular_catalog() -> list[dict]:
    """Add released 2026 series that the ECB country pages do not yet show."""
    records = []
    for value, denomination in DENOMINATIONS.values():
        lu_image = LU_GUILLAUME_IMAGES[value]
        lu_local = f"regular/lu-guillaume-2026-{value}{extension_for(lu_image)}"
        if value >= 100:
            lu_info = "Grand Duke Guillaume faces left beside a stylised Luxembourg lion and the vertical inscription LËTZEBUERG."
        elif value >= 10:
            lu_info = "Grand Duke Guillaume faces left, opposite a stylised Luxembourg flag and the inscription LËTZEBUERG."
        else:
            lu_info = "A partial effigy of Grand Duke Guillaume faces left beside the inscription LËTZEBUERG and a stylised Luxembourg flag."
        records.append({
            "id": f"lu-guillaume-2026-{value}",
            "country": "Luxembourg",
            "countryCode": "LU",
            "flag": "🇱🇺",
            "denomination": denomination,
            "valueCents": value,
            "motif": "Grand Duke Guillaume",
            "series": "Guillaume · 2026",
            "kind": "regular",
            "info": lu_info,
            "imagePath": f"coins/ecb/{lu_local}",
            "sourceUrl": LU_GUILLAUME_SOURCE,
            "imageSourceUrl": lu_image,
            "_local": lu_local,
        })

        va_local = "regular/va-leo-xiv-2026-set.jpg"
        va_motif = "Pope Leo XIV" if value >= 10 else "Pope Leo XIV coat of arms"
        va_info = (
            "The inaugural 2026 Vatican series alternates between Pope Leo XIV’s portrait on the higher "
            "denominations and his papal coat of arms on the 1, 2 and 5 cent coins."
        )
        records.append({
            "id": f"va-leo-xiv-2026-{value}",
            "country": "Vatican City",
            "countryCode": "VA",
            "flag": "🇻🇦",
            "denomination": denomination,
            "valueCents": value,
            "motif": va_motif,
            "series": "Leo XIV · 2026",
            "kind": "regular",
            "info": va_info,
            "imagePath": f"coins/ecb/{va_local}",
            "sourceUrl": VA_LEO_SOURCE,
            "imageSourceUrl": VA_LEO_IMAGE,
            "_local": va_local,
        })
    return records


def country_from_heading(heading: str) -> str:
    normalized = clean_text(heading).casefold()
    if normalized in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[normalized]
    raise RuntimeError(f"Unknown issuing country heading: {heading}")


def joint_country(year: int, image_path: str, index: int) -> str | None:
    name = Path(urlparse(image_path).path).stem.casefold().replace("_", " ").replace("-", " ")
    if year == 2009 and "face" in name:
        return None
    for alias, code in sorted(COUNTRY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if alias in name:
            return code
    if year == 2022 and index == 3:
        return "DE"
    raise RuntimeError(f"Could not identify joint-issue image {year}: {image_path}")


def commemorative_catalog(session: requests.Session) -> list[dict]:
    records = []
    used_ids: set[str] = set()
    for year in range(2004, 2026):
        page_url = f"{ECB}/euro/coins/comm/html/comm_{year}.en.html"
        response = session.get(page_url, timeout=40)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for box in soup.select("main .boxes > .box"):
            heading_tag = box.select_one("h3")
            if not heading_tag:
                continue
            heading = clean_text(heading_tag.get_text(" ", strip=True))
            feature = field_text(box, "Feature") or f"Commemorative issue {year}"
            description = field_text(box, "Description")
            issuing_volume = field_text(box, "Issuing volume")
            issuing_date = field_text(box, "Issuing date")
            images = image_candidates(box)
            if heading == "Euro area countries":
                issues = []
                for index, image_path in enumerate(images):
                    code = joint_country(year, image_path, index)
                    if code:
                        issues.append((code, image_path))
            else:
                code = country_from_heading(heading)
                fallback = OFFICIAL_IMAGE_FALLBACKS.get((year, code, slug(feature)))
                if not images and fallback:
                    images = [fallback["image"]]
                issues = [(code, image_path) for image_path in images]
            for image_index, (code, image_path) in enumerate(issues):
                _, country, flag, _ = COUNTRY_BY_CODE[code]
                base_id = f"{code.lower()}-commemorative-{year}-{slug(feature)}"
                record_id = base_id
                suffix = 2
                while record_id in used_ids:
                    record_id = f"{base_id}-{suffix}"
                    suffix += 1
                used_ids.add(record_id)
                image_url = absolute_url(page_url, image_path)
                fallback = OFFICIAL_IMAGE_FALLBACKS.get((year, code, slug(feature)))
                ext = extension_for(image_url)
                local = f"commemorative/{year}/{record_id}{ext}"
                records.append({
                    "id": record_id,
                    "country": country,
                    "countryCode": code,
                    "flag": flag,
                    "denomination": "€2",
                    "valueCents": 200,
                    "motif": feature,
                    "series": "Commemorative",
                    "kind": "commemorative",
                    "issueYear": year,
                    "info": description,
                    "issuingVolume": issuing_volume,
                    "issuingDate": issuing_date,
                    "imagePath": f"coins/ecb/{local}",
                    "sourceUrl": fallback["source"] if fallback else page_url,
                    "imageSourceUrl": image_url,
                    "_local": local,
                })
    return records


def download(session: requests.Session, record: dict) -> None:
    target = ASSET_ROOT / record["_local"]
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 1000:
        return
    response = session.get(record["imageSourceUrl"], timeout=60)
    response.raise_for_status()
    if not response.headers.get("content-type", "").startswith("image/"):
        raise RuntimeError(f"Unexpected content type for {record['imageSourceUrl']}")
    target.write_bytes(response.content)


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "Eurocase catalog builder (official ECB image mirror)"})
    records = regular_catalog(session) + supplemental_regular_catalog() + commemorative_catalog(session)
    print(f"Discovered {len(records)} official circulation coin issues; downloading images…")
    downloads = {record["_local"]: record for record in records}.values()
    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(lambda record: download(session, record), downloads))

    country_order = {code: index for index, (code, _, _, _) in enumerate(COUNTRIES)}
    records.sort(key=lambda record: (
        country_order[record["countryCode"]],
        -record["valueCents"],
        record["kind"] == "commemorative",
        -(record.get("issueYear") or 0),
        record["id"],
    ))
    for record in records:
        record.pop("_local", None)
    OUTPUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    regular_count = sum(record["kind"] == "regular" for record in records)
    commemorative_count = len(records) - regular_count
    print(f"Wrote {regular_count} regular and {commemorative_count} commemorative issues to {OUTPUT}")


if __name__ == "__main__":
    main()
