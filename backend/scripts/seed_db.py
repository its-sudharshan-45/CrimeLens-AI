# -*- coding: utf-8 -*-
# cspell:disable
import sys, io
# Force UTF-8 output so emoji/Unicode print statements work on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

"""
CrimeLens AI — Idempotent Database Seed Script
===============================================
Populates all application tables with realistic synthetic demo data.

Run from the repository root:
    python -m backend.scripts.seed_db

Safe to run multiple times — uses ON CONFLICT DO NOTHING / select-then-skip
for every entity so no duplicate records are ever created.

Seed order (respects FK dependencies):
  1. Seed Users (synthetic — NOT real Supabase auth accounts)
  2. Crime Categories
  3. Crime Locations
  4. Crime Reports
  5. Investigations
  6. Investigation Notes
  7. Evidence (metadata only — no file uploads)
  8. Audit Logs (setup events)
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Allow running as `python -m backend.scripts.seed_db` from repo root ─────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.app.db.session import AsyncSessionLocal
from backend.app.core.enums.crime_status import CrimeStatus
from backend.app.core.enums.priority import Priority
from backend.app.core.enums.evidence_type import EvidenceType
from backend.app.core.enums.investigation_status import InvestigationStatus

# ── Deterministic namespace for idempotent UUIDs ─────────────────────────────
_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def _uid(name: str) -> uuid.UUID:
    """Return a stable UUID derived from *name* — same every run."""
    return uuid.uuid5(_NS, name)


def utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc)


def days_ago(n: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=n)


# Legacy demo statuses → current InvestigationStatus enum values
_LEGACY_INVESTIGATION_STATUS = {
    "IN_PROGRESS": InvestigationStatus.UNDER_INVESTIGATION.value,
    "ASSIGNED": InvestigationStatus.OPEN.value,
    "COMPLETED": InvestigationStatus.CLOSED.value,
}


def normalize_investigation_status(status: str) -> str:
    return _LEGACY_INVESTIGATION_STATUS.get(status, status)


# ═════════════════════════════════════════════════════════════════════════════
# 1. SEED USERS  (synthetic — supabase_user_id is a local-only UUID)
# ═════════════════════════════════════════════════════════════════════════════
SEED_USERS = [
    {
        "id": _uid("user:admin"),
        "supabase_user_id": _uid("supabase:admin"),
        "email": "admin@crimelens.demo",
        "full_name": "Arjun Sharma",
        "badge_number": "ADM-001",
        "department": "Administration",
        "is_active": True,
        "email_verified": True,
    },
    {
        "id": _uid("user:officer1"),
        "supabase_user_id": _uid("supabase:officer1"),
        "email": "officer.priya@crimelens.demo",
        "full_name": "Priya Nair",
        "badge_number": "MUM-1042",
        "department": "Mumbai Police — Zone IV",
        "is_active": True,
        "email_verified": True,
    },
    {
        "id": _uid("user:investigator1"),
        "supabase_user_id": _uid("supabase:investigator1"),
        "email": "inv.rahul@crimelens.demo",
        "full_name": "Rahul Verma",
        "badge_number": "DEL-3317",
        "department": "Delhi Crime Branch",
        "is_active": True,
        "email_verified": True,
    },
    {
        "id": _uid("user:analyst1"),
        "supabase_user_id": _uid("supabase:analyst1"),
        "email": "analyst.meena@crimelens.demo",
        "full_name": "Meena Krishnamurthy",
        "badge_number": "BLR-0891",
        "department": "Bangalore Analytics Cell",
        "is_active": True,
        "email_verified": True,
    },
    {
        "id": _uid("user:officer2"),
        "supabase_user_id": _uid("supabase:officer2"),
        "email": "officer.suresh@crimelens.demo",
        "full_name": "Suresh Patel",
        "badge_number": "AHM-2205",
        "department": "Ahmedabad Police — North",
        "is_active": True,
        "email_verified": True,
    },
    {
        "id": _uid("user:investigator2"),
        "supabase_user_id": _uid("supabase:investigator2"),
        "email": "inv.kavitha@crimelens.demo",
        "full_name": "Kavitha Reddy",
        "badge_number": "HYD-4421",
        "department": "Hyderabad SIT",
        "is_active": True,
        "email_verified": True,
    },
]

# ═════════════════════════════════════════════════════════════════════════════
# 3. CRIME CATEGORIES
# ═════════════════════════════════════════════════════════════════════════════
CATEGORIES = [
    ("Assault", "Physical attack causing bodily harm to another person.", 4, "#EF4444"),
    ("Arson", "Deliberate setting fire to property or land.", 5, "#F97316"),
    ("Burglary", "Unlawful entry into a building with intent to commit a crime.", 4, "#F59E0B"),
    ("Counterfeiting", "Production or use of forged currency, documents or goods.", 3, "#84CC16"),
    ("Cybercrime", "Criminal activities conducted via computers or the internet.", 4, "#06B6D4"),
    ("Domestic Violence", "Abuse or violence within a domestic or family setting.", 4, "#8B5CF6"),
    ("Drug Offense", "Illegal production, distribution, or possession of controlled substances.", 4, "#EC4899"),
    ("Extortion", "Obtaining money or services through threats or coercion.", 4, "#14B8A6"),
    ("Firearm Offense", "Illegal possession, use, or trafficking of firearms.", 5, "#DC2626"),
    ("Fraud", "Deception for financial gain or other personal advantage.", 3, "#2563EB"),
    ("Homicide", "Unlawful killing of a human being.", 5, "#991B1B"),
    ("Identity Theft", "Fraudulent acquisition and use of another person's identity.", 3, "#7C3AED"),
    ("Illegal Possession", "Unlawful possession of prohibited items or substances.", 3, "#D97706"),
    ("Kidnapping", "Unlawful seizure and detention of a person against their will.", 5, "#B45309"),
    ("Public Intoxication", "Being visibly intoxicated in a public place.", 1, "#6B7280"),
    ("Robbery", "Taking property by force or threat from a person.", 4, "#EA580C"),
    ("Sexual Assault", "Non-consensual sexual contact or behaviour.", 5, "#BE123C"),
    ("Shoplifting", "Theft of goods from a retail establishment.", 2, "#CA8A04"),
    ("Traffic Violation", "Serious breach of road traffic regulations.", 1, "#65A30D"),
    ("Vandalism", "Deliberate destruction or damage to property.", 2, "#0891B2"),
    ("Vehicle Theft", "Unauthorized taking or attempted taking of a motor vehicle.", 4, "#1D4ED8"),
]

# ═════════════════════════════════════════════════════════════════════════════
# 4. CRIME LOCATIONS
# ═════════════════════════════════════════════════════════════════════════════
LOCATIONS = [
    # (address, landmark, city, district, state, zip_code, lat, lon)
    ("14 Anna Salai", "Near Spencer Plaza Mall", "Chennai", "Chennai", "Tamil Nadu", "600002", 13.0607, 80.2496),
    ("7 Poonamallee High Rd", "Opposite Central Railway Station", "Chennai", "Chennai", "Tamil Nadu", "600003", 13.0827, 80.2707),
    ("23 Marine Drive", "Near Gateway of India", "Mumbai", "Mumbai City", "Maharashtra", "400001", 18.9220, 72.8347),
    ("45 Linking Road, Bandra", "Near Bandra Station", "Mumbai", "Mumbai Suburban", "Maharashtra", "400050", 19.0544, 72.8403),
    ("102 Andheri Kurla Rd", "Behind SEEPZ Gate", "Mumbai", "Mumbai Suburban", "Maharashtra", "400093", 19.1136, 72.8697),
    ("12 MG Road", "Near Central Metro Station", "Bangalore", "Bengaluru Urban", "Karnataka", "560001", 12.9756, 77.6066),
    ("88 Koramangala 4th Block", "Opposite Forum Mall", "Bangalore", "Bengaluru Urban", "Karnataka", "560034", 12.9352, 77.6245),
    ("34 Banjara Hills Rd No 10", "Near Hyderabad Film Nagar", "Hyderabad", "Hyderabad", "Telangana", "500034", 17.4156, 78.4347),
    ("22 Secunderabad Station Rd", "Near Clock Tower", "Hyderabad", "Medchal-Malkajgiri", "Telangana", "500003", 17.4399, 78.4983),
    ("5 Connaught Place", "Near Rajiv Chowk Metro", "Delhi", "Central Delhi", "Delhi", "110001", 28.6315, 77.2167),
    ("78 Lajpat Nagar Market", "Near Ring Road Flyover", "Delhi", "South Delhi", "Delhi", "110024", 28.5672, 77.2430),
    ("31 Karol Bagh Main Rd", "Near Ajmal Khan Park", "Delhi", "West Delhi", "Delhi", "110005", 28.6517, 77.1900),
    ("15 Park Street", "Near Victoria Memorial", "Kolkata", "Kolkata", "West Bengal", "700016", 22.5535, 88.3510),
    ("67 Salt Lake Sector V", "Near IT Hub Gate", "Kolkata", "North 24 Parganas", "West Bengal", "700091", 22.5705, 88.4337),
    ("9 FC Road", "Near Shivajinagar Bus Stand", "Pune", "Pune", "Maharashtra", "411005", 18.5314, 73.8446),
    ("44 Aundh Main Rd", "Near D-Mart Aundh", "Pune", "Pune", "Maharashtra", "411007", 18.5590, 73.8075),
    ("3 MI Road", "Near Ajmer Gate", "Jaipur", "Jaipur", "Rajasthan", "302001", 26.9124, 75.7873),
    ("56 Vastrapur Lake Rd", "Near Ahmedabad Municipal Office", "Ahmedabad", "Ahmedabad", "Gujarat", "380054", 23.0380, 72.5290),
    ("18 Hazratganj", "Near Raj Bhawan", "Lucknow", "Lucknow", "Uttar Pradesh", "226001", 26.8567, 80.9462),
    ("27 Vijay Nagar Square", "Near Palasia Police Station", "Indore", "Indore", "Madhya Pradesh", "452010", 22.7196, 75.8577),
    ("11 Sitabuldi", "Near Nagpur Railway Station", "Nagpur", "Nagpur", "Maharashtra", "440012", 21.1458, 79.0882),
    ("39 Ring Road, Adajan", "Near Surat Diamond Bourse", "Surat", "Surat", "Gujarat", "395009", 21.1702, 72.8311),
    ("62 MVP Colony", "Near RK Beach", "Visakhapatnam", "Visakhapatnam", "Andhra Pradesh", "530017", 17.7231, 83.3012),
    ("8 Patna Junction Rd", "Near Gandhi Maidan", "Patna", "Patna", "Bihar", "800001", 25.6120, 85.1376),
    ("19 Arera Colony", "Near DB Mall", "Bhopal", "Bhopal", "Madhya Pradesh", "462016", 23.2599, 77.4126),
    ("25 Civil Lines", "Near Kanpur Central Station", "Kanpur", "Kanpur Nagar", "Uttar Pradesh", "208001", 26.4499, 80.3319),
    ("4 Taj Nagari Phase 2", "Near Taj Mahal East Gate", "Agra", "Agra", "Uttar Pradesh", "282001", 27.1767, 78.0081),
    ("71 College Road", "Near Nashik Road Station", "Nashik", "Nashik", "Maharashtra", "422005", 19.9975, 73.7898),
    ("53 Kalavad Road", "Near Rajkot Airport", "Rajkot", "Rajkot", "Gujarat", "360005", 22.3039, 70.8022),
    ("16 Hapur Road", "Near Meerut Cantt Station", "Meerut", "Meerut", "Uttar Pradesh", "250001", 28.9845, 77.7064),
    ("30 Ferozepur Road", "Near Ludhiana Bus Stand", "Ludhiana", "Ludhiana", "Punjab", "141001", 30.9010, 75.8573),
    ("48 Old Faridabad Sector 16", "Near Faridabad NIT Market", "Faridabad", "Faridabad", "Haryana", "121002", 28.4089, 77.3178),
    ("13 Kavi Nagar", "Near Ghaziabad Collectorate", "Ghaziabad", "Ghaziabad", "Uttar Pradesh", "201002", 28.6692, 77.4538),
    ("6 Kalyan Station Rd", "Near Kalyan Court", "Kalyan", "Thane", "Maharashtra", "421301", 19.2403, 73.1305),
    ("91 Ghodbunder Road", "Near Thane Station", "Thane", "Thane", "Maharashtra", "400601", 19.1972, 72.9620),
    ("2 Residency Road", "Near Srinagar Police Headquarters", "Srinagar", "Srinagar", "Jammu & Kashmir", "190001", 34.0837, 74.7973),
    ("37 Godowlia Chowk", "Near Kashi Vishwanath Temple", "Varanasi", "Varanasi", "Uttar Pradesh", "221001", 25.3176, 82.9739),
    ("21 Vasai Road West", "Near Vasai Railway Station", "Vasai", "Palghar", "Maharashtra", "401202", 19.3919, 72.8397),
]

# ═════════════════════════════════════════════════════════════════════════════
# 5. CRIME REPORTS  (60 records)
# ═════════════════════════════════════════════════════════════════════════════
# Format: (title, description, cat_name, loc_index, priority, status,
#           victim_count, suspect_count, estimated_loss, days_ago_incident)
RAW_REPORTS = [
    # ── Vehicle Theft ──
    ("Motorcycle Theft Near Central Market",
     "A Honda Activa scooter was reported stolen from the parking area outside Central Market. CCTV footage shows two suspects cutting the chain lock at 02:15 hrs.",
     "Vehicle Theft", 0, "HIGH", "UNDER_INVESTIGATION", 1, 2, 85000.0, 3),
    ("Car Theft from Residential Parking",
     "Owner reported a Maruti Swift missing from the basement parking of their apartment complex. No signs of forced entry to the building.",
     "Vehicle Theft", 3, "HIGH", "OPEN", 1, 1, 550000.0, 11),
    ("Bike Theft Outside Railway Station",
     "A Royal Enfield Bullet 350 was stolen from the two-wheeler parking zone. Victim had locked the ignition but chain lock was not used.",
     "Vehicle Theft", 9, "MEDIUM", "OPEN", 1, 0, 175000.0, 21),
    # ── Cybercrime ──
    ("Online Banking Fraud via OTP Phishing",
     "Victim received a call from an individual posing as a bank official. Caller obtained OTP under false pretext and transferred ₹75,000 from savings account.",
     "Cybercrime", 5, "HIGH", "UNDER_INVESTIGATION", 1, 1, 75000.0, 7),
    ("Social Media Account Hacked for Extortion",
     "Victim's Instagram account was compromised. Perpetrator accessed private photos and demanded ₹50,000 to prevent sharing.",
     "Cybercrime", 6, "HIGH", "OPEN", 1, 1, 50000.0, 14),
    ("E-Commerce Fraud — Fake Seller",
     "Complainant paid ₹32,000 for a laptop advertised on OLX. Seller disappeared after receiving payment. No product delivered.",
     "Cybercrime", 11, "MEDIUM", "OPEN", 1, 1, 32000.0, 28),
    ("Ransomware Attack on SME Office",
     "A small manufacturing firm's internal servers were encrypted. Attackers demanded ₹5,00,000 in Bitcoin for decryption keys.",
     "Cybercrime", 14, "CRITICAL", "UNDER_INVESTIGATION", 0, 0, 500000.0, 5),
    # ── Burglary ──
    ("Residential Burglary — Andheri West",
     "Family returned from vacation to find their flat burglarized. Television, jewellery worth ₹1,50,000 and ₹20,000 cash stolen. Lock tampered.",
     "Burglary", 4, "HIGH", "UNDER_INVESTIGATION", 2, 0, 170000.0, 9),
    ("Shop Burglary After Hours",
     "A mobile accessories shop was broken into between 23:00 and 05:00. Display stock valued at ₹85,000 was removed.",
     "Burglary", 7, "HIGH", "OPEN", 0, 0, 85000.0, 33),
    ("Office Break-In — IT Firm",
     "An IT office was burgled over a weekend. Three laptops and petty cash of ₹15,000 were stolen. Rear glass panel broken.",
     "Burglary", 10, "MEDIUM", "CLOSED", 0, 1, 210000.0, 60),
    # ── Assault ──
    ("Street Fight Near Bus Stand",
     "Two groups clashed outside the main bus stand following a road-rage incident. Three persons sustained minor injuries. Weapons: iron rods.",
     "Assault", 12, "HIGH", "UNDER_INVESTIGATION", 3, 5, 0.0, 2),
    ("Bar Brawl — Banjara Hills",
     "A physical altercation broke out inside a pub at 23:30. One victim sustained a fractured nose. Security footage recovered.",
     "Assault", 7, "MEDIUM", "CLOSED", 1, 3, 0.0, 45),
    ("Domestic Dispute Turned Violent",
     "Neighbours intervened in a domestic dispute where the husband assaulted his wife with a belt. Victim admitted for treatment.",
     "Assault", 15, "HIGH", "OPEN", 1, 1, 0.0, 6),
    # ── Robbery ──
    ("Chain Snatching on Busy Street",
     "A 58-year-old woman's gold chain was snatched by a pillion rider on a motorcycle near the vegetable market. Estimated value: ₹1,20,000.",
     "Robbery", 1, "HIGH", "UNDER_INVESTIGATION", 1, 2, 120000.0, 4),
    ("ATM Robbery at Gunpoint",
     "A customer was robbed of ₹40,000 cash outside an ATM kiosk at 21:00 hrs. Armed suspect fled on bicycle.",
     "Robbery", 9, "CRITICAL", "UNDER_INVESTIGATION", 1, 1, 40000.0, 8),
    ("Taxi Driver Robbed by Passengers",
     "Cab driver was assaulted and robbed by two passengers near an isolated stretch. Cash and phone stolen. Driver hospitalised.",
     "Robbery", 13, "HIGH", "OPEN", 1, 2, 25000.0, 19),
    # ── Fraud ──
    ("Real Estate Fraud — Fake Documents",
     "Complainant paid ₹8,00,000 as advance for a flat. Seller provided forged NOC and sale deed. Property belongs to another party.",
     "Fraud", 16, "CRITICAL", "UNDER_INVESTIGATION", 1, 2, 800000.0, 15),
    ("Job Offer Scam",
     "Victim paid ₹45,000 in processing fees to a fraudulent placement agency. Company address was found to be fake.",
     "Fraud", 17, "MEDIUM", "OPEN", 1, 3, 45000.0, 40),
    ("Fake Lottery Fraud",
     "Retired individual defrauded of ₹2,50,000 after being told he won an international lottery. Funds transferred via multiple accounts.",
     "Fraud", 18, "HIGH", "CLOSED", 1, 2, 250000.0, 90),
    # ── Drug Offense ──
    ("Ganja Seizure from Courier Parcel",
     "Narcotics cell intercepted a courier parcel containing 1.2 kg of cannabis at a logistics hub. Sender address found to be fake.",
     "Drug Offense", 6, "HIGH", "UNDER_INVESTIGATION", 0, 1, 0.0, 12),
    ("Methamphetamine Peddler Arrested",
     "Acting on a tip, officers apprehended a street-level dealer carrying 15 sachets of methamphetamine valued at ₹90,000.",
     "Drug Offense", 9, "CRITICAL", "CLOSED", 0, 1, 90000.0, 55),
    ("Drug Den Raid — Slum Area",
     "A shanty operating as a drug distribution point was raided. Three arrested; heroin worth ₹3,50,000 seized.",
     "Drug Offense", 22, "CRITICAL", "UNDER_INVESTIGATION", 0, 3, 350000.0, 25),
    # ── Homicide ──
    ("Suspected Homicide — Industrial Area",
     "Body of an unidentified male discovered near an industrial drainage canal. Cause of death: blunt force trauma. Postmortem ordered.",
     "Homicide", 30, "CRITICAL", "UNDER_INVESTIGATION", 1, 0, 0.0, 18),
    ("Family Murder — Domestic Dispute",
     "Double homicide reported in a residential colony. Preliminary inquiry points to family property dispute. Suspect fled the scene.",
     "Homicide", 11, "CRITICAL", "UNDER_INVESTIGATION", 2, 1, 0.0, 32),
    # ── Domestic Violence ──
    ("Recurring Domestic Abuse — Thane",
     "Complainant reported repeated physical abuse over 6 months. Medical certificates submitted. FIR registered under Section 498A.",
     "Domestic Violence", 34, "HIGH", "UNDER_INVESTIGATION", 1, 1, 0.0, 1),
    ("Dowry Harassment Complaint",
     "Newlywed reported sustained mental and physical abuse by in-laws over dowry demands amounting to ₹5,00,000.",
     "Domestic Violence", 26, "HIGH", "OPEN", 1, 3, 0.0, 10),
    # ── Vandalism ──
    ("CCTV Cameras Smashed at Market",
     "Four surveillance cameras installed by the municipality were deliberately damaged outside the wholesale market. Incident coincides with a robbery the same night.",
     "Vandalism", 0, "MEDIUM", "OPEN", 0, 0, 120000.0, 7),
    ("Car Windows Broken in Parking Lot",
     "Eight vehicles had their windows smashed in an open parking lot. Personal items were stolen from three of them.",
     "Vandalism", 3, "LOW", "CLOSED", 0, 0, 40000.0, 65),
    ("Graffiti on Heritage Building",
     "Obscene graffiti was painted on the exterior wall of a Grade II heritage structure. Archaeological Survey notified.",
     "Vandalism", 36, "LOW", "OPEN", 0, 0, 15000.0, 22),
    # ── Shoplifting ──
    ("Shoplifting at Departmental Store",
     "Store manager detained a suspect who concealed electronics worth ₹18,000 under clothing. CCTV footage available.",
     "Shoplifting", 5, "LOW", "CLOSED", 0, 1, 18000.0, 70),
    ("Repeat Shoplifter Arrested",
     "Individual arrested for the third time for stealing from a supermarket chain. Items concealed in a modified bag.",
     "Shoplifting", 14, "MEDIUM", "CLOSED", 0, 1, 12000.0, 85),
    # ── Kidnapping ──
    ("Child Abduction Near School",
     "An 8-year-old was lured into a vehicle outside school gate. Child recovered within 4 hours after Amber Alert activated. Suspect arrested.",
     "Kidnapping", 15, "CRITICAL", "CLOSED", 1, 1, 0.0, 50),
    ("Ransom Kidnapping — Businessman",
     "Local businessman was abducted from his office car park. Ransom of ₹50,00,000 demanded. Special task force deployed.",
     "Kidnapping", 8, "CRITICAL", "UNDER_INVESTIGATION", 1, 3, 0.0, 38),
    # ── Arson ──
    ("Warehouse Fire — Suspected Arson",
     "A textile warehouse was deliberately set on fire at 03:00 hrs. Loss estimated at ₹22,00,000. Petrol traces found at origin point.",
     "Arson", 21, "CRITICAL", "UNDER_INVESTIGATION", 0, 0, 2200000.0, 20),
    ("Vehicle Set Ablaze — Rival Gang",
     "A truck belonging to a transport firm was set on fire in an open lot. Owner suspects business rivals. CCTV shows hooded figures.",
     "Arson", 29, "HIGH", "OPEN", 0, 0, 800000.0, 43),
    # ── Sexual Assault ──
    ("Sexual Assault in Public Park",
     "Victim reported assault by an unknown individual in a public park at late hours. Medical examination conducted. Forensic evidence collected.",
     "Sexual Assault", 12, "CRITICAL", "UNDER_INVESTIGATION", 1, 0, 0.0, 6),
    ("Workplace Sexual Harassment",
     "Female employee filed complaint against supervisor for repeated harassment over 3 months. Witness statements recorded.",
     "Sexual Assault", 13, "HIGH", "UNDER_INVESTIGATION", 1, 1, 0.0, 27),
    # ── Extortion ──
    ("Small Business Owner Extorted",
     "Restaurant owner received repeated threats demanding ₹50,000 per month as protection money. Two suspects identified from CCTV.",
     "Extortion", 2, "HIGH", "UNDER_INVESTIGATION", 1, 2, 150000.0, 16),
    ("Online Extortion via Email",
     "Victim received emails threatening to expose personal data unless ₹2,00,000 was paid via cryptocurrency.",
     "Extortion", 5, "MEDIUM", "OPEN", 1, 0, 200000.0, 31),
    # ── Firearm Offense ──
    ("Illegal Country-Made Pistol Seized",
     "Routine check at a naka point revealed a country-made pistol and 3 live cartridges concealed in the suspect's vehicle.",
     "Firearm Offense", 10, "CRITICAL", "CLOSED", 0, 1, 0.0, 58),
    ("Gang Shootout — Two Injured",
     "Rival faction clash resulted in two gunshot injuries near an industrial colony. Crude firearms recovered from the scene.",
     "Firearm Offense", 31, "CRITICAL", "UNDER_INVESTIGATION", 2, 4, 0.0, 24),
    # ── Identity Theft ──
    ("Aadhaar-Based Identity Fraud",
     "Fraudster used a cloned Aadhaar card to obtain a SIM card and open a bank account in the victim's name. Loans taken.",
     "Identity Theft", 17, "HIGH", "UNDER_INVESTIGATION", 1, 1, 120000.0, 36),
    ("PAN Card Misuse for Tax Fraud",
     "Victim discovered ITR was filed fraudulently using their PAN. Unknown income sources and refund claims were made.",
     "Identity Theft", 9, "HIGH", "OPEN", 1, 0, 0.0, 42),
    # ── Counterfeiting ──
    ("Fake Currency Notes Seized at Border",
     "Customs and local police jointly seized ₹2,40,000 in high-quality fake currency (₹500 denomination) from a cross-border smuggler.",
     "Counterfeiting", 25, "HIGH", "CLOSED", 0, 2, 240000.0, 75),
    ("Counterfeit Goods Market Busted",
     "A wholesale market stall selling fake branded electronics was raided. Goods worth ₹4,50,000 (MRP) seized.",
     "Counterfeiting", 18, "MEDIUM", "CLOSED", 0, 3, 450000.0, 100),
    # ── Illegal Possession ──
    ("Wildlife Parts Seized",
     "Forest department and police seized illegal wildlife parts (deer antlers, turtle shells) from a transport vehicle.",
     "Illegal Possession", 28, "HIGH", "UNDER_INVESTIGATION", 0, 2, 0.0, 13),
    ("Illegal Alcohol Storage",
     "Municipal inspection revealed 2,000 litres of illegally brewed hooch stored in a residential warehouse.",
     "Illegal Possession", 20, "MEDIUM", "CLOSED", 0, 1, 80000.0, 80),
    # ── Public Intoxication ──
    ("Drunk Driver Causes Minor Collision",
     "Individual tested 0.12 BAC at a check naka. Vehicle had minor collision at a junction. No injuries. DL seized.",
     "Public Intoxication", 14, "LOW", "CLOSED", 0, 1, 25000.0, 5),
    ("Intoxicated Person Creating Public Nuisance",
     "Individual found unconscious near a bus shelter, creating disturbance. Taken into temporary custody for medical examination.",
     "Public Intoxication", 1, "LOW", "CLOSED", 0, 1, 0.0, 30),
    # ── Traffic Violation ──
    ("Hit and Run — Pedestrian Injured",
     "A pedestrian was struck by a speeding vehicle near a school zone at 08:20 hrs. Vehicle fled. CCTV plate partially captured.",
     "Traffic Violation", 11, "HIGH", "UNDER_INVESTIGATION", 1, 0, 0.0, 17),
    ("Overloaded Truck Seized on Highway",
     "Truck carrying 45 tonnes (permitted: 25 tonnes) was intercepted. Driver and owner booked. Vehicle impounded.",
     "Traffic Violation", 25, "LOW", "CLOSED", 0, 2, 0.0, 55),
    # ── Additional reports for analytics variety ──
    ("Phishing SMS Campaign",
     "Multiple victims received SMS mimicking IRCTC seeking login credentials. At least 12 bank accounts reported unauthorized access.",
     "Cybercrime", 9, "HIGH", "UNDER_INVESTIGATION", 12, 0, 180000.0, 35),
    ("Moped Theft — College Area",
     "A moped was stolen from outside a college campus during afternoon hours. Theft occurred in a blind spot.",
     "Vehicle Theft", 5, "LOW", "OPEN", 1, 0, 45000.0, 48),
    ("Attempted Burglary Foiled by Neighbours",
     "Neighbours spotted a suspicious individual prying open a window and alerted police. Suspect fled; tools abandoned at scene.",
     "Burglary", 33, "MEDIUM", "CLOSED", 0, 1, 0.0, 110),
    ("Medical Certificate Forgery",
     "Employer discovered an employee had submitted a forged medical certificate from a non-existent hospital.",
     "Fraud", 14, "LOW", "CLOSED", 0, 1, 5000.0, 120),
    ("Commercial Drug Sale Near School",
     "Acting on a parent complaint, officers arrested a peddler selling narcotics to school students near the school gate.",
     "Drug Offense", 0, "CRITICAL", "UNDER_INVESTIGATION", 0, 1, 0.0, 9),
    ("Domestic Violence — Elderly Abuse",
     "Elderly man reported physical abuse by his adult son over property matters. Medical examination confirmed bruising.",
     "Domestic Violence", 36, "HIGH", "OPEN", 1, 1, 0.0, 4),
    ("Repeated Theft from Construction Site",
     "Construction materials including copper wiring worth ₹95,000 stolen over three consecutive nights.",
     "Burglary", 30, "MEDIUM", "UNDER_INVESTIGATION", 0, 0, 95000.0, 29),
    ("Road Rage Assault",
     "Driver stopped and assaulted another motorist with a steering-wheel lock during a traffic dispute on a flyover.",
     "Assault", 3, "HIGH", "CLOSED", 1, 1, 0.0, 88),
    ("Jewellery Shop Robbery",
     "Masked individuals entered a jewellery shop at opening time, overpowered staff and fled with gold ornaments worth ₹18,00,000.",
     "Robbery", 16, "CRITICAL", "UNDER_INVESTIGATION", 2, 4, 1800000.0, 22),
    ("Cyber Stalking via WhatsApp",
     "Female complainant received persistent threatening messages and morphed images from an anonymous number over 3 weeks.",
     "Cybercrime", 6, "HIGH", "OPEN", 1, 0, 0.0, 11),
]

# ═════════════════════════════════════════════════════════════════════════════
# 6. INVESTIGATIONS  (25 records — linked to reports by index)
# ═════════════════════════════════════════════════════════════════════════════
# Format: (report_index, investigator_key, priority, status, notes, days_since_assigned, resolution)
RAW_INVESTIGATIONS = [
    (0, "user:investigator1", "HIGH", "IN_PROGRESS",
     "CCTV from three angles obtained. Two suspects identified as repeat offenders from prior records.", 3, None),
    (3, "user:investigator1", "HIGH", "IN_PROGRESS",
     "Victim's bank logs obtained. Call records of suspect number under forensic analysis.", 7, None),
    (4, "user:investigator2", "HIGH", "ASSIGNED",
     "Screenshot evidence preserved. Suspect number traced to a prepaid SIM with fake ID.", 14, None),
    (7, "user:investigator1", "HIGH", "IN_PROGRESS",
     "Fingerprints lifted from window frame. Matches one prior case. Forensic lab report awaited.", 9, None),
    (10, "user:investigator2", "MEDIUM", "CLOSED",
     "Suspect identified from CCTV. Confessed during questioning. Items partially recovered.",
     60, "Suspect pleaded guilty. Items valued Rs 1,80,000 recovered. Case closed."),
    (13, "user:investigator1", "HIGH", "IN_PROGRESS",
     "Witness descriptions collected. Motorcycle plate partially captured on CCTV. DMV query raised.", 4, None),
    (14, "user:investigator2", "CRITICAL", "IN_PROGRESS",
     "ATM CCTV footage obtained. Forensic analysis of bicycle tyre marks in progress.", 8, None),
    (16, "user:investigator1", "CRITICAL", "IN_PROGRESS",
     "Documents submitted for forensic verification. Second seller identified; absconding.", 15, None),
    (19, "user:investigator2", "HIGH", "IN_PROGRESS",
     "Courier company records subpoenaed. Origin traced to a border district. NIA consulted.", 12, None),
    (20, "user:investigator1", "CRITICAL", "CLOSED",
     "Suspect arrested in a joint operation with narcotics bureau. All evidence verified.",
     55, "Suspect convicted. Sentenced to 7 years under NDPS Act."),
    (22, "user:investigator2", "CRITICAL", "IN_PROGRESS",
     "Postmortem confirms blunt force trauma. DNA samples sent to CFSL. Missing persons cross-checked.", 18, None),
    (24, "user:investigator1", "HIGH", "IN_PROGRESS",
     "Victim's medical records compiled. Witness statements from neighbours taken.", 1, None),
    (25, "user:investigator2", "HIGH", "IN_PROGRESS",
     "Dowry list documents seized. Social worker appointed for victim support.", 10, None),
    (30, "user:investigator1", "CRITICAL", "CLOSED",
     "Suspect apprehended within 4 hours. Child safely recovered. Charges filed.",
     50, "Suspect sentenced under POCSO Act. Child reunited with family."),
    (31, "user:investigator2", "CRITICAL", "IN_PROGRESS",
     "Negotiation team engaged. Victim's last location traced via mobile tower data.", 38, None),
    (32, "user:investigator1", "CRITICAL", "IN_PROGRESS",
     "Fire origin confirmed as arson via forensic report. Accelerant type: kerosene mixed with petrol.", 20, None),
    (35, "user:investigator2", "CRITICAL", "IN_PROGRESS",
     "Forensic samples collected. Victim's route reconstructed. Park CCTV non-operational.", 6, None),
    (37, "user:investigator1", "HIGH", "IN_PROGRESS",
     "Two suspects identified from CCTV. One suspect has prior extortion record.", 16, None),
    (39, "user:investigator2", "CRITICAL", "CLOSED",
     "Firearm traced to an illegal workshop in a neighbouring state. Two more arrests made.",
     58, "All suspects convicted. Firearms destroyed per court order."),
    (41, "user:investigator1", "HIGH", "IN_PROGRESS",
     "Aadhaar misuse flagged to UIDAI. Bank account frozen. Email trail under analysis.", 36, None),
    (43, "user:investigator2", "HIGH", "CLOSED",
     "Fake notes compared with known counterfeit batches. Printing source identified.",
     75, "Currency forger arrested. Printing press seized."),
    (51, "user:investigator1", "HIGH", "IN_PROGRESS",
     "Phishing domain taken down on coordination with CERT-In. Victim accounts secured.", 35, None),
    (56, "user:investigator2", "CRITICAL", "IN_PROGRESS",
     "School gate CCTV reviewed. Peddler's supply chain under analysis.", 9, None),
    (58, "user:investigator1", "MEDIUM", "IN_PROGRESS",
     "Site night watchman interviewed. Copper wire samples matched to recovered rolls.", 29, None),
    (59, "user:investigator2", "CRITICAL", "IN_PROGRESS",
     "CCTV from shops around the jewellery store pooled. Gold hallmarks recorded for tracking.", 22, None),
]

# ═════════════════════════════════════════════════════════════════════════════
# 7. EVIDENCE  (35 records)
# ═════════════════════════════════════════════════════════════════════════════
# Format: (report_index, description, file_name, file_type, mime_type,
#          file_size_kb, file_extension, checksum_hint, days_ago_upload)
RAW_EVIDENCE = [
    (0, "CCTV footage showing suspects cutting chain lock", "cctv_motorcycle_theft_0145.mp4", "VIDEO", "video/mp4", 51200, "mp4", "a1b2c3", 3),
    (0, "Photograph of cut chain and tyre marks", "crime_scene_photo_001.jpg", "IMAGE", "image/jpeg", 2048, "jpg", "b2c3d4", 3),
    (3, "Bank transaction log showing fraudulent transfers", "bank_statement_victim.pdf", "DOCUMENT", "application/pdf", 512, "pdf", "c3d4e5", 7),
    (3, "Screenshot of phishing call recording transcript", "call_transcript.pdf", "DOCUMENT", "application/pdf", 256, "pdf", "d4e5f6", 7),
    (4, "Screenshot of threatening messages on Instagram", "instagram_threat_screenshots.jpg", "IMAGE", "image/jpeg", 1024, "jpg", "e5f6a7", 14),
    (6, "Encrypted drive image from ransomware-hit server", "server_disk_image.bin", "OTHER", "application/octet-stream", 204800, "bin", "f6a7b8", 5),
    (7, "Fingerprint lift from window frame", "fingerprint_scan_001.jpg", "IMAGE", "image/jpeg", 1536, "jpg", "a7b8c9", 9),
    (7, "Interior photographs of burglarized flat", "flat_crime_scene.jpg", "IMAGE", "image/jpeg", 3072, "jpg", "b8c9d0", 9),
    (10, "Office CCTV showing suspect entering via rear panel", "office_cctv_rear.mp4", "VIDEO", "video/mp4", 25600, "mp4", "c9d0e1", 60),
    (13, "Witness statement from auto-rickshaw driver", "witness_stmt_chain_snatch.pdf", "DOCUMENT", "application/pdf", 128, "pdf", "d0e1f2", 4),
    (14, "ATM CCTV footage — robbery at 21:08", "atm_cctv_robbery.mp4", "VIDEO", "video/mp4", 38400, "mp4", "e1f2a3", 8),
    (16, "Forged sale deed (forensic copy)", "forged_sale_deed.pdf", "DOCUMENT", "application/pdf", 2048, "pdf", "f2a3b4", 15),
    (16, "Forensic analysis report on document ink", "forensic_doc_report.pdf", "DOCUMENT", "application/pdf", 512, "pdf", "a3b4c5", 14),
    (19, "Courier parcel X-ray image", "parcel_xray.jpg", "IMAGE", "image/jpeg", 4096, "jpg", "b4c5d6", 12),
    (19, "Physical evidence tag photo — cannabis sample", "cannabis_sample_tag.jpg", "IMAGE", "image/jpeg", 1024, "jpg", "c5d6e7", 12),
    (20, "Arrest photo and seized narcotics log", "narcotics_seizure_log.pdf", "DOCUMENT", "application/pdf", 256, "pdf", "d6e7f8", 55),
    (22, "Postmortem report (redacted)", "postmortem_report.pdf", "DOCUMENT", "application/pdf", 1024, "pdf", "e7f8a9", 18),
    (22, "Crime scene photograph — drainage canal", "scene_industrial.jpg", "IMAGE", "image/jpeg", 2560, "jpg", "f8a9b0", 18),
    (24, "Victim medical certificate — bruising documented", "medical_cert_victim.pdf", "DOCUMENT", "application/pdf", 256, "pdf", "a9b0c1", 1),
    (30, "Child rescue operation log", "rescue_operation_log.pdf", "DOCUMENT", "application/pdf", 384, "pdf", "b0c1d2", 50),
    (32, "Fire investigation report — accelerant detected", "fire_investigation_report.pdf", "DOCUMENT", "application/pdf", 768, "pdf", "c1d2e3", 19),
    (32, "Photograph of burn origin point", "arson_origin_photo.jpg", "IMAGE", "image/jpeg", 2048, "jpg", "d2e3f4", 19),
    (35, "Forensic kit collection record", "forensic_collection_record.pdf", "DOCUMENT", "application/pdf", 512, "pdf", "e3f4a5", 6),
    (35, "Park CCTV unavailability report", "cctv_unavailability_report.pdf", "DOCUMENT", "application/pdf", 128, "pdf", "f4a5b6", 6),
    (37, "Extortion threat audio recording (anonymised)", "threat_audio_extract.mp3", "AUDIO", "audio/mpeg", 3072, "mp3", "a5b6c7", 16),
    (37, "CCTV frames showing suspects", "extortion_suspect_cctv.jpg", "IMAGE", "image/jpeg", 1536, "jpg", "b6c7d8", 16),
    (39, "Seized firearm photograph", "firearm_seized_photo.jpg", "IMAGE", "image/jpeg", 2048, "jpg", "c7d8e9", 58),
    (39, "Ballistic analysis report", "ballistics_report.pdf", "DOCUMENT", "application/pdf", 1024, "pdf", "d8e9f0", 57),
    (41, "UIDAI misuse complaint acknowledgement", "uidai_complaint.pdf", "DOCUMENT", "application/pdf", 128, "pdf", "e9f0a1", 36),
    (41, "Fraudulent bank account opening documents", "fraud_bank_docs.pdf", "DOCUMENT", "application/pdf", 512, "pdf", "f0a1b2", 36),
    (43, "Fake currency note forensic analysis", "currency_forensic.pdf", "DOCUMENT", "application/pdf", 768, "pdf", "a1b2c3d4", 74),
    (51, "Phishing domain WHOIS and IP report", "phishing_domain_report.pdf", "DOCUMENT", "application/pdf", 256, "pdf", "b2c3d4e5", 35),
    (56, "Peddler arrest photo and seized sachets", "drug_peddler_arrest.jpg", "IMAGE", "image/jpeg", 1024, "jpg", "c3d4e5f6", 9),
    (58, "Inventory of stolen copper wire", "stolen_copper_inventory.pdf", "DOCUMENT", "application/pdf", 128, "pdf", "d4e5f6a7", 28),
    (59, "Jewellery shop CCTV — robbery in progress", "jewellery_robbery_cctv.mp4", "VIDEO", "video/mp4", 76800, "mp4", "e5f6a7b8", 21),
]

# ═════════════════════════════════════════════════════════════════════════════
# 8. INVESTIGATION NOTES
# ═════════════════════════════════════════════════════════════════════════════
# Format: (investigation_index, author_key, note_text, days_ago)
RAW_NOTES = [
    (0, "user:investigator1", "Initial CCTV request sent to municipal corporation. Awaiting 48-hour turnaround.", 3),
    (0, "user:investigator1", "Two suspects matched to prior vehicle theft case from 2024. Warrants prepared.", 1),
    (1, "user:investigator1", "Bank confirmed the OTP was sent to victim's registered number. Suspect used SIM swap.", 6),
    (1, "user:investigator1", "Call detail records received from telecom provider. Suspect number active in the city.", 4),
    (2, "user:investigator2", "Account suspended by platform after CERT-In coordination. Evidence screenshots archived.", 13),
    (3, "user:investigator1", "FSL report received — 3 latent prints, 1 match to known offender database.", 8),
    (3, "user:investigator1", "Neighbour witness confirmed seeing suspicious activity the previous evening.", 6),
    (4, "user:investigator2", "Spoke to judge re: bail; remand extended by 14 days. Victim goods recovery proceeding.", 58),
    (5, "user:investigator1", "Witness statement from vegetable vendor corroborates timeline. Sketch prepared.", 4),
    (5, "user:investigator1", "Motorcycle identified — stolen from another district 6 days prior.", 2),
    (6, "user:investigator2", "Banking CCTV reviewed alongside ATM footage — suspect covered face. Gait analysis ordered.", 7),
    (7, "user:investigator1", "Second seller's last known address checked — abandoned rental property.", 14),
    (7, "user:investigator1", "Land registry cross-verification complete — property legally belongs to a third party.", 13),
    (8, "user:investigator2", "Laboratory chemical analysis confirms cannabis — THC level 18%. Weight verified.", 11),
    (9, "user:investigator1", "Conviction upheld on appeal. All case files archived.", 50),
    (10, "user:investigator2", "DNA profile sent to NCRB DNA database for matching.", 16),
    (10, "user:investigator2", "Unidentified victim's photo circulated to missing persons cell — 3 possible matches.", 14),
    (11, "user:investigator1", "Social worker assigned. Victim in temporary shelter. Legal aid provided.", 1),
    (12, "user:investigator2", "Bank accounts attached pending court order. In-laws summoned for questioning.", 9),
    (13, "user:investigator1", "Juvenile court procedures activated. Child handed to CWC. Parents counselled.", 48),
    (14, "user:investigator2", "Ransom caller used VOIP — traced to a foreign VPN exit node. Cyber cell engaged.", 35),
    (15, "user:investigator1", "Fire forensics: pour pattern consistent with deliberate arson. Insurance claim flagged.", 18),
    (16, "user:investigator2", "Forensic samples sent to AIIMS for detailed analysis. Chain of custody documented.", 5),
    (17, "user:investigator1", "Two suspects from CCTV identified — prior extortion convictions in 2022.", 15),
    (18, "user:investigator2", "Recovered firearm serial number filed off — sent to ballistics for recovery etching.", 56),
    (19, "user:investigator1", "UIDAI confirmed fraudulent Aadhaar use. Bank account frozen; funds partially traced.", 33),
    (20, "user:investigator2", "Fake currency traced to a known syndicate operating in the northern corridor.", 72),
    (21, "user:investigator1", "12 victim accounts secured. Phishing kit code analysed — links to known cybercrime group.", 33),
    (22, "user:investigator2", "Student identified. Minor cautioned. Supply chain being investigated.", 8),
    (23, "user:investigator1", "Night watchman CCTV timestamps inconsistent — watchman questioned as possible abettor.", 27),
    (24, "user:investigator2", "Gold hallmark numbers circulated to jewellers' federation. Three items spotted at a shop.", 20),
]


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

async def _table_exists(session, table_name: str) -> bool:
    q = text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = :t)"
    )
    result = await session.execute(q, {"t": table_name})
    return result.scalar()


async def _count(session, table_name: str) -> int:
    result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
    return result.scalar()


async def _upsert(session, table, rows: list[dict], conflict_cols: list[str]) -> int:
    """INSERT ... ON CONFLICT DO NOTHING — returns number of new rows inserted."""
    if not rows:
        return 0
    stmt = pg_insert(table).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=conflict_cols)
    result = await session.execute(stmt)
    return result.rowcount


# ═════════════════════════════════════════════════════════════════════════════
# MAIN SEED LOGIC
# ═════════════════════════════════════════════════════════════════════════════

async def seed():
    # Import here to avoid circular-import issues at module load time
    from backend.app.models.user import User
    from backend.app.models.crime_category import CrimeCategory
    from backend.app.models.crime_location import CrimeLocation
    from backend.app.models.crime_report import CrimeReport
    from backend.app.models.investigation import Investigation
    from backend.app.models.investigation_note import InvestigationNote
    from backend.app.models.evidence import Evidence
    from backend.app.models.audit_log import AuditLog

    NOW = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        # ── 0. Verify DB connectivity ────────────────────────────────────────
        await session.execute(text("SELECT 1"))
        print("[OK] Database connection verified")

        # ── 1. SEED USERS ────────────────────────────────────────────────────
        print("\n[1/8] Seeding Users...")
        user_rows = []
        for u in SEED_USERS:
            user_rows.append({
                "id": u["id"],
                "supabase_user_id": u["supabase_user_id"],
                "email": u["email"],
                "full_name": u["full_name"],
                "badge_number": u["badge_number"],
                "department": u["department"],
                "is_active": u["is_active"],
                "email_verified": u["email_verified"],
                "phone_number": None,
                "profile_image_url": None,
                "last_login": None,
                "is_deleted": False,
                "created_at": NOW,
                "updated_at": NOW,
                "deleted_at": None,
            })
        inserted = await _upsert(session, User.__table__, user_rows, ["email"])
        await session.commit()
        print(f"   Users: {inserted} inserted (skipped duplicates)")

        # Resolve actual user IDs from DB (in case emails already existed)
        result = await session.execute(select(User.id, User.email).where(
            User.email.in_([u["email"] for u in SEED_USERS])
        ))
        user_map: dict[str, uuid.UUID] = {email: uid for uid, email in result.all()}
        admin_id = user_map.get("admin@crimelens.demo", _uid("user:admin"))
        officer1_id = user_map.get("officer.priya@crimelens.demo", _uid("user:officer1"))
        investigator1_id = user_map.get("inv.rahul@crimelens.demo", _uid("user:investigator1"))
        investigator2_id = user_map.get("inv.kavitha@crimelens.demo", _uid("user:investigator2"))
        officer2_id = user_map.get("officer.suresh@crimelens.demo", _uid("user:officer2"))
        analyst_id = user_map.get("analyst.meena@crimelens.demo", _uid("user:analyst1"))

        user_id_map = {
            "user:admin": admin_id,
            "user:officer1": officer1_id,
            "user:officer2": officer2_id,
            "user:investigator1": investigator1_id,
            "user:investigator2": investigator2_id,
            "user:analyst1": analyst_id,
        }

        # Reporter pool — cycle through officers
        reporters = [officer1_id, officer2_id, admin_id, investigator1_id, investigator2_id]

        # ── 3. CRIME CATEGORIES ──────────────────────────────────────────────
        print("\n[3/9] Seeding Crime Categories...")
        cat_rows = []
        for name, desc, sev, color in CATEGORIES:
            cat_rows.append({
                "id": _uid(f"cat:{name}"),
                "name": name,
                "description": desc,
                "severity_level": sev,
                "color_code": color,
                "created_at": NOW,
                "updated_at": NOW,
                "deleted_at": None,
            })
        inserted = await _upsert(session, CrimeCategory.__table__, cat_rows, ["name"])
        await session.commit()
        print(f"   Categories: {inserted} inserted")

        # Resolve category name → DB id
        res = await session.execute(select(CrimeCategory.id, CrimeCategory.name))
        cat_map: dict[str, uuid.UUID] = {name: cid for cid, name in res.all()}

        # ── 4. CRIME LOCATIONS ───────────────────────────────────────────────
        print("\n[4/9] Seeding Crime Locations...")
        loc_rows = []
        for i, (addr, landmark, city, district, state, zc, lat, lon) in enumerate(LOCATIONS):
            loc_rows.append({
                "id": _uid(f"loc:{i}:{city}:{addr}"),
                "address": addr,
                "landmark": landmark,
                "city": city,
                "district": district,
                "state": state,
                "zip_code": zc,
                "latitude": lat,
                "longitude": lon,
                "created_at": NOW,
                "updated_at": NOW,
                "deleted_at": None,
            })
        inserted = await _upsert(session, CrimeLocation.__table__, loc_rows, ["id"])
        await session.commit()
        print(f"   Locations: {inserted} inserted")

        # Resolve location ids in order
        loc_id_list = [row["id"] for row in loc_rows]
        # Verify they exist
        res = await session.execute(
            select(CrimeLocation.id).where(CrimeLocation.id.in_(loc_id_list))
        )
        existing_loc_ids = {r[0] for r in res.all()}
        loc_id_list = [lid for lid in loc_id_list if lid in existing_loc_ids]

        # ── 5. CRIME REPORTS ─────────────────────────────────────────────────
        print("\n[5/9] Seeding Crime Reports...")
        report_rows = []
        report_ids: list[uuid.UUID] = []
        for i, (title, desc, cat_name, loc_idx, prio, status,
                victims, suspects, loss, ago) in enumerate(RAW_REPORTS):
            rid = _uid(f"report:{i}:{title[:30]}")
            report_ids.append(rid)
            cat_id = cat_map.get(cat_name)
            if cat_id is None:
                print(f"   ⚠️  Category '{cat_name}' not found — skipping report #{i}")
                continue
            safe_loc_idx = loc_idx % len(loc_id_list)
            loc_id = loc_id_list[safe_loc_idx]
            reporter_id = reporters[i % len(reporters)]
            incident_dt = days_ago(ago)
            cr_number = f"CR-{incident_dt.year}-{str(i + 1).zfill(6)}"
            report_rows.append({
                "id": rid,
                "crime_number": cr_number,
                "title": title,
                "description": desc,
                "incident_date": incident_dt,
                "report_date": incident_dt + timedelta(hours=2),
                "status": status,
                "priority": prio,
                "victim_count": victims,
                "suspect_count": suspects,
                "estimated_loss": loss,
                "reporter_id": reporter_id,
                "category_id": cat_id,
                "location_id": loc_id,
                "created_at": incident_dt + timedelta(hours=2),
                "updated_at": NOW,
                "deleted_at": None,
            })
        inserted = await _upsert(session, CrimeReport.__table__, report_rows, ["crime_number"])
        await session.commit()
        print(f"   Crime Reports: {inserted} inserted")

        # Resolve actual report IDs from DB
        res = await session.execute(
            select(CrimeReport.id, CrimeReport.crime_number).where(
                CrimeReport.crime_number.in_([r["crime_number"] for r in report_rows])
            )
        )
        cr_by_number = {cn: cid for cid, cn in res.all()}
        db_report_ids = [cr_by_number.get(r["crime_number"], r["id"]) for r in report_rows]

        # ── 6. INVESTIGATIONS ────────────────────────────────────────────────
        print("\n[6/9] Seeding Investigations...")
        inv_rows = []
        inv_ids: list[uuid.UUID] = []
        for j, (rep_idx, inv_user_key, prio, status, notes, days_since, resolution) in enumerate(RAW_INVESTIGATIONS):
            safe_idx = rep_idx if rep_idx < len(db_report_ids) else rep_idx % len(db_report_ids)
            report_id = db_report_ids[safe_idx]
            inv_id = _uid(f"inv:{j}:{rep_idx}")
            inv_ids.append(inv_id)
            assigned_dt = days_ago(days_since)
            closed_dt = NOW if status == "CLOSED" else None
            inv_rows.append({
                "id": inv_id,
                "report_id": report_id,
                "investigator_id": user_id_map.get(inv_user_key, investigator1_id),
                "notes": notes,
                "status": normalize_investigation_status(status),
                "priority": prio,
                "assigned_at": assigned_dt,
                "closed_at": closed_dt,
                "resolution_summary": resolution,
                "created_at": assigned_dt,
                "updated_at": NOW,
                "deleted_at": None,
            })
        inserted = await _upsert(session, Investigation.__table__, inv_rows, ["id"])
        await session.commit()
        print(f"   Investigations: {inserted} inserted")

        # ── 7. INVESTIGATION NOTES ───────────────────────────────────────────
        print("\n[7/9] Seeding Investigation Notes...")
        note_rows = []
        for k, (inv_idx, author_key, note_text, ago) in enumerate(RAW_NOTES):
            safe_idx = inv_idx if inv_idx < len(inv_ids) else inv_idx % len(inv_ids)
            inv_id = inv_ids[safe_idx]
            note_rows.append({
                "id": _uid(f"note:{k}:{inv_idx}"),
                "investigation_id": inv_id,
                "author_id": user_id_map.get(author_key, investigator1_id),
                "note": note_text,
                "attachment_evidence_id": None,
                "edited": False,
                "created_at": days_ago(ago),
                "updated_at": days_ago(ago),
                "deleted_at": None,
            })
        inserted = await _upsert(session, InvestigationNote.__table__, note_rows, ["id"])
        await session.commit()
        print(f"   Investigation Notes: {inserted} inserted")

        # ── 8. EVIDENCE ──────────────────────────────────────────────────────
        print("\n[8/9] Seeding Evidence (metadata only)...")
        ev_rows = []
        for m, (rep_idx, desc, fname, ftype, mime, size_kb, ext, csum, ago) in enumerate(RAW_EVIDENCE):
            safe_idx = rep_idx if rep_idx < len(db_report_ids) else rep_idx % len(db_report_ids)
            rep_id = db_report_ids[safe_idx]
            upload_dt = days_ago(ago)
            uploader_id = investigator1_id if m % 2 == 0 else investigator2_id
            ev_rows.append({
                "id": _uid(f"evidence:{m}:{fname}"),
                "report_id": rep_id,
                "uploaded_by": uploader_id,
                "description": desc,
                "file_name": fname,
                "file_type": ftype,
                "mime_type": mime,
                "file_size": size_kb * 1024,
                "file_url": f"https://storage.crimelens.demo/evidence/seed/{fname}",
                "storage_path": f"evidence/seed/{fname}",
                "bucket_name": "evidence",
                "checksum": csum,
                "file_extension": ext,
                "uploaded_at": upload_dt,
                "created_at": upload_dt,
                "updated_at": upload_dt,
                "deleted_at": None,
            })
        inserted = await _upsert(session, Evidence.__table__, ev_rows, ["id"])
        await session.commit()
        print(f"   Evidence: {inserted} inserted")

        # ── 9. AUDIT LOGS (seed setup events) ────────────────────────────────
        print("\n[9/9] Seeding Audit Logs...")
        audit_rows = []
        for idx, (cat_name, _, _, _) in enumerate(CATEGORIES):
            cat_id = cat_map.get(cat_name)
            if cat_id:
                audit_rows.append({
                    "id": _uid(f"audit:cat:{cat_name}"),
                    "action": "CATEGORY_CREATED",
                    "entity_type": "crime_category",
                    "entity_id": cat_id,
                    "details": {"name": cat_name, "seeded": True},
                    "ip_address": "127.0.0.1",
                    "user_agent": "seed_script/1.0",
                    "user_id": admin_id,
                    "created_at": days_ago(120 - idx),
                    "updated_at": days_ago(120 - idx),
                    "deleted_at": None,
                })
        for idx, lid in enumerate(loc_id_list[:10]):
            audit_rows.append({
                "id": _uid(f"audit:loc:{str(lid)}"),
                "action": "LOCATION_CREATED",
                "entity_type": "crime_location",
                "entity_id": lid,
                "details": {"city": LOCATIONS[idx][2], "seeded": True},
                "ip_address": "127.0.0.1",
                "user_agent": "seed_script/1.0",
                "user_id": admin_id,
                "created_at": days_ago(110 - idx),
                "updated_at": days_ago(110 - idx),
                "deleted_at": None,
            })
        for idx, rid in enumerate(db_report_ids[:10]):
            audit_rows.append({
                "id": _uid(f"audit:report:{str(rid)}"),
                "action": "CRIME_REPORT_CREATED",
                "entity_type": "crime_report",
                "entity_id": rid,
                "details": {"title": RAW_REPORTS[idx][0][:60], "seeded": True},
                "ip_address": "10.0.0.1",
                "user_agent": "seed_script/1.0",
                "user_id": reporters[idx % len(reporters)],
                "created_at": days_ago(RAW_REPORTS[idx][9]),
                "updated_at": days_ago(RAW_REPORTS[idx][9]),
                "deleted_at": None,
            })
        for idx, inv_id in enumerate(inv_ids[:5]):
            audit_rows.append({
                "id": _uid(f"audit:inv:{str(inv_id)}"),
                "action": "INVESTIGATION_ASSIGNED",
                "entity_type": "investigation",
                "entity_id": inv_id,
                "details": {"investigator": RAW_INVESTIGATIONS[idx][1], "seeded": True},
                "ip_address": "10.0.0.1",
                "user_agent": "seed_script/1.0",
                "user_id": admin_id,
                "created_at": days_ago(RAW_INVESTIGATIONS[idx][5]),
                "updated_at": days_ago(RAW_INVESTIGATIONS[idx][5]),
                "deleted_at": None,
            })
        inserted = await _upsert(session, AuditLog.__table__, audit_rows, ["id"])
        await session.commit()
        print(f"   Audit Logs: {inserted} inserted")

        # ── SUMMARY ──────────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("SEED COMPLETE -- Final record counts:")
        print("=" * 60)
        for tbl in ["users", "crime_categories", "crime_locations",
                    "crime_reports", "investigations", "investigation_notes",
                    "evidence", "audit_logs"]:
            n = await _count(session, tbl)
            print(f"   {tbl:<28} {n:>5} records")
        print("=" * 60)
        print("\n[DONE] All seed data inserted. Application is ready for demo use.")
        print("   Frontend: http://localhost:5173")
        print("   API Docs: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(seed())
