from datetime import datetime
from app import models

def test_offender_profiling_list_and_profile(client, db_session, investigator_headers):
    # Create two cases linked to the same suspect phone
    case1 = models.Case(
        case_id="CR-2026-OFF1",
        title="Burglary Case 1",
        crime_type="Burglary",
        district="Model Town",
        station_name="PS Model Town",
        severity=models.Severity.critical,
        incident_date=datetime.utcnow(),
    )
    case2 = models.Case(
        case_id="CR-2026-OFF2",
        title="Burglary Case 2",
        crime_type="Burglary",
        district="Model Town",
        station_name="PS Model Town",
        severity=models.Severity.high,
        incident_date=datetime.utcnow(),
    )
    db_session.add_all([case1, case2])
    db_session.flush()

    person1 = models.Person(
        case_id=case1.id,
        name="Repeat Suspect",
        role_in_case="suspect",
        phone_number="+91-9999900000",
        mo_tags="night-burglary",
        is_flagged_offender=True,
    )
    person2 = models.Person(
        case_id=case2.id,
        name="Repeat Suspect",
        role_in_case="suspect",
        phone_number="+91-9999900000",
        mo_tags="night-burglary",
        is_flagged_offender=True,
    )
    db_session.add_all([person1, person2])
    db_session.commit()

    # List offenders
    res = client.get("/api/offenders", headers=investigator_headers)
    assert res.status_code == 200
    offenders = res.json()
    assert len(offenders) >= 1
    target = next((o for o in offenders if o["name"] == "Repeat Suspect"), None)
    assert target is not None
    assert target["case_count"] == 2
    assert target["risk_score"] > 30

    # Get offender detail profile
    detail_res = client.get(f"/api/offenders/{person1.id}", headers=investigator_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["person_id"] == person1.id
    assert len(detail["linked_cases"]) == 2


def test_demographic_analytics_and_correlation(client, admin_headers):
    res = client.get("/api/analytics/demographics", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "by_age_group" in data
    assert "by_gender" in data

    corr_res = client.get("/api/analytics/socioeconomic-correlation", headers=admin_headers)
    assert corr_res.status_code == 200
    corr_data = corr_res.json()
    assert "disclaimer" in corr_data
    assert "district_correlations" in corr_data


def test_financial_accounts_transactions_and_trail(client, db_session, investigator_headers):
    # Create case
    case = models.Case(
        case_id="CR-2026-FIN",
        title="OTP Phishing Case",
        crime_type="Cybercrime",
        district="Civil Lines",
        station_name="PS Civil Lines",
        severity=models.Severity.high,
        incident_date=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.flush()

    # Create accounts
    acc1 = models.FinancialAccount(bank_name="HDFC Bank", account_number_masked="XXXX-1111", account_type="savings")
    acc2 = models.FinancialAccount(bank_name="SBI", account_number_masked="XXXX-2222", account_type="wallet")
    db_session.add_all([acc1, acc2])
    db_session.flush()

    # Create transaction
    tx = models.FinancialTransaction(
        from_account_id=acc1.id,
        to_account_id=acc2.id,
        amount=50000.0,
        case_id=case.id,
        flagged_reason="Rapid withdrawal after phishing report",
    )
    db_session.add(tx)
    db_session.commit()

    # Get financial trail
    trail_res = client.get(f"/api/finance/trail/{case.id}", headers=investigator_headers)
    assert trail_res.status_code == 200
    trail = trail_res.json()
    assert trail["case_id"] == case.id
    assert trail["total_amount"] == 50000.0
    assert trail["flagged_count"] == 1
    assert len(trail["nodes"]) == 2
    assert len(trail["edges"]) == 1
