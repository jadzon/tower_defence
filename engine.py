import math
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
        self.bullets: list[Bullet] = []
        self.place_tower(self.tower_slots[0],"basic")
        self.place_tower(self.tower_slots[1],"rocketeer")

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
            b.update(dt)

        self._remove_dead_units()
        self._remove_finished_bullets()
        
    
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
        elif tower_type == "rocketeer":
            tower = RocketeerTower(tower_slot.x,tower_slot.y)
            tower_slot.add_tower(tower)
            self.towers.append(tower)
        else:
            tower = BeamTower(tower_slot.x,tower_slot.y)
            tower_slot.add_tower(tower)
            self.towers.append(tower)

    
    def _remove_dead_units(self):
        self.units = [u for u in self.units if not u.finished]
    
    def _remove_finished_bullets(self):
        self.bullets= [b for b in self.bullets if not b.finished]
        

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



class Tower:
    def __init__(self,tower_type,x,y,range,damage,fire_rate):
        self.tower_type = tower_type
        self.x = x
        self.y = y
        self.range = range
        self.damage = damage
        self.fire_rate = fire_rate
        self.cooldown = 0.0
        self.pick_target = None
    
    def attack(self, t_unit: Unit):
        if t_unit is None:
            return None
        
        bullet = BasicBullet(self.x,self.y,t_unit,self.damage)
        return bullet

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
            return None
        units = [u for u in units if self._is_unit_in_range(u)]
        if self.pick_target is None:
            self.pick_target = self._pick_target_highest_hp
        target = self.pick_target(units)
        if target is None:
            return None
        
        bullet = self.attack(target)
        self.cooldown= 1.0/self.fire_rate
        return bullet

    def change_targeting_strategy(self, strategy):
        if strategy == "nearest":
            self.pick_target = self._pick_target_nearest
    
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


class BasicTower(Tower):
    def __init__(self, x,y):
        super().__init__("basic",x,y,200,1,3)

class RocketeerTower(Tower):
    def __init__(self,x,y):
        super().__init__("rocketeer",x,y,800,3,1)

    def attack(self, t_unit: Unit):
        if t_unit is None:
            return None
        
        bullet = RocketBullet(self.x,self.y,t_unit,self.damage)
        return bullet

class BeamTower(Tower):
    def __init__(self,x,y):
        super().__init__("beam",x,y,300,1,0.5)


class Bullet:
    def __init__(self,type, x, y, speed, damage, target: Unit):
        self.x = x
        self.y = y
        self.type = type
        self.speed = speed
        self.damage = damage
        self.target = target
        self.finished = False
    
    def update(self, dt):
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
        super().__init__("basic",x,y,500, damage, target)

class RocketBullet(Bullet):
    def __init__(self, x, y, target, damage):
        super().__init__("rocket",x,y,50, damage, target)
        self.acceleration = 700
        self.max_speed = 1500

    def update(self, dt):
        self.speed = min(self.speed + self.acceleration * dt, self.max_speed)
        super().update(dt)



        
