from app.learning import SCORE_DELTAS


def test_mastery_deltas_are_bounded_and_ordered():
    assert SCORE_DELTAS["correct"] > SCORE_DELTAS["correct_after_hint"] > SCORE_DELTAS["partially_correct"]
    assert SCORE_DELTAS["incorrect"] < 0


def test_weekly_report_has_database_statistics(client, student):
    report = client.get(f"/api/v1/learning/{student['id']}/weekly-report")
    assert report.status_code == 200
    assert report.json()["attempts"] == 0
    assert report.json()["accuracy"] == 0

