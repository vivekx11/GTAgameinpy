from ursina import *
from random import uniform, randint, choice

app = Ursina()

# Lighting and sky
Sky()
DirectionalLight(rotation=(45, -45, 45), shadows=True)
AmbientLight(color=color.rgba(100, 100, 100, 0.5))

# Larger world
world_size = 300
ground = Entity(
    model='plane',
    texture='grass',
    scale=(world_size, 1, world_size),
    collider='box'
)

# City grid
road_spacing = 60
road_width = 20

# Roads (fixed valid color)
for i in range(-5, 6):
    z = i * road_spacing
    Entity(model='plane', scale=(world_size * 2, 0.1, road_width), position=(0, 0.05, z), color=color.dark_gray)
    
    x = i * road_spacing
    Entity(model='plane', scale=(road_width, 0.1, world_size * 2), position=(x, 0.05, 0), color=color.dark_gray)

# Add simple white road markings (dashed lines)
for i in range(-5, 6):
    z = i * road_spacing
    for dash in range(-20, 21, 4):
        Entity(model='cube', scale=(4, 0.11, 1), position=(dash*10, 0.06, z), color=color.white)
    
    x = i * road_spacing
    for dash in range(-20, 21, 4):
        Entity(model='cube', scale=(1, 0.11, 4), position=(x, 0.06, dash*10), color=color.white)

# Buildings and police station
police_station_pos = None
for ix in range(-5, 6):
    for iz in range(-5, 6):
        bx = ix * road_spacing + road_width / 2 + (road_spacing - road_width) / 4
        bz = iz * road_spacing + road_width / 2 + (road_spacing - road_width) / 4
        block_w = (road_spacing - road_width) / 2
        
        height = uniform(8, 25)
        building_color = color.gray.tint(uniform(-0.2, 0.2))
        
        if randint(1, 12) == 1:  # Hotels
            height = uniform(35, 60)
            building_color = color.azure.tint(uniform(-0.1, 0.1))
        
        if ix == 2 and iz == 2:  # Police station
            height = 30
            building_color = color.blue
            police_station_pos = (bx, 0, bz)
            Entity(model='cube', position=(bx, height/2, bz), scale=(block_w * 1.8, height, block_w * 1.8),
                   texture='brick', color=building_color, collider='box')
        else:
            Entity(model='cube', position=(bx, height/2, bz), scale=(block_w * 1.6, height, block_w * 1.6),
                   texture='brick', color=building_color, collider='box')

# Vehicle base
class Vehicle(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model='cube',
            scale=(4, 2, 8),
            collider='box',
            **kwargs
        )
        self.speed = 30  # Increased max speed

# Drivable cars
drivable_vehicles = []
park_positions = [
    (15, 1, 30), (-15, 1, 30), (30, 1, -15), (-30, 1, 90),
    (90, 1, 15), (-90, 1, -60), (60, 1, -90), (-60, 1, 60),
    (120, 1, 120), (-120, 1, -120), (0, 1, 100), (100, 1, 0)
]
car_colors = [color.red, color.yellow, color.green, color.orange, color.violet, color.cyan, color.lime]
for pos in park_positions:
    car = Vehicle(position=pos, color=choice(car_colors), rotation_y=randint(0, 3)*90)
    drivable_vehicles.append(car)

# Traffic cars
class TrafficCar(Vehicle):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.direction = 1

    def update(self):
        self.z += self.speed * self.direction * time.dt
        if abs(self.z) > world_size / 2 - 30:
            self.direction *= -1

for i in range(10):
    TrafficCar(position=(i*40 - 180, 1, -160), color=color.gray, rotation_y=choice([0, 90, 180, 270]))

# Pedestrians
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
        self.velocity = Vec3(uniform(-2,2), 0, uniform(-2,2)).normalized() * 4
        self.change_timer = uniform(3, 8)

    def update(self):
        self.position += self.velocity * time.dt
        self.change_timer -= time.dt
        if self.change_timer <= 0:
            self.velocity = Vec3(uniform(-2,2), 0, uniform(-2,2)).normalized() * 4
            self.look_at(self.position + self.velocity, 'forward')
            self.change_timer = uniform(3, 8)

for _ in range(50):
    pos = (uniform(-140, 140), 1, uniform(-140, 140))
    pedestrians.append(Pedestrian(position=pos))

# Police
police_cars = []
wanted_level = 0

class PoliceCar(Vehicle):
    def __init__(self, **kwargs):
        super().__init__(color=color.blue.tint(-0.3), **kwargs)

    def update(self):
        if wanted_level > 0 and player:
            target = player.position if not player.in_vehicle else player.in_vehicle.position
            direction = (target - self.position)
            dist = direction.length()
            if dist > 8:
                self.look_at(target, 'forward')
                self.position += self.forward * 40 * time.dt

# Player
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
        self.health = 100
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
        self.in_vehicle = vehicle
        self.disable()
        camera.parent = vehicle
        camera.position = (0, 6, -18)
        camera.rotation_x = 12

    def exit_vehicle(self):
        if not self.in_vehicle:
            return
        vehicle = self.in_vehicle
        self.position = vehicle.position + vehicle.right * 5
        self.enable()
        camera.parent = self
        camera.position = (0, 5, -15)
        camera.rotation_x = 20
        self.in_vehicle = None

    def update(self):
        self.nearest_vehicle = None
        if not self.in_vehicle:
            for v in drivable_vehicles:
                if distance(self, v) < 7:
                    self.nearest_vehicle = v
                    break

        if self.in_vehicle:
            v = self.in_vehicle
            turn = held_keys['d'] - held_keys['a']
            v.rotation_y += turn * 120 * time.dt
            accel = held_keys['w'] - held_keys['s']
            v.position += v.forward * accel * v.speed * time.dt
        else:
            turn = held_keys['d'] - held_keys['a']
            self.rotation_y += turn * self.rotation_speed * time.dt
            move = held_keys['w'] - held_keys['s']
            self.position += self.forward * move * self.speed * time.dt

# Hit detection
def check_hits():
    global wanted_level
    if player.in_vehicle:
        car = player.in_vehicle
        for ped in pedestrians[:]:
            if car.intersects(ped).hit:
                destroy(ped)
                pedestrians.remove(ped)
                wanted_level = min(wanted_level + 1, 5)
                spawn_police()

def spawn_police():
    if police_station_pos and wanted_level > 0 and len(police_cars) < wanted_level * 3:
        for _ in range(min(3, wanted_level * 3 - len(police_cars))):
            offset = Vec3(uniform(-40,40), 1, uniform(-40,40))
            p_car = PoliceCar(position=Vec3(police_station_pos) + offset)
            police_cars.append(p_car)

# === GOOD UI ADDITIONS ===
# Health bar (bottom left)
health_bar_bg = Entity(parent=camera.ui, model='quad', color=color.black, scale=(0.3, 0.04), position=(-0.7, -0.4), alpha=0.7)
health_bar_fill = Entity(parent=health_bar_bg, model='quad', color=color.red, scale=(1, 1), origin=(-0.5, 0), position=(-0.5, 0))
health_text = Text('HEALTH', parent=camera.ui, scale=1.2, position=(-0.7, -0.36), color=color.white)

# Wanted stars (top right - GTA style)
wanted_stars = Text('', parent=camera.ui, scale=4, position=(0.65, 0.45), color=color.yellow)

# Speedometer (bottom center - visible only in vehicle)
speed_text = Text('', parent=camera.ui, scale=2, position=(0, -0.4), color=color.white)

# Crosshair (center)
crosshair = Text('+', parent=camera.ui, scale=1.5, origin=(0,0), color=color.white.tint(0.5))

# Hint / Instructions (fades after 10 seconds)
hint_text = Text("WASD = Move/Turn | E = Enter/Exit Car (near parked car) | Hit pedestrians = Wanted!", 
                 parent=camera.ui, origin=(0,0), y=-0.3, scale=1.8, color=color.yellow)
invoke(setattr, hint_text, 'alpha', 0, delay=10)
invoke(destroy, hint_text, delay=12)

# Minimap placeholder (simple circle for player position - advanced minimap possible later)
# For now, a small radar circle
minimap_bg = Entity(parent=camera.ui, model='circle', color=color.black.tint(0.5), scale=0.2, position=(0.75, 0.35), alpha=0.6)
minimap_player = Entity(parent=minimap_bg, model='circle', color=color.lime, scale=0.2)

# Setup player and camera
player = Player()
camera.parent = player
camera.position = (0, 5, -15)
camera.rotation_x = 20
camera.fov = 90

# Global update
def update():
    check_hits()
    
    # Update health bar (currently static, can add damage later)
    health_bar_fill.scale_x = player.health / 100
    
    # Update wanted stars
    wanted_stars.text = '★' * wanted_level
    
    # Update speedometer
    if player.in_vehicle:
        accel = held_keys['w'] - held_keys['s']
        current_speed = int(abs(accel) * player.in_vehicle.speed * 3)  # Scaled for realism
        speed_text.text = f"{current_speed} km/h"
        speed_text.visible = True
    else:
        speed_text.text = ''
        speed_text.visible = False

app.run()
