import json
from dataclasses import dataclass
from pathlib import Path

_CONFIG_DIR = Path(__file__).resolve().parent

@dataclass
class EconomySpec:
    starting_gold: int
    gold_generation: int
    tower_costs: dict[str,int]
    kill_reward: dict[str,int]


@dataclass
class WaveSpec:
    delay_sec: float
    count: int
    unit_type: str
    interval_sec: float


@dataclass
class MapSpec:
    nodes: list[tuple[int,int]]
    edges: list[tuple[int, int]]
    spawn_node_index: int
    goal_node_index: int
    tower_slots: list[tuple[int,int]]


@dataclass
class LevelSpec:
    id: int
    name: str
    map: MapSpec
    waves: list[WaveSpec]


@dataclass
class GameConfig:
    levels: list[LevelSpec]
    economy: EconomySpec


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
    tower_slots = [(s["x"], s["y"]) for s in raw["tower_slots"]]
    return MapSpec(
        nodes=nodes,
        edges=edges,
        spawn_node_index=raw["spawn_node_index"],
        goal_node_index=raw["goal_node_index"],
        tower_slots= tower_slots
    )


def _parse_level(raw: dict) -> LevelSpec:
    return LevelSpec(
        id=raw["id"],
        name=raw["name"],
        map=_parse_map(raw["map"]),
        waves=_parse_waves(raw["waves"]),
    )

def _parse_economy(raw: dict) ->EconomySpec:
    return EconomySpec(
        starting_gold = raw["starting_gold"],
        gold_generation = raw["gold_generation"],
        tower_costs = raw["tower_costs"],
        kill_reward = raw["kill_reward"]
    )


def load_game_config() -> GameConfig:
    path = _CONFIG_DIR / "game.json"
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    levels = [_parse_level(lvl) for lvl in data["levels"]]
    economy = _parse_economy(data["global"]["economy"])

    return GameConfig(levels=levels,economy=economy)