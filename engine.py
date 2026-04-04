from __future__ import annotations
import math
from platform import node
from timeit import Timer
from xxlimited import new

from config import load_game_config

class Game:
    def __init__(self):

        cfg = load_game_config()

        self.levels = cfg.levels

        # level 1
        self.nodes: list[Node] =  []
        # get nodes
        for n_x, n_y in cfg.levels[0].map.nodes:
            self.nodes.append(Node(n_x,n_y))
        
        # get node relations
        for a,b in cfg.levels[0].map.edges:
            self.nodes[a].add_neighbor(self.nodes[b])

        self.first_node = self.nodes[cfg.levels[0].map.spawn_node_index]
        self.last_node = self.nodes[cfg.levels[0].map.goal_node_index]

        self.waves = cfg.levels[0].waves
        self.elapsed = 0
        self.wave_index = 0
        self.spawned_in_wave = 0
        self.next_spawn_at = 0
        
        self.units: list[Unit] = []
        self.dt = 1
        self.towers: list[Tower] = []
        self.tower_slots: list[TowerSlot] = [TowerSlot(x,y) for x,y in cfg.levels[0].map.tower_slots]
        self.bullets: list[Bullet] = []
        self.gold = cfg.economy.starting_gold
        self.gold_generation_per_sec = cfg.economy.gold_generation
        self.kill_reward: dict[str,int] = cfg.economy.kill_reward
        self.tower_costs: dict[str,int] = cfg.economy.tower_costs
        self.bullet_costs: dict[str,int] = cfg.economy.bullet_costs
        self.tower_sell_return_ratio: float = cfg.economy.sell_return_ratio
        self._gold_timer = 0
        self.stat_upgrade_costs: dict[str, int] = {
            "damage": 100,
            "range": 100,
            "fire-rate": 100,
        }
        self.class_spec_upgrade_costs: dict[str, int] = {
            "beam": 150,
            "vine": 200,
            "cluster-size":200
        }
        # self.place_tower(self.tower_slots[0],"basic")
        # self.place_tower(self.tower_slots[1],"rocketeer")
        self._place_tower(self.tower_slots[0],"beam")
        self._place_tower(self.tower_slots[1],"vine")
        self._place_tower(self.tower_slots[2],"rocketeer")
    def add_gold(self,dt):
        self._gold_timer += dt
        if self._gold_timer > 1:
            self.gold += self.gold_generation_per_sec
            self._gold_timer = 0
    def tick(self,dt):

        self.elapsed += dt
        self._process_waves()
        
        for t in self.towers:
            bullet = t.update(dt, self.units)
            if bullet is not None:
                self.bullets.append(bullet)

        for u in self.units:
            u.update(dt)
            

        for b in self.bullets:
            b_c = b.update(dt,self.units)
            if b_c is not None:
                self.bullets.extend(b_c)

        self._remove_dead_units()
        self._remove_finished_bullets()
        self.add_gold(dt)
        
    
    def _add_unit(self, spawn_node, unit_type):
        unit = create_unit(spawn_node,unit_type)
        self.units.append(unit)
    
    def _process_waves(self):
        waves = self.waves 
        if self.wave_index >= len(waves):
            return

        w = waves[self.wave_index]

        if self.elapsed < w.delay_sec:
            return

        if self.next_spawn_at is None:
            self.next_spawn_at = w.delay_sec

        while (
            self.spawned_in_wave < w.count
            and self.elapsed >= self.next_spawn_at
        ):
            self._add_unit(self.first_node, w.unit_type)
            self.spawned_in_wave += 1
            self.next_spawn_at += w.interval_sec 

        if self.spawned_in_wave >= w.count:
            self.wave_index += 1
            self.spawned_in_wave = 0
            self.next_spawn_at = None
    
    def _place_tower(self,tower_slot,tower_type):

        if tower_slot.occupied:
            return
        if tower_type == "basic":
            tower = BasicTower(tower_slot.x,tower_slot.y, self.last_node)
            tower_slot.add_tower(tower)
            self.towers.append(tower)
        elif tower_type == "rocketeer":
            tower = RocketeerTower(tower_slot.x,tower_slot.y,self.last_node)
            tower_slot.add_tower(tower)
            self.towers.append(tower)
        elif tower_type == "vine":
            tower = VineTower(tower_slot.x,tower_slot.y,self.last_node)
            tower_slot.add_tower(tower)
            self.towers.append(tower)
        else:
            tower = BeamTower(tower_slot.x,tower_slot.y,self.last_node)
            tower_slot.add_tower(tower)
            self.towers.append(tower)
    
    def buy_tower(self,tower_slot,tower_type):
        if tower_slot.occupied:
            return
        tower_cost = self.tower_costs[tower_type]
        if self.gold < tower_cost:
            return
        
        self.gold -= tower_cost
        self._place_tower(tower_slot,tower_type)
    
    def sell_tower(self, tower_slot):

        if not tower_slot.occupied:
            return
        
        self.towers = [t for t in self.towers if t is not tower_slot.tower]
        for b in tower_slot.tower.bullets:
            b.finished = True
        gold = self.tower_costs[tower_slot.tower.tower_type] * self.tower_sell_return_ratio
        gold  = math.trunc(gold)
        self.gold += gold
        tower_slot.remove_tower()
        

    
    def _remove_dead_units(self):
        def _check_unit_type(u):
            if isinstance(u,GruntUnit):
                return "grunt"
            elif isinstance(u, FastUnit):
                return "fast"
            else:
                return "tank"
        new_units = []
        for u in self.units:
            if u.killed:
                self.gold += self.kill_reward[_check_unit_type(u)]
            elif u.finished:
                print("penalty")
            else:
                new_units.append(u)
        self.units = new_units

        # dead_units = [u for u in self.units if u.killed]
        # self.units = [u for u in self.units if not u.finished]
    
    def _remove_finished_bullets(self):
        self.bullets= [b for b in self.bullets if not b.finished]

    
    def change_bullet_type(self,tower,b_type):

        cost = self.get_bullet_change_cost(tower,b_type)
        if self.gold >= cost:
            tower.change_bullet_type(b_type)
            self.gold -= cost
    
    def get_bullet_change_cost(self, tower, b_type) -> int:
        cost = self.bullet_costs[b_type] - self.bullet_costs[tower.bullet_type]
        if cost < 0:
            cost = math.trunc(cost * self.tower_sell_return_ratio)
        return cost
    def possible_upgrades(self,tower: Tower):
        return tower.possible_upgrades()
    
    def upgrade_cost(self,tower: Tower, upgrade: UpgradeSpec):
        if upgrade.kind == "bullet":
            basic_cost = self.get_bullet_change_cost(tower,upgrade.type)
            return basic_cost
        elif upgrade.kind == "stat":
            basic_cost = self.stat_upgrade_costs[upgrade.type]
            return basic_cost
        elif upgrade.kind =="class-spec":
            basic_cost = self.class_spec_upgrade_costs[upgrade.type]
            return basic_cost


    def apply_upgrade(self,tower: Tower,upgrade: UpgradeSpec):
        cost = self.upgrade_cost(tower,upgrade)
        if cost is None:
            return
        if cost > self.gold:
            return
        
        self.gold -= cost
        if upgrade.kind == "stat":
            if upgrade.type == "damage":
                tower.upgrade_damage()
            elif upgrade.type == "range":
                tower.upgrade_range()
            elif upgrade.type == "fire-rate":
                tower.upgrade_fire_rate()
            else:
                self.gold += cost
                return 
        elif upgrade.kind == "bullet":
            tower.change_bullet_type(upgrade.type)
        elif upgrade.kind == "class-spec":
            if upgrade.type == "beam" and isinstance(tower, BeamTower):
                tower.upgrade_beam_radius()
            elif upgrade.type == "vine" and isinstance(tower, VineTower):
                tower.vine_count += 1
            elif upgrade.type == "cluster-size"  and isinstance(tower, RocketeerTower):
                tower.rocket_cluster_size +=1
            else:
                self.gold += cost
                return 
        return

        

class Node:

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.neighbors = []
    
    def add_neighbor(self, neighbor):
        self.neighbors.append(neighbor)
        neighbor.neighbors.append(self)
    
    def get_neighbors(self):
        return self.neighbors
    
    def get_x(self):
        return self.x
    
    def get_y(self):
        return self.y
    
    def __eq__(self, other):

        if self.x == other.x and self.y == other.y:
            return True
        
        return False

    def __repr__(self):
        return f"Node({self.x}, {self.y})"


class Unit:
    
    def __init__(self, start_node, unit_type, speed, health):
        self.health = health
        self.current_node = start_node
        self.next_node = start_node.neighbors[0]
        self.unit_type = unit_type
        self.speed = speed
        self.x = start_node.x
        self.y = start_node.y
        self.visited_nodes = [start_node]
        self.finished = False
        self.killed = False
        self.slowed = False
        self.slow_factor = 0.5
        self.burn_hi = 1 #burn hit interval
        self.burning = False
        self.burning_timer = 0
        self.burning_damage = 1
        self.burning_time = 2.1
        self.burning_last_hi = 0
        self.poison_hi = 1 #poison hit interval
        self.poisoned = False
        self.poison_timer = 0
        self.poison_damage = 1
        self.poison_time = 2.1
        self.poison_last_hi = 0

    def update(self,dt):

        if self.next_node is None or self.finished:
            return
        self._update_effects(dt)
        dist_x = (self.next_node.x - self.x) 
        dist_y = (self.next_node.y - self.y)
        dist = math.sqrt(math.pow(dist_x,2) + math.pow(dist_y,2))

        if dist < 1:
            self.x = self.next_node.x
            self.y = self.next_node.y
            self.current_node = self.next_node
            if self.current_node not in self.visited_nodes:
                self.visited_nodes.append(self.current_node)
            self.next_node = self._choose_next_node()
            if self.next_node is None:
                self.finished = True
            return
        
        step = min(self.speed * dt, dist)
        self.x += (dist_x/dist) * step
        self.y += (dist_y/dist) * step

    def _choose_next_node(self):
        neighbors = self.current_node.neighbors
        for n in neighbors:
            if n not in self.visited_nodes:
                return n
            
        return None
    
    def take_damage(self, dmg):
        self.health -= dmg
        if self.health <=0:
            self.health = 0
            self.killed = True
            self.finished = True
        
        # print(f"{self.unit_type} HP: {self.health}")
    
    def add_slow_effect(self):
        self.speed = math.trunc(self.speed * (1-self.slow_factor))
        self.slowed = True

    def add_fire_effect(self, damage):
        self.burning = True
        self.burning_damage = damage
        self.burning_timer = 0
        self.nurn_last_hi = 0
    
    def add_poison_effect(self, damage):
        self.poisoned = True
        self.poison_damage = damage
        self.poison_timer = 0
        self.poison_last_hi = 0
    
    def remove_poison_effect(self):
        self.poisoned = False
        self.poison_damage = 1
    
    def remove_burning_effect(self):
        self.burning = False
        self.burning_damage = 1
    def _update_effects(self,dt):
        if self.poisoned:
            if self.poison_timer - self.poison_last_hi> self.poison_hi:
                self.take_damage(self.poison_damage)
                self.poison_last_hi +=self.poison_hi

            self.poison_timer += dt
            if self.poison_timer > self.poison_time:
                self.remove_poison_effect()
        
        if self.burning:
            if self.burning_timer - self.burning_last_hi> self.burn_hi:
                self.take_damage(self.burning_damage)
                self.burning_last_hi +=self.burn_hi
            self.burning_timer += dt
            if self.burning_timer > self.burning_time:
                self.remove_burning_effect()
        

        
        


  

class GruntUnit(Unit):
    def __init__(self, start_node):
        super().__init__(start_node, "grunt", 100,3)

class TankUnit(Unit):
    def __init__(self, start_node):
        super().__init__(start_node, "tank", 60,10)

class FastUnit(Unit):
    def __init__(self, start_node):
        super().__init__(start_node, "fast", 140,1)


def create_unit(start_node, unit_type):
    if unit_type == "grunt":
        return GruntUnit(start_node)
    
    elif unit_type == "tank":
        return TankUnit(start_node)
    
    else:
        return FastUnit(start_node)
    
class TowerSlot:
    def __init__(self,x,y):
        self.x = x
        self.y = y
        self.tower = None

    @property
    def occupied(self): 
        return self.tower is not None
    
    def add_tower(self,tower):
        self.tower = tower
    
    def remove_tower(self):
        self.tower = None

class UpgradeSpec:
    def __init__(self, kind, type, label, count,cost=0):
        self.kind = kind
        self.type = type
        self.label = label
        self.count = count
        self.cost = cost

class Tower:
    def __init__(self,tower_type,x,y,range,damage,fire_rate, last_node:Node):
        self.tower_type = tower_type
        self.x = x
        self.y = y
        self.range = range
        self.damage = damage
        self.fire_rate = fire_rate
        self.cooldown = 0.0
        self.pick_target = self._pick_target_nearest
        self.bullets: list[Bullet] = []
        self.create_bullet = BasicBullet
        self._bullet_options = []
        self.last_node: Node= last_node
    
    def attack(self, t_unit: Unit):
        if t_unit is None:
            return None
        
        bullet = self.create_bullet(self.x,self.y,t_unit,self.damage)
        self.bullets.append(bullet)
        return bullet
    def _remove_finished_bullets(self):
        self.bullets = [b for b in self.bullets if not b.finished]
    def choose_target(self,units):
        for u in units:
            if u.finished:
                continue
            dist_x = u.x - self.x
            dist_y = u.y - self.y
            if dist_x*dist_x + dist_y*dist_y <= self.range * self.range:
                return u
        return None
    
    def update(self, dt, units):
        self._remove_finished_bullets()
        self.cooldown -= dt
        if self.cooldown > 0:
            return None
        units = [u for u in units if self._is_unit_in_range(u)]
        if self.pick_target is None:
            self.pick_target = self._pick_target_lowest_hp
        target = self.pick_target(units)
        if target is None:
            return None
        
        bullet = self.attack(target)
        self.cooldown= 1.0/self.fire_rate
        return bullet

    
    def _is_unit_in_range(self,unit):
        dist = math.hypot(unit.x-self.x,unit.y-self.y)
        if dist > self.range:
            return False
        return True

    def _pick_target_nearest(self,units):
        closest_dist = math.inf
        closest_unit = None
        for u in units:
            if u.finished:
                continue
            dist = math.hypot(u.x-self.x,u.y-self.y)
            if dist > self.range:
                continue
            if closest_dist > dist:
                closest_dist = dist
                closest_unit = u 

        return closest_unit
    
    def _pick_target_lowest_hp(self,units):
        lowest_hp = math.inf
        unit_lowest_hp = None
        for u in units:
            if u.finished:
                continue
            if lowest_hp > u.health:
                lowest_hp = u.health
                unit_lowest_hp = u 

        return unit_lowest_hp
    
    def _pick_target_highest_hp(self,units):
        highest_hp = 0
        unit_highest_hp = None
        for u in units:
            if u.finished:
                continue
            if highest_hp < u.health:
                highest_hp = u.health
                unit_highest_hp = u 

        return unit_highest_hp
    def _pick_target_furthest(self,units):
        furthest_dist = 0.0
        furthest_unit = None
        for u in units:
            if u.finished:
                continue
            dist = math.hypot(u.x-self.x,u.y-self.y)
            if dist > self.range:
                continue
            if furthest_dist < dist:
                furthest_dist = dist
                furthest_unit = u 

        return furthest_unit

    def change_targeting_strategy(self, strategy: str) -> None:

        mapping = {
            "nearest": self._pick_target_nearest,
            "weakest": self._pick_target_lowest_hp,
            "strongest": self._pick_target_highest_hp,
            "furthest": self._pick_target_furthest
        }
        fn = mapping.get(strategy)
        if fn is None:
            return
        self.pick_target = fn
    
    def change_bullet_type(self,bullet_type):
        bullets = {
            "basic":BasicBullet,
            "rocket":RocketBullet,
            "beam": BeamBullet,
            "vine": VineBullet,
            "fire": FireBullet,
            "poison": PoisonBullet,
            "cluster": RocketClusterBullet,
            "spread-vine": SpreadVineBullet
            }
        self.create_bullet = bullets[bullet_type]

    @property
    def bullet_type(self):
        if self.create_bullet is None:
            return
        bullet_class_name = self.create_bullet.__name__
        class_to_Name_dict = {
            "BasicBullet":"basic",
            "FireBullet":"fire",
            "BeamBullet":"beam",
            "VineBullet":"vine",
            "SpreadVineBullet":"spread-vine",
            "RocketBullet":"rocket",
            "RocketClusterBullet":"cluster",
            "PoisonBullet":"poison"
        }
        return class_to_Name_dict[bullet_class_name]
    
    def get_available_bullet_upgrades(self):
        current_btype = self.bullet_type
        upgrades = [b_op for b_op in self._bullet_options if b_op != current_btype]
        return upgrades
    
    def upgrade_damage(self):
        if math.trunc(self.damage * 0.2) == 0:
            self.damage = self.damage + 1
        else:
            self.damage = math.trunc(self.damage * 1.2)
    def upgrade_range(self):
        self.range = math.trunc(self.range * 1.2)

    def upgrade_fire_rate(self):
        self.fire_rate = self.fire_rate * 1.2

    def get_stats(self):
        return {
            "type": self.tower_type,
            "damage": self.damage,
            "fire_rate": self.fire_rate,
            "range": self.range,
        }
    @property
    def _spec_damage(self) -> UpgradeSpec:
        def _calc_damage():
            if math.trunc(self.damage * 0.2) == 0:
                return self.damage + 1
            else:
                return self.damage * 1.2
        def _calc_cost():
            print("TODO")

        return UpgradeSpec(
            kind = "stat",
            type = "damage",
            label= f"cur: {self.damage}, up: +{_calc_damage()-self.damage}",
            count = 0
        )
    @property
    def _spec_range(self) -> UpgradeSpec:
        def _calc_cost():
            print("TODO")

        return UpgradeSpec(
            kind = "stat",
            type = "range",
            label = f"cur: {self.range}, up: +{self.range * 0.2}",
            count = 0
        )
    @property
    def _spec_fire_rate(self) -> UpgradeSpec:
        def _calc_cost():
            print("TODO")

        return UpgradeSpec(
            kind = "stat",
            type = "fire-rate",
            label = f"cur: {self.fire_rate}, up: +{self.fire_rate * 0.2}",
            count = 0
        )
    
    def _get_bullet_specs(self)-> list[UpgradeSpec] | None:
        upgrades: list[UpgradeSpec] = []
        for b_type in self.get_available_bullet_upgrades():
            up = UpgradeSpec(
                kind = "bullet",
                type = b_type,
                label = f"{self.bullet_type} -> {b_type}",
                cost = 100,
                count=0
            )

    def possible_upgrades(self):
        u = []
        u.append(self._spec_damage)
        u.append(self._spec_range)
        u.append(self._spec_fire_rate)
        for b_type in self.get_available_bullet_upgrades():
            upd = UpgradeSpec(
                kind = "bullet",
                type = b_type,
                label = f"{self.bullet_type} -> {b_type}",
                count = 0
            )
            u.append(upd)
        return u


class BasicTower(Tower):
    def __init__(self, x,y,last_node:Node):
        super().__init__("basic",x,y,200,1,3,last_node)
        self.create_bullet = BasicBullet
        self._bullet_options.extend(["basic","fire","poison"])


class RocketeerTower(Tower):
    def __init__(self,x,y, last_node: Node):
        super().__init__("rocketeer",x,y,800,3,1,last_node)
        self.create_bullet = RocketBullet
        self.rocket_cluster_size = 2
        self._bullet_options.extend(["rocket","cluster"])

    def attack(self, t_unit: Unit):
        if t_unit is None:
            return None
        bullet = self.create_bullet(self.x,self.y,t_unit,self.damage,self.rocket_cluster_size)
        self.bullets.append(bullet)
        return bullet
    
    def possible_upgrades(self):
        u = super().possible_upgrades()
        upd = UpgradeSpec(
            kind = "class-spec",
            type = "cluster-size",
            label = f"cluster size {self.rocket_cluster_size} -> {self.rocket_cluster_size + 1}",
            count=0

        )
        u.append(upd)
        return u


class BeamTower(Tower):
    def __init__(self,x,y,last_node:Node):
        super().__init__("beam",x,y,300,1,4,last_node)
        self.create_bullet = BeamBullet
        self._bullet_options.extend(["beam"])
        self.beam_radius = 1
    def attack(self, t_unit: Unit):
        if t_unit is None:
            return None
        
        bullet = self.create_bullet(self.x,self.y,t_unit,self.damage,self.beam_radius)
        self.bullets.append(bullet)
        return bullet
    
    def possible_upgrades(self):
        u = super().possible_upgrades()
        upd = UpgradeSpec(
            kind = "class-spec",
            type = "beam",
            label = f"beam rad {self.beam_radius} -> {self.beam_radius*1.2}",
            count=0

        )
        u.append(upd)
        return u
    
    def upgrade_beam_radius(self):
        if math.trunc(self.beam_radius * 0.2) <1:
            self.beam_radius +=1
        else:
            self.beam_radius += math.trunc(self.beam_radius * 0.2) 

class VineTower(Tower):
    def __init__(self,x,y,last_node: Node):
        super().__init__("vine",x,y,300,1,1,last_node)
        self.create_bullet = VineBullet
        self._bullet_options.extend(["vine", "spread-vine"])
        self.vine_count = 1
    def attack(self, t_unit: Unit):
        if len(self.bullets) >= self.vine_count:
            return

        else:
            if t_unit is None:
                return None
        
            bullet = self.create_bullet(self.x,self.y,t_unit,self.damage)
            self.bullets.append(bullet)
            return bullet
        
    def update(self, dt, units: list[Unit]):
        current_targ: list[Unit] = []
        for b in self.bullets:
            current_targ.append(b.target)

        not_yet_target = [u for u in units if u not in current_targ]

        return super().update(dt,not_yet_target)
    
    def possible_upgrades(self):
        u = super().possible_upgrades()
        upd = UpgradeSpec(
            kind = "class-spec",
            type = "vine",
            label = f"vine count {self.vine_count} -> {self.vine_count + 1}",
            count=0

        )
        u.append(upd)
        return u

class Bullet:
    def __init__(self,type, x, y, speed, damage, target: Unit):
        self.x = x
        self.y = y
        self.type = type
        self.speed = speed
        self.damage = damage
        self.target: Unit = target
        self.finished = False
    
    def update(self, dt, units: list[Unit]):
        if self.target.finished:
            self.finished = True
            return
        dist_x = self.target.x - self.x
        dist_y = self.target.y - self.y
        dist = math.hypot(dist_x, dist_y)

        if dist < 3:
            self.x = self.target.x
            self.y = self.target.y
            self.finished = True
            self._deal_dmg()
            return

        step = min(self.speed * dt, dist)
        self.x += (dist_x/dist) * step
        self.y += (dist_y/dist) * step
    
    def _deal_dmg(self):
        self.target.take_damage(self.damage)


class BasicBullet(Bullet):
    def __init__(self, x, y, target, damage):
        super().__init__("basic",x,y,400, damage, target)

class FireBullet(Bullet):
    def __init__(self, x, y, target, damage):
        super().__init__("fire",x,y,400, damage, target)
        self.fire_damage = 1

    def _deal_dmg(self):
        self.target.take_damage(self.damage)
        self.target.add_fire_effect(self.fire_damage)

class PoisonBullet(Bullet):
    def __init__(self, x, y, target, damage):
        super().__init__("poison",x,y,400, damage, target)
        self.poison_damage = 1

    def update(self, dt, units: list[Unit]):

        def _pick_target_nearest(t_units):
            closest_dist = math.inf
            closest_unit = None
            for u in t_units:
                if u.finished:
                    continue
                dist = math.hypot(u.x-self.x,u.y-self.y)
                if closest_dist > dist:
                    closest_dist = dist
                    closest_unit = u 

            return closest_unit
        
        if self.target.finished:
            self.finished = True
            return
        dist_x = self.target.x - self.x
        dist_y = self.target.y - self.y
        dist = math.hypot(dist_x, dist_y)

        if dist < 3:
            self.x = self.target.x
            self.y = self.target.y
            self.finished = True
            self._deal_dmg()
            if not self.target.finished:
                nt = _pick_target_nearest([t for t in units if t not in [self.target]])
                if nt is None:
                    return
                return [PoisonBullet(self.x, self.y, nt, self.damage)]
            return
        step = min(self.speed * dt, dist)
        self.x += (dist_x/dist) * step
        self.y += (dist_y/dist) * step

class RocketBullet(Bullet):
    def __init__(self, x, y, target, damage, rocket_cluster_size=2):
        super().__init__("rocket",x,y,10, damage, target)
        self.acceleration = 1.8
        self.max_speed = 1500
        self.t_x = x
        self.t_y = y
        self.rocket_cluster_size = rocket_cluster_size

    def update(self, dt, units: list[Unit]):
        def _pick_target_nearest():
            closest_dist = math.inf
            closest_unit = None
            for u in units:
                if u.finished:
                    continue
                dist = math.hypot(u.x-self.x,u.y-self.y)
                if closest_dist > dist:
                    closest_dist = dist
                    closest_unit = u 

            return closest_unit
        if self.target is not None and self.target.finished:
            self.target = _pick_target_nearest()
        if self.target is None:
            self.finished = True
            return
        self.acceleration += self.acceleration*dt
        speed = min((self.speed)**self.acceleration, self.max_speed)
        dist_x = self.target.x - self.x
        dist_y = self.target.y - self.y
        dist = math.hypot(dist_x, dist_y)

        if dist < 3:
            self.x = self.target.x
            self.y = self.target.y
            self.finished = True
            self._deal_dmg()
            return

        step = min(speed * dt, dist)
        self.x += (dist_x/dist) * step
        self.y += (dist_y/dist) * step

class MiniRocketClusterBullet(RocketBullet):
    def __init__(self, x, y, target, damage,rocket_cluster_size, acceleration):
        super().__init__(x,y,target,damage,rocket_cluster_size)
        self.type="mini-cluster"
        self.acceleration = acceleration

class RocketClusterBullet(RocketBullet):
    def __init__(self, x, y, target, damage,rocket_cluster_size):
        super().__init__(x,y,target,damage,rocket_cluster_size)
        self.type = "cluster"
        self.age = 0
        self.age_treshold = 0.33
        self._mini_cluster_range = 200
        self._mini_cluster_damage = 1

    def update(self, dt, units: list[Unit]):
        self.age += dt
        def _pick_target_nearest():
            closest_dist = math.inf
            closest_unit = None
            for u in units:
                if u.finished:
                    continue
                dist = math.hypot(u.x-self.x,u.y-self.y)
                if closest_dist > dist:
                    closest_dist = dist
                    closest_unit = u 

            return closest_unit
        if self.acceleration < 3:
            self.acceleration += self.acceleration*dt/20
        if self.target is not None and self.target.finished:
            self.target = _pick_target_nearest()
        if self.target is None:
            self.finished = True
            return
        
        if self.age > self.age_treshold:
            cluster_bullets = self._deploy_cluster(units)
            if cluster_bullets is None:
                self.age = 0
                return
            self.finished = True
            return cluster_bullets



        self.acceleration += self.acceleration*dt/10  
        speed = min((self.speed)**self.acceleration, self.max_speed)
        dist_x = self.target.x - self.x
        dist_y = self.target.y - self.y
        dist = math.hypot(dist_x, dist_y)

        if dist < 3:
            self.x = self.target.x
            self.y = self.target.y
            self.finished = True
            self._deal_dmg()
            return

        step = min(speed * dt, dist)
        self.x += (dist_x/dist) * step
        self.y += (dist_y/dist) * step
    
    def _deploy_cluster(self,units: list[Unit]):
        in_dist = [u for u in units if math.hypot(u.x-self.x,u.y-self.y)<=self._mini_cluster_range]
        b_count = 0
        bullets = []
        if len(in_dist) == 0:
            return
        while len(bullets) < self.rocket_cluster_size:
            for u in in_dist:
                if b_count == self.rocket_cluster_size:
                    return bullets
                bullets.append(MiniRocketClusterBullet(self.x,self.y,u,self._mini_cluster_damage,1,self.acceleration))
                b_count += 1
                
        return bullets
    
        
class BeamBullet(Bullet):
    def __init__(self, x, y, target, damage, radius):
        super().__init__("beam",x,y,50, damage, target)
        self.beam_radius = radius
        self.t_x = x
        self.t_y = y
        self.beam_decay = 0.5
        self.ttl = 20
        self._damage_done = False
    
    def update(self,dt, units: list[Unit]):
        if self.target.finished:
            self.finished = True
            return
        self.ttl -=1
        
        self.x = self.target.x
        self.y = self.target.y
        if self.ttl == 0:
            self.finished = True

        if self._damage_done == False:
            self._damage_done = True
            self._deal_dmg(units)
        return

    def _deal_dmg(self, units: list[Unit]):
        
        def _calculate_damage(dist):
            damage = math.trunc((1-(dist/self.beam_radius))*self.damage)
            return damage

        dx = self.x - self.t_x
        dy = self.y - self.t_y

        if abs(dx) < 1e-6:
            x0 = self.t_x
            for u in units:
                dist = abs(u.x-x0)
                if dist <= self.beam_radius:
                    dmg = _calculate_damage(dist)
                    u.take_damage(dmg)

        else:
            a = dy/dx
            b = self.y - a* self.x
            for u in units:
                if u.finished:
                    continue
                dist = abs(-a *u.x +u.y-b)/(a**2+1)
                if dist <= self.beam_radius:
                    dmg = _calculate_damage(dist)
                    u.take_damage(dmg)

class VineBullet(Bullet):
    def __init__(self, x, y, target, damage):
        super().__init__("vine",x,y,10, damage, target)
        self.acceleration = 1
        self.max_speed = 1500
        self.poison = 1
        self.t_x = x
        self.t_y = y
        self.timer = 0
    
    def update(self, dt, units: list[Unit]):
        
        self.timer +=1
        if self.target is None or self.target.finished:
            self.finished = True
            return
        if self.acceleration < 20:
            self.acceleration += self.acceleration*dt
        speed = min((self.speed)**self.acceleration, self.max_speed)
        dist_x = self.target.x - self.x
        dist_y = self.target.y - self.y
        dist = math.hypot(dist_x, dist_y)

        if dist < 3:
            self.x = self.target.x
            self.y = self.target.y
            if not self.target.slowed: 
                self.target.add_slow_effect()
            # self.finished = True
            # self._deal_dmg()
            return
        
        if self.timer == 60:
            self._deal_dmg()

        step = min(speed * dt, dist)
        self.x += (dist_x/dist) * step
        self.y += (dist_y/dist) * step

class SpreadVineBullet(VineBullet):

    def __init__(self, x, y, target, damage):
        super().__init__(x, y, target, damage)
        self.type = "spread-vine"
        self.targets:list[Unit] = [target]
        self.target_cap = 3
    def update(self, dt, units: list[Unit]):

        def _pick_target_nearest(t_units):
            closest_dist = math.inf
            closest_unit = None
            for u in t_units:
                if u.finished:
                    continue
                dist = math.hypot(u.x-self.x,u.y-self.y)
                if closest_dist > dist:
                    closest_dist = dist
                    closest_unit = u 

            return closest_unit
        
        self.timer += 1

        if self.targets is None:
            self.finished = True
            return
        self.targets = [t for t in self.targets if not t.finished]

        if len(self.targets) == 0:
            self.finished = True
            return
        
        if len(self.targets) >= self.target_cap:
            return

        if self.acceleration < 20:
            self.acceleration += self.acceleration*dt

        speed = min((self.speed)**self.acceleration, self.max_speed)
        dist_x = self.target.x - self.x
        dist_y = self.target.y - self.y
        dist = math.hypot(dist_x, dist_y)

        if dist < 3:
            self.x = self.target.x
            self.y = self.target.y
            if not self.target.slowed: 
                self.target.add_slow_effect()
            
            new_target = _pick_target_nearest([t for t in units if t not in self.targets])
            if new_target is None:
                return
            self.targets.append(new_target)
            # self.finished = True
            # self._deal_dmg()
            return
        
        if self.timer == 60:
            self._deal_dmg()

        step = min(speed * dt, dist)
        self.x += (dist_x/dist) * step
        self.y += (dist_y/dist) * step

                