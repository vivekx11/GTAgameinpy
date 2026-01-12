from ursina import *
from ursina.shaders import lit_with_shadows_shader
import random
import math

# Initialize the game
app = Ursina()
window.title = 'GTA: Python City'
window.borderless = False
window.fullscreen = False

# Custom UI Colors
UI_COLORS = {
    'primary': color.rgb(41, 128, 185),      # Blue
    'secondary': color.rgb(52, 152, 219),    # Light Blue
    'danger': color.rgb(231, 76, 60),        # Red
    'warning': color.rgb(241, 196, 15),      # Yellow
    'success': color.rgb(46, 204, 113),      # Green
    'dark': color.rgb(44, 62, 80),           # Dark Blue
    'light': color.rgb(236, 240, 241),       # Light Gray
    'dark_transparent': color.rgba(0, 0, 0, 180),
    'police_blue': color.rgb(33, 97, 140),
    'health_green': color.rgb(39, 174, 96),
    'armor_blue': color.rgb(52, 152, 219),
    'money_gold': color.rgb(241, 196, 15),
    'dark_gray': color.rgb(40, 40, 40),
}

# Game state
game_state = {
    'wanted_level': 0,
    'money': 2500,
    'health': 100,
    'armor': 50,
    'in_vehicle': False,
    'current_vehicle': None,
    'police_chase': False,
    'ammo': 30,
    'max_ammo': 90,
    'weapon': 'Pistol',
    'radio_station': 'Radio Los Santos',
    'time': '12:00',
    'day': 1,
    'mission_active': False,
    'mission_name': 'None',
}

class ProgressBar(Entity):
    def __init__(self, value=100, max_value=100, bar_color=color.green, position=(-0.8, 0.45), **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.value = value
        self.max_value = max_value
        self.bg = Entity(
            parent=self,
            model='quad',
            color=UI_COLORS['dark_gray'],
            scale=(0.2, 0.03),
            position=position
        )
        self.fill = Entity(
            parent=self.bg,
            model='quad',
            color=bar_color,
            scale=(value/max_value, 0.9),
            position=(-0.5 + (value/max_value)/2, 0, -0.01)
        )
        self.text = Text(
            parent=self.bg,
            text=f'{value}/{max_value}',
            origin=(0, 0),
            position=(0, 0),
            scale=1.5,
            color=color.white
        )
        
    def update_value(self, new_value):
        self.value = max(0, min(new_value, self.max_value))
        self.fill.scale_x = self.value / self.max_value
        self.fill.x = -0.5 + (self.value/self.max_value)/2
        self.text.text = f'{int(self.value)}/{self.max_value}'

class IconDisplay(Entity):
    def __init__(self, icon='●', icon_color=color.white, position=(0, 0), scale=1, **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.icon = Text(
            text=icon,
            position=position,
            scale=scale,
            color=icon_color
        )
        self.value_text = Text(
            text='',
            position=(position[0] + 0.05, position[1]),
            scale=scale * 0.8,
            color=color.white
        )
        
    def update_value(self, value, max_value=None):
        if max_value:
            self.value_text.text = f'{value}/{max_value}'
        else:
            self.value_text.text = str(value)

class WantedStars(Entity):
    def __init__(self, position=(-0.8, 0.4), **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.stars = []
        self.base_position = position
        
        for i in range(5):
            star = Entity(
                parent=self,
                model='circle',
                color=color.gray,
                position=(position[0] + i * 0.04, position[1]),
                scale=0.02
            )
            self.stars.append(star)
            
    def update_stars(self, wanted_level):
        for i, star in enumerate(self.stars):
            if i < wanted_level:
                star.color = UI_COLORS['warning']
                if hasattr(self, 'time'):
                    pulse = math.sin(self.time * 5 + i) * 0.005
                else:
                    pulse = 0
                star.scale = (0.02 + pulse, 0.02 + pulse)
            else:
                star.color = color.gray
                star.scale = (0.02, 0.02)
                
    def update(self):
        if hasattr(self, 'time'):
            self.time += time.dt
        else:
            self.time = 0
        self.update_stars(game_state['wanted_level'])

class MiniMap(Entity):
    def __init__(self, position=(0.75, 0.35), size=0.2, **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.position = position
        self.size = size
        
        # Background
        self.bg = Entity(
            parent=self,
            model='quad',
            color=UI_COLORS['dark_transparent'],
            scale=(size, size),
            position=position
        )
        
        # Player marker
        self.player_marker = Entity(
            parent=self.bg,
            model='circle',
            color=UI_COLORS['success'],
            scale=0.01,
            position=(0, 0, -0.02)
        )
        
        # North indicator
        self.north = Text(
            parent=self.bg,
            text='N',
            position=(0, 0.45),
            scale=0.8,
            color=color.white
        )
        
    def update(self):
        # Update player position on minimap
        if player:
            map_x = player.x / 100 * 0.4
            map_y = player.z / 100 * 0.4
            self.player_marker.position = (map_x, map_y, -0.02)

class RadioDisplay(Entity):
    def __init__(self, position=(0.75, 0.15), **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.stations = [
            'Radio Los Santos',
            'K-DST',
            'Bounce FM',
            'SF-UR',
            'Radio X',
            'Master Sounds 98.3'
        ]
        self.current_index = 0
        
        self.bg = Entity(
            parent=self,
            model='quad',
            color=UI_COLORS['dark_transparent'],
            scale=(0.2, 0.06),
            position=position
        )
        
        self.icon = Text(
            parent=self.bg,
            text='📻',
            position=(-0.4, 0),
            scale=1.2,
            color=UI_COLORS['primary']
        )
        
        self.station_text = Text(
            parent=self.bg,
            text=self.stations[self.current_index],
            position=(0, 0),
            scale=1,
            color=color.white
        )
        
    def next_station(self):
        self.current_index = (self.current_index + 1) % len(self.stations)
        self.station_text.text = self.stations[self.current_index]
        game_state['radio_station'] = self.stations[self.current_index]
        
    def prev_station(self):
        self.current_index = (self.current_index - 1) % len(self.stations)
        self.station_text.text = self.stations[self.current_index]
        game_state['radio_station'] = self.stations[self.current_index]

class NotificationSystem:
    def __init__(self):
        self.notifications = []
        self.max_notifications = 3
        
    def add_notification(self, title, message, icon='ℹ️', notif_color=color.white):
        notification = {
            'title': title,
            'message': message,
            'icon': icon,
            'color': notif_color,
            'time': 0,
            'duration': 3,
            'y_position': 0.35 - len(self.notifications) * 0.08
        }
        
        self.notifications.append(notification)
        
        # Create UI elements for notification
        bg = Entity(
            parent=camera.ui,
            model='quad',
            color=UI_COLORS['dark_transparent'],
            scale=(0.3, 0.07),
            position=(0, notification['y_position']),
            origin=(0, 0)
        )
        
        icon_text = Text(
            parent=bg,
            text=icon,
            position=(-0.45, 0),
            scale=1.5,
            color=notif_color
        )
        
        title_text = Text(
            parent=bg,
            text=title,
            position=(-0.35, 0.02),
            scale=1.2,
            color=notif_color
        )
        
        message_text = Text(
            parent=bg,
            text=message,
            position=(-0.35, -0.02),
            scale=0.9,
            color=color.gray
        )
        
        notification['ui_elements'] = [bg, icon_text, title_text, message_text]
        
        # Limit number of notifications
        if len(self.notifications) > self.max_notifications:
            self.remove_notification(self.notifications[0])
            
    def remove_notification(self, notification):
        for element in notification['ui_elements']:
            destroy(element)
        self.notifications.remove(notification)
        self.reposition_notifications()
        
    def reposition_notifications(self):
        for i, notification in enumerate(self.notifications):
            new_y = 0.35 - i * 0.08
            notification['y_position'] = new_y
            for element in notification['ui_elements']:
                if isinstance(element, Entity):
                    element.animate_y(new_y, duration=0.2)
                    
    def update(self):
        for notification in self.notifications[:]:
            notification['time'] += time.dt
            if notification['time'] >= notification['duration']:
                self.remove_notification(notification)

class MissionDisplay(Entity):
    def __init__(self, **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.active = False
        
        self.bg = Entity(
            parent=self,
            model='quad',
            color=UI_COLORS['dark_transparent'],
            scale=(0.35, 0.08),
            position=(0, 0.4)
        )
        
        self.icon = Text(
            parent=self.bg,
            text='🎯',
            position=(-0.45, 0),
            scale=1.5,
            color=UI_COLORS['warning']
        )
        
        self.title = Text(
            parent=self.bg,
            text='MISSION ACTIVE',
            position=(-0.35, 0.02),
            scale=1.2,
            color=UI_COLORS['warning']
        )
        
        self.mission_name = Text(
            parent=self.bg,
            text='None',
            position=(-0.35, -0.02),
            scale=1,
            color=color.white
        )
        
    def set_mission(self, name):
        self.active = True
        self.mission_name.text = name
        game_state['mission_active'] = True
        game_state['mission_name'] = name
        
    def clear_mission(self):
        self.active = False
        self.mission_name.text = 'None'
        game_state['mission_active'] = False
        game_state['mission_name'] = 'None'

# Initialize UI Components
def setup_ui():
    # Health Bar
    global health_bar
    health_bar = ProgressBar(
        value=game_state['health'],
        max_value=100,
        bar_color=UI_COLORS['health_green'],
        position=(-0.8, 0.45)
    )
    
    # Armor Bar
    global armor_bar
    armor_bar = ProgressBar(
        value=game_state['armor'],
        max_value=100,
        bar_color=UI_COLORS['armor_blue'],
        position=(-0.8, 0.4)
    )
    
    # Wanted Stars
    global wanted_stars
    wanted_stars = WantedStars(position=(-0.8, 0.35))
    
    # MiniMap
    global minimap
    minimap = MiniMap(position=(0.75, 0.35), size=0.2)
    
    # Radio Display
    global radio_display
    radio_display = RadioDisplay(position=(0.75, 0.15))
    
    # Money Display
    global money_display
    money_display = IconDisplay(
        icon='💰',
        icon_color=UI_COLORS['money_gold'],
        position=(-0.8, 0.3),
        scale=2
    )
    money_display.update_value(game_state['money'])
    
    # Ammo Display
    global ammo_display
    ammo_display = IconDisplay(
        icon='🔫',
        icon_color=color.white,
        position=(0.8, -0.4),
        scale=2
    )
    ammo_display.update_value(game_state['ammo'], game_state['max_ammo'])
    
    # Weapon Name
    global weapon_name_display
    weapon_name_display = Text(
        text=game_state['weapon'],
        position=(0.65, -0.4),
        scale=1.5,
        color=color.white
    )
    
    # Vehicle Display
    global vehicle_display
    vehicle_display = Text(
        text='ON FOOT',
        position=(0, -0.45),
        scale=1.5,
        color=color.white
    )
    
    # Time Display
    global time_display
    time_display = Text(
        text=f'DAY {game_state["day"]} - {game_state["time"]}',
        position=(-0.8, -0.45),
        scale=1.5,
        color=color.gray
    )
    
    # Notification System
    global notification_system
    notification_system = NotificationSystem()
    
    # Mission Display
    global mission_display
    mission_display = MissionDisplay()

# Update UI Function
def update_ui():
    # Update progress bars
    health_bar.update_value(game_state['health'])
    armor_bar.update_value(game_state['armor'])
    
    # Update wanted stars
    wanted_stars.update_stars(game_state['wanted_level'])
    
    # Update text displays
    money_display.update_value(game_state['money'])
    ammo_display.update_value(game_state['ammo'], game_state['max_ammo'])
    weapon_name_display.text = game_state['weapon']
    time_display.text = f'DAY {game_state["day"]} - {game_state["time"]}'
    
    # Update vehicle display
    if game_state['in_vehicle'] and game_state['current_vehicle']:
        vehicle_display.text = f'IN VEHICLE: {game_state["current_vehicle"].model_type.upper()}'
        vehicle_display.color = UI_COLORS['primary']
    else:
        vehicle_display.text = 'ON FOOT'
        vehicle_display.color = color.white
    
    # Update notification system
    notification_system.update()
    
    # Update minimap
    minimap.update()

# Add sample notifications
def add_sample_notifications():
    notification_system.add_notification(
        'Welcome to Python City',
        'Explore the city and complete missions',
        '🎮',
        UI_COLORS['primary']
    )
    
    notification_system.add_notification(
        'Quick Cash',
        'Find the hidden packages around the city',
        '💰',
        UI_COLORS['money_gold']
    )
    
    notification_system.add_notification(
        'Police Alert',
        'Avoid wanted levels to stay safe',
        '🚨',
        UI_COLORS['danger']
    )

# Test mission
def start_test_mission():
    mission_display.set_mission('First Assignment')
    
    notification_system.add_notification(
        'Mission Started',
        'First Assignment: Steal a car',
        '🎯',
        UI_COLORS['success']
    )

# ------------------------------------------------------------
# GAME CODE - SIMPLIFIED
# ------------------------------------------------------------

# Create the world
ground = Entity(
    model='plane',
    texture='grass',
    collider='box',
    scale=(100, 1, 100),
    shader=lit_with_shadows_shader
)

# Create roads
for z in range(-40, 41, 20):
    road = Entity(
        model='plane',
        texture='brick',
        position=(0, 0.01, z),
        scale=(15, 1, 100),
        color=color.dark_gray,
        collider='box'
    )

for x in range(-40, 41, 20):
    road = Entity(
        model='plane',
        texture='brick',
        position=(x, 0.01, 0),
        scale=(100, 1, 15),
        color=color.dark_gray,
        collider='box'
    )

# Create buildings
for x in range(-30, 31, 15):
    for z in range(-30, 31, 15):
        if abs(x) > 10 or abs(z) > 10:
            building = Entity(
                model='cube',
                texture='brick',
                position=(x, 2, z),
                scale=(4, random.uniform(3, 8), 4),
                collider='box',
                shader=lit_with_shadows_shader
            )

class Player(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model='cube',
            texture='white_cube',
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

    def update(self):
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
            texture='brick',
            position=position,
            scale=(2, 1, 4),
            collider='box',
            shader=lit_with_shadows_shader,
            **kwargs
        )
        self.model_type = model_type
        self.speed = 0
        self.max_speed = 15
        self.acceleration = 8
        self.brake_power = 12
        self.turn_speed = 60
        self.driver = None

    def update(self):
        if self.driver is not None:
            # Player is driving
            # Acceleration
            if held_keys['w']:
                self.speed += self.acceleration * time.dt
            elif held_keys['s']:
                self.speed -= self.brake_power * time.dt
            else:
                self.speed *= 0.95
            
            self.speed = max(-self.max_speed/2, min(self.speed, self.max_speed))
            
            # Steering
            if held_keys['d']:
                self.rotation_y += self.turn_speed * time.dt * (self.speed/self.max_speed)
            if held_keys['a']:
                self.rotation_y -= self.turn_speed * time.dt * (self.speed/self.max_speed)
            
            # Movement
            forward = Vec3(self.forward.x, 0, self.forward.z).normalized()
            self.position += forward * self.speed * time.dt
            
            # Camera
            camera.parent = self
            camera.position = (0, 8, -15)
            camera.rotation_x = 20

# Create player
player = Player()

# Create sample vehicle
car = Vehicle(position=(5, 0.5, 5))

# Setup UI
setup_ui()
add_sample_notifications()

# Setup camera
camera.parent = player
camera.position = (0, 5, -15)
camera.rotation_x = 20

# Lighting
DirectionalLight(parent=scene, rotation=(45, -45, 45), shadows=True)
AmbientLight(color=color.rgba(100, 100, 100, 0.5))

# Input handling
def input(key):
    # Enter/Exit vehicle
    if key == 'f':
        if not game_state['in_vehicle']:
            # Try to enter nearest vehicle
            for entity in scene.entities:
                if hasattr(entity, 'model_type') and distance(player, entity) < 3:
                    entity.driver = player
                    player.visible = False
                    game_state['in_vehicle'] = True
                    game_state['current_vehicle'] = entity
                    notification_system.add_notification(
                        'Vehicle',
                        f'Entered {entity.model_type}',
                        '🚗',
                        UI_COLORS['primary']
                    )
                    break
        else:
            # Exit current vehicle
            if game_state['current_vehicle']:
                game_state['current_vehicle'].driver = None
                player.visible = True
                player.position = game_state['current_vehicle'].position + Vec3(2, 0, 0)
                game_state['in_vehicle'] = False
                game_state['current_vehicle'] = None
                camera.parent = player
                camera.position = (0, 5, -15)
    
    # Radio controls
    if key == 'r':
        radio_display.next_station()
        notification_system.add_notification(
            'Radio',
            f'Switched to {game_state["radio_station"]}',
            '📻',
            UI_COLORS['secondary']
        )
    
    # Debug keys
    if key == 'p':
        game_state['wanted_level'] = min(5, game_state['wanted_level'] + 1)
        notification_system.add_notification(
            'Wanted Level',
            f'Increased to {game_state["wanted_level"]} stars',
            '🚨',
            UI_COLORS['danger']
        )
    
    if key == 'o':
        if game_state['wanted_level'] > 0:
            game_state['wanted_level'] = max(0, game_state['wanted_level'] - 1)
    
    if key == 'm':
        game_state['money'] += 1000
        notification_system.add_notification(
            'Money',
            f'Added $1000',
            '💰',
            UI_COLORS['money_gold']
        )
    
    # Mission start
    if key == 'n':
        if not game_state['mission_active']:
            start_test_mission()
        else:
            mission_display.clear_mission()
            notification_system.add_notification(
                'Mission',
                'Mission completed! +$500',
                '✅',
                UI_COLORS['success']
            )
            game_state['money'] += 500
    
    # Change weapon
    if key == '1':
        game_state['weapon'] = 'Fist'
        game_state['ammo'] = 0
        game_state['max_ammo'] = 0
    elif key == '2':
        game_state['weapon'] = 'Pistol'
        game_state['ammo'] = 30
        game_state['max_ammo'] = 90
    elif key == '3':
        game_state['weapon'] = 'Shotgun'
        game_state['ammo'] = 8
        game_state['max_ammo'] = 24

# Update function
def update():
    update_ui()
    
    # Auto-decrease wanted level
    if game_state['wanted_level'] > 0 and random.random() < 0.001:
        game_state['wanted_level'] -= 1
    
    # Update time (simple simulation)
    total_seconds = int(time.time() * 10) % 86400  # Speed up time (10x)
    hours = (total_seconds // 3600) % 24
    minutes = (total_seconds % 3600) // 60
    game_state['time'] = f'{hours:02d}:{minutes:02d}'

# Run the game
print("""
=== GTA: PYTHON CITY ===
CONTROLS:
WASD: Move character/vehicle
Space: Jump
Q/E: Strafe left/right
F: Enter/Exit vehicle
R: Change radio station
1-3: Select weapons (Fist, Pistol, Shotgun)
P: Increase wanted level (debug)
O: Decrease wanted level (debug)
M: Add money (debug)
N: Start/Complete mission
""")

app.run()
