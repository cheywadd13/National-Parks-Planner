"""Official NPS content adapters and public-page snapshot transformations."""

from datetime import datetime, timezone
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

NPS_BASE = "https://developer.nps.gov/api/v1/"
ACTIVITY_LABELS = {
    "Hiking": r"^(?:day )?hik(?:ing|es|e)(?:\b|$)",
    "Camping": r"^(?:camping|campgrounds?)(?:\b|$)",
    "Scenic drives": r"^(?:auto touring|scenic drives?|driving|scenic roads?)(?:\b|$)",
    "Wildlife viewing": r"^(?:wildlife (?:watching|viewing)|birdwatching|bird watching|birds)(?:\b|$)",
    "Photography": r"^(?:photography|art and photography)(?:\b|$)",
    "Ranger programs": r"^(?:ranger|interpretive programs|guided walks)(?:\b|-)",
    "Water activities": r"^(?:water activities|boating|swimming|canoeing|kayaking|river trips|paddling|fishing)(?:\b|$)",
    "Bicycling": r"^(?:biking|bicycling|cycling)(?:\b|$)",
    "Stargazing": r"^(?:stargazing|night sky|astronomy)(?:\b|$)",
    "Climbing": r"^(?:rock climbing|climbing|canyoneering)(?:\b|$)",
    "Backpacking": r"^(?:backpacking|wilderness backpacking)(?:\b|$)",
    "Horseback riding": r"^(?:horseback riding|horse riding|stock use)(?:\b|$)",
    "Tidepooling": r"^tidepooling(?:\b|$)",
}


def checked_now():
    return datetime.now(timezone.utc).isoformat()


def clean_text(value):
    soup = BeautifulSoup(str(value or ""), "html.parser")
    for element in soup(["script", "style"]):
        element.decompose()
    text = " ".join(soup.get_text(" ", strip=True).split())
    text = re.sub(r"(?<=\w)\ufffd(?=\w)", "'", text)
    return text.replace("\ufffd", " ")


def official_url(value, base="https://www.nps.gov/"):
    if not value or not str(value).strip():
        return None
    url = urljoin(base, value or "")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not (parsed.hostname == "nps.gov" or
                                       (parsed.hostname or "").endswith(".nps.gov")):
        return None
    return url


def decode_html(content):
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("windows-1252", errors="replace")


def activity_category(label):
    for category, pattern in ACTIVITY_LABELS.items():
        if re.search(pattern, label, re.I):
            return category
    return None


def credited_image(url, credit, caption="", alt="", source_url=None):
    credit = clean_text(credit)
    trusted = re.match(r"^(?:NPS(?:[ /]|$)|National Park Service)", credit, re.I)
    if not official_url(url) or not trusted or re.search(r"copyright|©|courtesy", credit, re.I):
        return None
    return {"url": official_url(url), "credit": credit, "caption": clean_text(caption),
            "alt": clean_text(alt), "source_url": source_url,
            "rights_basis": "NPS-authored credit and NPS public-domain policy",
            "rights_url": "https://www.nps.gov/aboutus/disclaimer.htm"}


def parse_public_profile(html, code, source_url, checked_at):
    soup = BeautifulSoup(html, "html.parser")
    descriptions = [clean_text(tag.get("content")) for tag in soup.select('meta[property="og:description"]')]
    description = max(descriptions, key=len, default="")
    if len(description) < 50:
        introduction = soup.select_one(".ParkIntro p, .park-intro p")
        description = clean_text(introduction) if introduction else ""
    images = []
    for figure in soup.select("figure"):
        image, credit = figure.select_one("img[src]"), figure.select_one(".credit")
        if image and credit:
            caption = figure.select_one("figcaption")
            record = credited_image(urljoin(source_url, image["src"]), credit.get_text(" ", strip=True),
                                    caption.get_text(" ", strip=True) if caption else "",
                                    image.get("alt", ""), source_url)
            if record and record["url"] not in {item["url"] for item in images}:
                images.append(record)
    main = soup.select_one("#main") or soup
    highlights = []
    for anchor in main.select("a[href]"):
        label = clean_text(anchor.get_text(" ", strip=True))
        url = official_url(anchor["href"], source_url)
        if url and f"/{code.lower()}/" in url and 8 <= len(label) <= 80:
            if anchor.find(["h2", "h3"]) or anchor.find_parent(["h2", "h3"]):
                highlights.append({"title": label, "url": url})
    return {"park_code": code.upper(), "description": description,
            "official_url": source_url, "source_url": source_url, "checked_at": checked_at,
            "source_kind": "Official NPS website snapshot", "images": images[:4],
            "highlights": highlights[:4], "activities": []}


def parse_public_activities(html, code, source_url):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("#main")
    if main is None:
        return []
    records, seen = [], set()
    for anchor in main.select("a[href]"):
        label = clean_text(anchor.get_text(" ", strip=True))
        category = activity_category(label)
        url = official_url(anchor["href"], source_url)
        if category and url and f"/{code.lower()}/" in url and (category, url) not in seen:
            records.append({"id": category, "name": category, "source_label": label,
                            "url": url, "source_url": source_url})
            seen.add((category, url))
    return records


def normalize_api_profile(record, checked_at):
    code = record["parkCode"].upper()
    url = official_url(record.get("url")) or f"https://www.nps.gov/{code.lower()}/index.htm"
    images = []
    for item in record.get("images", []):
        image = credited_image(item.get("url"), item.get("credit"),
                               item.get("caption"), item.get("altText"), url)
        if image:
            images.append(image)
    activities = []
    for item in record.get("activities", []):
        label = clean_text(item.get("name"))
        activities.append({"id": str(item["id"]), "name": activity_category(label) or label,
                           "source_label": label, "url": url, "source_url": url})
    return {"park_code": code, "description": clean_text(record.get("description")),
            "official_url": url, "source_url": url, "checked_at": checked_at,
            "source_kind": "Official NPS API", "images": images[:4],
            "highlights": [], "activities": activities,
            "directions": clean_text(record.get("directionsInfo"))}


def api_session():
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=.5, status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["GET"], respect_retry_after_header=True)
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def api_records(endpoint, code, api_key, session=None):
    if endpoint not in {"parks", "alerts", "thingstodo", "campgrounds"}:
        raise ValueError("Unsupported NPS endpoint")
    if not re.fullmatch(r"[A-Za-z0-9]{4}", code):
        raise ValueError("Invalid park code")
    client = session or api_session()
    records, start = [], 0
    while True:
        response = client.get(NPS_BASE + endpoint,
                              params={"parkCode": code.lower(), "limit": 100, "start": start,
                                      **({"fields": "images,activities"} if endpoint == "parks" else {})},
                              headers={"X-Api-Key": api_key}, timeout=(5, 15))
        response.raise_for_status()
        payload = response.json()
        batch = payload["data"]
        if not isinstance(batch, list):
            raise ValueError("Invalid NPS response")
        records.extend(batch)
        start += len(batch)
        if start >= int(payload["total"]):
            return records
        if not batch or start > 10000:
            raise ValueError("Incomplete NPS pagination")


def fetch_profile(code, api_key):
    records = api_records("parks", code, api_key)
    matching = [row for row in records if row.get("parkCode", "").upper() == code.upper()]
    if len(matching) != 1:
        raise ValueError("NPS park identity did not match")
    return normalize_api_profile(matching[0], checked_now())


def fetch_alerts(code, api_key, session=None):
    records = api_records("alerts", code, api_key, session)
    alerts = []
    for item in records:
        url = official_url(item.get("url"))
        alerts.append({"id": str(item["id"]), "title": clean_text(item.get("title")),
                       "category": clean_text(item.get("category")),
                       "description": clean_text(item.get("description")), "url": url,
                       "last_updated": item.get("lastIndexedDate")})
    return {"status": "ok", "checked_at": checked_now(), "alerts": alerts}
