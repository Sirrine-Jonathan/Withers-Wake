import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Mock pykraken to allow testing without a real engine instance/window
sys.modules['pykraken'] = MagicMock()
import pykraken as kn

# Import the classes we want to test
# We need to re-import or use a trick because we mocked kn
from main import DecayingPlatform, LifeSpark, Game

def test_decaying_platform_lifecycle():
    world = MagicMock()
    pos = kn.Vec2(100, 100)
    size = kn.Vec2(50, 50)
    atlas = MagicMock()
    
    # Mock StaticBody and its return
    mock_body = MagicMock()
    kn.physics.StaticBody.return_value = mock_body
    
    plat = DecayingPlatform(world, pos, size, atlas)
    
    # Initial state
    assert plat.lifetime == 5.0
    assert not plat.update(1.0) # Should not be removed yet
    assert plat.lifetime == 4.0
    
    # Reach end of life
    assert plat.update(4.0) # Should return True (remove)
    assert plat.lifetime <= 0
    mock_body.destroy.assert_called_once()

def test_life_spark_collection():
    atlas = MagicMock()
    pos = kn.Vec2(200, 200)
    spark = LifeSpark(pos, atlas)
    
    assert spark.collected == False
    spark.collected = True
    assert spark.collected == True

def test_game_reset():
    # Mock the whole kn module for Game init
    with patch('pykraken.init'), \
         patch('pykraken.window.create'), \
         patch('pykraken.physics.World'), \
         patch('pykraken.Camera'), \
         patch('pykraken.physics.CharacterBody'), \
         patch('pykraken.physics.StaticBody'):
        
        game = Game()
        game.essence = 50
        game.won = True
        game.platforms.append(MagicMock())
        
        game.reset()
        
        assert game.essence == 100.0
        assert game.won == False
        assert len(game.platforms) == 0
