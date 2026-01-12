from ursina import *
from ursina.shaders import lit_with_shadows_shader
import random

app = Ursina()

# Game state
class GameState:
    def __init__(self):
        self.wanted_level = 0
        self.in_vehicle = False
        self.current_vehicle = None
        self.police_chase_active = False

game_state = GameState()

# Player class
class Player(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model='cube',
            color=color.blue,
            position=(0, 1, 0),
            scale=(0.8, 1.8, 0.8),
            collider='box',
            **kwargs
        )
        self.speed = 8
        self.rotation_speed = 150
        self.health = 100

    def update(self):
        if not game_state.in_vehicle:
            # Player movement
            self.rotation_y += held_keys['d'] * self.rotation_speed * time.dt
            self.rotation_y -= held_keys['a'] * self.rotation_speed * time.dt
            forward = Vec3(self.forward.x, 0, self.forward.z).normalized()
            self.position += forward * held_keys['w'] * self.speed * time.dt
            self.position -= forward * held_keys['s'] * self.speed * time.dt
            
            # Keep player on ground
            self.y = 1
            
            # Check for nearby vehicles to enter
            if held_keys['e']:
                self.try_enter_vehicle()

    def try_enter_vehicle(self):
        for vehicle in vehicles:
            if distance(self.position, vehicle.position) < 3:
                game_state.in_vehicle = True
                game_state.current_vehicle = vehicle
                self.visible = False
                vehicle.take_control()
                break

    def exit_vehicle(self):
        if game_state.in_vehicle and game_state.current_vehicle:
            game_state.in_vehicle = False
            self.position = game_state.current_vehicle.position + Vec3(2, 0, 0)
            self.visible = True
            game_state.current_vehicle.release_control()
            game_state.current_vehicle = None

# Vehicle class
class Vehicle(Entity):
    def __init__(self, position=(0, 0, 0), vehicle_type='car', **kwargs):
        color_choice = random.choice([color.red, color.yellow, color.green, color.white, color.black])
        scale_choice = (2.5, 1.2, 5) if vehicle_type == 'car' else (3, 2, 6)
        
        super().__init__(
            model='cube',
            color=color_choice,
            position=position,
            scale=scale_choice,
            collider='box',
            **kwargs
        )
        self.speed = 0
        self.max_speed = 25
        self.acceleration = 15
        self.brake_force = 20
        self.turn_speed = 80
        self.controlled = False
        self.ai_speed = random.uniform(8, 15)
        self.ai_direction = random.choice([1, -1])
        self.vehicle_type = vehicle_type

    def update(self):
        if self.controlled:
            # Player control
            if held_keys['w']:
                self.speed = min(self.speed + self.acceleration * time.dt, self.max_speed)
            elif held_keys['s']:
                self.speed = max(self.speed - self.brake_force * time.dt, -self.max_speed * 0.5)
            else:
                # Gradual deceleration
                if self.speed > 0:
                    self.speed = max(0, self.speed - self.brake_force * 0.5 * time.dt)
                elif self.speed < 0:
                    self.speed = min(0, self.speed + self.brake_force * 0.5 * time.dt)
            
            # Steering
            if abs(self.speed) > 0.1:
                self.rotation_y += held_keys['d'] * self.turn_speed * time.dt * (self.speed / self.max_speed)
                self.rotation_y -= held_keys['a'] * self.turn_speed * time.dt * (self.speed / self.max_speed)
            
            # Movement
            forward = Vec3(self.forward.x, 0, self.forward.z).normalized()
            self.position += forward * self.speed * time.dt
            self.y = 0.6
            
            # Exit vehicle
            if held_keys['f']:
                player.exit_vehicle()
        else:
            # AI vehicle movement
            forward = Vec3(self.forward.x, 0, self.forward.z).normalized()
            self.position += forward * self.ai_speed * self.ai_direction * time.dt
            
            # Reverse direction at boundaries
            if abs(self.position.x) > 80 or abs(self.position.z) > 80:
                self.ai_direction *= -1
                self.rotation_y += 180

    def take_control(self):
        self.controlled = True
        self.speed = 0

    def release_control(self):
        self.controlled = False
        self.speed = 0

# Pedestrian class
class Pedestrian(Entity):
    def __init__(self, position=(0, 0, 0), **kwargs):
        super().__init__(
            model='cube',
            color=random.choice([color.orange, color.pink, color.violet, color.cyan]),
            position=position,
            scale=(0.7, 1.6, 0.7),
            collider='box',
            **kwargs
        )
        self.walk_speed = random.uniform(2, 4)
        self.direction = random.uniform(0, 360)
        self.rotation_y = self.direction
        self.alive = True

    def update(self):
        if self.alive:
            # Random walking
            forward = Vec3(self.forward.x, 0, self.forward.z).normalized()
            self.position += forward * self.walk_speed * time.dt
            
            # Random direction changes
            if random.random() < 0.01:
                self.direction = random.uniform(0, 360)
                self.rotation_y = self.direction
            
            # Stay within bounds
            if abs(self.position.x) > 90 or abs(self.position.z) > 90:
                self.direction += 180
                self.rotation_y = self.direction
            
            self.y = 0.8
            
            # Check collision with vehicles
            for vehicle in vehicles:
                if vehicle.controlled and distance(self.position, vehicle.position) < 3 and abs(vehicle.speed) > 5:
                    self.get_hit()
                    break

    def get_hit(self):
        self.alive = False
        self.color = color.dark_gray
        self.y = 0.2
        game_state.wanted_level += 1
        if game_state.wanted_level >= 2 and not game_state.police_chase_active:
            spawn_police()
        print(f"Wanted Level: {game_state.wanted_level} ⭐")

# Police vehicle class
class PoliceVehicle(Vehicle):
    def __init__(self, position=(0, 0, 0), **kwargs):
        super().__init__(position=position, vehicle_type='police', **kwargs)
        self.color = color.rgb(0, 0, 200)
        self.scale = (2.5, 1.2, 5)
        self.chase_speed = 18
        self.controlled = False

    def update(self):
        if not self.controlled:
            # Chase player
            if game_state.in_vehicle and game_state.current_vehicle:
                target_pos = game_state.current_vehicle.position
            else:
                target_pos = player.position
            
            direction_to_player = (target_pos - self.position).normalized()
            self.look_at(target_pos)
            self.position += direction_to_player * self.chase_speed * time.dt
            self.y = 0.6

def spawn_police():
    game_state.police_chase_active = True
    spawn_positions = [
        Vec3(player.position.x + 50, 0.6, player.position.z),
        Vec3(player.position.x - 50, 0.6, player.position.z),
        Vec3(player.position.x, 0.6, player.position.z + 50),
    ]
    for pos in spawn_positions[:game_state.wanted_level]:
        police_car = PoliceVehicle(position=pos)
        vehicles.append(police_car)

# Create world
ground = Entity(
    model='plane',
    color=color.rgb(40, 40, 40),
    collider='box',
    scale=(200, 1, 200),
    texture='white_cube',
    shader=lit_with_shadows_shader
)

# Create road grid
roads = []
road_width = 4
for i in range(-100, 101, 20):
    # Horizontal roads
    road = Entity(
        model='cube',
        color=color.rgb(30, 30, 30),
        position=(0, 0.02, i),
        scale=(200, 0.1, road_width),
        shader=lit_with_shadows_shader
    )
    roads.append(road)
    
    # Vertical roads
    road = Entity(
        model='cube',
        color=color.rgb(30, 30, 30),
        position=(i, 0.02, 0),
        scale=(road_width, 0.1, 200),
        shader=lit_with_shadows_shader
    )
    roads.append(road)

# Create buildings
buildings = []
building_types = [
    {'color': color.rgb(100, 100, 120), 'height': 15, 'name': 'Office'},
    {'color': color.rgb(150, 80, 80), 'height': 20, 'name': 'Apartment'},
    {'color': color.rgb(80, 120, 80), 'height': 10, 'name': 'Store'},
    {'color': color.rgb(180, 150, 100), 'height': 25, 'name': 'Hotel'},
]

for x in range(-90, 91, 20):
    for z in range(-90, 91, 20):
        if abs(x) < 5 and abs(z) < 5:
            continue
        
        building_type = random.choice(building_types)
        building = Entity(
            model='cube',
            color=building_type['color'],
            position=(x + random.uniform(-3, 3), building_type['height'] / 2, z + random.uniform(-3, 3)),
            scale=(random.uniform(6, 10), building_type['height'], random.uniform(6, 10)),
            collider='box',
            shader=lit_with_shadows_shader
        )
        buildings.append(building)

# Special buildings
police_station = Entity(
    model='cube',
    color=color.rgb(0, 0, 150),
    position=(50, 8, 50),
    scale=(12, 16, 12),
    collider='box',
    shader=lit_with_shadows_shader
)

hotel = Entity(
    model='cube',
    color=color.rgb(200, 180, 100),
    position=(-50, 15, -50),
    scale=(15, 30, 15),
    collider='box',
    shader=lit_with_shadows_shader
)

# Create player
player = Player()

# Create vehicles
vehicles = []
for _ in range(15):
    x = random.uniform(-80, 80)
    z = random.uniform(-80, 80)
    vehicle = Vehicle(position=(x, 0.6, z))
    vehicles.append(vehicle)

# Create pedestrians
pedestrians = []
for _ in range(20):
    x = random.uniform(-80, 80)
    z = random.uniform(-80, 80)
    pedestrian = Pedestrian(position=(x, 0.8, z))
    pedestrians.append(pedestrian)

# Camera setup
camera.parent = player
camera.position = (0, 8, -20)
camera.rotation_x = 15

def update():
    # Update camera to follow player or vehicle
    if game_state.in_vehicle and game_state.current_vehicle:
        camera.parent = game_state.current_vehicle
        camera.position = (0, 8, -20)
    else:
        camera.parent = player
        camera.position = (0, 8, -20)

# Lighting
DirectionalLight(parent=scene, y=2, z=3, shadows=True, rotation=(45, -45, 45))
AmbientLight(color=color.rgba(100, 100, 100, 0.6))

# UI
wanted_text = Text(
    text='Wanted: ⭐ 0',
    position=(-0.85, 0.45),
    origin=(0, 0),
    scale=2,
    color=color.red
)

info_text = Text(
    text='WASD: Move/Drive | E: Enter Vehicle | F: Exit Vehicle',
    position=(0, -0.45),
    origin=(0, 0),
    scale=1.5,
    color=color.white
)

def update_ui():
    wanted_text.text = f'Wanted: {"⭐" * game_state.wanted_level} {game_state.wanted_level}'
    if game_state.in_vehicle:
        info_text.text = f'Speed: {abs(game_state.current_vehicle.speed):.1f} | F: Exit Vehicle'
    else:
        info_text.text = 'WASD: Move | E: Enter Vehicle'

# Update UI continuously
def game_update():
    update_ui()

app.update = game_update

app.run()
