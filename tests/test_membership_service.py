from app.services.membership_service import build_membership_summary, get_membership_rank, get_next_rank_info


def test_get_membership_rank_thresholds():
    assert get_membership_rank(0) == "Member"
    assert get_membership_rank(999_999) == "Member"
    assert get_membership_rank(1_000_000) == "Silver"
    assert get_membership_rank(5_000_000) == "Gold"
    assert get_membership_rank(15_000_000) == "Platinum"
    assert get_membership_rank(30_000_000) == "Diamond"


def test_get_next_rank_info_examples():
    zero_case = get_next_rank_info(0)
    assert zero_case["next_rank"] == "Silver"
    assert zero_case["amount_to_next_rank"] == 1_000_000

    silver_case = get_next_rank_info(1_200_000)
    assert silver_case["next_rank"] == "Gold"
    assert silver_case["amount_to_next_rank"] == 3_800_000

    platinum_case = get_next_rank_info(29_000_000)
    assert platinum_case["next_rank"] == "Diamond"
    assert platinum_case["amount_to_next_rank"] == 1_000_000

    diamond_case = get_next_rank_info(30_000_000)
    assert diamond_case["next_rank"] is None
    assert diamond_case["amount_to_next_rank"] == 0
    assert diamond_case["progress_percent"] == 100.0


def test_build_membership_summary_shape():
    summary = build_membership_summary(7_200_000)

    assert summary.rank == "Gold"
    assert summary.total_spent == 7_200_000
    assert summary.next_rank == "Platinum"
    assert summary.amount_to_next_rank == 7_800_000
    assert summary.progress_percent > 0
    assert len(summary.benefits) >= 1
    assert len(summary.tiers) == 5
