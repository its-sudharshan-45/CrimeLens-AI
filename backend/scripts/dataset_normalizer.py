# -*- coding: utf-8 -*-
"""
CrimeLens AI — crime_dataset_india.csv normalizer.

Single source of truth: Dataset/crime_dataset_india.csv
Produces database-ready records while preserving every original field.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / "Dataset" / "crime_dataset_india.csv"
FALLBACK_CSV = ROOT / "datasets" / "raw" / "crime_dataset_india.csv"
OUTPUT_DIR = ROOT / "datasets" / "processed"

DATE_FORMATS = ("%d-%m-%Y %H:%M", "%d-%m-%Y")

CRIME_DESC_TO_CATEGORY: dict[str, str] = {
    "ASSAULT": "Assault",
    "HOMICIDE": "Homicide",
    "ROBBERY": "Robbery",
    "BURGLARY": "Burglary",
    "ARSON": "Arson",
    "KIDNAPPING": "Kidnapping",
    "FRAUD": "Fraud",
    "CYBERCRIME": "Cybercrime",
    "IDENTITY THEFT": "Identity Theft",
    "DRUG OFFENSE": "Drug Offense",
    "VEHICLE - STOLEN": "Vehicle Theft",
    "VANDALISM": "Vandalism",
    "EXTORTION": "Extortion",
    "COUNTERFEITING": "Counterfeiting",
    "SHOPLIFTING": "Shoplifting",
    "SEXUAL ASSAULT": "Sexual Assault",
    "PUBLIC INTOXICATION": "Public Intoxication",
    "ILLEGAL POSSESSION": "Illegal Possession",
    "FIREARM OFFENSE": "Firearm Offense",
    "TRAFFIC VIOLATION": "Traffic Violation",
    "DOMESTIC VIOLENCE": "Domestic Violence",
}

PRIORITY_BY_CRIME: dict[str, str] = {
    "HOMICIDE": "CRITICAL",
    "SEXUAL ASSAULT": "CRITICAL",
    "KIDNAPPING": "CRITICAL",
    "ARSON": "HIGH",
    "ROBBERY": "HIGH",
    "ASSAULT": "HIGH",
    "EXTORTION": "HIGH",
    "FIREARM OFFENSE": "HIGH",
    "DOMESTIC VIOLENCE": "HIGH",
    "BURGLARY": "MEDIUM",
    "CYBERCRIME": "MEDIUM",
    "IDENTITY THEFT": "MEDIUM",
    "FRAUD": "MEDIUM",
    "DRUG OFFENSE": "MEDIUM",
    "VEHICLE - STOLEN": "LOW",
    "VANDALISM": "LOW",
    "COUNTERFEITING": "LOW",
    "SHOPLIFTING": "LOW",
    "PUBLIC INTOXICATION": "LOW",
    "ILLEGAL POSSESSION": "LOW",
    "TRAFFIC VIOLATION": "LOW",
}

CATEGORY_DEFS: dict[str, tuple[int, str, str]] = {
    "Assault": (4, "#EF4444", "Physical attack causing bodily harm to another person."),
    "Homicide": (5, "#7F1D1D", "Intentional killing or culpable homicide."),
    "Robbery": (4, "#DC2626", "Theft using force or threat of violence."),
    "Burglary": (4, "#F59E0B", "Unlawful entry into a building with intent to commit a crime."),
    "Arson": (5, "#F97316", "Deliberate setting fire to property or land."),
    "Kidnapping": (5, "#B91C1C", "Unlawful seizure and detention of a person."),
    "Fraud": (3, "#8B5CF6", "Intentional deception for financial gain."),
    "Cybercrime": (3, "#6366F1", "Crimes committed via digital networks and systems."),
    "Identity Theft": (3, "#7C3AED", "Fraudulent acquisition and use of another person's identity."),
    "Drug Offense": (3, "#10B981", "Illegal possession, trade, or manufacture of narcotics."),
    "Vehicle Theft": (2, "#3B82F6", "Theft of motor vehicles including cars and motorcycles."),
    "Vandalism": (2, "#F472B6", "Deliberate destruction of public or private property."),
    "Extortion": (4, "#D97706", "Obtaining money by threats or coercion."),
    "Counterfeiting": (3, "#84CC16", "Production or use of forged currency or documents."),
    "Shoplifting": (1, "#22D3EE", "Theft of goods from a retail establishment."),
    "Sexual Assault": (5, "#EC4899", "Non-consensual sexual contact or conduct."),
    "Public Intoxication": (1, "#A78BFA", "Disorderly conduct affecting public peace."),
    "Illegal Possession": (3, "#78716C", "Possession of prohibited items without authorisation."),
    "Firearm Offense": (4, "#EF4444", "Offenses related to illegal use or possession of firearms."),
    "Traffic Violation": (1, "#FACC15", "Violations of traffic laws and road safety regulations."),
    "Domestic Violence": (4, "#F43F5E", "Violence or abuse within a domestic or family setting."),
}

CITY_GEO: dict[str, dict[str, Any]] = {
    "Mumbai": {"state": "Maharashtra", "district": "Mumbai", "lat": 19.0760, "lon": 72.8777, "zip": "400"},
    "Delhi": {"state": "Delhi", "district": "New Delhi", "lat": 28.6139, "lon": 77.2090, "zip": "110"},
    "Bangalore": {"state": "Karnataka", "district": "Bangalore Urban", "lat": 12.9716, "lon": 77.5946, "zip": "560"},
    "Hyderabad": {"state": "Telangana", "district": "Hyderabad", "lat": 17.3850, "lon": 78.4867, "zip": "500"},
    "Chennai": {"state": "Tamil Nadu", "district": "Chennai", "lat": 13.0827, "lon": 80.2707, "zip": "600"},
    "Kolkata": {"state": "West Bengal", "district": "Kolkata", "lat": 22.5726, "lon": 88.3639, "zip": "700"},
    "Pune": {"state": "Maharashtra", "district": "Pune", "lat": 18.5204, "lon": 73.8567, "zip": "411"},
    "Ahmedabad": {"state": "Gujarat", "district": "Ahmedabad", "lat": 23.0225, "lon": 72.5714, "zip": "380"},
    "Jaipur": {"state": "Rajasthan", "district": "Jaipur", "lat": 26.9124, "lon": 75.7873, "zip": "302"},
    "Lucknow": {"state": "Uttar Pradesh", "district": "Lucknow", "lat": 26.8467, "lon": 80.9462, "zip": "226"},
    "Surat": {"state": "Gujarat", "district": "Surat", "lat": 21.1702, "lon": 72.8311, "zip": "395"},
    "Kanpur": {"state": "Uttar Pradesh", "district": "Kanpur", "lat": 26.4499, "lon": 80.3319, "zip": "208"},
    "Nagpur": {"state": "Maharashtra", "district": "Nagpur", "lat": 21.1458, "lon": 79.0882, "zip": "440"},
    "Indore": {"state": "Madhya Pradesh", "district": "Indore", "lat": 22.7196, "lon": 77.8577, "zip": "452"},
    "Bhopal": {"state": "Madhya Pradesh", "district": "Bhopal", "lat": 23.2599, "lon": 77.4126, "zip": "462"},
    "Patna": {"state": "Bihar", "district": "Patna", "lat": 25.5941, "lon": 85.1376, "zip": "800"},
    "Ludhiana": {"state": "Punjab", "district": "Ludhiana", "lat": 30.9010, "lon": 75.8573, "zip": "141"},
    "Agra": {"state": "Uttar Pradesh", "district": "Agra", "lat": 27.1767, "lon": 78.0081, "zip": "282"},
    "Nashik": {"state": "Maharashtra", "district": "Nashik", "lat": 19.9975, "lon": 73.7898, "zip": "422"},
    "Faridabad": {"state": "Haryana", "district": "Faridabad", "lat": 28.4089, "lon": 77.3178, "zip": "121"},
    "Meerut": {"state": "Uttar Pradesh", "district": "Meerut", "lat": 28.9845, "lon": 77.7064, "zip": "250"},
    "Rajkot": {"state": "Gujarat", "district": "Rajkot", "lat": 22.3039, "lon": 70.8022, "zip": "360"},
    "Varanasi": {"state": "Uttar Pradesh", "district": "Varanasi", "lat": 25.3176, "lon": 82.9739, "zip": "221"},
    "Srinagar": {"state": "Jammu & Kashmir", "district": "Srinagar", "lat": 34.0837, "lon": 74.7973, "zip": "190"},
    "Visakhapatnam": {"state": "Andhra Pradesh", "district": "Visakhapatnam", "lat": 17.6868, "lon": 83.2185, "zip": "530"},
    "Thane": {"state": "Maharashtra", "district": "Thane", "lat": 19.2183, "lon": 72.9781, "zip": "400"},
    "Ghaziabad": {"state": "Uttar Pradesh", "district": "Ghaziabad", "lat": 28.6692, "lon": 77.4538, "zip": "201"},
    "Vasai": {"state": "Maharashtra", "district": "Palghar", "lat": 19.3919, "lon": 72.8397, "zip": "401"},
    "Kalyan": {"state": "Maharashtra", "district": "Thane", "lat": 19.2437, "lon": 73.1355, "zip": "421"},
}

GENDER_LABELS = {"M": "Male", "F": "Female", "X": "Unknown"}


def resolve_csv_path(path: Optional[Path] = None) -> Path:
    if path and path.exists():
        return path
    if DEFAULT_CSV.exists():
        return DEFAULT_CSV
    if FALLBACK_CSV.exists():
        return FALLBACK_CSV
    raise FileNotFoundError("crime_dataset_india.csv not found in Dataset/ or datasets/raw/")


def _clean_key(key: str) -> str:
    return key.strip().lstrip("\ufeff")


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_datetime(value: str) -> Optional[datetime]:
    text = _clean_text(value)
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def normalize_gender(raw: str) -> str:
    key = _clean_text(raw).upper()
    return GENDER_LABELS.get(key, "Unknown")


def normalize_weapon(raw: str) -> str:
    text = _clean_text(raw)
    if not text or text.lower() == "none":
        return "None/Unidentified"
    return text


def normalize_crime_description(raw: str) -> str:
    return _clean_text(raw).upper()


def normalize_city(raw: str) -> str:
    city = _clean_text(raw)
    if not city:
        return ""
    return city.title()


def normalize_case_closed(raw: str) -> bool:
    return _clean_text(raw).lower() in {"yes", "y", "true", "1"}


def normalize_int(raw: str, default: int = 0) -> int:
    text = _clean_text(raw)
    if not text:
        return default
    try:
        return int(float(text))
    except ValueError:
        return default


def normalize_status(case_closed: bool, police_deployed: int) -> str:
    if case_closed:
        return "CLOSED"
    if police_deployed > 0:
        return "UNDER_INVESTIGATION"
    return "OPEN"


def normalize_priority(crime_desc: str, crime_domain: str) -> str:
    prio = PRIORITY_BY_CRIME.get(crime_desc, "MEDIUM")
    if crime_domain == "Violent Crime" and prio == "MEDIUM":
        return "HIGH"
    return prio


def crime_number_for(report_number: int) -> str:
    return f"IND-{report_number:06d}"


def build_description(normalized: dict[str, Any]) -> str:
    raw = normalized["raw"]
    return (
        f"[SOURCE: crime_dataset_india.csv | Report #{normalized['report_number']}]\n"
        f"Crime: {normalized['crime_description']} (Code {normalized['crime_code']}) | "
        f"Domain: {normalized['crime_domain']}\n"
        f"Victim: {normalized['victim_age']}yo {normalized['victim_gender_label']} | "
        f"Weapon: {normalized['weapon_used']} | Police Deployed: {normalized['police_deployed']}\n"
        f"Dates — Occurrence: {raw['Date of Occurrence']} | "
        f"Incident Time: {raw['Time of Occurrence']} | "
        f"Reported: {raw['Date Reported']} | "
        f"Case Closed: {raw['Case Closed']}"
        + (f" | Closed On: {raw['Date Case Closed']}" if raw.get("Date Case Closed") else "")
        + f"\nCity: {normalized['city']}"
    )


def build_title(normalized: dict[str, Any]) -> str:
    crime_title = normalized["crime_description"].title()
    title = f"{normalized['city']} — {crime_title} (#{normalized['report_number']:06d})"
    return title[:255]


def normalize_row(raw_row: dict[str, Any]) -> Optional[dict[str, Any]]:
    row = {_clean_key(k): v for k, v in raw_row.items()}

    report_number = normalize_int(row.get("Report Number", ""), default=-1)
    if report_number < 1:
        return None

    city = normalize_city(row.get("City", ""))
    crime_desc = normalize_crime_description(row.get("Crime Description", ""))
    category_name = CRIME_DESC_TO_CATEGORY.get(crime_desc)
    if not category_name or not city:
        return None

    incident_dt = parse_datetime(row.get("Time of Occurrence", "")) or parse_datetime(
        row.get("Date of Occurrence", "")
    )
    report_dt = parse_datetime(row.get("Date Reported", ""))
    closed_dt = parse_datetime(row.get("Date Case Closed", ""))

    if incident_dt is None:
        return None
    if report_dt is None or report_dt < incident_dt:
        report_dt = incident_dt

    victim_age = normalize_int(row.get("Victim Age", ""), default=0)
    police_deployed = normalize_int(row.get("Police Deployed", ""), default=0)
    case_closed = normalize_case_closed(row.get("Case Closed", ""))
    crime_domain = _clean_text(row.get("Crime Domain", "")) or "Other Crime"
    weapon = normalize_weapon(row.get("Weapon Used", ""))
    gender_label = normalize_gender(row.get("Victim Gender", ""))

    normalized: dict[str, Any] = {
        "report_number": report_number,
        "crime_number": crime_number_for(report_number),
        "city": city,
        "crime_code": normalize_int(row.get("Crime Code", ""), default=0),
        "crime_description": crime_desc,
        "category_name": category_name,
        "crime_domain": crime_domain,
        "victim_age": victim_age,
        "victim_gender": _clean_text(row.get("Victim Gender", "")).upper() or "X",
        "victim_gender_label": gender_label,
        "weapon_used": weapon,
        "police_deployed": police_deployed,
        "case_closed": case_closed,
        "status": normalize_status(case_closed, police_deployed),
        "priority": normalize_priority(crime_desc, crime_domain),
        "incident_date": incident_dt.isoformat(),
        "report_date": report_dt.isoformat(),
        "date_case_closed": closed_dt.isoformat() if closed_dt else None,
        "victim_count": 1,
        "suspect_count": 0,
        "estimated_loss": 0.0,
        "raw": {k: _clean_text(v) for k, v in row.items()},
    }
    normalized["title"] = build_title(normalized)
    normalized["description"] = build_description(normalized)
    return normalized


def load_and_normalize(csv_path: Optional[Path] = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = resolve_csv_path(csv_path)
    rows: list[dict[str, Any]] = []
    skipped = 0

    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = [_clean_key(c) for c in (reader.fieldnames or [])]
        for raw in reader:
            cleaned = {_clean_key(k): v for k, v in raw.items()}
            normalized = normalize_row(cleaned)
            if normalized is None:
                skipped += 1
                continue
            rows.append(normalized)

    rows.sort(key=lambda r: r["report_number"])
    summary = {
        "source_file": str(path),
        "source_records": len(rows) + skipped,
        "normalized_records": len(rows),
        "skipped_records": skipped,
        "fieldnames": fieldnames,
        "cities": sorted({r["city"] for r in rows}),
        "categories": sorted({r["category_name"] for r in rows}),
        "crime_types": sorted({r["crime_description"] for r in rows}),
        "domains": sorted({r["crime_domain"] for r in rows}),
        "closed_cases": sum(1 for r in rows if r["case_closed"]),
        "open_cases": sum(1 for r in rows if not r["case_closed"]),
    }
    return rows, summary


def write_normalized_artifacts(rows: list[dict[str, Any]], summary: dict[str, Any]) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = OUTPUT_DIR / "crime_dataset_india_normalized.jsonl"
    summary_path = OUTPUT_DIR / "crime_dataset_india_normalization_summary.json"

    with open(jsonl_path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)

    csv_path = OUTPUT_DIR / "crime_dataset_india_normalized.csv"
    if rows:
        export_fields = [
            "report_number", "crime_number", "city", "crime_code", "crime_description",
            "category_name", "crime_domain", "victim_age", "victim_gender", "victim_gender_label",
            "weapon_used", "police_deployed", "case_closed", "status", "priority",
            "incident_date", "report_date", "date_case_closed", "title",
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=export_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    return jsonl_path, summary_path


def location_record(city: str, now: datetime) -> dict[str, Any]:
    geo = CITY_GEO.get(city, {"state": "India", "district": city, "lat": 20.5937, "lon": 78.9629, "zip": "000"})
    return {
        "city": city,
        "address": f"Central jurisdiction — {city}",
        "landmark": f"{city} metropolitan area",
        "district": geo["district"],
        "state": geo["state"],
        "zip_code": f"{geo['zip']}001",
        "latitude": geo["lat"],
        "longitude": geo["lon"],
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
