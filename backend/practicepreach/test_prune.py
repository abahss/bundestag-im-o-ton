from unittest.mock import Mock

from practicepreach.updater import _maybe_prune


def test_disabled_by_default_never_prunes():
    rag = Mock()
    assert _maybe_prune(rag, n_embedded=100, prune_weeks=None) == 0
    rag.prune_speeches_before.assert_not_called()


def test_skips_when_nothing_embedded():
    rag = Mock()
    assert _maybe_prune(rag, n_embedded=0, prune_weeks=52) == 0
    rag.prune_speeches_before.assert_not_called()


def test_prunes_when_enabled_and_new_data():
    rag = Mock()
    rag.prune_speeches_before.return_value = 7
    assert _maybe_prune(rag, n_embedded=10, prune_weeks=52) == 7
    rag.prune_speeches_before.assert_called_once()
