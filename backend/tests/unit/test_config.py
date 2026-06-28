"""Testes da configuracao central."""

from __future__ import annotations

from circuit_inspector.config import DEFAULT_CONFIG, BoardLayout, InspectorConfig


def test_board_rows_are_ordered_top_to_bottom() -> None:
    layout = BoardLayout()
    assert layout.rows == ("j", "i", "h", "g", "f", "e", "d", "c", "b", "a")


def test_board_column_count() -> None:
    layout = BoardLayout(min_column=1, max_column=63)
    assert layout.column_count == 63


def test_default_config_is_inspector_config() -> None:
    assert isinstance(DEFAULT_CONFIG, InspectorConfig)


def test_red_profile_is_split_for_hue_wraparound() -> None:
    assert DEFAULT_CONFIG.colors.red.is_split is True
    assert DEFAULT_CONFIG.colors.led_blue.is_split is False


def test_wire_colors_contains_expected_keys() -> None:
    assert set(DEFAULT_CONFIG.colors.wire_colors()) == {
        "red",
        "orange",
        "green",
        "black",
    }


def test_led_colors_contains_expected_keys() -> None:
    assert set(DEFAULT_CONFIG.colors.led_colors()) == {"blue", "red"}
