"""O gate deve rejeitar cada limiar separadamente, sem arredondamento."""
import pytest

from scripts.check_coverage import main


@pytest.mark.parametrize("lines,branches,expected", [
    (8500, 8000, 0),
    (8499, 10000, 1),
    (10000, 7999, 1),
    (10000, 10000, 0),
])
def test_coverage_thresholds(tmp_path, lines, branches, expected):
    report = tmp_path / "coverage.xml"
    report.write_text(
        f'<coverage lines-covered="{lines}" lines-valid="10000" '
        f'branches-covered="{branches}" branches-valid="10000"/>', encoding="utf-8",
    )
    assert main(report) == expected


@pytest.mark.parametrize("lines,branches", [(0, 100), (100, 0)])
def test_coverage_rejects_uninstrumented_report(tmp_path, lines, branches):
    report = tmp_path / "coverage.xml"
    report.write_text(
        f'<coverage lines-covered="{lines}" lines-valid="{lines}" '
        f'branches-covered="{branches}" branches-valid="{branches}"/>', encoding="utf-8",
    )
    assert main(report) == 1
