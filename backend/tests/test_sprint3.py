from datetime import datetime
from app import models, schemas

def test_crime_number_generator_format():
    crime_no = schemas.generate_crime_no(category_code="1", district_code="12", station_code="45", year="2026", serial=18)
    assert len(crime_no) == 18
    assert crime_no == "100120045202600018"


def test_master_lookup_endpoints(client, db_session, investigator_headers):
    # Add sample master category and act
    cat = models.CaseCategoryMaster(name="FIR")
    act = models.Act(name="Indian Penal Code")
    db_session.add_all([cat, act])
    db_session.commit()

    res = client.get("/api/masters/categories", headers=investigator_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1

    res_acts = client.get("/api/masters/acts", headers=investigator_headers)
    assert res_acts.status_code == 200
    assert len(res_acts.json()) >= 1


def test_sensitive_field_masking_complainant(client, db_session, admin_headers, investigator_headers):
    # Setup test case, complainant, religion, caste
    rel = models.ReligionMaster(name="Hinduism")
    caste = models.CasteMaster(name="General")
    db_session.add_all([rel, caste])
    db_session.flush()

    case = models.Case(
        case_id="CR-2026-COMP",
        title="Complainant Test",
        crime_type="Theft",
        district="Bengaluru City",
        station_name="PS Central",
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.flush()

    comp = models.ComplainantDetails(
        case_id=case.id,
        name="Anil Kumar",
        age=38,
        gender="male",
        religion_id=rel.id,
        caste_id=caste.id,
    )
    db_session.add(comp)
    db_session.commit()

    # Investigator gets masked religion_name=None and caste_name=None
    inv_res = client.get(f"/api/cases/{case.id}/complainant", headers=investigator_headers)
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["name"] == "Anil Kumar"
    assert inv_data["religion_name"] is None
    assert inv_data["caste_name"] is None

    # Admin gets full religion_name and caste_name
    admin_res = client.get(f"/api/cases/{case.id}/complainant", headers=admin_headers)
    assert admin_res.status_code == 200
    admin_data = admin_res.json()
    assert admin_data["religion_name"] == "Hinduism"
    assert admin_data["caste_name"] == "General"


def test_fir_details_and_chargesheet_endpoints(client, db_session, investigator_headers):
    case = models.Case(
        case_id="CR-2026-FIRTEST",
        title="FIR Details Test Case",
        crime_type="Burglary",
        district="Bengaluru City",
        station_name="PS Central",
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    # Create FIR Details
    fir_res = client.post(
        f"/api/cases/{case.id}/fir-details",
        json={"case_no": "2026/0099"},
        headers=investigator_headers,
    )
    assert fir_res.status_code == 201
    fir_data = fir_res.json()
    assert fir_data["case_id"] == case.id
    assert len(fir_data["crime_no"]) == 18

    # Create Chargesheet
    cs_res = client.post(
        f"/api/cases/{case.id}/chargesheet",
        json={"cs_type": "A", "remarks": "Test chargesheet filed"},
        headers=investigator_headers,
    )
    assert cs_res.status_code == 201
    assert cs_res.json()["cs_type"] == "A"
