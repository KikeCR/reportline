"""Smoke test: scripts/explain_queries.py must actually run against real
seeded data and print IXSCAN-backed plans, not just parse without crashing.
"""

import pytest

from scripts.explain_queries import main
from scripts.seed import seed

pytestmark = pytest.mark.integration


def test_explain_queries_runs_and_reports_index_scans(db, capsys):
    seed()

    exit_code = main()

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "P7: full graph read" in output
    assert "P6: manager permission-scope subtree" in output
    assert "P2: get_descendants via $graphLookup" in output
    assert "IXSCAN" in output
