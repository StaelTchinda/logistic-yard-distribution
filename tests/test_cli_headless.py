from src.cli import main


def test_list_runs(capsys):
    assert main(["--list"]) == 0
    out = capsys.readouterr().out
    assert "simple_test_data" in out and "test0_2275" in out


def test_run_headless_prints_score(capsys):
    rc = main(
        [
            "--run",
            "--yard",
            "small",
            "--dataset",
            "simple_test_data",
            "--strategy",
            "test0_2275",
        ]
    )
    assert rc == 0
    assert "TOTAL" in capsys.readouterr().out


def test_compare_headless(capsys):
    rc = main(["--compare", "--yard", "small", "--dataset", "simple_test_data"])
    assert rc == 0
    assert "comparison" in capsys.readouterr().out.lower()


def test_run_unknown_strategy_errors(capsys):
    rc = main(["--run", "--yard", "small", "--dataset", "simple_test_data", "--strategy", "nope"])
    assert rc == 2
