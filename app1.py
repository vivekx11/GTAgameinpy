from ursina import *
from ursina.shaders import lit_with_shadows_shader
import random

# Initialize the game
app = Ursina()
window.title = 'GTA-Style Game'
window.borderless = False
window.fullscreen = False

# Load assets (you should replace these with actual texture files)
# For now, we'll use built-in textures
ground_texture = 'grass'
road_texture = 'brick'
building_texture = 'brick'
car_textures = ['brick', 'white_cube']
player_texture = 'white_cube'

# Game state
game_state = {
    'wanted_level': 0,
    'money': 1000,
    'health': 100,
    'in_vehicle': False,
    'current_vehicle': None,
    'police_chase': False
}

class Player(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model='cube',
            texture=player_texture,
            position=(0, 1, 0),
            scale=(0.5, 1.8, 0.5),
            collider='box',
            shader=lit_with_shadows_shader,
            **kwargs
        )
        self.speed = 6
        self.rotation_speed = 150
        self.jump_height = 3
        self.gravity = 1
        self.velocity_y = 0
        self.on_ground = True
        self.in_vehicle = False

    def update(self):
        if self.in_vehicle:
            return
            
        # Movement controls
        self.rotation_y += held_keys['d'] * self.rotation_speed * time.dt
        self.rotation_y -= held_keys['a'] * self.rotation_speed * time.dt
        
        forward = Vec3(self.forward.x, 0, self.forward.z).normalized()
        right = Vec3(self.right.x, 0, self.right.z).normalized()
        
        # Forward/backward movement
        if held_keys['w']:
            self.position += forward * self.speed * time.dt
        if held_keys['s']:
            self.position -= forward * self.speed * time.dt
        
        # Strafe movement
        if held_keys['q']:
            self.position -= right * self.speed * time.dt
        if held_keys['e']:
            self.position += right * self.speed * time.dt
        
        # Jump
        if held_keys['space'] and self.on_ground:
            self.velocity_y = self.jump_height
            self.on_ground = False
        
        # Apply gravity
        if not self.on_ground:
            self.velocity_y -= self.gravity * time.dt
            self.y += self.velocity_y * time.dt
            
            # Ground collision
            if self.y <= 0.9:
                self.y = 0.9
                self.velocity_y = 0
                self.on_ground = True

class Vehicle(Entity):
    def __init__(self, model_type='car', position=(0, 0, 0), **kwargs):
        super().__init__(
            model='cube',
            texture=random.choice(car_textures),
            position=position,
            scale=(2, 1, 4),
            collider='box',
            shader=lit_with_shadows_shader,
            **kwargs
        )
        self.model_type = model_type
        self.speed = 0
        self.max_speed = 15 if model_type == 'car' else 20
        self.acceleration = 8 if model_type == 'car' else 12
        self.brake_power = 12
        self.turn_speed = 60
        self.engine_on = False
        self.driver = None
        
        # Different vehicle types
        if model_type == 'police':
            self.color = color.blue
            self.max_speed = 18
        elif model_type == 'taxi':
            self.color = color.yellow
        elif model_type == 'sports':
            self.color = color.red
            self.max_speed = 25
            self.acceleration = 15

    def update(self):
        if self.driver is not None:
            # Player is driving
            self.engine_on = True
            
            # Acceleration
            if held_keys['w']:
                self.speed += self.acceleration * time.dt
            elif held_keys['s']:
                self.speed -= self.brake_power * time.dt
            else:
                # Natural deceleration
                self.speed *= 0.95
            
            # Limit speed
            self.speed = max(-self.max_speed/2, min(self.speed, self.max_speed))
            
            # Steering
            if held_keys['d']:
                self.rotation_y += self.turn_speed * time.dt * (self.speed/self.max_speed)
            if held_keys['a']:
                self.rotation_y -= self.turn_speed * time.dt * (self.speed/self.max_speed)
            
            # Movement
            forward = Vec3(self.forward.x, 0, self.forward.z).normalized()
            self.position += forward * self.speed * time.dt
            
            # Keep vehicle on ground
            self.y = max(0.5, self.y)
            
            # Update camera
            camera.parent = self
            camera.position = (0, 8, -15)
            camera.rotation_x = 20
        else:
            # NPC vehicle behavior
            if random.random() < 0.01:  # 1% chance to change direction
                self.rotation_y += random.uniform(-30, 30)
            
            forward = Vec3(self.forward.x, 0, self.forward.z).normalized()
            self.position += forward * 5 * time.dt
            
            # Keep on road (simple boundary check)
            if abs(self.x) > 40 or abs(self.z) > 40:
                self.rotation_y += 180
            
            # Natural stop
            self.speed *= 0.98

    def enter_vehicle(self, player):
        self.driver = player
        player.visible = False
        player.in_vehicle = True
        player.position = self.position
        game_state['in_vehicle'] = True
        game_state['current_vehicle'] = self
        
    def exit_vehicle(self, player):
        self.driver = None
        player.visible = True
        player.in_vehicle = False
        player.position = self.position + Vec3(2, 0, 0)
        game_state['in_vehicle'] = False
        game_state['current_vehicle'] = None
        camera.parent = player
        camera.position = (0, 5, -15)

class NPC(Entity):
    def __init__(self, position=(0, 0, 0), **kwargs):
        super().__init__(
            model='cube',
            texture=player_texture,
            position=position,
            scale=(0.5, 1.8, 0.5),
            collider='box',
            shader=lit_with_shadows_shader,
            **kwargs
        )
        self.speed = random.uniform(1, 3)
        self.direction = random.uniform(0, 360)
        self.walk_timer = 0
        
    def update(self):
        self.walk_timer += time.dt
        if self.walk_timer > random.uniform(2, 5):
            self.direction = random.uniform(0, 360)
            self.walk_timer = 0
        
        self.rotation_y = self.direction
        forward = Vec3(self.forward.x, 0, self.forward.z).normalized()
        self.position += forward * self.speed * time.dt
        
        # Keep NPCs in bounds
        if abs(self.x) > 45 or abs(self.z) > 45:
            self.rotation_y += 180

class Police(Entity):
    def __init__(self, position=(0, 0, 0), **kwargs):
        super().__init__(
            model='cube',
            texture=player_texture,
            position=position,
            scale=(0.5, 1.8, 0.5),
            color=color.blue,
            collider='box',
            shader=lit_with_shadows_shader,
            **kwargs
        )
        self.speed = 4
        self.target = None
        
    def update(self):
        if game_state['wanted_level'] > 0:
            # Chase player
            if player.visible:
                self.target = player
            elif game_state['current_vehicle']:
                self.target = game_state['current_vehicle']
            
            if self.target:
                direction = self.target.position - self.position
                if direction.length() > 0:
                    direction.normalize()
                    self.position += direction * self.speed * time.dt
                    self.look_at(self.target)

class Building(Entity):
    def __init__(self, position=(0, 0, 0), building_type='apartment', **kwargs):
        super().__init__(
            model='cube',
            texture=building_texture,
            position=position,
            collider='box',
            shader=lit_with_shadows_shader,
            **kwargs
        )
        
        self.building_type = building_type
        self.scale_y = random.uniform(3, 8)
        
        if building_type == 'hotel':
            self.color = color.gold
            self.scale = (6, self.scale_y, 6)
        elif building_type == 'police_station':
            self.color = color.blue
            self.scale = (8, self.scale_y, 8)
            self.texture = 'white_cube'
        elif building_type == 'hospital':
            self.color = color.white
            self.scale = (7, self.scale_y, 7)
        elif building_type == 'bank':
            self.color = color.gray
            self.scale = (5, self.scale_y, 5)
        else:  # apartment
            self.scale = (4, self.scale_y, 4)

# Create the world
ground = Entity(
    model='plane',
    texture=ground_texture,
    collider='box',
    scale=(100, 1, 100),
    shader=lit_with_shadows_shader
)

# Create roads
roads = []
for z in range(-40, 41, 20):
    road = Entity(
        model='plane',
        texture=road_texture,
        position=(0, 0.01, z),
        scale=(15, 1, 100),
        color=color.dark_gray,
        collider='box'
    )
    roads.append(road)

for x in range(-40, 41, 20):
    road = Entity(
        model='plane',
        texture=road_texture,
        position=(x, 0.01, 0),
        scale=(100, 1, 15),
        color=color.dark_gray,
        collider='box'
    )
    roads.append(road)

# Add road markings
for z in range(-50, 51, 10):
    line = Entity(
        model='cube',
        color=color.yellow,
        position=(0, 0.02, z),
        scale=(0.1, 0.01, 2)
    )

# Create buildings with different types
building_types = ['apartment', 'hotel', 'police_station', 'hospital', 'bank']
buildings = []

for x in range(-30, 31, 15):
    for z in range(-30, 31, 15):
        if abs(x) > 10 or abs(z) > 10:  # Leave center area open
            building_type = random.choice(building_types)
            building = Building(
                position=(x, building.scale_y/2 if 'scale_y' in locals() else 2, z),
                building_type=building_type
            )
            buildings.append(building)

# Create player
player = Player()

# Create vehicles
vehicles = []
vehicle_positions = [(-10, 0, -10), (10, 0, 10), (-15, 0, 15), (15, 0, -15)]

for i, pos in enumerate(vehicle_positions):
    if i == 0:
        vehicle = Vehicle(model_type='police', position=pos)
    elif i == 1:
        vehicle = Vehicle(model_type='sports', position=pos)
    elif i == 2:
        vehicle = Vehicle(model_type='taxi', position=pos)
    else:
        vehicle = Vehicle(model_type='car', position=pos)
    vehicles.append(vehicle)

# Create NPCs
npcs = []
for _ in range(20):
    npc = NPC(position=(random.uniform(-40, 40), 0.9, random.uniform(-40, 40)))
    npcs.append(npc)

# Create police officers
police_force = []
for _ in range(5):
    police = Police(position=(random.uniform(-40, 40), 0.9, random.uniform(-40, 40)))
    police_force.append(police)

# Setup camera
camera.parent = player
camera.position = (0, 5, -15)
camera.rotation_x = 20
camera.fov = 90

# Lighting
DirectionalLight(parent=scene, rotation=(45, -45, 45), shadows=True)
AmbientLight(color=color.rgba(100, 100, 100, 0.5))

# UI Elements
wanted_display = Text(text=f'Wanted Level: {game_state["wanted_level"]}', 
                      position=(-0.85, 0.45), scale=2, color=color.red)
health_display = Text(text=f'Health: {game_state["health"]}', 
                     position=(-0.85, 0.4), scale=2, color=color.green)
money_display = Text(text=f'Money: ${game_state["money"]}', 
                    position=(-0.85, 0.35), scale=2, color=color.yellow)
vehicle_display = Text(text='', position=(-0.85, 0.3), scale=2, color=color.cyan)

instructions = Text(text='WASD: Move | Space: Jump | F: Enter/Exit Vehicle | Q/E: Strafe', 
                   position=(-0.85, -0.45), scale=1.5, color=color.white)

def update_ui():
    wanted_display.text = f'Wanted Level: {game_state["wanted_level"]}'
    health_display.text = f'Health: {game_state["health"]}'
    money_display.text = f'Money: ${game_state["money"]}'
    
    if game_state['in_vehicle']:
        vehicle_display.text = f'In: {game_state["current_vehicle"].model_type}'
        vehicle_display.color = color.cyan
    else:
        vehicle_display.text = 'On Foot'
        vehicle_display.color = color.white

def check_collisions():
    # Check vehicle collisions with NPCs
    for vehicle in vehicles:
        if vehicle.driver is player:  # Player is driving
            for npc in npcs:
                if distance(vehicle, npc) < 2:
                    # Hit an NPC
                    npc.position = (random.uniform(-40, 40), 0.9, random.uniform(-40, 40))
                    game_state['wanted_level'] = min(5, game_state['wanted_level'] + 1)
                    game_state['money'] -= 100
                    
    # Check player collisions with police
    if game_state['wanted_level'] > 0:
        for police in police_force:
            if distance(player, police) < 2:
                # Caught by police
                game_state['wanted_level'] = 0
                game_state['money'] = max(0, game_state['money'] - 500)

def input(key):
    # Enter/Exit vehicle
    if key == 'f':
        if not game_state['in_vehicle']:
            # Try to enter nearest vehicle
            for vehicle in vehicles:
                if distance(player, vehicle) < 3:
                    vehicle.enter_vehicle(player)
                    break
        else:
            # Exit current vehicle
            if game_state['current_vehicle']:
                game_state['current_vehicle'].exit_vehicle(player)
    
    # Debug keys
    if key == 'p':
        game_state['wanted_level'] = min(5, game_state['wanted_level'] + 1)
    if key == 'o':
        game_state['wanted_level'] = max(0, game_state['wanted_level'] - 1)
    if key == 'm':
        game_state['money'] += 1000

def update():
    update_ui()
    check_collisions()
    
    # Auto-decrease wanted level over time
    if game_state['wanted_level'] > 0 and random.random() < 0.001:
        game_state['wanted_level'] -= 1

# Run the game
print("""
=== GTA-STYLE GAME CONTROLS ===
WASD: Move character/vehicle
Space: Jump
Q/E: Strafe left/right
F: Enter/Exit vehicle
P: Increase wanted level (debug)
O: Decrease wanted level (debug)
M: Add money (debug)
""")

app.run()
