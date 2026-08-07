def test_chat_session_lifecycle(client, investigator_headers):
    # Create session
    res = client.post("/api/chat/sessions", headers=investigator_headers)
    assert res.status_code == 200
    session_id = res.json()["id"]

    # Send message (without Anthropic key, gracefully degrades with fallback message)
    msg_res = client.post(
        f"/api/chat/sessions/{session_id}/messages",
        json={"content": "Are there any recent burglary incidents?"},
        headers=investigator_headers,
    )
    assert msg_res.status_code == 200
    answer = msg_res.json()
    assert "user_message" in answer
    assert "assistant_message" in answer

    # Get session messages
    history_res = client.get(f"/api/chat/sessions/{session_id}/messages", headers=investigator_headers)
    assert history_res.status_code == 200
    assert len(history_res.json()) == 2
