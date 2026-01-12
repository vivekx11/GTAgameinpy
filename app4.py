from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from random import uniform, randint, choice

app = Ursina()

# Lighting and sky for a more immersive world
Sky()
directional_light = DirectionalLight(rotation=(45, -45, 45), shadows=True)
AmbientLight(color=color.rgba(100, 100, 100, 0.5))

# Larger world
world_size = 300
ground = Entity(
    model='plane',
    texture='grass',
    scale=(world_size, 1, world_size),
    collider='box'
)

# City grid parameters
road_spacing = 60
road_width = 20

# Create roads (horizontal and vertical)
for i in range(-5, 6):
    z = i * road_spacing
    Entity(model='plane', scale=(world_size * 2, 0.1, road_width), position=(0, 0.05, z), color=color.gray66)
    
    x = i * road_spacing
    Entity(model='plane', scale=(road_width, 0.1, world_size * 2), position=(x, 0.05, 0), color=color.gray66)

# Generate buildings in city blocks (between roads)
police_station_pos = None
for ix in range(-5, 6):
    for iz in range(-5, 6):
        # Center of block
        bx = ix * road_spacing + road_width / 2 + (road_spacing - road_width) / 4
        bz = iz * road_spacing + road_width / 2 + (road_spacing - road_width) / 4
        
        block_w = (road_spacing - road_width) / 2
        
        # Normal building
        height = uniform(8, 25)
        building_color = color.white
        
        # Occasionally make a hotel (taller)
        if randint(1, 12) == 1:
            height = uniform(35, 60)
            building_color = color.azure
        
        # Special police station
        if ix == 2 and iz == 2:
            height = 30
            building_color = color.blue
            police_station_pos = (bx, 0, bz)
            Entity(model='cube', position=(bx, height/2, bz), scale=(block_w * 1.8, height, block_w * 1.8),
                   texture='brick', color=building_color, collider='box')
        else:
            Entity(model='cube', position=(bx, height/2, bz), scale=(block_w * 1.6, height, block_w * 1.6),
                   texture='brick', color=building_color, collider='box')

# Vehicle base class
class Vehicle(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model='cube',
            scale=(4, 2, 8),  # Longer car shape
            collider='box',
            **kwargs
        )
        self.speed = 20

# Drivable vehicles (parked cars you can enter)
drivable_vehicles = []
park_positions = [
    (15, 1, 30), (-15, 1, 30), (30, 1, -15), (-30, 1, 90),
    (90, 1, 15), (-90, 1, -60), (60, 1, -90), (-60, 1, 60)
]
car_colors = [color.red, color.yellow, color.green, color.orange, color.violet]
for pos in park_positions:
    car = Vehicle(position=pos, color=choice(car_colors), rotation_y=randint(0, 3)*90)
    drivable_vehicles.append(car)

# Traffic cars (AI moving back and forth)
class TrafficCar(Vehicle):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.direction = 1

    def update(self):
        self.z += self.speed * self.direction * time.dt
        if abs(self.z) > world_size / 2 - 20:
            self.direction *= -1

for i in range(6):
    TrafficCar(position=(i*40 - 100, 1, -150), color=color.gray, rotation_y=90)

# Pedestrians (NPCs that walk randomly)
pedestrians = []
class Pedestrian(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model='cube',
            scale=(0.8, 1.8, 0.8),
            color=color.random_color(),
            collider='box',
            **kwargs
        )
        self.velocity = Vec3(uniform(-1,1), 0, uniform(-1,1)).normalized() * 3
        self.change_timer = uniform(4, 10)

    def update(self):
        self.position += self.velocity * time.dt
        self.change_timer -= time.dt
        if self.change_timer <= 0:
            self.velocity = Vec3(uniform(-1,1), 0, uniform(-1,1)).normalized() * 3
            self.look_at(self.position + self.velocity, 'forward')
            self.change_timer = uniform(4, 10)

# Spawn pedestrians
for _ in range(30):
    pos = (uniform(-140, 140), 1, uniform(-140, 140))
    pedestrians.append(Pedestrian(position=pos))

# Police cars (spawn when wanted)
police_cars = []
wanted_level = 0

class PoliceCar(Vehicle):
    def __init__(self, **kwargs):
        super().__init__(color=color.blue.tint(-0.4), **kwargs)

    def update(self):
        if wanted_level > 0:
            target = player.position if not player.in_vehicle else player.in_vehicle.position
            direction = target - self.position
            if direction.length() > 5:
                self.look_at(target, 'forward')
                self.position += self.forward * 25 * time.dt

# Player class with vehicle enter/exit
class Player(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model='cube',
            texture='white_cube',
            scale=(1, 2, 1),
            position=(0, 2, 0),
            collider='box',
            **kwargs
        )
        self.speed = 6
        self.rotation_speed = 120
        self.in_vehicle = None
        self.nearest_vehicle = None

    def input(self, key):
        if key == 'e':
            if self.in_vehicle:
                self.exit_vehicle()
            elif self.nearest_vehicle:
                self.enter_vehicle(self.nearest_vehicle)

    def enter_vehicle(self, vehicle):
        global wanted_level
        self.in_vehicle = vehicle
        self.visible = False
        self.collider = None
        camera.parent = vehicle
        camera.position = (0, 5, -15)
        camera.rotation_x = 15
        # Reset wanted when entering a new car (for testing)
        wanted_level = 0

    def exit_vehicle(self):
        vehicle = self.in_vehicle
        self.position = vehicle.position + vehicle.right * 4  # Exit to the right
        self.visible = True
        self.collider = 'box'
        camera.parent = self
        camera.position = (0, 5, -15)
        camera.rotation_x = 20
        self.in_vehicle = None

    def update(self):
        # Find nearest drivable vehicle when on foot
        self.nearest_vehicle = None
        if not self.in_vehicle:
            for v in drivable_vehicles:
                if distance(self, v) < 6:
                    self.nearest_vehicle = v
                    break

        if self.in_vehicle:
            # Drive the vehicle
            v = self.in_vehicle
            v.rotation_y += held_keys['d'] * 100 * time.dt
            v.rotation_y -= held_keys['a'] * 100 * time.dt
            v.position += v.forward * (held_keys['w'] - held_keys['s']) * v.speed * time.dt
        else:
            # Normal walking
            self.rotation_y += held_keys['d'] * self.rotation_speed * time.dt
            self.rotation_y -= held_keys['a'] * self.rotation_speed * time.dt
            direction = self.forward * (held_keys['w'] - held_keys['s'])
            self.position += direction * self.speed * time.dt

# Collision check for hitting pedestrians
def check_hits():
    global wanted_level
    if player.in_vehicle:
        car = player.in_vehicle
        for ped in pedestrians[:]:
            if car.intersects(ped).hit:
                destroy(ped)
                pedestrians.remove(ped)
                wanted_level = 1
                spawn_police()

def spawn_police():
    global police_cars
    if len(police_cars) < 4 and police_station_pos:
        for _ in range(2):
            offset = Vec3(uniform(-20,20), 1, uniform(-20,20))
            p_car = PoliceCar(position=Vec3(police_station_pos) + offset)
            police_cars.append(p_car)

# Create player and camera
player = Player()
camera.parent = player
camera.position = (0, 5, -15)
camera.rotation_x = 20
camera.fov = 90

# Global update for collisions
def update():
    check_hits()

app.run()
