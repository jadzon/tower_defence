import math
from mimetypes import init
from config import load_game_config

class Game:
    def __init__(self):

        cfg = load_game_config()

        self.levels = cfg.levels

        #level 1
        self.nodes: list[Node] =  []
        # get nodes
        for n_x, n_y in cfg.levels[0].map.nodes:
            self.nodes.append(Node(n_x,n_y))
        
        #get node relations
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
        
        self.place_tower(self.tower_slots[0],"basic")

    def tick(self,dt):

        self.elapsed += dt

        self._process_waves()
        
        for t in self.towers:
            t.update(dt, self.units)

        for u in self.units:
            u.update(dt)

        self._remove_dead_units()
        
    
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
    
    def place_tower(self,tower_slot,tower_type):

        if tower_slot.occupied:
            return
        if tower_type == "basic":
            tower = BasicTower(tower_slot.x,tower_slot.y)
            tower_slot.add_tower(tower)
            self.towers.append(tower)
    
    def _remove_dead_units(self):
        self.units = [u for u in self.units if not u.finished]
        

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
    
    def __init__(self, start_node, unit_type, speed):
        self.health = 3
        self.current_node = start_node
        self.next_node = start_node.neighbors[0]
        self.unit_type = unit_type
        self.speed = speed
        self.x = start_node.x
        self.y = start_node.y
        self.visited_nodes = [start_node]
        self.finished = False

    def update(self,dt):
        if self.next_node is None or self.finished:
            return
        
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
            self.finished = True
        
        print(f"{self.unit_type} HP: {self.health}")

    

class GruntUnit(Unit):
    def __init__(self, start_node):
        super().__init__(start_node, "grunt", 100)


class TankUnit(Unit):
    def __init__(self, start_node):
        super().__init__(start_node, "tank", 60)

class FastUnit(Unit):
    def __init__(self, start_node):
        super().__init__(start_node, "fast", 140)


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



class Tower:
    def __init__(self,tower_type,x,y,range,damage,fire_rate):
        self.tower_type = tower_type
        self.x = x
        self.y = y
        self.range = range
        self.damage = damage
        self.fire_rate = fire_rate
        self.cooldown = 0.0
    
    def attack(self, t_unit: Unit):
        if t_unit is None:
            return
        
        t_unit.take_damage(self.damage)

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
        self.cooldown -= dt
        if self.cooldown > 0:
            return
        
        target = self.choose_target(units)
        if target is None:
            return
        
        self.attack(target)
        self.cooldown= 1.0/self.fire_rate




class BasicTower(Tower):
    def __init__(self, x,y):
        super().__init__("basic",x,y,200,1,3)


        
