"""Testes dos detectores de componente sobre imagens sinteticas."""

from __future__ import annotations

import pytest

from circuit_inspector.detection.button_detector import ButtonDetector
from circuit_inspector.detection.capacitor_detector import CapacitorDetector
from circuit_inspector.detection.ldr_detector import LdrDetector
from circuit_inspector.detection.led_detector import LedDetector
from circuit_inspector.detection.potentiometer_detector import PotentiometerDetector
from circuit_inspector.detection.registry import DetectorRegistry
from circuit_inspector.detection.resistor_detector import ResistorDetector
from circuit_inspector.detection.wire_detector import WireDetector
from circuit_inspector.models import ComponentKind, Hole, Point

from tests.fixtures.synthetic_board import (
    ComponentSpec,
    build_board,
    default_circuit,
    full_circuit,
    full_circuit_layout,
)


def _closest_terminal_distance(terminals, target: Point) -> float:
    return min(t.pixel.distance_to(target) for t in terminals)


class TestWireDetector:
    def test_detects_colored_wire_with_endpoints(self) -> None:
        spec = ComponentSpec(
            ComponentKind.WIRE, "wire:red", Hole(2, row="j"), Hole(2, rail="+")
        )
        board = build_board([spec])

        components = WireDetector().detect(board.image)

        assert len(components) == 1
        wire = components[0]
        assert wire.kind == ComponentKind.WIRE
        assert wire.label == "wire:red"
        # Os terminais detectados ficam proximos dos furos verdadeiros.
        truth_a = board.grid.hole_to_pixel(spec.hole_a)
        truth_b = board.grid.hole_to_pixel(spec.hole_b)
        assert _closest_terminal_distance(wire.terminals, truth_a) < 12.0
        assert _closest_terminal_distance(wire.terminals, truth_b) < 12.0


class TestLedDetector:
    def test_detects_led(self) -> None:
        spec = ComponentSpec(
            ComponentKind.LED, "led:blue", Hole(2, row="e"), Hole(3, row="e")
        )
        board = build_board([spec])
        components = LedDetector().detect(board.image)
        assert len(components) == 1
        assert components[0].kind == ComponentKind.LED


class TestLdrDetector:
    def test_detects_ldr(self) -> None:
        spec = ComponentSpec(
            ComponentKind.LDR, "ldr", Hole(5, row="e"), Hole(6, row="e")
        )
        board = build_board([spec])
        components = LdrDetector().detect(board.image)
        assert len(components) == 1
        assert components[0].kind == ComponentKind.LDR


class TestResistorDetector:
    def test_detects_resistor(self) -> None:
        spec = ComponentSpec(
            ComponentKind.RESISTOR, "resistor", Hole(8, row="c"), Hole(10, row="c")
        )
        board = build_board([spec])
        components = ResistorDetector().detect(board.image)
        assert len(components) == 1
        assert components[0].kind == ComponentKind.RESISTOR


class TestGreenWire:
    def test_detects_green_wire(self) -> None:
        spec = ComponentSpec(
            ComponentKind.WIRE, "wire:green", Hole(4, row="a"), Hole(7, row="a")
        )
        board = build_board([spec])
        components = WireDetector().detect(board.image)
        assert len(components) == 1
        assert components[0].label == "wire:green"


class TestRedLed:
    def test_detects_red_led_with_label(self) -> None:
        spec = ComponentSpec(
            ComponentKind.LED, "led:red", Hole(2, row="e"), Hole(3, row="e")
        )
        board = build_board([spec])
        components = LedDetector().detect(board.image)
        assert len(components) == 1
        assert components[0].label == "led:red"


class TestCapacitorDetector:
    def test_detects_capacitor(self) -> None:
        spec = ComponentSpec(
            ComponentKind.CAPACITOR, "capacitor", Hole(3, row="c"), Hole(5, row="c")
        )
        board = build_board([spec])
        components = CapacitorDetector().detect(board.image)
        assert len(components) == 1
        assert components[0].kind == ComponentKind.CAPACITOR


class TestPotentiometerDetector:
    def test_detects_potentiometer(self) -> None:
        spec = ComponentSpec(
            ComponentKind.POTENTIOMETER,
            "potentiometer",
            Hole(3, row="h"),
            Hole(7, row="h"),
        )
        board = build_board(
            [spec], layout=full_circuit_layout()
        )
        components = PotentiometerDetector().detect(board.image)
        assert len(components) == 1
        assert components[0].kind == ComponentKind.POTENTIOMETER


class TestButtonDetector:
    def test_detects_button(self) -> None:
        spec = ComponentSpec(
            ComponentKind.BUTTON, "button", Hole(8, row="c"), Hole(9, row="c")
        )
        board = build_board([spec])
        components = ButtonDetector().detect(board.image)
        assert len(components) == 1
        assert components[0].kind == ComponentKind.BUTTON


class TestRegistry:
    def test_detect_all_finds_each_component(self) -> None:
        board = build_board(default_circuit())
        components = DetectorRegistry.default().detect_all(board.image)

        kinds = [c.kind for c in components]
        assert kinds.count(ComponentKind.WIRE) == 3
        assert kinds.count(ComponentKind.LED) == 1
        assert kinds.count(ComponentKind.LDR) == 0
        assert kinds.count(ComponentKind.RESISTOR) == 1
        # Novos tipos nao devem aparecer espuriamente no circuito simples.
        assert kinds.count(ComponentKind.CAPACITOR) == 0
        assert kinds.count(ComponentKind.POTENTIOMETER) == 0
        assert kinds.count(ComponentKind.BUTTON) == 0

    def test_detect_all_on_full_circuit(self) -> None:
        board = build_board(full_circuit(), layout=full_circuit_layout())
        labels = sorted(c.label for c in DetectorRegistry.default().detect_all(board.image))
        assert labels == [
            "button",
            "capacitor",
            "ldr",
            "led:blue",
            "led:red",
            "potentiometer",
            "resistor",
            "wire:black",
            "wire:green",
            "wire:orange",
            "wire:red",
        ]
