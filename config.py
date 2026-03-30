import json
from dataclasses import dataclass
from pathlib import Path

_CONFIG_DIR = Path(__file__).resolve().parent


@dataclass
class WaveSpec:
    delay_sec: float
    count: int
    unit_type: str
    interval_sec: float


@dataclass
class MapSpec:
    nodes: list[tuple[float, float]]
    edges: list[tuple[int, int]]
    spawn_node_index: int
    goal_node_index: int


@dataclass
class LevelSpec:
    id: int
    name: str
    map: MapSpec
    waves: list[WaveSpec]


@dataclass
class GameConfig:
    levels: list[LevelSpec]


def _parse_waves(raw: list[dict]) -> list[WaveSpec]:
    return [
        WaveSpec(
            delay_sec=w["delay_sec"],
            count=w["count"],
            unit_type=w["type"],
            interval_sec=w["interval_sec"],
        )
        for w in raw
    ]


def _parse_map(raw: dict) -> MapSpec:
    nodes = [(n["x"], n["y"]) for n in raw["nodes"]]
    edges = [(e[0], e[1]) for e in raw["edges"]]
    return MapSpec(
        nodes=nodes,
        edges=edges,
        spawn_node_index=raw["spawn_node_index"],
        goal_node_index=raw["goal_node_index"],
    )


def _parse_level(raw: dict) -> LevelSpec:
    return LevelSpec(
        id=raw["id"],
        name=raw["name"],
        map=_parse_map(raw["map"]),
        waves=_parse_waves(raw["waves"]),
    )


def load_game_config() -> GameConfig:
    path = _CONFIG_DIR / "game.json"
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    levels = [_parse_level(lvl) for lvl in data["levels"]]
    return GameConfig(levels=levels)