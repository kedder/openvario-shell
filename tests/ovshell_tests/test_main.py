from ovshell import main


def test_debounce_esc() -> None:
    assert main.debounce_esc(["down"], []) == ["down"]
    assert main.debounce_esc(["down", "down"], []) == ["down", "down"]
    assert main.debounce_esc(["esc"], []) == ["esc"]
    assert main.debounce_esc(["esc", "esc"], []) == ["esc"]
    assert main.debounce_esc(["esc", "esc", "esc"], []) == ["esc", "esc"]
    assert main.debounce_esc(["esc", "down", "esc"], []) == ["esc", "down", "esc"]
