import math
from timeit import Timer
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
        self.gold_generation_per_tick = cfg.economy.gold_generation
        self.kill_reward: dict[str,int] = cfg.economy.kill_reward
        self.tower_costs: dict[str,int] = cfg.economy.tower_costs
        self.bullet_costs: dict[str,int] = cfg.economy.bullet_costs
        self.tower_sell_return_ratio: float = cfg.economy.sell_return_ratio
        # self.place_tower(self.tower_slots[0],"basic")
        # self.place_tower(self.tower_slots[1],"rocketeer")
        self._place_tower(self.tower_slots[0],"beam")
        self._place_tower(self.tower_slots[1],"vine")
        self._place_tower(self.tower_slots[2],"rocketeer")

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
            tower = BasicTower(tower_slot.x,tower_slot.y)
            tower_slot.add_tower(tower)
            self.towers.append(tower)
        elif tower_type == "rocketeer":
            tower = RocketeerTower(tower_slot.x,tower_slot.y)
            tower_slot.add_tower(tower)
            self.towers.append(tower)
        elif tower_type == "vine":
            tower = VineTower(tower_slot.x,tower_slot.y)
            tower_slot.add_tower(tower)
            self.towers.append(tower)
        else:
            tower = BeamTower(tower_slot.x,tower_slot.y)
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
        self.burning = False
        self.burning_timer = 0
        self.burning_damage = 1

    def update(self,dt):
        self.burning_timer += dt
        if self.next_node is None or self.finished:
            return
        if self.burning and self.burning_timer>1:
            self.take_damage(self.burning_damage)
            print("damage")
            self.burning_timer = 0
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


class Tower:
    def __init__(self,tower_type,x,y,range,damage,fire_rate):
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
    

    def change_targeting_strategy(self, strategy: str) -> None:

        mapping = {
            "nearest": self._pick_target_nearest,
            "weakest": self._pick_target_lowest_hp,
            "strongest": self._pick_target_highest_hp,
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
            "cluster": RocketClusterBullet,
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
            "RocketBullet":"rocket",
            "RocketClusterBullet":"cluster",
        }
        return class_to_Name_dict[bullet_class_name]
    
    def get_available_bullet_upgrades(self):
        current_btype = self.bullet_type
        upgrades = [b_op for b_op in self._bullet_options if b_op != current_btype]
        return upgrades

class BasicTower(Tower):
    def __init__(self, x,y):
        super().__init__("basic",x,y,200,1,3)
        self.create_bullet = BasicBullet
        self._bullet_options.extend(["basic","fire"])

class RocketeerTower(Tower):
    def __init__(self,x,y):
        super().__init__("rocketeer",x,y,800,3,1)
        self.create_bullet = RocketBullet
        self._bullet_options.extend(["rocket","cluster"])

    def attack(self, t_unit: Unit):
        if t_unit is None:
            return None
        bullet = self.create_bullet(self.x,self.y,t_unit,self.damage)
        self.bullets.append(bullet)
        return bullet


class BeamTower(Tower):
    def __init__(self,x,y):
        super().__init__("beam",x,y,300,1,4)
        self.create_bullet = BeamBullet
        self._bullet_options.extend(["beam"])
    def attack(self, t_unit: Unit):
        if t_unit is None:
            return None
        
        bullet = self.create_bullet(self.x,self.y,t_unit,self.damage)
        self.bullets.append(bullet)
        return bullet

class VineTower(Tower):
    def __init__(self,x,y):
        super().__init__("vine",x,y,300,1,1)
        self.create_bullet = VineBullet
        self._bullet_options.extend(["vine"])
        self.bullet_cap = 5
    def attack(self, t_unit: Unit):
        if len(self.bullets) >= self.bullet_cap:
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

class RocketBullet(Bullet):
    def __init__(self, x, y, target, damage):
        super().__init__("rocket",x,y,10, damage, target)
        self.acceleration = 1
        self.max_speed = 1500
        self.t_x = x
        self.t_y = y

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
    def __init__(self, x, y, target, damage, acceleration):
        super().__init__(x,y,target,damage)
        self.type="mini-cluster"
        self.acceleration

class RocketClusterBullet(RocketBullet):
    def __init__(self, x, y, target, damage):
        super().__init__(x,y,target,damage)
        self.type = "cluster"
        self.rocket_cluster = 5
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
        while len(bullets) < 5:
            for u in in_dist:
                if b_count == 5:
                    return bullets
                bullets.append(MiniRocketClusterBullet(self.x,self.y,u,self._mini_cluster_damage,self.acceleration))
                b_count += 1
                
        return bullets
        

    
class BeamBullet(Bullet):
    def __init__(self, x, y, target, damage):
        super().__init__("rocket",x,y,50, damage, target)
        self.beam_radius = 1
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
                    u.take_damage(dmg )

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
        

                