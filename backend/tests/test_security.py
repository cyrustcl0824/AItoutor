def test_unauthenticated_textbook_page_is_denied(client):
    client.cookies.clear()
    assert client.get("/api/v1/textbooks/pages/not-a-page/image").status_code == 401


def test_student_cannot_be_read_across_families(client, student):
    client.cookies.clear()
    client.post("/api/v1/auth/register", json={"email": "other@example.com", "password": "another-secure-password", "family_name": "另一个家庭"})
    response = client.patch(f"/api/v1/students/{student['id']}", json={"display_name": "stolen"})
    assert response.status_code == 404

