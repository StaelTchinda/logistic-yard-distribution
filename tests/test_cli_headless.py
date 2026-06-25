from src.cli import main


def test_list_runs(capsys):
    assert main(["--list"]) == 0
    out = capsys.readouterr().out
    assert "first_fit" in out and "mixed" in out


def test_run_headless_prints_score(capsys):
    rc = main(["--run", "--yard", "main", "--dataset", "mixed", "--strategy", "first_fit"])
    assert rc == 0
    assert "TOTAL" in capsys.readouterr().out


def test_compare_headless(capsys):
    rc = main(["--compare", "--yard", "main", "--dataset", "mixed"])
    assert rc == 0
    assert "comparison" in capsys.readouterr().out.lower()


def test_run_unknown_strategy_errors(capsys):
    rc = main(["--run", "--yard", "main", "--dataset", "mixed", "--strategy", "nope"])
    assert rc == 2
