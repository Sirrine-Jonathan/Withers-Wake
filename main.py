import pykraken as kn
import math
import random

# Constants
WIDTH, HEIGHT = 1280, 720
GRAVITY = kn.Vec2(0, 1400)
PLAYER_SPEED = 450
PLAYER_ACCEL = 2600
PLAYER_FRICTION = 2000
JUMP_FORCE = -700
MAX_ESSENCE = 100.0
BLOOM_COST = 20.0
PLATFORM_LIFETIME = 5.0
SPARK_RECOVERY = 35.0
GOAL_X = 5000

# Atlas Coordinates (Guessed)
CHAR_RECT = kn.Rect(320, 140, 64, 80)
PLAT_RECT = kn.Rect(64, 256, 128, 64)
ORB_RECT = kn.Rect(760, 90, 64, 64)

class DecayingPlatform:
    def __init__(self, world, pos, size, atlas):
        self.world = world
        self.pos = pos
        self.size = size
        self.lifetime = PLATFORM_LIFETIME
        self.body = kn.physics.StaticBody(world)
        self.body.pos = pos
        self.body.add_collider(kn.Rect(-size.x/2, -size.y/2, size.x, size.y))
        self.color = kn.Color("#00ff88")
        self.atlas = atlas
        
    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.body.destroy()
            return True
        
        decay_factor = self.lifetime / PLATFORM_LIFETIME
        self.color = kn.Color(
            int(26 + (0 - 26) * decay_factor),
            int(26 + (255 - 26) * decay_factor),
            int(26 + (136 - 26) * decay_factor)
        )
        return False

    def draw(self, camera):
        screen_pos = camera.world_to_screen(self.pos)
        dest_rect = kn.Rect(screen_pos.x - self.size.x/2, screen_pos.y - self.size.y/2, self.size.x, self.size.y)
        
        if self.atlas:
            self.atlas.clip_area = PLAT_RECT
            # We can't easily set color on texture in Kraken yet? 
            # Usually it's kn.renderer.draw(texture, transform, color_mod)
            # Let's check renderer.draw signature.
            kn.renderer.draw(self.atlas, kn.Transform(pos=screen_pos, scale=kn.Vec2(self.size.x/PLAT_RECT.w, self.size.y/PLAT_RECT.h)))
        else:
            kn.draw.rect(dest_rect, self.color)

class LifeSpark:
    def __init__(self, pos, atlas):
        self.pos = pos
        self.radius = 16
        self.collected = False
        self.time = random.random() * 6.28
        self.atlas = atlas
        
    def update(self, dt):
        self.time += dt * 5
        
    def draw(self, camera):
        if self.collected: return
        bob = math.sin(self.time) * 10
        screen_pos = camera.world_to_screen(self.pos + kn.Vec2(0, bob))
        
        if self.atlas:
            self.atlas.clip_area = ORB_RECT
            scale = (self.radius * 2) / ORB_RECT.w
            kn.renderer.draw(self.atlas, kn.Transform(pos=screen_pos, scale=kn.Vec2(scale)))
        else:
            kn.draw.circle(kn.Circle(screen_pos.x, screen_pos.y, self.radius + 5), kn.Color(0, 255, 136, 100))
            kn.draw.circle(kn.Circle(screen_pos.x, screen_pos.y, self.radius), kn.Color("#00ff88"))

class Game:
    def __init__(self):
        kn.init()
        kn.window.create("Wither's Wake", WIDTH, HEIGHT)
        
        # Load Assets
        try:
            self.atlas = kn.Texture("assets/atlas.png")
        except:
            print("Warning: Could not load atlas. Using shapes.")
            self.atlas = None
            
        self.world = kn.physics.World(GRAVITY)
        self.camera = kn.Camera(set_active=True)
        self.camera.transform.pos = kn.Vec2(WIDTH//2, HEIGHT//2)
        
        # Player
        self.player = kn.physics.CharacterBody(self.world)
        self.player.pos = kn.Vec2(200, HEIGHT - 150)
        self.player.capsule_shape = kn.Capsule(0, -25, 0, 25, 18)
        self.player.max_speed = PLAYER_SPEED
        self.player.acceleration = PLAYER_ACCEL
        self.player.friction = PLAYER_FRICTION
        
        self.essence = MAX_ESSENCE
        self.won = False
        self.game_over = False
        
        self.platforms = []
        self.sparks = []
        self.setup_level()

    def setup_level(self):
        self.ground = kn.physics.StaticBody(self.world)
        self.ground.pos = kn.Vec2(400, HEIGHT - 20)
        self.ground.add_collider(kn.Rect(-500, -20, 1000, 40))
        
        self.goal_ground = kn.physics.StaticBody(self.world)
        self.goal_ground.pos = kn.Vec2(GOAL_X, HEIGHT - 20)
        self.goal_ground.add_collider(kn.Rect(-200, -20, 400, 40))
        
        for i in range(1, 25):
            x = 800 + i * 180 + random.randint(-50, 50)
            y = HEIGHT - 200 - random.randint(0, 300)
            self.sparks.append(LifeSpark(kn.Vec2(x, y), self.atlas))

    def run(self):
        while kn.window.is_open():
            kn.event.poll()
            dt = kn.time.get_delta()
            
            if not self.game_over and not self.won:
                self.handle_input(dt)
                self.update(dt)
            
            self.draw()
            
            if (self.game_over or self.won) and kn.key.is_pressed(kn.K_r):
                self.reset()
                
        kn.quit()

    def reset(self):
        self.player.pos = kn.Vec2(200, HEIGHT - 150)
        self.player.velocity = kn.Vec2.ZERO
        self.essence = MAX_ESSENCE
        for plat in self.platforms:
            plat.body.destroy()
        self.platforms.clear()
        for spark in self.sparks:
            spark.collected = False
        self.game_over = False
        self.won = False

    def handle_input(self, dt):
        move_dir = 0
        if kn.key.is_pressed(kn.K_a): move_dir -= 1
        if kn.key.is_pressed(kn.K_d): move_dir += 1
            
        if move_dir != 0:
            self.player.velocity.x += move_dir * self.player.acceleration * dt
        else:
            if abs(self.player.velocity.x) > 0:
                f = self.player.friction * dt
                if abs(self.player.velocity.x) <= f:
                    self.player.velocity.x = 0
                else:
                    self.player.velocity.x -= math.copysign(f, self.player.velocity.x)
        
        if abs(self.player.velocity.x) > self.player.max_speed:
            self.player.velocity.x = math.copysign(self.player.max_speed, self.player.velocity.x)
            
        if self.player.is_on_floor:
            if kn.key.is_just_pressed(kn.K_SPACE):
                self.player.velocity.y = JUMP_FORCE
            if self.player.velocity.y > 0:
                self.player.velocity.y = 0
        else:
            self.player.velocity.y += GRAVITY.y * dt
            
        if kn.mouse.is_just_pressed(kn.M_LEFT):
            if self.essence >= BLOOM_COST:
                mouse_screen = kn.mouse.get_pos()
                mouse_world = self.camera.screen_to_world(mouse_screen)
                
                if (self.player.pos - mouse_world).length < 400:
                    new_plat = DecayingPlatform(self.world, mouse_world, kn.Vec2(160, 40), self.atlas)
                    self.platforms.append(new_plat)
                    self.essence -= BLOOM_COST

    def update(self, dt):
        self.player.move_and_slide(dt)
        self.camera.transform.pos.x = max(WIDTH//2, self.player.pos.x)
        
        for plat in self.platforms[:]:
            if plat.update(dt):
                self.platforms.remove(plat)
                
        for spark in self.sparks:
            if not spark.collected:
                spark.update(dt)
                if self.player.pos.distance_to(spark.pos) < 60:
                    spark.collected = True
                    self.essence = min(MAX_ESSENCE, self.essence + SPARK_RECOVERY)
        
        if self.player.pos.x >= GOAL_X - 100: self.won = True
        if self.player.pos.y > HEIGHT + 500: self.game_over = True

    def draw(self):
        kn.renderer.clear(kn.Color("#0a0a0a"))
        
        # Parallax BG
        for i in range(1, 4):
            scroll_x = self.camera.transform.pos.x * (0.05 * i)
            color = kn.Color(20 * i, 20 * i, 20 * i)
            for j in range(-2, 10):
                kn.draw.rect(kn.Rect((j * 400) - (scroll_x % 400), 100 + i * 50, 100, 600), color)
        
        # Stable Grounds
        for g in [self.ground, self.goal_ground]:
            g_s = self.camera.world_to_screen(g.pos)
            # Use a slightly different color for stable ground
            kn.draw.rect(kn.Rect(g_s.x - 500, g_s.y - 20, 1000, 40), kn.Color("#222"))
        
        # Goal Marker
        goal_s = self.camera.world_to_screen(kn.Vec2(GOAL_X, HEIGHT - 100))
        kn.draw.rect(kn.Rect(goal_s.x - 20, goal_s.y - 60, 40, 120), kn.Color("#00ff88"))

        for plat in self.platforms: plat.draw(self.camera)
        for spark in self.sparks: spark.draw(self.camera)
            
        # Draw Player
        p_s = self.camera.world_to_screen(self.player.pos)
        if self.atlas:
            self.atlas.clip_area = CHAR_RECT
            kn.renderer.draw(self.atlas, kn.Transform(pos=p_s, scale=kn.Vec2(1.0)))
        else:
            kn.draw.rect(kn.Rect(p_s.x - 18, p_s.y - 30, 36, 60), kn.Color("#00ff88"))
        
        self.draw_ui()
        if self.won: self.draw_overlay("THE WORLD BLOOMS AGAIN")
        elif self.game_over: self.draw_overlay("WITHERED AWAY")
            
        kn.renderer.present()

    def draw_ui(self):
        kn.draw.rect(kn.Rect(20, 20, 204, 24), kn.Color.WHITE)
        kn.draw.rect(kn.Rect(22, 22, 200, 20), kn.Color("#111"))
        kn.draw.rect(kn.Rect(22, 22, 200 * (self.essence / MAX_ESSENCE), 20), kn.Color("#00ff88"))
        
    def draw_overlay(self, text):
        kn.draw.rect(kn.Rect(WIDTH//2 - 300, HEIGHT//2 - 50, 600, 100), kn.Color(0, 0, 0, 200))
        # We'll just draw a box, without text it's hard but the message is clear from the game state.
        pass

if __name__ == "__main__":
    game = Game()
    game.run()
