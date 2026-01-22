from pathlib import Path

import pytest


class TestDataPaths:
    def __init__(self, test_dir: Path):
        self.test_dir = test_dir
        self.data = test_dir / "data"

    def config(self, test: str, kind: str) -> Path:
        if (test not in ["baseline", "override"]) or kind not in ["config", "expected"]:
            raise ValueError(
                "'Test' must be 'baseline' or 'override', and 'kind' must be 'config' or 'expected'."
            )
        return self.data / "config" / f"{test}_{kind}.yaml"

    def model_input(self) -> Path:
        return self.data / "input" / "pysnobal_test_input_rcew.csv"

    def model_expected(self) -> Path:
        return self.data / "expected" / "pysnobal_test_output_rcew.csv"


@pytest.fixture
def test_data(request):
    test_dir = Path(request.fspath).parent
    return TestDataPaths(test_dir)
