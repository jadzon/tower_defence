import json
from dataclasses import dataclass
from pathlib import Path

_CONFIG_DIR = Path(__file__).resolve().parent

@dataclass
class EconomySpec:
    starting_gold: int
    gold_generation: int
    sell_return_ratio: float
    tower_costs: dict[str,int]
    bullet_costs: dict[str,int]
    kill_reward: dict[str,int]

@dataclass
class SpawnSpec:
    unit_type: str
    count: int

@dataclass
class WaveSpec:
    delay_sec: float
    interval_sec: float
    spawns: list[SpawnSpec]

@dataclass
class RoundSpec:
    delay_sec: float
    waves: list[WaveSpec]


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
    rounds: list[RoundSpec]

@dataclass
class GameConfig:
    levels: list[LevelSpec]
    economy: EconomySpec

def _parse_spawns(raw: list[dict]) -> list[SpawnSpec]:
    return [
        SpawnSpec(
            unit_type = s["type"],
            count = s["count"],
        )
        for s in raw
    ]

def _parse_wave(raw: dict) -> WaveSpec:
    return WaveSpec(
        delay_sec=raw["delay_sec"],
        spawns=_parse_spawns(raw["spawns"]),
        interval_sec=float(raw.get("interval_sec", 0.1)),
    )
def _parse_round(raw: dict) -> RoundSpec:
    return RoundSpec(
        delay_sec=raw["delay_sec"],
        waves=[_parse_wave(w) for w in raw["waves"]],
    )

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
    rounds = [_parse_round(r) for r in raw["rounds"]]
    return LevelSpec(
        id=raw["id"],
        name=raw["name"],
        map=_parse_map(raw["map"]),
        rounds=rounds,
)

def _parse_economy(raw: dict) ->EconomySpec:
    return EconomySpec(
        starting_gold = raw["starting_gold"],
        gold_generation = raw["gold_generation"],
        sell_return_ratio = raw["sell_return_ratio"],
        tower_costs = raw["tower_costs"],
        bullet_costs = raw["bullet_costs"],
        kill_reward = raw["kill_reward"]
    )


def load_game_config() -> GameConfig:
    path = _CONFIG_DIR / "game.json"
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    levels = [_parse_level(lvl) for lvl in data["levels"]]
    economy = _parse_economy(data["global"]["economy"])

    return GameConfig(levels=levels,economy=economy)