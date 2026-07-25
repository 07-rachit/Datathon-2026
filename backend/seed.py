"""Run with: python seed.py
Populates default users, connected storylines A-F, synthetic demographics, district indicators,
offender profiles, financial transactions, and KSP FIR lookup master tables.

DISCLAIMER: All demographic, financial, complainant, and FIR transaction records seeded here are
CLEARLY SYNTHETIC DEMO DATA generated for evaluation and policy insight demonstration.
"""
from datetime import datetime, timedelta
import random

from app.database import SessionLocal, Base, engine
from app import models, auth, schemas, rag

# Re-create tables cleanly for idempotent demo state
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

print("--> Starting CrimeIntel Demo Seed Pipeline...")

# ── 1. Reference Lookup Masters ──────────────────────────────────────────────

def seed_masters():
    # Categories
    categories = ["FIR", "UDR", "Zero FIR", "PAR"]
    cat_objs = {}
    for c in categories:
        obj = models.CaseCategoryMaster(name=c)
        db.add(obj)
        cat_objs[c] = obj
    db.flush()

    # Gravities
    gravities = ["Heinous", "Non-Heinous"]
    grav_objs = {}
    for g in gravities:
        obj = models.GravityOffenceMaster(name=g)
        db.add(obj)
        grav_objs[g] = obj
    db.flush()

    # Crime Heads & Sub-Heads
    heads_map = {
        "Crimes Against Body": ["Murder", "Assault", "Kidnapping"],
        "Crimes Against Property": ["Burglary", "Theft", "Robbery", "Vehicle Theft"],
        "Cyber & Financial Crimes": ["Phone OTP Fraud", "Phishing Link", "ATM Skimming", "Crypto Fraud"],
        "Public Tranquility": ["Rioting", "Unlawful Assembly"],
    }
    head_objs = {}
    sub_objs = {}
    for head_name, sub_names in heads_map.items():
        ch = models.CrimeHead(name=head_name)
        db.add(ch)
        db.flush()
        head_objs[head_name] = ch
        for sub_name in sub_names:
            sh = models.CrimeSubHead(crime_head_id=ch.id, name=sub_name)
            db.add(sh)
            db.flush()
            sub_objs[sub_name] = sh

    # Statuses
    statuses = ["Under Investigation", "Charge Sheeted", "Closed", "Transferred", "Under Trial"]
    status_objs = {}
    for s in statuses:
        obj = models.CaseStatusMaster(name=s)
        db.add(obj)
        status_objs[s] = obj
    db.flush()

    # Acts & Sections
    acts_map = {
        "Indian Penal Code (IPC)": [("302", "Punishment for Murder"), ("379", "Punishment for Theft"), ("392", "Punishment for Robbery"), ("420", "Cheating and Dishonesty")],
        "Bharatiya Nyaya Sanhita (BNS)": [("103", "Murder"), ("303", "Theft"), ("309", "Robbery"), ("318", "Cheating")],
        "Information Technology (IT) Act": [("66C", "Identity Theft"), ("66D", "Cheating by Personation using Computer Resource")],
    }
    act_objs = {}
    sec_objs = {}
    for act_name, secs in acts_map.items():
        act_obj = models.Act(name=act_name)
        db.add(act_obj)
        db.flush()
        act_objs[act_name] = act_obj
        for sec_num, desc in secs:
            s_obj = models.Section(act_id=act_obj.id, section_number=sec_num, description=desc)
            db.add(s_obj)
            db.flush()
            sec_objs[f"{act_name}-{sec_num}"] = s_obj

    # Occupations
    occupations = ["Business", "IT Professional", "Government Employee", "Laborer", "Driver", "Student", "Unemployed", "Self-Employed"]
    occ_objs = {}
    for o in occupations:
        obj = models.OccupationMaster(name=o)
        db.add(obj)
        occ_objs[o] = obj
    db.flush()

    # Religions & Castes (Statutory Masked Compliance Masters)
    religions = ["Hinduism", "Islam", "Christianity", "Sikhism", "Buddhism", "Jainism", "Other"]
    rel_objs = {}
    for r in religions:
        obj = models.ReligionMaster(name=r)
        db.add(obj)
        rel_objs[r] = obj
    db.flush()

    castes = ["General", "OBC", "SC", "ST", "Unspecified"]
    caste_objs = {}
    for c in castes:
        obj = models.CasteMaster(name=c)
        db.add(obj)
        caste_objs[c] = obj
    db.flush()

    # State, District, Unit Type, Units, Courts
    st = models.StateMaster(name="Karnataka", code="KA")
    db.add(st)
    db.flush()

    dist_bgl = models.DistrictMaster(state_id=st.id, name="Bengaluru City", code="0012")
    dist_ludh = models.DistrictMaster(state_id=st.id, name="Ludhiana West", code="0014")
    dist_mys = models.DistrictMaster(state_id=st.id, name="Mysuru", code="0018")
    db.add_all([dist_bgl, dist_ludh, dist_mys])
    db.flush()

    ut = models.UnitTypeMaster(name="Police Station")
    db.add(ut)
    db.flush()

    unit = models.UnitMaster(district_id=dist_bgl.id, unit_type_id=ut.id, unit_name="PS Commercial Street", code="0045")
    db.add(unit)
    db.flush()

    court = models.CourtMaster(district_id=dist_bgl.id, court_name="Principal District & Sessions Court", court_type="Sessions")
    db.add(court)
    db.flush()

    # Rank, Designation, Employee
    rank = models.RankMaster(name="Inspector of Police", code="INS")
    db.add(rank)
    db.flush()

    desig = models.DesignationMaster(name="Station House Officer (SHO)")
    db.add(desig)
    db.flush()

    emp = models.EmployeeMaster(
        kgid="KGID-88492",
        name="Inspector K. Sharma",
        gender="male",
        appointment_date=datetime(2015, 6, 1),
        rank_id=rank.id,
        designation_id=desig.id,
        unit_id=unit.id,
    )
    db.add(emp)
    db.flush()

    db.commit()
    print("--> Seeded Reference Masters successfully.")
    return {
        "cat": cat_objs,
        "grav": grav_objs,
        "head": head_objs,
        "sub": sub_objs,
        "status": status_objs,
        "act": act_objs,
        "sec": sec_objs,
        "occ": occ_objs,
        "rel": rel_objs,
        "caste": caste_objs,
        "unit": unit,
        "court": court,
        "emp": emp,
    }

masters = seed_masters()

# ── 2. Users (Admin, Investigator, Analyst, Viewer) ─────────────────────────

admin_user = models.User(
    name="Admin User (DGP Office)",
    email="admin@crimeintel.local",
    hashed_password=auth.hash_password("Admin@123"),
    role=models.RoleEnum.admin,
)
analyst_user = models.User(
    name="Lead Analyst Priya",
    email="analyst@crimeintel.local",
    hashed_password=auth.hash_password("Analyst@123"),
    role=models.RoleEnum.analyst,
)
investigator_user = models.User(
    name="Inspector K. Sharma",
    email="investigator@crimeintel.local",
    hashed_password=auth.hash_password("Investigator@123"),
    role=models.RoleEnum.investigator,
)
viewer_user = models.User(
    name="Junior Duty Officer",
    email="viewer@crimeintel.local",
    hashed_password=auth.hash_password("Viewer@123"),
    role=models.RoleEnum.viewer,
)

db.add_all([admin_user, analyst_user, investigator_user, viewer_user])
db.commit()
print("--> Seeded RBAC Users.")

# ── 3. STORYLINE A: Repeat Offender ("Ramesh @ 'Black Hat' Rao") ────────────

story_a_cases = [
    {
        "case_id": "CR-2026-0101",
        "title": "Night Burglary at Electronics Warehouse",
        "crime_type": "Burglary",
        "district": "Bengaluru City",
        "station_name": "PS Commercial Street",
        "summary": "Night break-in at electronics godown. CCTV disabled with laser cutter. Over ₹4 Lakhs worth laptops looted.",
        "severity": models.Severity.medium,
        "date": datetime(2025, 11, 10, 3, 15),
    },
    {
        "case_id": "CR-2026-0102",
        "title": "Armed Robbery at Commercial Jewelry Outlet",
        "crime_type": "Robbery",
        "district": "Bengaluru City",
        "station_name": "PS Central",
        "summary": "Armed robbers held store manager at gunpoint during closing hours. Stole gold ornaments and fled on getaway bike.",
        "severity": models.Severity.high,
        "date": datetime(2026, 2, 14, 21, 30),
    },
    {
        "case_id": "CR-2026-0103",
        "title": "Highway Cash Van Interception & Robbery",
        "crime_type": "Robbery",
        "district": "Mysuru",
        "station_name": "PS Mysuru Highway",
        "summary": "Highway heist on cash transfer van. Spike strip deployed on road. Suspect Ramesh Rao spotted on toll camera.",
        "severity": models.Severity.critical,
        "date": datetime(2026, 5, 20, 23, 45),
    },
    {
        "case_id": "CR-2026-0104",
        "title": "Attempted Bank Vault Tampering",
        "crime_type": "Burglary",
        "district": "Ludhiana West",
        "station_name": "PS Model Town",
        "summary": "Attempted night burglary at cooperative bank. Alarm triggered; suspect Ramesh Rao evaded arrest.",
        "severity": models.Severity.high,
        "date": datetime(2026, 6, 28, 2, 0),
    },
]

person_ramesh = None
for cd in story_a_cases:
    c = models.Case(
        case_id=cd["case_id"],
        title=cd["title"],
        crime_type=cd["crime_type"],
        district=cd["district"],
        station_name=cd["station_name"],
        summary=cd["summary"],
        status=models.CaseStatus.open,
        severity=cd["severity"],
        incident_date=cd["date"],
        latitude=12.9716,
        longitude=77.5946,
    )
    db.add(c)
    db.flush()

    p = models.Person(
        case_id=c.id,
        name="Ramesh @ 'Black Hat' Rao",
        role_in_case="accused",
        phone_number="9876543210",
        notes="Serial offender. Expert in CCTV bypass and armed robbery.",
        is_flagged_offender=True,
        mo_tags="night-burglary,cctv-tampering,armed-robbery,getaway-bike",
    )
    db.add(p)
    db.flush()
    if not person_ramesh:
        person_ramesh = p

db.commit()
print("--> Seeded Storyline A (Repeat Offender Ramesh Rao across 4 cases).")

# ── 4. STORYLINE B: Organized Syndicate ("The Electronic City Cyber Syndicate")

story_b_cases = [
    {
        "case_id": "CR-2026-0201",
        "title": "Multi-District ATM Skimming & Card Cloning Racket",
        "crime_type": "Fraud",
        "district": "Bengaluru City",
        "station_name": "PS Commercial Street",
        "summary": "Organized syndicate installed hidden skimmers across 6 ATMs. Stole PIN numbers and withdrew ₹12 Lakhs.",
        "severity": models.Severity.critical,
        "date": datetime(2026, 4, 12, 11, 0),
    },
    {
        "case_id": "CR-2026-0202",
        "title": "Illegal Firearms Trafficking & Extortion Ring",
        "crime_type": "Assault",
        "district": "Bengaluru City",
        "station_name": "PS Central",
        "summary": "Syndicate members extorted local traders using illicit country-made pistols. Inter-state weapons trail detected.",
        "severity": models.Severity.critical,
        "date": datetime(2026, 6, 2, 19, 15),
    },
]

syndicate_members = [
    ("Vikram 'Viper' Singh", "accused", "9876543210", "Gang Leader / Firearms coordinator"),
    ("Anand 'Techie' Rao", "co-accused", "9876543210", "Technical mastermind / ATM skimmer installer"),
    ("Suresh 'Broker' Kumar", "co-accused", "9988776655", "Mule account provider & cash handler"),
    ("Deepak 'Rider' Verma", "co-accused", "9988776655", "Logistics & getaway driver"),
]

person_anand = None
person_suresh = None

for cd in story_b_cases:
    c = models.Case(
        case_id=cd["case_id"],
        title=cd["title"],
        crime_type=cd["crime_type"],
        district=cd["district"],
        station_name=cd["station_name"],
        summary=cd["summary"],
        status=models.CaseStatus.open,
        severity=cd["severity"],
        incident_date=cd["date"],
        latitude=12.9352,
        longitude=77.6245,
    )
    db.add(c)
    db.flush()

    for name, role, phone, notes in syndicate_members:
        p = models.Person(
            case_id=c.id,
            name=name,
            role_in_case=role,
            phone_number=phone,
            notes=notes,
            is_flagged_offender=True,
            mo_tags="syndicate,atm-skimming,firearms,extortion",
        )
        db.add(p)
        db.flush()
        if "Anand" in name and not person_anand:
            person_anand = p
        elif "Suresh" in name and not person_suresh:
            person_suresh = p

db.commit()
print("--> Seeded Storyline B (Organized Gang Cluster with 4 co-accused & shared phone links).")

# ── 5. STORYLINE C: Multi-Hop Financial Crime Trail ──────────────────────────

c_financial = models.Case(
    case_id="CR-2026-0301",
    title="Phishing OTP Fraud & Multi-Hop Wire Transfer",
    crime_type="Fraud",
    district="Bengaluru City",
    station_name="PS Commercial Street",
    summary="Victim defrauded of ₹8,50,000 via fake banking portal. Funds routed through 3 mule accounts within 15 minutes.",
    status=models.CaseStatus.open,
    severity=models.Severity.critical,
    incident_date=datetime(2026, 6, 18, 14, 20),
    latitude=12.9716,
    longitude=77.5946,
)
db.add(c_financial)
db.flush()

acc1 = models.FinancialAccount(
    person_id=None,
    bank_name="HDFC Bank",
    account_number_masked="XXXX-XXXX-9001",
    account_type="Savings (Victim)",
)
acc2 = models.FinancialAccount(
    person_id=person_anand.id if person_anand else None,
    bank_name="ICICI Bank",
    account_number_masked="XXXX-XXXX-9002",
    account_type="Current (Transit)",
)
acc3 = models.FinancialAccount(
    person_id=person_suresh.id if person_suresh else None,
    bank_name="Paytm Payments Bank",
    account_number_masked="XXXX-XXXX-9003",
    account_type="Digital Mule Wallet",
)
db.add_all([acc1, acc2, acc3])
db.flush()

tx1 = models.FinancialTransaction(
    case_id=c_financial.id,
    from_account_id=acc1.id,
    to_account_id=acc2.id,
    amount=850000.0,
    transaction_date=datetime(2026, 6, 18, 14, 22),
    flagged_reason="Phishing OTP Wire Transfer",
)
tx2 = models.FinancialTransaction(
    case_id=c_financial.id,
    from_account_id=acc2.id,
    to_account_id=acc3.id,
    amount=500000.0,
    transaction_date=datetime(2026, 6, 18, 14, 28),
    flagged_reason="Rapid Split to Mule Account",
)
tx3 = models.FinancialTransaction(
    case_id=c_financial.id,
    from_account_id=acc2.id,
    to_account_id=acc3.id,
    amount=350000.0,
    transaction_date=datetime(2026, 6, 18, 14, 30),
    flagged_reason="ATM Cash Withdrawal",
)
db.add_all([tx1, tx2, tx3])
db.commit()
print("--> Seeded Storyline C (Multi-hop Financial Wire Transfer Trail).")

# ── 6. STORYLINE D: Full KSP FIR Lifecycle Case ─────────────────────────────

case_d = models.Case(
    case_id="CR-2026-0401",
    title="Commercial Street Jewelry Heist & Homicide",
    crime_type="Robbery",
    district="Bengaluru City",
    station_name="PS Commercial Street",
    summary="Armed heist at commercial jewelry showroom. Guard injured. Full statutory lifecycle recorded under KSP FIR standards.",
    status=models.CaseStatus.closed,
    severity=models.Severity.critical,
    incident_date=datetime(2026, 5, 1, 20, 10),
    latitude=12.9812,
    longitude=77.6089,
)
db.add(case_d)
db.flush()

# Structured FIR Details
fir_d = models.CaseFIRDetails(
    case_id=case_d.id,
    crime_no=schemas.generate_crime_no(category_code="1", district_code="0012", station_code="0045", year="2026", serial=401),
    case_no="2026/0401",
    crime_registered_date=datetime(2026, 5, 1, 22, 0),
    incident_from_date=datetime(2026, 5, 1, 20, 10),
    incident_to_date=datetime(2026, 5, 1, 20, 40),
    info_received_ps_date=datetime(2026, 5, 1, 21, 0),
    case_category_id=masters["cat"]["FIR"].id,
    gravity_offence_id=masters["grav"]["Heinous"].id,
    crime_head_id=masters["head"]["Crimes Against Property"].id,
    crime_sub_head_id=masters["sub"]["Robbery"].id,
    case_status_id=masters["status"]["Charge Sheeted"].id,
    court_id=masters["court"].id,
    police_station_id=masters["unit"].id,
    registering_officer_id=masters["emp"].id,
)
db.add(fir_d)

# Statutory Sensitive Masked Complainant
comp_d = models.ComplainantDetails(
    case_id=case_d.id,
    name="Ramesh Kumar (Store Owner)",
    age=48,
    gender="male",
    occupation_id=masters["occ"]["Business"].id,
    religion_id=masters["rel"]["Hinduism"].id,
    caste_id=masters["caste"]["General"].id,
)
db.add(comp_d)

# Act Section Association
assoc_d = models.ActSectionAssociation(
    case_id=case_d.id,
    act_id=masters["act"]["Indian Penal Code (IPC)"].id,
    section_id=masters["sec"]["Indian Penal Code (IPC)-392"].id,
    display_order=1,
)
db.add(assoc_d)

# Arrest & Surrender Event
arr_d = models.ArrestSurrender(
    case_id=case_d.id,
    accused_person_id=person_ramesh.id if person_ramesh else None,
    event_type="arrest",
    event_date=datetime(2026, 5, 15, 14, 30),
    investigating_officer_id=masters["emp"].id,
    unit_id=masters["unit"].id,
    court_id=masters["court"].id,
)
db.add(arr_d)

# Chargesheet Details
cs_d = models.ChargesheetDetails(
    case_id=case_d.id,
    chargesheet_date=datetime(2026, 6, 1, 11, 0),
    cs_type="A",
    filing_officer_id=masters["emp"].id,
    remarks="Complete charge sheet filed in Principal District Court within 30 days.",
)
db.add(cs_d)
db.commit()
print("--> Seeded Storyline D (Full KSP FIR Lifecycle with FIR, Arrest, Chargesheet).")

# ── 7. STORYLINE E: Festive Season Spike Cluster ──────────────────────────────

spike_dates = [
    # 2024 October festival cluster
    datetime(2024, 10, 5, 2, 10), datetime(2024, 10, 12, 3, 0), datetime(2024, 10, 18, 1, 45), datetime(2024, 10, 25, 4, 20),
    # 2025 October & November festival cluster
    datetime(2025, 10, 2, 3, 30), datetime(2025, 10, 10, 2, 15), datetime(2025, 10, 21, 4, 0), datetime(2025, 10, 28, 1, 30),
    datetime(2025, 11, 2, 3, 10), datetime(2025, 11, 14, 2, 45), datetime(2025, 11, 20, 4, 15),
    # 2026 October cluster
    datetime(2026, 10, 8, 2, 0), datetime(2026, 10, 16, 3, 20), datetime(2026, 10, 24, 1, 50),
]

for idx, dt in enumerate(spike_dates, 1):
    c_spike = models.Case(
        case_id=f"CR-SPIKE-{idx:03d}",
        title=f"Festive Season Burglary #{idx}",
        crime_type="Burglary",
        district="Bengaluru City",
        station_name="PS Commercial Street",
        summary=f"Seasonal residential burglary recorded during Deepavali festive holiday period in Bengaluru City.",
        status=models.CaseStatus.closed,
        severity=models.Severity.medium,
        incident_date=dt,
        latitude=12.9716,
        longitude=77.5946,
    )
    db.add(c_spike)

db.commit()
print("--> Seeded Storyline E (Festive Season Burglary Spike Cluster in Oct/Nov).")

# ── 8. STORYLINE F: Statutory Sensitive Data Masking Demo Case ────────────────

c_sensitive = models.Case(
    case_id="CR-2026-0601",
    title="High-Value Cyber Extortion & Statutory Compliance FIR",
    crime_type="Fraud",
    district="Bengaluru City",
    station_name="PS Central",
    summary="Corporate CEO targeted in spear-phishing extortion. Statutory FIR complainant record contains masked demographic fields.",
    status=models.CaseStatus.open,
    severity=models.Severity.high,
    incident_date=datetime(2026, 7, 1, 10, 0),
    latitude=12.9716,
    longitude=77.5946,
)
db.add(c_sensitive)
db.flush()

comp_f = models.ComplainantDetails(
    case_id=c_sensitive.id,
    name="Suresh Adiga (Tech Executive)",
    age=52,
    gender="male",
    occupation_id=masters["occ"]["IT Professional"].id,
    religion_id=masters["rel"]["Hinduism"].id,
    caste_id=masters["caste"]["General"].id,
)
db.add(comp_f)
db.commit()
print("--> Seeded Storyline F (Sensitive Complainant Masking Demo Case).")

# ── 9. Background Noise Cases (~30 Cases) ────────────────────────────────────

crime_types = ["Burglary", "Vehicle Theft", "Fraud", "Assault", "Theft"]
districts = ["Bengaluru City", "Ludhiana West", "Mysuru"]
stations = ["PS Commercial Street", "PS Model Town", "PS Mysuru Highway", "PS Central"]

for i in range(1, 31):
    dt = datetime(2026, 1, 1) + timedelta(days=random.randint(0, 180), hours=random.randint(0, 23))
    ctype = random.choice(crime_types)
    dist = random.choice(districts)
    c_bg = models.Case(
        case_id=f"CR-2026-9{i:03d}",
        title=f"{ctype} Incident #{i}",
        crime_type=ctype,
        district=dist,
        station_name=random.choice(stations),
        summary=f"Standard incident investigation for {ctype.lower()} recorded in {dist}.",
        status=random.choice(list(models.CaseStatus)),
        severity=random.choice(list(models.Severity)),
        incident_date=dt,
        latitude=12.97 + (random.random() * 0.05),
        longitude=77.59 + (random.random() * 0.05),
    )
    db.add(c_bg)

db.commit()
print("--> Seeded 30 Background Noise Cases.")

# ── 10. Seed Sprint 6 Case Collaboration Data (Assignments, Tasks, Comments) ──

case_heist = db.query(models.Case).filter(models.Case.case_id == "CR-2026-0401").first()
case_phish = db.query(models.Case).filter(models.Case.case_id == "CR-2026-0301").first()
case_robbery = db.query(models.Case).filter(models.Case.case_id == "CR-2026-0103").first()

if case_heist and investigator_user and analyst_user:
    # Assignments
    db.add(models.CaseAssignment(
        case_id=case_heist.id,
        assigned_to_user_id=investigator_user.id,
        assigned_by_user_id=admin_user.id,
        role_on_case="Lead Investigator",
        status="active",
    ))
    db.add(models.CaseAssignment(
        case_id=case_heist.id,
        assigned_to_user_id=analyst_user.id,
        assigned_by_user_id=admin_user.id,
        role_on_case="Reviewing Analyst",
        status="active",
    ))

    # Tasks
    db.add(models.CaseTask(
        case_id=case_heist.id,
        title="Cross-verify CCTV footage from Commercial Street entrance",
        description="Review 4K camera feeds from 20:00 to 21:00 on incident night.",
        assigned_to_user_id=investigator_user.id,
        created_by_user_id=admin_user.id,
        due_date=datetime.utcnow() + timedelta(days=2),
        status="in_progress",
    ))
    db.add(models.CaseTask(
        case_id=case_heist.id,
        title="Issue formal seizure memo for recovered gold ornaments",
        description="Prepare evidence inventory for judicial magistrate submission.",
        assigned_to_user_id=investigator_user.id,
        created_by_user_id=analyst_user.id,
        due_date=datetime.utcnow() + timedelta(days=5),
        status="todo",
    ))
    db.add(models.CaseTask(
        case_id=case_heist.id,
        title="Submit preliminary forensic report to District Court",
        description="Ballistics and fingerprint verification documentation.",
        assigned_to_user_id=analyst_user.id,
        created_by_user_id=admin_user.id,
        due_date=datetime.utcnow() - timedelta(days=1),
        status="done",
        completed_at=datetime.utcnow() - timedelta(hours=12),
    ))

    # Comments
    db.add(models.CaseComment(
        case_id=case_heist.id,
        author_user_id=investigator_user.id,
        content="Initial crime scene inspection complete. Suspects fled on a black getaway bike towards MG Road.",
    ))
    db.add(models.CaseComment(
        case_id=case_heist.id,
        author_user_id=analyst_user.id,
        content="Cross-referenced offender directory: MO tags and CCTV height match suspect Ramesh 'Black Hat' Rao.",
    ))

if case_phish and investigator_user:
    db.add(models.CaseAssignment(
        case_id=case_phish.id,
        assigned_to_user_id=investigator_user.id,
        assigned_by_user_id=analyst_user.id,
        role_on_case="Lead Cyber Investigator",
        status="active",
    ))
    db.add(models.CaseTask(
        case_id=case_phish.id,
        title="Freeze ICICI Transit Account ACC-9002",
        description="Dispatch urgent section 91 CrPC notice to ICICI fraud monitoring cell.",
        assigned_to_user_id=investigator_user.id,
        created_by_user_id=investigator_user.id,
        due_date=datetime.utcnow() + timedelta(days=1),
        status="todo",
    ))
    db.add(models.CaseTask(
        case_id=case_phish.id,
        title="Request KYC and IP logs for Paytm Mule Wallet ACC-9003",
        description="Track digital wallet registration IP address and linked mobile SIM.",
        assigned_to_user_id=investigator_user.id,
        created_by_user_id=analyst_user.id,
        due_date=datetime.utcnow() + timedelta(days=3),
        status="todo",
    ))

if case_robbery and analyst_user:
    db.add(models.CaseAssignment(
        case_id=case_robbery.id,
        assigned_to_user_id=analyst_user.id,
        assigned_by_user_id=admin_user.id,
        role_on_case="Supporting Officer",
        status="active",
    ))

db.commit()
print("--> Seeded Sprint 6 Case Collaboration Data (Assignments, Tasks, Comments).")

# ── 11. Rebuild RAG Search Index ─────────────────────────────────────────────

indexed_count = rag.build_index(db)
print(f"--> Rebuilt RAG TF-IDF Search Index with {indexed_count} total evidence chunks.")

db.close()
print("--> CrimeIntel Demo Seed Pipeline Completed Successfully! System ready for live presentation.")

