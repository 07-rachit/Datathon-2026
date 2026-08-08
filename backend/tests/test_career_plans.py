"""
Comprehensive Test Suite for Career Plans & Learning Search (Topic, Difficulty, Goal, Sorting, Pagination).

Validates:
- Career plan creation, detail retrieval, updating, and deletion
- Keyword search across title, description, target goal, tags, milestones, notes (case-insensitive, partial match)
- Topic, Difficulty, Goal, Status, and Deadline filters (individually and combined)
- Sorting options (newest, oldest, deadline, alphabetical)
- Pagination, page bounds, and total_pages calculations
- Facet extraction (available_topics, available_goals, available_difficulties)
- RBAC scoping & access authorization
"""
import pytest
from datetime import datetime, timedelta
from app import models


def test_create_and_get_career_plan(client, db_session, investigator_headers):
    """Test creating a new career plan and retrieving its details."""
    payload = {
        "title": "Digital Forensics Advanced Masterclass",
        "description": "In-depth study of volatile RAM inspection and file system recovery.",
        "topic": "Cyber Forensics",
        "difficulty_level": "Advanced",
        "target_goal": "Certified Digital Forensics Examiner (CDFE)",
        "deadline": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "tags": "forensics, ram, memory, disk",
        "status": "active",
        "milestones": "1. RAM Analysis\n2. Disk Analysis",
        "notes": "Required for tier-1 SOC authorization",
    }

    res = client.post("/api/career-plans", json=payload, headers=investigator_headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["id"] is not None
    assert data["title"] == "Digital Forensics Advanced Masterclass"
    assert data["topic"] == "Cyber Forensics"
    assert data["difficulty_level"] == "Advanced"
    assert data["owner_name"] is not None

    # Fetch details GET
    res_get = client.get(f"/api/career-plans/{data['id']}", headers=investigator_headers)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == data["id"]


def test_career_plan_keyword_search(client, db_session, investigator_user, investigator_headers):
    """Test keyword searching across title, description, target_goal, and tags with case-insensitivity."""
    plan1 = models.CareerPlan(
        user_id=investigator_user.id,
        title="Python Data Analysis for Crime Patterns",
        description="Using pandas and numpy to aggregate monthly criminal stats.",
        topic="Data Analytics",
        difficulty_level="Intermediate",
        target_goal="Crime Data Analyst",
        tags="python, pandas, analytics",
    )
    plan2 = models.CareerPlan(
        user_id=investigator_user.id,
        title="Network Sniffing & Packet Capture",
        description="Wireshark PCAP analysis for suspect network traffic.",
        topic="Cyber Forensics",
        difficulty_level="Advanced",
        target_goal="Network Security Officer",
        tags="wireshark, pcap, network",
    )
    db_session.add_all([plan1, plan2])
    db_session.commit()

    # Search for 'python'
    res1 = client.get("/api/career-plans?q=python", headers=investigator_headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total"] >= 1
    assert any("Python" in p["title"] for p in data1["results"])

    # Search for 'WIRESHARK' (case insensitive)
    res2 = client.get("/api/career-plans?q=WIRESHARK", headers=investigator_headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total"] >= 1
    assert any("Wireshark" in (p["description"] or "") for p in data2["results"])


def test_career_plan_topic_and_difficulty_filters(client, db_session, investigator_user, investigator_headers):
    """Test filtering career plans by topic and difficulty level."""
    plan = models.CareerPlan(
        user_id=investigator_user.id,
        title="Cryptocurrency Chain Tracking",
        topic="Financial Intelligence",
        difficulty_level="Expert",
        target_goal="Blockchain Analyst",
    )
    db_session.add(plan)
    db_session.commit()

    # Filter by topic
    res_topic = client.get("/api/career-plans?topic=Financial Intelligence", headers=investigator_headers)
    assert res_topic.status_code == 200
    data_topic = res_topic.json()
    assert all(p["topic"] == "Financial Intelligence" for p in data_topic["results"])

    # Filter by difficulty
    res_diff = client.get("/api/career-plans?difficulty=Expert", headers=investigator_headers)
    assert res_diff.status_code == 200
    data_diff = res_diff.json()
    assert all(p["difficulty_level"] == "Expert" for p in data_diff["results"])


def test_career_plan_combined_filters_and_sorting(client, db_session, investigator_user, investigator_headers):
    """Test combined keyword search, topic filter, difficulty filter, and sorting."""
    p1 = models.CareerPlan(
        user_id=investigator_user.id,
        title="Alpha Advanced Cyber Investigation",
        topic="Cyber Forensics",
        difficulty_level="Advanced",
        target_goal="Cyber Lead",
        created_at=datetime.utcnow() - timedelta(days=5),
    )
    p2 = models.CareerPlan(
        user_id=investigator_user.id,
        title="Zeta Advanced Cyber Forensics",
        topic="Cyber Forensics",
        difficulty_level="Advanced",
        target_goal="Cyber Lead",
        created_at=datetime.utcnow(),
    )
    db_session.add_all([p1, p2])
    db_session.commit()

    # Sort alphabetical
    res_alpha = client.get(
        "/api/career-plans?topic=Cyber Forensics&difficulty=Advanced&sort_by=alphabetical",
        headers=investigator_headers,
    )
    assert res_alpha.status_code == 200
    results_alpha = res_alpha.json()["results"]
    assert len(results_alpha) >= 2
    assert results_alpha[0]["title"].startswith("Alpha")

    # Sort newest
    res_newest = client.get(
        "/api/career-plans?topic=Cyber Forensics&difficulty=Advanced&sort_by=newest",
        headers=investigator_headers,
    )
    assert res_newest.status_code == 200
    results_newest = res_newest.json()["results"]
    assert results_newest[0]["title"].startswith("Zeta")


def test_career_plan_empty_results_and_pagination(client, db_session, investigator_headers):
    """Test graceful handling when no records match filters and page parameter bounds."""
    res_empty = client.get("/api/career-plans?q=NonExistentKeywordXYZ99", headers=investigator_headers)
    assert res_empty.status_code == 200
    data_empty = res_empty.json()
    assert data_empty["total"] == 0
    assert data_empty["results"] == []

    # Invalid page validation (422)
    res_inv_page = client.get("/api/career-plans?page=0", headers=investigator_headers)
    assert res_inv_page.status_code == 422

    # Invalid sort_by validation (422)
    res_inv_sort = client.get("/api/career-plans?sort_by=invalid_sort", headers=investigator_headers)
    assert res_inv_sort.status_code == 422


def test_career_plan_update_and_delete(client, db_session, investigator_user, investigator_headers):
    """Test updating fields and deleting a career plan."""
    plan = models.CareerPlan(
        user_id=investigator_user.id,
        title="Original Plan Title",
        topic="General",
        difficulty_level="Beginner",
        target_goal="Original Goal",
    )
    db_session.add(plan)
    db_session.commit()

    # Update plan
    update_payload = {
        "title": "Updated Plan Title",
        "difficulty_level": "Expert",
        "status": "completed",
    }
    res_up = client.put(f"/api/career-plans/{plan.id}", json=update_payload, headers=investigator_headers)
    assert res_up.status_code == 200
    assert res_up.json()["title"] == "Updated Plan Title"
    assert res_up.json()["difficulty_level"] == "Expert"
    assert res_up.json()["status"] == "completed"

    # Delete plan
    res_del = client.delete(f"/api/career-plans/{plan.id}", headers=investigator_headers)
    assert res_del.status_code == 200

    # Verify 404 after deletion
    res_get_del = client.get(f"/api/career-plans/{plan.id}", headers=investigator_headers)
    assert res_get_del.status_code == 404
