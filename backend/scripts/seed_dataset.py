# -*- coding: utf-8 -*-
# cspell:disable
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

"""
CrimeLens AI — Comprehensive Dataset Seeder
===========================================
Reads crime_dataset_india.csv to generate 500+ interconnected records across
all application tables: crime_reports, investigations, evidence, predictions,
investigation_notes, investigation_assignments, investigation_timeline, audit_logs.

Run from repository root:
    python -m backend.scripts.seed_dataset

Safe to run multiple times — idempotent via ON CONFLICT DO NOTHING.
"""

import asyncio
import csv
import hashlib
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.app.db.session import AsyncSessionLocal

# ── Stable UUID namespace ─────────────────────────────────────────────────
_NS = uuid.UUID("b2c3d4e5-f6a7-8901-bcde-f12345678901")

def _uid(name: str) -> uuid.UUID:
    return uuid.uuid5(_NS, name)

NOW = datetime.now(timezone.utc)
random.seed(42)

def days_ago(n: float) -> datetime:
    return NOW - timedelta(days=n)

# ─────────────────────────────────────────────────────────────────────────
# GEO DATA
# ─────────────────────────────────────────────────────────────────────────
CITY_GEO = {
    "Mumbai":        {"state": "Maharashtra",     "district": "Mumbai",         "lat": 19.0760, "lon": 72.8777, "zip": "400"},
    "Delhi":         {"state": "Delhi",           "district": "New Delhi",      "lat": 28.6139, "lon": 77.2090, "zip": "110"},
    "Bangalore":     {"state": "Karnataka",       "district": "Bangalore Urban","lat": 12.9716, "lon": 77.5946, "zip": "560"},
    "Hyderabad":     {"state": "Telangana",       "district": "Hyderabad",      "lat": 17.3850, "lon": 78.4867, "zip": "500"},
    "Chennai":       {"state": "Tamil Nadu",      "district": "Chennai",        "lat": 13.0827, "lon": 80.2707, "zip": "600"},
    "Kolkata":       {"state": "West Bengal",     "district": "Kolkata",        "lat": 22.5726, "lon": 88.3639, "zip": "700"},
    "Pune":          {"state": "Maharashtra",     "district": "Pune",           "lat": 18.5204, "lon": 73.8567, "zip": "411"},
    "Ahmedabad":     {"state": "Gujarat",         "district": "Ahmedabad",      "lat": 23.0225, "lon": 72.5714, "zip": "380"},
    "Jaipur":        {"state": "Rajasthan",       "district": "Jaipur",         "lat": 26.9124, "lon": 75.7873, "zip": "302"},
    "Lucknow":       {"state": "Uttar Pradesh",   "district": "Lucknow",        "lat": 26.8467, "lon": 80.9462, "zip": "226"},
    "Surat":         {"state": "Gujarat",         "district": "Surat",          "lat": 21.1702, "lon": 72.8311, "zip": "395"},
    "Kanpur":        {"state": "Uttar Pradesh",   "district": "Kanpur",         "lat": 26.4499, "lon": 80.3319, "zip": "208"},
    "Nagpur":        {"state": "Maharashtra",     "district": "Nagpur",         "lat": 21.1458, "lon": 79.0882, "zip": "440"},
    "Indore":        {"state": "Madhya Pradesh",  "district": "Indore",         "lat": 22.7196, "lon": 75.8577, "zip": "452"},
    "Bhopal":        {"state": "Madhya Pradesh",  "district": "Bhopal",         "lat": 23.2599, "lon": 77.4126, "zip": "462"},
    "Patna":         {"state": "Bihar",           "district": "Patna",          "lat": 25.5941, "lon": 85.1376, "zip": "800"},
    "Ludhiana":      {"state": "Punjab",          "district": "Ludhiana",       "lat": 30.9010, "lon": 75.8573, "zip": "141"},
    "Agra":          {"state": "Uttar Pradesh",   "district": "Agra",           "lat": 27.1767, "lon": 78.0081, "zip": "282"},
    "Nashik":        {"state": "Maharashtra",     "district": "Nashik",         "lat": 19.9975, "lon": 73.7898, "zip": "422"},
    "Faridabad":     {"state": "Haryana",         "district": "Faridabad",      "lat": 28.4089, "lon": 77.3178, "zip": "121"},
    "Meerut":        {"state": "Uttar Pradesh",   "district": "Meerut",         "lat": 28.9845, "lon": 77.7064, "zip": "250"},
    "Rajkot":        {"state": "Gujarat",         "district": "Rajkot",         "lat": 22.3039, "lon": 70.8022, "zip": "360"},
    "Varanasi":      {"state": "Uttar Pradesh",   "district": "Varanasi",       "lat": 25.3176, "lon": 82.9739, "zip": "221"},
    "Srinagar":      {"state": "Jammu & Kashmir", "district": "Srinagar",       "lat": 34.0837, "lon": 74.7973, "zip": "190"},
    "Visakhapatnam": {"state": "Andhra Pradesh",  "district": "Visakhapatnam",  "lat": 17.6868, "lon": 83.2185, "zip": "530"},
    "Thane":         {"state": "Maharashtra",     "district": "Thane",          "lat": 19.2183, "lon": 72.9781, "zip": "400"},
    "Ghaziabad":     {"state": "Uttar Pradesh",   "district": "Ghaziabad",      "lat": 28.6692, "lon": 77.4538, "zip": "201"},
    "Vasai":         {"state": "Maharashtra",     "district": "Palghar",        "lat": 19.3919, "lon": 72.8397, "zip": "401"},
    "Kalyan":        {"state": "Maharashtra",     "district": "Thane",          "lat": 19.2437, "lon": 73.1355, "zip": "421"},
}

CITY_LANDMARKS = {
    "Mumbai":    ["Dharavi Slum", "Bandra Station", "Andheri Market", "Dadar Circle", "Kurla Complex", "Worli Sea Link", "Juhu Beach"],
    "Delhi":     ["Connaught Place", "Paharganj Market", "Saket Mall", "Rohini Sector 22", "Karol Bagh", "Lajpat Nagar", "Dwarka"],
    "Bangalore": ["Brigade Road", "Koramangala", "Whitefield IT Park", "Majestic Bus Stand", "JP Nagar", "Banashankari", "Yelahanka"],
    "Hyderabad": ["Charminar Area", "Banjara Hills", "Gachibowli", "Secunderabad", "HITEC City", "Kukatpally", "Mehdipatnam"],
    "Chennai":   ["T Nagar", "Guindy Industrial", "Velachery", "Anna Nagar", "Adyar", "Perambur", "Tambaram"],
    "Kolkata":   ["Park Street", "Salt Lake City", "Howrah Bridge", "Ballygunge", "Tollygunge", "New Market", "Dum Dum"],
    "Pune":      ["Shivajinagar", "Kothrud", "Wakad", "Hadapsar", "Pimpri", "Camp Area", "Kharadi"],
    "Ahmedabad": ["CG Road", "Maninagar", "Chandkheda", "Vatva GIDC", "Gota", "Naroda", "Nikol"],
    "Jaipur":    ["Pink City Market", "Malviya Nagar", "Vaishali Nagar", "Sanganer", "Mansarovar", "Shyam Nagar", "Tonk Road"],
    "Lucknow":   ["Hazratganj", "Gomti Nagar", "Alambagh", "Chowk", "Aliganj", "Indira Nagar", "Mahanagar"],
}
DEFAULT_LANDMARKS = ["Main Market", "Railway Station Area", "Bus Stand", "Industrial Estate", "Old City Quarter", "New Township"]
ADDR_TEMPLATES = [
    "Sector {n} Road", "Plot {n} Industrial Area", "{n}th Cross Road",
    "Lane {n}", "Near Court Complex", "Opposite Hospital Gate",
    "Behind Highway {n}", "Near Police Station",
]

# ─────────────────────────────────────────────────────────────────────────
# MAPPINGS
# ─────────────────────────────────────────────────────────────────────────
CRIME_DESC_TO_CAT = {
    "ASSAULT":            "Assault",
    "HOMICIDE":           "Homicide",
    "ROBBERY":            "Robbery",
    "BURGLARY":           "Burglary",
    "ARSON":              "Arson",
    "KIDNAPPING":         "Kidnapping",
    "FRAUD":              "Fraud",
    "CYBERCRIME":         "Cybercrime",
    "IDENTITY THEFT":     "Cybercrime",
    "DRUG OFFENSE":       "Drug Offense",
    "VEHICLE - STOLEN":   "Vehicle Theft",
    "VANDALISM":          "Vandalism",
    "EXTORTION":          "Extortion",
    "COUNTERFEITING":     "Counterfeiting",
    "SHOPLIFTING":        "Shoplifting",
    "SEXUAL ASSAULT":     "Sexual Assault",
    "PUBLIC INTOXICATION": "Public Intoxication",
    "ILLEGAL POSSESSION": "Illegal Possession",
    "FIREARM OFFENSE":    "Firearm Offense",
    "TRAFFIC VIOLATION":  "Traffic Violation",
    "DOMESTIC VIOLENCE":  "Domestic Violence",
}

PRIORITY_MAP = {
    "HOMICIDE": "CRITICAL", "SEXUAL ASSAULT": "CRITICAL", "KIDNAPPING": "CRITICAL",
    "ARSON": "HIGH", "ROBBERY": "HIGH", "ASSAULT": "HIGH", "EXTORTION": "HIGH", "FIREARM OFFENSE": "HIGH",
    "DOMESTIC VIOLENCE": "HIGH",
    "BURGLARY": "MEDIUM", "CYBERCRIME": "MEDIUM", "IDENTITY THEFT": "MEDIUM",
    "FRAUD": "MEDIUM", "DRUG OFFENSE": "MEDIUM",
    "VEHICLE - STOLEN": "LOW", "VANDALISM": "LOW", "COUNTERFEITING": "LOW",
    "SHOPLIFTING": "LOW", "PUBLIC INTOXICATION": "LOW", "ILLEGAL POSSESSION": "LOW",
    "TRAFFIC VIOLATION": "LOW",
}

LOSS_RANGE = {
    "IDENTITY THEFT": (50_000, 500_000), "FRAUD": (100_000, 2_000_000),
    "CYBERCRIME": (25_000, 1_500_000), "ROBBERY": (5_000, 200_000),
    "BURGLARY": (10_000, 300_000), "VEHICLE - STOLEN": (200_000, 800_000),
    "SHOPLIFTING": (500, 15_000), "VANDALISM": (2_000, 50_000),
    "EXTORTION": (50_000, 1_000_000), "COUNTERFEITING": (20_000, 500_000),
    "ARSON": (100_000, 5_000_000), "KIDNAPPING": (100_000, 3_000_000),
    "ASSAULT": (0, 20_000), "DRUG OFFENSE": (10_000, 500_000),
    "ILLEGAL POSSESSION": (5_000, 100_000), "FIREARM OFFENSE": (10_000, 200_000),
    "DOMESTIC VIOLENCE": (0, 10_000), "TRAFFIC VIOLATION": (0, 50_000),
}

EVIDENCE_TEMPLATES = {
    "CCTV":      ("cctv_footage_{seq}.mp4",        "VIDEO",    "video/mp4",         ".mp4", (50_000, 500_000)),
    "Photo":     ("crime_scene_{seq}.jpg",          "IMAGE",    "image/jpeg",        ".jpg", (500,    8_000)),
    "Report":    ("incident_report_{seq}.pdf",      "DOCUMENT", "application/pdf",   ".pdf", (100,    2_000)),
    "FIR":       ("fir_{seq}.pdf",                  "DOCUMENT", "application/pdf",   ".pdf", (50,     500)),
    "Witness":   ("witness_stmt_{seq}.pdf",         "DOCUMENT", "application/pdf",   ".pdf", (50,     300)),
    "Audio":     ("interrogation_{seq}.mp3",        "AUDIO",    "audio/mpeg",        ".mp3", (2_000,  20_000)),
    "Financial": ("bank_statement_{seq}.pdf",       "DOCUMENT", "application/pdf",   ".pdf", (100,    2_000)),
    "Medical":   ("medical_report_{seq}.pdf",       "DOCUMENT", "application/pdf",   ".pdf", (200,    3_000)),
    "Forensic":  ("forensic_analysis_{seq}.pdf",    "DOCUMENT", "application/pdf",   ".pdf", (500,    5_000)),
    "Screenshot":("screenshot_{seq}.png",           "IMAGE",    "image/png",         ".png", (100,    5_000)),
}

CRIME_EVIDENCE_MAP = {
    "ASSAULT":            ["Photo", "Medical", "CCTV", "Witness"],
    "HOMICIDE":           ["Photo", "CCTV", "Forensic", "Medical", "Witness"],
    "ROBBERY":            ["CCTV", "Photo", "Witness", "FIR"],
    "BURGLARY":           ["CCTV", "Photo", "Forensic", "FIR"],
    "ARSON":              ["Photo", "CCTV", "Forensic", "Report"],
    "KIDNAPPING":         ["CCTV", "Witness", "FIR", "Audio"],
    "FRAUD":              ["Financial", "Report", "Screenshot"],
    "CYBERCRIME":         ["Screenshot", "Report", "Forensic"],
    "IDENTITY THEFT":     ["Screenshot", "Financial", "Report"],
    "DRUG OFFENSE":       ["Photo", "FIR", "Report"],
    "VEHICLE - STOLEN":   ["CCTV", "Photo", "FIR"],
    "VANDALISM":          ["Photo", "CCTV", "Witness"],
    "EXTORTION":          ["Audio", "Screenshot", "FIR"],
    "COUNTERFEITING":     ["Photo", "Financial", "Forensic"],
    "SHOPLIFTING":        ["CCTV", "Photo"],
    "SEXUAL ASSAULT":     ["Medical", "Witness", "Forensic"],
    "PUBLIC INTOXICATION":["CCTV", "FIR"],
    "ILLEGAL POSSESSION": ["Photo", "FIR"],
    "FIREARM OFFENSE":    ["Photo", "Forensic", "FIR"],
    "DOMESTIC VIOLENCE":  ["Photo", "Medical", "Witness"],
    "TRAFFIC VIOLATION":  ["Photo", "CCTV", "FIR"],
}

INV_NOTES = [
    "Initial crime scene examination completed. {n} witness statements recorded.",
    "Forensic team deployed. Samples sent to state forensic laboratory.",
    "CCTV footage from {n} nearby establishments retrieved for analysis.",
    "Suspect profile established from witness accounts and forensic data.",
    "Digital forensics requested for seized electronic devices.",
    "Coordination established with {city} Police for inter-jurisdiction tracking.",
    "Victim provided supplementary statement with additional details.",
    "Suspect detained for questioning. Legal counsel present.",
    "Field survey conducted covering {n} km radius from the incident site.",
    "AI prediction model cross-referenced with {n} similar historical cases.",
    "Charge sheet prepared and reviewed by senior officer.",
    "Court date scheduled. Witness summons issued.",
    "Lab results awaited. Estimated turnaround: 10 days.",
    "New CCTV lead from adjacent street confirms suspect vehicle.",
    "Arrest warrant obtained from duty magistrate.",
    "Evidence chain-of-custody verified and documented.",
    "Inter-state coordination initiated for fugitive tracking.",
    "Financial transaction analysis completed by forensic accountant.",
]

RESOLUTIONS = [
    "Accused arrested and charged. Case transferred to trial court.",
    "All stolen property recovered. Accused confessed during interrogation.",
    "Conviction secured after trial. Sentence awarded by Sessions Court.",
    "Case closed — insufficient evidence to proceed to trial.",
    "Accused absconded. Red corner notice issued. Case remains open.",
    "Case resolved via mediation. Accused paid full restitution.",
    "Charge sheet filed. Awaiting trial date from Sessions Court.",
    "Multiple accused arrested. Organised crime angle under investigation.",
    "FIR closed on magistrate order — reclassified as civil dispute.",
    "Suspect acquitted on benefit of doubt. Case closed.",
]

TIMELINE_ACTIONS = [
    ("INVESTIGATION_OPENED",  "Investigation file opened and case intake completed."),
    ("EVIDENCE_COLLECTED",    "Physical and digital evidence collected from the crime scene."),
    ("WITNESS_INTERVIEWED",   "Key witnesses interviewed and sworn statements recorded."),
    ("SUSPECT_IDENTIFIED",    "Primary suspect identified through witness accounts and forensics."),
    ("SUSPECT_DETAINED",      "Suspect detained for questioning under Section 41 CrPC."),
    ("FORENSICS_SUBMITTED",   "Evidence submitted to state forensic science laboratory."),
    ("WARRANT_ISSUED",        "Arrest warrant obtained from the jurisdictional magistrate."),
    ("COURT_FILING",          "Charge sheet filed with magistrate court."),
    ("CASE_STATUS_UPDATED",   "Investigation status updated based on recent developments."),
    ("BAIL_GRANTED",          "Accused released on bail by court. Monitoring order imposed."),
]

CRIME_TYPE_LABELS = {
    "ASSAULT": "Physical Assault", "HOMICIDE": "Homicide / Murder",
    "ROBBERY": "Armed Robbery", "BURGLARY": "Residential Burglary",
    "ARSON": "Property Arson", "KIDNAPPING": "Abduction / Kidnapping",
    "FRAUD": "Financial Fraud", "CYBERCRIME": "Cybercrime",
    "IDENTITY THEFT": "Identity Theft", "DRUG OFFENSE": "Narcotics Offense",
    "VEHICLE - STOLEN": "Motor Vehicle Theft", "VANDALISM": "Property Vandalism",
    "EXTORTION": "Extortion / Blackmail", "COUNTERFEITING": "Counterfeiting",
    "SHOPLIFTING": "Retail Shoplifting", "SEXUAL ASSAULT": "Sexual Offense",
    "PUBLIC INTOXICATION": "Public Order Offense", "ILLEGAL POSSESSION": "Illegal Possession",
    "FIREARM OFFENSE": "Firearm Offense", "TRAFFIC VIOLATION": "Traffic Offense",
    "DOMESTIC VIOLENCE": "Domestic Violence",
}

RISK_LABELS   = ["VERY_LOW", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
HOTSPOT_LABELS = ["STABLE",  "EMERGING", "ACTIVE", "HOTSPOT", "CRITICAL_HOTSPOT"]

CATEGORY_DEFS = {
    "Assault":           (4, "#EF4444", "Physical attack causing bodily harm to another person."),
    "Homicide":          (5, "#7F1D1D", "Intentional killing or culpable homicide."),
    "Robbery":           (4, "#DC2626", "Theft using force or threat of violence."),
    "Burglary":          (4, "#F59E0B", "Unlawful entry into a building with intent to commit a crime."),
    "Arson":             (5, "#F97316", "Deliberate setting fire to property or land."),
    "Kidnapping":        (5, "#B91C1C", "Unlawful seizure and detention of a person."),
    "Fraud":             (3, "#8B5CF6", "Intentional deception for financial gain."),
    "Cybercrime":        (3, "#6366F1", "Crimes committed via digital networks and systems."),
    "Drug Offense":      (3, "#10B981", "Illegal possession, trade, or manufacture of narcotics."),
    "Vehicle Theft":     (2, "#3B82F6", "Theft of motor vehicles including cars and motorcycles."),
    "Vandalism":         (2, "#F472B6", "Deliberate destruction of public or private property."),
    "Extortion":         (4, "#D97706", "Obtaining money by threats or coercion."),
    "Counterfeiting":    (3, "#84CC16", "Production or use of forged currency or documents."),
    "Shoplifting":       (1, "#22D3EE", "Theft of goods from a retail establishment."),
    "Sexual Assault":    (5, "#EC4899", "Non-consensual sexual contact or conduct."),
    "Public Intoxication": (1, "#A78BFA", "Disorderly conduct affecting public peace."),
    "Illegal Possession":(3, "#78716C", "Possession of prohibited items without authorisation."),
    "Firearm Offense":   (4, "#EF4444", "Offenses related to illegal use or possession of firearms."),
    "Traffic Violation": (1, "#FACC15", "Violations of traffic laws and road safety regulations."),
    "Domestic Violence": (4, "#F43F5E", "Violence or abuse within a domestic or family setting."),
}

# ─────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────
async def _upsert(session, table, rows: list[dict], conflict_cols: list[str]) -> int:
    if not rows:
        return 0
    inserted = 0
    BATCH = 200
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        stmt = pg_insert(table).values(batch).on_conflict_do_nothing(index_elements=conflict_cols)
        result = await session.execute(stmt)
        inserted += result.rowcount
    return inserted

async def _count(session, table_name: str) -> int:
    r = await session.execute(text(f'SELECT count(*) FROM "{table_name}"'))
    return r.scalar()

def parse_dt(s: str) -> datetime:
    for fmt in ("%d-%m-%Y %H:%M", "%d-%m-%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            pass
    return NOW - timedelta(days=random.randint(30, 400))

def make_loc(city: str, idx: int) -> dict:
    g = CITY_GEO.get(city, {"state": "India", "district": city,
                             "lat": 20.59 + random.uniform(-5, 5),
                             "lon": 78.96 + random.uniform(-10, 10), "zip": "000"})
    landmarks = CITY_LANDMARKS.get(city, DEFAULT_LANDMARKS)
    landmark  = landmarks[idx % len(landmarks)]
    addr = ADDR_TEMPLATES[idx % len(ADDR_TEMPLATES)].replace("{n}", str(random.randint(1, 50)))
    return {
        "id":         _uid(f"loc:csv:{city}:{idx}"),
        "address":    addr,
        "landmark":   landmark,
        "city":       city,
        "district":   g["district"],
        "state":      g["state"],
        "zip_code":   f"{g['zip']}{str(random.randint(0, 99)).zfill(3)}",
        "latitude":   round(g["lat"] + random.uniform(-0.06, 0.06), 6),
        "longitude":  round(g["lon"] + random.uniform(-0.06, 0.06), 6),
        "created_at": NOW - timedelta(days=500),
        "updated_at": NOW - timedelta(days=500),
        "deleted_at": None,
    }

def confidence_for(crime_desc: str) -> float:
    base = {"HOMICIDE": 0.91, "ROBBERY": 0.87, "ASSAULT": 0.85, "BURGLARY": 0.83,
            "FRAUD": 0.79, "CYBERCRIME": 0.76, "DRUG OFFENSE": 0.82}.get(crime_desc, 0.74)
    return round(min(0.99, base + random.uniform(-0.09, 0.09)), 4)


# ─────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────
async def seed():
    from backend.app.models.user import User
    from backend.app.models.crime_category import CrimeCategory
    from backend.app.models.crime_location import CrimeLocation
    from backend.app.models.crime_report import CrimeReport
    from backend.app.models.investigation import Investigation
    from backend.app.models.investigation_note import InvestigationNote
    from backend.app.models.investigation_assignment import InvestigationAssignment
    from backend.app.models.investigation_timeline import InvestigationTimeline
    from backend.app.models.evidence import Evidence
    from backend.app.models.prediction import Prediction
    from backend.app.models.audit_log import AuditLog

    print("=" * 65)
    print("  CrimeLens AI — Comprehensive Dataset Seeder")
    print("=" * 65)

    # Load CSV
    csv_path = ROOT / "Dataset" / "crime_dataset_india.csv"
    if not csv_path.exists():
        csv_path = ROOT / "datasets" / "raw" / "crime_dataset_india.csv"
    print(f"\n[LOAD] Reading {csv_path.name}...")
    csv_rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 500:
                break
            csv_rows.append(row)
    print(f"       {len(csv_rows)} records loaded")

    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
        print("[OK]   Database connection verified\n")

        # ── 1. USERS ──────────────────────────────────────────────────────
        print("[1/10] Resolving users...")
        res = await session.execute(select(User.id, User.email))
        all_users = list(res.all())
        if not all_users:
            print("       ERROR: No users found. Run seed_db.py first.")
            return

        admin_id     = next((uid for uid, e in all_users if "admin" in e), all_users[0][0])
        investigators = [uid for uid, e in all_users if "inv" in e or "investigator" in e] or [all_users[0][0]]
        officers      = [uid for uid, e in all_users if "officer" in e or "priya" in e or "suresh" in e] or [all_users[0][0]]
        all_user_ids  = [uid for uid, _ in all_users]
        print(f"       {len(all_users)} users: {len(investigators)} investigators, {len(officers)} officers")

        # ── 2. CATEGORIES ─────────────────────────────────────────────────
        print("\n[2/10] Ensuring crime categories...")
        cat_rows = []
        for name, (sev, color, desc) in CATEGORY_DEFS.items():
            cat_rows.append({
                "id": _uid(f"cat:v2:{name}"),
                "name": name, "description": desc, "severity_level": sev, "color_code": color,
                "created_at": NOW - timedelta(days=500),
                "updated_at": NOW - timedelta(days=500),
                "deleted_at": None,
            })
        ins = await _upsert(session, CrimeCategory.__table__, cat_rows, ["name"])
        await session.commit()
        res = await session.execute(select(CrimeCategory.id, CrimeCategory.name))
        cat_map: dict[str, uuid.UUID] = {name: cid for cid, name in res.all()}
        print(f"       {len(cat_map)} categories ({ins} new)")

        # ── 3. LOCATIONS ──────────────────────────────────────────────────
        print("\n[3/10] Seeding crime locations...")
        cities = list({row["City"] for row in csv_rows if row["City"] in CITY_GEO})
        loc_rows = []
        for city in cities:
            for idx in range(6):          # 6 distinct locations per city
                loc_rows.append(make_loc(city, idx))
        ins = await _upsert(session, CrimeLocation.__table__, loc_rows, ["id"])
        await session.commit()

        res = await session.execute(select(CrimeLocation.id, CrimeLocation.city))
        city_locs: dict[str, list[uuid.UUID]] = {}
        for lid, lcity in res.all():
            city_locs.setdefault(lcity, []).append(lid)
        all_loc_ids = [lid for lids in city_locs.values() for lid in lids]
        print(f"       {len(all_loc_ids)} locations across {len(city_locs)} cities ({ins} new)")

        # ── 4. CRIME REPORTS ──────────────────────────────────────────────
        print("\n[4/10] Seeding crime reports...")
        report_rows = []
        report_meta = []
        seq = 2000   # start seq beyond existing CR numbers

        for i, row in enumerate(csv_rows):
            crime_desc = row.get("Crime Description", "").strip().upper()
            city       = row.get("City", "").strip()
            cat_name   = CRIME_DESC_TO_CAT.get(crime_desc)
            if not cat_name or cat_name not in cat_map:
                continue
            if city not in city_locs:
                continue

            loc_id     = city_locs[city][i % len(city_locs[city])]
            cat_id     = cat_map[cat_name]
            incident_dt = parse_dt(row.get("Date of Occurrence", ""))
            report_dt   = parse_dt(row.get("Date Reported", ""))
            if report_dt < incident_dt:
                report_dt = incident_dt + timedelta(hours=random.randint(1, 48))

            closed      = row.get("Case Closed", "No").strip().lower() == "yes"
            if closed:
                status = random.choice(["CLOSED", "CLOSED", "ARCHIVED"])
            else:
                status = random.choice(["OPEN", "OPEN", "UNDER_INVESTIGATION", "UNDER_INVESTIGATION"])

            prio = PRIORITY_MAP.get(crime_desc, "MEDIUM")
            domain = row.get("Crime Domain", "Other Crime")
            if domain == "Violent Crime" and prio == "MEDIUM":
                prio = "HIGH"

            victim_age = int(float(row.get("Victim Age", "30") or "30"))
            gender_word = {"M": "male", "F": "female", "X": "unidentified"}.get(
                row.get("Victim Gender", "M").strip(), "unknown")
            weapon = row.get("Weapon Used", "unidentified").strip() or "unidentified"
            try:
                police_count = int(float(row.get("Police Deployed", "5") or "5"))
            except Exception:
                police_count = random.randint(1, 20)

            loss_min, loss_max = LOSS_RANGE.get(crime_desc, (0, 50_000))
            estimated_loss = round(random.uniform(loss_min, loss_max), 2)

            reporter_id = officers[i % len(officers)]
            seq += 1
            cr_num = f"CR-{incident_dt.year}-{str(seq).zfill(6)}"
            rid    = _uid(f"csv:report:{i}:{cr_num}")

            description = (
                f"A {crime_desc.lower()} incident was reported in {city}. "
                f"Victim: {victim_age}-year-old {gender_word}. "
                f"Weapon: {weapon}. Police deployed: {police_count}. "
                f"Domain: {domain}. "
                f"Estimated financial impact: INR {estimated_loss:,.0f}."
            )

            report_rows.append({
                "id": rid,
                "crime_number": cr_num,
                "title": f"{city} — {crime_desc.title()} (Case {seq})",
                "description": description,
                "incident_date": incident_dt,
                "report_date": report_dt,
                "status": status,
                "priority": prio,
                "victim_count": random.randint(1, 3),
                "suspect_count": random.randint(0, 3),
                "estimated_loss": estimated_loss,
                "reporter_id": reporter_id,
                "category_id": cat_id,
                "location_id": loc_id,
                "created_at": report_dt,
                "updated_at": NOW - timedelta(days=random.randint(0, 30)),
                "deleted_at": None,
            })
            report_meta.append({
                "id": rid, "crime_number": cr_num, "crime_desc": crime_desc,
                "city": city, "incident_date": incident_dt, "status": status,
                "priority": prio, "closed": closed, "reporter_id": reporter_id,
            })

        ins = await _upsert(session, CrimeReport.__table__, report_rows, ["crime_number"])
        await session.commit()

        # Resolve actual DB ids
        res = await session.execute(
            select(CrimeReport.id, CrimeReport.crime_number).where(
                CrimeReport.crime_number.in_([r["crime_number"] for r in report_rows])
            )
        )
        cr_num_map = {cn: cid for cid, cn in res.all()}
        resolved = [{**m, "id": cr_num_map.get(m["crime_number"], m["id"])} for m in report_meta if m["crime_number"] in cr_num_map]
        print(f"       {len(resolved)} crime reports ({ins} new)")

        # ── 5. INVESTIGATIONS ─────────────────────────────────────────────
        print("\n[5/10] Seeding investigations...")
        inv_rows = []
        inv_meta = []

        # Investigate ~65% of reports — prioritise higher priority
        to_investigate = [r for r in resolved if r["priority"] in ("CRITICAL", "HIGH", "MEDIUM") or not r["closed"]]
        random.shuffle(to_investigate)
        to_investigate = to_investigate[:320]

        for j, rm in enumerate(to_investigate):
            inv_id = _uid(f"csv:inv:{j}:{rm['crime_number']}")
            inv_id_str = str(inv_id)
            investigator_id = investigators[j % len(investigators)]
            assigned_dt     = rm["incident_date"] + timedelta(days=random.randint(1, 5))

            if rm["closed"]:
                inv_status  = random.choice(["CLOSED", "CLOSED", "ARCHIVED"])
                closed_at   = rm["incident_date"] + timedelta(days=random.randint(30, 180))
                resolution  = random.choice(RESOLUTIONS).replace("{n}", str(random.randint(1, 7)))
            elif rm["status"] == "UNDER_INVESTIGATION":
                inv_status  = random.choice(["UNDER_INVESTIGATION", "WAITING_FOR_EVIDENCE", "ON_HOLD"])
                closed_at   = None
                resolution  = None
            else:
                inv_status  = "OPEN"
                closed_at   = None
                resolution  = None

            inv_rows.append({
                "id": inv_id,
                "report_id": rm["id"],
                "investigator_id": investigator_id,
                "notes": f"Case opened for {rm['crime_desc'].lower()} in {rm['city']}. Priority: {rm['priority']}.",
                "status": inv_status,
                "priority": rm["priority"],
                "assigned_at": assigned_dt,
                "closed_at": closed_at,
                "resolution_summary": resolution,
                "created_at": assigned_dt,
                "updated_at": NOW - timedelta(days=random.randint(0, 10)),
                "deleted_at": None,
            })
            inv_meta.append({
                "id": inv_id, "report_id": rm["id"], "investigator_id": investigator_id,
                "city": rm["city"], "crime_desc": rm["crime_desc"],
                "status": inv_status, "priority": rm["priority"],
                "assigned_dt": assigned_dt,
            })

        ins = await _upsert(session, Investigation.__table__, inv_rows, ["id"])
        await session.commit()
        print(f"       {len(inv_meta)} investigations ({ins} new)")

        # ── 6. ASSIGNMENTS ────────────────────────────────────────────────
        print("\n[6/10] Seeding investigation assignments...")
        assign_rows = []
        for k, im in enumerate(inv_meta[:250]):
            assign_rows.append({
                "id": _uid(f"csv:assign:{k}:{str(im['id'])}"),
                "investigation_id": im["id"],
                "investigator_id":  im["investigator_id"],
                "assigned_by":      admin_id,
                "assigned_at":      im["assigned_dt"],
                "unassigned_at":    None,
                "reason": f"Assigned based on caseload and expertise in {im['crime_desc'].lower()} cases.",
                "is_active": im["status"] not in ("CLOSED", "ARCHIVED"),
                "created_at": im["assigned_dt"],
                "updated_at": NOW,
                "deleted_at": None,
            })
        ins = await _upsert(session, InvestigationAssignment.__table__, assign_rows, ["id"])
        await session.commit()
        print(f"       {len(assign_rows)} assignments ({ins} new)")

        # ── 7. INVESTIGATION NOTES ────────────────────────────────────────
        print("\n[7/10] Seeding investigation notes...")
        note_rows = []
        for n, im in enumerate(inv_meta):
            num = random.randint(2, 4)
            for ni in range(num):
                tmpl = INV_NOTES[(n + ni) % len(INV_NOTES)]
                text_note = tmpl.replace("{n}", str(random.randint(2, 8))).replace("{city}", im["city"])
                note_dt = im["assigned_dt"] + timedelta(days=ni * random.randint(2, 8))
                if note_dt > NOW:
                    note_dt = NOW - timedelta(hours=1)
                note_rows.append({
                    "id": _uid(f"csv:note:{n}:{ni}:{str(im['id'])}"),
                    "investigation_id": im["id"],
                    "author_id": im["investigator_id"] if ni % 2 == 0 else random.choice(all_user_ids),
                    "note": text_note,
                    "attachment_evidence_id": None,
                    "edited": random.random() < 0.12,
                    "created_at": note_dt,
                    "updated_at": note_dt,
                    "deleted_at": None,
                })
        ins = await _upsert(session, InvestigationNote.__table__, note_rows, ["id"])
        await session.commit()
        print(f"       {len(note_rows)} notes ({ins} new)")

        # ── 8. TIMELINE EVENTS ────────────────────────────────────────────
        print("\n[8/10] Seeding investigation timeline events...")
        tl_rows = []
        for ti, im in enumerate(inv_meta[:280]):
            num_events = random.randint(2, 5)
            pool = random.sample(TIMELINE_ACTIONS, min(num_events, len(TIMELINE_ACTIONS)))
            ev_dt = im["assigned_dt"]
            for ei, (action, base_desc) in enumerate(pool):
                ev_dt = ev_dt + timedelta(days=random.randint(1, 10))
                if ev_dt > NOW:
                    break
                tl_rows.append({
                    "id": _uid(f"csv:tl:{ti}:{ei}:{str(im['id'])}"),
                    "investigation_id": im["id"],
                    "action": action,
                    "description": f"{base_desc} [{im['city']} — {im['crime_desc'].title()}]",
                    "performed_by": im["investigator_id"] if ei % 2 == 0 else random.choice(all_user_ids),
                    "metadata": {"city": im["city"], "crime_type": im["crime_desc"], "priority": im["priority"]},
                    "created_at": ev_dt,
                    "updated_at": ev_dt,
                    "deleted_at": None,
                })
        ins = await _upsert(session, InvestigationTimeline.__table__, tl_rows, ["id"])
        await session.commit()
        print(f"       {len(tl_rows)} timeline events ({ins} new)")

        # ── 9. EVIDENCE ───────────────────────────────────────────────────
        print("\n[9/10] Seeding evidence records...")
        ev_rows = []
        for ei, rm in enumerate(resolved):
            ev_types   = CRIME_EVIDENCE_MAP.get(rm["crime_desc"], ["FIR", "Photo"])
            num        = random.randint(1, min(len(ev_types), 4))
            selected   = random.sample(ev_types, num)
            uploader   = random.choice(investigators)

            for eti, etype in enumerate(selected):
                tmpl_fname, ftype, mime, ext, (szmin, szmax) = EVIDENCE_TEMPLATES[etype]
                seq_n = ei * 10 + eti
                fname = tmpl_fname.replace("{seq}", str(seq_n))
                fsize = random.randint(szmin, szmax)
                chk   = hashlib.md5(f"{rm['crime_number']}{fname}".encode()).hexdigest()
                up_dt = rm["incident_date"] + timedelta(hours=random.randint(2, 72))
                if up_dt > NOW:
                    up_dt = NOW - timedelta(hours=1)

                ev_rows.append({
                    "id": _uid(f"csv:ev:{ei}:{eti}:{fname}"),
                    "report_id":    rm["id"],
                    "uploaded_by":  uploader,
                    "description":  f"{etype} for {rm['crime_desc'].lower()} — {rm['crime_number']} ({rm['city']})",
                    "file_name":    fname,
                    "file_type":    ftype,
                    "mime_type":    mime,
                    "file_size":    fsize * 1024,
                    "file_url":     f"https://storage.crimelens.demo/evidence/dataset/{fname}",
                    "storage_path": f"evidence/dataset/{fname}",
                    "bucket_name":  "evidence",
                    "checksum":     chk,
                    "file_extension": ext,
                    "uploaded_at":  up_dt,
                    "created_at":   up_dt,
                    "updated_at":   up_dt,
                    "deleted_at":   None,
                })
        ins = await _upsert(session, Evidence.__table__, ev_rows, ["id"])
        await session.commit()
        print(f"       {len(ev_rows)} evidence records ({ins} new)")

        # ── 10. PREDICTIONS ───────────────────────────────────────────────
        print("\n[10/10] Seeding AI predictions...")
        pred_rows = []
        for pi, rm in enumerate(resolved):
            cd    = rm["crime_desc"]
            conf  = confidence_for(cd)
            label = CRIME_TYPE_LABELS.get(cd, cd.title())
            prio_idx = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}.get(rm["priority"], 2)
            pred_dt  = rm["incident_date"] + timedelta(hours=random.randint(4, 24))
            if pred_dt > NOW:
                pred_dt = NOW - timedelta(hours=1)

            # Crime-type classification
            pred_rows.append({
                "id": _uid(f"csv:pred:type:{pi}:{rm['crime_number']}"),
                "report_id": rm["id"],
                "user_id":   rm["reporter_id"],
                "prediction_label": label,
                "prediction_type":  "CRIME_TYPE",
                "confidence_score": conf,
                "model_name":    "EnsembleClassifier",
                "model_version": "v1.0.0",
                "prediction_time": pred_dt,
                "execution_time_ms": random.randint(45, 280),
                "explanation": f"High-confidence classification based on crime pattern, location ({rm['city']}), weapon type, and temporal features.",
                "raw_output": {
                    "top_prediction": label, "confidence": conf,
                    "city": rm["city"], "crime_number": rm["crime_number"],
                    "features_used": ["city", "time_of_day", "weapon_type", "victim_profile"],
                },
                "created_at": pred_dt, "updated_at": pred_dt, "deleted_at": None,
            })

            # Risk score (~40%)
            if pi % 3 == 0:
                risk_label = RISK_LABELS[min(prio_idx, 4)]
                pred_rows.append({
                    "id": _uid(f"csv:pred:risk:{pi}:{rm['crime_number']}"),
                    "report_id": rm["id"],
                    "user_id":   rm["reporter_id"],
                    "prediction_label": risk_label,
                    "prediction_type":  "RISK_SCORE",
                    "confidence_score": round(random.uniform(0.70, 0.95), 4),
                    "model_name":    "CrimeEmbeddingNetwork",
                    "model_version": "v1.0.0",
                    "prediction_time": pred_dt + timedelta(minutes=5),
                    "execution_time_ms": random.randint(100, 350),
                    "explanation": f"Risk assessment for {rm['city']} zone based on recent crime trends and historical density.",
                    "raw_output": {
                        "risk_level": risk_label,
                        "risk_score": round(prio_idx / 4.0 + random.uniform(-0.1, 0.1), 4),
                        "city": rm["city"],
                        "factors": ["historical_density", "time_factor", "crime_severity"],
                    },
                    "created_at": pred_dt + timedelta(minutes=5),
                    "updated_at": pred_dt + timedelta(minutes=5),
                    "deleted_at": None,
                })

            # Hotspot (~25%)
            if pi % 5 == 0:
                hl = HOTSPOT_LABELS[min(prio_idx, 4)]
                pred_rows.append({
                    "id": _uid(f"csv:pred:hotspot:{pi}:{rm['crime_number']}"),
                    "report_id": rm["id"],
                    "user_id":   None,
                    "prediction_label": hl,
                    "prediction_type":  "HOTSPOT",
                    "confidence_score": round(random.uniform(0.68, 0.93), 4),
                    "model_name":    "CityHotspotCNN",
                    "model_version": "v1.0.0",
                    "prediction_time": pred_dt + timedelta(minutes=10),
                    "execution_time_ms": random.randint(200, 600),
                    "explanation": f"Spatial clustering model classifies {rm['city']} zone as '{hl}' based on incident density.",
                    "raw_output": {
                        "zone_classification": hl, "city": rm["city"],
                        "heat_index": round(prio_idx * 0.25 + random.uniform(0, 0.2), 4),
                    },
                    "created_at": pred_dt + timedelta(minutes=10),
                    "updated_at": pred_dt + timedelta(minutes=10),
                    "deleted_at": None,
                })

        ins = await _upsert(session, Prediction.__table__, pred_rows, ["id"])
        await session.commit()
        print(f"       {len(pred_rows)} predictions ({ins} new)")

        # ── AUDIT LOGS ────────────────────────────────────────────────────
        print("\n[+]    Seeding audit logs...")
        audit_rows = []
        for ai, rm in enumerate(resolved[:200]):
            audit_rows.append({
                "id": _uid(f"csv:audit:report:{ai}:{rm['crime_number']}"),
                "action": "CRIME_REPORT_CREATED",
                "entity_type": "crime_report",
                "entity_id": rm["id"],
                "details": {"crime_number": rm["crime_number"], "city": rm["city"],
                            "type": rm["crime_desc"], "priority": rm["priority"], "source": "dataset_seed"},
                "ip_address": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
                "user_agent": "CrimeLens-OfficerApp/2.1",
                "user_id": rm["reporter_id"],
                "created_at": rm["incident_date"],
                "updated_at": rm["incident_date"],
                "deleted_at": None,
            })
        for ai, im in enumerate(inv_meta[:150]):
            audit_rows.append({
                "id": _uid(f"csv:audit:inv:{ai}:{str(im['id'])}"),
                "action": "INVESTIGATION_ASSIGNED",
                "entity_type": "investigation",
                "entity_id": im["id"],
                "details": {"city": im["city"], "crime_type": im["crime_desc"],
                            "status": im["status"], "source": "dataset_seed"},
                "ip_address": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
                "user_agent": "CrimeLens-AdminPanel/2.1",
                "user_id": admin_id,
                "created_at": im["assigned_dt"],
                "updated_at": im["assigned_dt"],
                "deleted_at": None,
            })

        ins = await _upsert(session, AuditLog.__table__, audit_rows, ["id"])
        await session.commit()
        print(f"       {len(audit_rows)} audit logs ({ins} new)")

        # ── SUMMARY ───────────────────────────────────────────────────────
        print("\n" + "=" * 65)
        print("SEED COMPLETE — Final Record Counts:")
        print("=" * 65)
        for tbl in ["users", "crime_categories", "crime_locations",
                    "crime_reports", "investigations", "investigation_assignments",
                    "investigation_notes", "investigation_timeline",
                    "evidence", "predictions", "audit_logs"]:
            n = await _count(session, tbl)
            print(f"   {tbl:<34} {n:>6} records")
        print("=" * 65)
        print("\n[DONE] CrimeLens AI database fully populated with dataset.")
        print("       Frontend : http://localhost:5173/  (or 5174)")
        print("       API Docs : http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(seed())
