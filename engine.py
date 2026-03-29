import math

class Game:
    def __init__(self):
        self.waypoints = [(100, 100), (400, 100), (400, 500), (1000, 500)]
        node1 = Node(100, 100)
        node2 = Node(400, 100)
        node3 = Node(400, 500)
        node4 = Node(1000, 500)
        node5 = Node(1000, 600)
        node6 = Node(300, 600)

        node1.add_neighbor(node2)
        node2.add_neighbor(node3)
        node3.add_neighbor(node4)
        node4.add_neighbor(node5)
        node5.add_neighbor(node6)

        print(node1.get_neighbors())
        print(node2.get_neighbors())
        print(node3.get_neighbors())
        print(node4.get_neighbors())

        self.nodes = [node1, node2, node3, node4, node5, node6]
        self.first_node = node1
        self.last_node = node6

        
        self.units = [Unit(self.first_node,"grunt",100)]
        self.dt = 1
    
    def tick(self,dt):
        for u in self.units:
            u.update(dt)
        
        


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
            



        
