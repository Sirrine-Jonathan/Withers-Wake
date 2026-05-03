import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Mock pykraken to allow testing without a real engine instance/window
sys.modules['pykraken'] = MagicMock()
import pykraken as kn

# Simple FakeVec2 for testing math
class FakeVec2:
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)
    def __add__(self, other): return FakeVec2(self.x + other.x, self.y + other.y)
    def __sub__(self, other): return FakeVec2(self.x - other.x, self.y - other.y)
    def __mul__(self, scalar): return FakeVec2(self.x * scalar, self.y * scalar)
    def __abs__(self): return FakeVec2(abs(self.x), abs(self.y))
    def __gt__(self, other): return self.x > other
    def __lt__(self, other): return self.x < other
    def __le__(self, other): return self.x <= other
    def __ge__(self, other): return self.x >= other
    @property
    def length(self): return (self.x**2 + self.y**2)**0.5
    def distance_to(self, other): return ((self.x - other.x)**2 + (self.y - other.y)**2)**0.5

# Re-configure mock to return FakeVec2
kn.Vec2.side_effect = lambda x=0, y=0: FakeVec2(x, y)
kn.Vec2.ZERO = FakeVec2(0, 0)

# Ensure input functions return False by default
kn.key.is_pressed.return_value = False
kn.key.is_just_pressed.return_value = False
kn.mouse.is_pressed.return_value = False
kn.mouse.is_just_pressed.return_value = False

def create_mock_body(*args, **kwargs):
    body = MagicMock()
    body.pos = FakeVec2(0, 0)
    body.velocity = FakeVec2(0, 0)
    body.acceleration = 2000.0
    body.max_speed = 400.0
    body.friction = 1000.0
    body.is_on_floor = False
    body.add_collider = MagicMock()
    body.move_and_slide = MagicMock()
    body.destroy = MagicMock()
    return body

kn.physics.CharacterBody.side_effect = create_mock_body
kn.physics.StaticBody.side_effect = create_mock_body

# Import the classes we want to test
from main import DecayingPlatform, LifeSpark, Game

def test_decaying_platform_lifecycle():
    # We need to manually set the return value for this specific test
    mock_body = MagicMock()
    with patch('pykraken.physics.StaticBody', return_value=mock_body):
        world = MagicMock()
        pos = kn.Vec2(100, 100)
        size = kn.Vec2(50, 50)
        atlas = MagicMock()
        
        plat = DecayingPlatform(world, pos, size, atlas)
        
        # Initial state
        assert plat.lifetime == 5.0
        assert not plat.update(1.0)
        
        # Reach end of life
        assert plat.update(4.0)
        mock_body.destroy.assert_called_once()

def test_life_spark_collection():
    atlas = MagicMock()
    pos = kn.Vec2(200, 200)
    spark = LifeSpark(pos, atlas)
    
    assert spark.collected == False
    spark.collected = True
    assert spark.collected == True

def test_game_reset():
    # Only patch things that might have side effects like window creation
    with patch('pykraken.init'), \
         patch('pykraken.window.create'), \
         patch('pykraken.Camera'):
        
        game = Game()
        game.essence = 50
        game.won = True
        
        game.reset()
        
        assert game.essence == 100.0
        assert game.won == False
        assert len(game.platforms) == 0

def test_integration_player_movement():
    with patch('pykraken.init'), \
         patch('pykraken.window.create'), \
         patch('pykraken.Camera'):
        
        game = Game()
        game.player.is_on_floor = True
        
        # Simulate pressing 'D' (Move Right)
        with patch('pykraken.key.is_pressed', side_effect=lambda k: k == kn.K_d):
            game.tick(dt=0.1)
            assert game.player.velocity.x > 0
            game.player.move_and_slide.assert_called()

def test_integration_bloom_mechanic():
    with patch('pykraken.init'), \
         patch('pykraken.window.create'), \
         patch('pykraken.Camera') as mock_camera_cls:
        
        mock_camera = MagicMock()
        mock_camera.screen_to_world.return_value = FakeVec2(300, 400)
        mock_camera_cls.return_value = mock_camera
        
        game = Game()
        game.player.pos = FakeVec2(200, 400)
        initial_essence = game.essence
        
        with patch('pykraken.mouse.is_just_pressed', side_effect=lambda m: m == kn.M_LEFT), \
             patch('pykraken.mouse.get_pos', return_value=FakeVec2(100, 100)):
            
            game.tick(dt=0.1)
            
            assert len(game.platforms) == 1
            assert game.essence < initial_essence

def test_integration_player_movement_left():
    with patch('pykraken.init'), patch('pykraken.window.create'), patch('pykraken.Camera'):
        game = Game()
        game.player.is_on_floor = True
        # Simulate pressing 'A' (Move Left)
        with patch('pykraken.key.is_pressed', side_effect=lambda k: k == kn.K_a):
            game.tick(dt=0.1)
            assert game.player.velocity.x < 0

def test_friction_deceleration():
    with patch('pykraken.init'), patch('pykraken.window.create'), patch('pykraken.Camera'):
        game = Game()
        game.player.velocity.x = 200.0 # Moving right
        # No keys pressed
        with patch('pykraken.key.is_pressed', return_value=False):
            # Use a very small dt so it doesn't stop completely
            game.tick(dt=0.01)
            # Velocity should have decreased due to friction
            assert game.player.velocity.x < 200.0
            assert game.player.velocity.x > 0

def test_gravity_accumulation():
    with patch('pykraken.init'), patch('pykraken.window.create'), patch('pykraken.Camera'):
        game = Game()
        game.player.is_on_floor = False
        game.player.velocity.y = 0.0
        
        # Multiple ticks
        for _ in range(3):
            game.tick(dt=0.1)
        
        # Velocity.y should be positive (falling)
        assert game.player.velocity.y > 0

def test_win_condition_trigger():
    from main import GOAL_X
    with patch('pykraken.init'), patch('pykraken.window.create'), patch('pykraken.Camera'):
        game = Game()
        # Move player to goal
        game.player.pos = FakeVec2(GOAL_X + 10, 500)
        game.update(0.1)
        assert game.won == True

def test_game_over_trigger():
    from main import HEIGHT
    with patch('pykraken.init'), patch('pykraken.window.create'), patch('pykraken.Camera'):
        game = Game()
        # Move player below the world
        game.player.pos = FakeVec2(500, HEIGHT + 1000)
        game.update(0.1)
        assert game.game_over == True

def test_e2e_gameplay_sequence():
    # Simulate: Move right -> Collect Spark -> Create Platform
    with patch('pykraken.init'), \
         patch('pykraken.window.create'), \
         patch('pykraken.Camera'):
        
        game = Game()
        # Place a spark ahead
        game.sparks = [LifeSpark(FakeVec2(300, 500), MagicMock())]
        game.player.pos = FakeVec2(200, 500)
        game.player.is_on_floor = True
        game.essence = 50.0 # Start with less than max
        
        initial_essence = game.essence
        
        # 1. Move Right
        with patch('pykraken.key.is_pressed', side_effect=lambda k: k == kn.K_d):
            # Manually update position since we mocked the engine
            game.tick(dt=0.1)
            game.player.pos.x += 100 # Simulate engine movement
            
        # 2. Update to collect spark
        game.update(0.1)
        assert game.sparks[0].collected == True
        assert game.essence > initial_essence
        
        # 3. Create Platform
        with patch('pykraken.mouse.is_just_pressed', return_value=True), \
             patch('pykraken.mouse.get_pos', return_value=FakeVec2(100, 100)):
            game.tick(dt=0.1)
            assert len(game.platforms) == 1
