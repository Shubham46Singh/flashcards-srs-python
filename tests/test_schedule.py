
from datetime import date, datetime, timedelta, timezone

import pytest

from app.schedule import (
    CardError,
    apply_answer,
    deck_summary,
    due_cards,
    due_date,
    is_due,
    is_pass,
    is_repeat_in_same_day,
    next_ease,
    next_interval,
    overdue_days,
    queue_for,
    review,
    study_day,
    validate_grade,
)


@pytest.mark.parametrize("grade,expected", [
    (0, 1.7),
    (1, 1.96),
    (2, 2.18),
    (3, 2.36),
    (4, 2.5),
    (5, 2.6),
])
def test_next_ease_all_grades(grade, expected):
    assert next_ease(2.5, grade) == pytest.approx(expected)


def test_ease_floor_after_ten_failures():
    ease = 2.5
    for _ in range(10):
        ease = next_ease(ease, 0)
    assert ease == 1.3


def test_ease_has_no_ceiling():
    ease = 2.5
    for _ in range(30):
        ease = next_ease(ease, 5)
    assert ease > 2.5


def test_pass_boundary():
    assert is_pass(3) is True
    assert is_pass(2) is False


@pytest.mark.parametrize("grade", [-1, 6, "invalid", None])
def test_invalid_grades(grade):
    with pytest.raises(CardError):
        validate_grade(grade)


def test_valid_grade():
    assert validate_grade(5) == 5


def test_review_intervals():
    card = {}
    first = review(card, 5)
    second = review(first, 5)
    third = review(second, 5)

    assert first["interval"] == 1
    assert second["interval"] == 6
    assert third["interval"] == round(6 * third["ease"])


def test_review_lapse():
    card = {"repetitions": 5, "ease": 2.5, "interval": 30}
    result = review(card, 0)

    assert result["repetitions"] == 0
    assert result["interval"] == 1
    assert result["ease"] == 1.7
    assert result["lapsed"] is True


def test_review_does_not_mutate_original():
    card = {"repetitions": 0, "ease": 2.5, "interval": 0}
    original = card.copy()

    review(card, 5)

    assert card == original


def test_next_interval():
    assert next_interval(10, 3, 2.5, False) == 1
    assert next_interval(0, 1, 2.5, True) == 1
    assert next_interval(1, 2, 2.5, True) == 6
    assert next_interval(6, 3, 2.5, True) == 15


IST = timezone(timedelta(hours=5, minutes=30))


def test_study_day_across_midnight():
    before = datetime(2026, 10, 9, 23, 58, tzinfo=IST)
    after = datetime(2026, 10, 10, 0, 2, tzinfo=IST)

    assert study_day(before) == study_day(after)
    assert study_day(after) == date(2026, 10, 9)


def test_study_day_four_am_boundary():
    before = datetime(2026, 10, 10, 3, 59, tzinfo=IST)
    after = datetime(2026, 10, 10, 4, 0, tzinfo=IST)

    assert study_day(before) == date(2026, 10, 9)
    assert study_day(after) == date(2026, 10, 10)


def test_study_day_invalid_input():
    with pytest.raises(CardError):
        study_day("not a datetime")


def test_repeat_in_same_day():
    before = datetime(2026, 10, 9, 23, 58, tzinfo=IST)
    after = datetime(2026, 10, 10, 0, 2, tzinfo=IST)

    assert is_repeat_in_same_day(before, after)
    assert not is_repeat_in_same_day(None, after)


def test_due_date():
    assert due_date(date(2026, 10, 9), 6) == date(2026, 10, 15)

    with pytest.raises(CardError):
        due_date(date(2026, 10, 9), -1)


def test_apply_answer_first_time():
    now = datetime(2026, 10, 10, 12, 0, tzinfo=IST)
    result = apply_answer({}, 5, now)

    assert result["same_session"] is False
    assert result["interval"] == 1
    assert result["due_on"] == date(2026, 10, 11)


def test_apply_answer_same_session():
    before = datetime(2026, 10, 9, 23, 58, tzinfo=IST)
    after = datetime(2026, 10, 10, 0, 2, tzinfo=IST)

    card = {"repetitions": 2, "ease": 2.5, "interval": 6}
    result = apply_answer(card, 5, after, last_reviewed=before)

    assert result["same_session"] is True
    assert result["interval"] == 6
    assert result["repetitions"] == 2
    assert result["ease"] == 2.6


def test_due_cards_order():
    today = date(2026, 10, 10)
    cards = [
        {"id": 3, "due_on": date(2026, 10, 9), "ease": 2.5},
        {"id": 2, "due_on": date(2026, 10, 8), "ease": 2.5},
        {"id": 1, "due_on": date(2026, 10, 8), "ease": 1.5},
        {"id": 4, "due_on": date(2026, 10, 11), "ease": 1.3},
    ]

    assert queue_for(cards, today) == [1, 2, 3]
    assert [c["id"] for c in due_cards(cards, today, 2)] == [1, 2]


def test_due_helpers():
    today = date(2026, 10, 10)
    card = {"id": 1, "due_on": date(2026, 10, 8)}

    assert is_due(card, today)
    assert overdue_days(card, today) == 2
    assert is_due({"id": 2}, today)


def test_deck_summary():
    today = date(2026, 10, 10)
    cards = [
        {"id": 1, "due_on": None},
        {"id": 2, "due_on": today, "repetitions": 1, "interval": 1},
        {"id": 3, "due_on": date(2026, 10, 20), "repetitions": 4, "interval": 30},
    ]

    summary = deck_summary(cards, today)

    assert summary["cards"] == 3
    assert summary["new"] == 1
    assert summary["due_today"] == 2
    assert summary["learning"] == 1
    assert summary["mature"] == 1
