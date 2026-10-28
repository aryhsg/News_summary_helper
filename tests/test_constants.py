from constants import (
    ALL_CATEGORIES,
    CATE_SUMMARY_CATEGORIES,
    BATCH_SUMMARY_CATEGORIES,
    SANDBOX_CATEGORIES,
)


def test_cate_summary_categories_is_subset_of_all():
    assert set(CATE_SUMMARY_CATEGORIES) <= set(ALL_CATEGORIES)


def test_batch_summary_categories_is_subset_of_all():
    assert set(BATCH_SUMMARY_CATEGORIES) <= set(ALL_CATEGORIES)


def test_sandbox_categories_is_subset_of_all():
    assert set(SANDBOX_CATEGORIES) <= set(ALL_CATEGORIES)


def test_no_duplicate_categories_within_each_list():
    for categories in (ALL_CATEGORIES, CATE_SUMMARY_CATEGORIES, BATCH_SUMMARY_CATEGORIES, SANDBOX_CATEGORIES):
        assert len(categories) == len(set(categories))
