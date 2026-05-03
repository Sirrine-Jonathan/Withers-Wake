import pykraken as kn
import math
import random

# Constants
WIDTH, HEIGHT = 1280, 720
GRAVITY = kn.Vec2(0, 1500)
PLAYER_SPEED = 450
PLAYER_ACCEL = 2600
PLAYER_FRICTION = 2000
JUMP_FORCE = -750
MAX_ESSENCE = 100.0
BLOOM_COST = 20.0
PLATFORM_LIFETIME = 5.0
SPARK_RECOVERY = 35.0
GOAL_X = 5000

# Atlas Coordinates (Verified via script)
CHAR_RECT = kn.Rect(591, 87, 81, 157)
PLAT_RECT = kn.Rect(544, 597, 416, 427)
ORB_RECT = kn.Rect(768, 86, 167, 163)

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
        # When camera is active, we draw in World Space
        if self.atlas:
            self.atlas.clip_area = PLAT_RECT
            scale = kn.Vec2(self.size.x/PLAT_RECT.w, self.size.y/PLAT_RECT.h)
            kn.renderer.draw(self.atlas, kn.Transform(pos=self.pos, scale=scale))
        else:
            kn.draw.rect(kn.Rect(self.pos.x - self.size.x/2, self.pos.y - self.size.y/2, self.size.x, self.size.y), self.color)

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
        world_pos = self.pos + kn.Vec2(0, bob)
        
        if self.atlas:
            self.atlas.clip_area = ORB_RECT
            scale = (self.radius * 2) / ORB_RECT.w
            kn.renderer.draw(self.atlas, kn.Transform(pos=world_pos, scale=kn.Vec2(scale)))
        else:
            # We don't have a world-space circle draw in kn.draw that doesn't use camera?
            # Actually kn.draw uses world space when camera is active.
            kn.draw.circle(kn.Circle(world_pos.x, world_pos.y, self.radius), kn.Color("#00ff88"))

class Game:
    def __init__(self):
        kn.init()
        kn.window.create("Wither's Wake", WIDTH, HEIGHT)
        
        # Assets
        self.atlas = kn.Texture("assets/atlas.png")
            
        self.world = kn.physics.World(GRAVITY)
        self.camera = kn.Camera(set_active=True)
        self.camera.transform.pos = kn.Vec2(WIDTH//2, HEIGHT//2)
        
        # Player
        self.player = kn.physics.CharacterBody(self.world)
        self.player.pos = kn.Vec2(200, HEIGHT - 150)
        # Tighter capsule for better platforming
        self.player.capsule_shape = kn.Capsule(0, -20, 0, 20, 16)
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
        # Stable Start
        self.ground = kn.physics.StaticBody(self.world)
        self.ground.pos = kn.Vec2(400, HEIGHT - 20)
        self.ground.add_collider(kn.Rect(-500, -20, 1000, 40))
        
        # Stable Goal
        self.goal_ground = kn.physics.StaticBody(self.world)
        self.goal_ground.pos = kn.Vec2(GOAL_X, HEIGHT - 20)
        self.goal_ground.add_collider(kn.Rect(-200, -20, 400, 40))
        
        for i in range(1, 25):
            x = 800 + i * 180 + random.randint(-50, 50)
            y = HEIGHT - 200 - random.randint(0, 300)
            self.sparks.append(LifeSpark(kn.Vec2(x, y), self.atlas))

    def run(self):
        while kn.window.is_open():
            self.tick()
        kn.quit()

    def tick(self, dt=None):
        kn.event.poll()
        if dt is None:
            dt = kn.time.get_delta()
        
        if not self.game_over and not self.won:
            self.handle_input(dt)
            self.update(dt)
        
        self.draw()
        
        if (self.game_over or self.won) and kn.key.is_pressed(kn.K_r):
            self.reset()

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
        # Horizontal
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
            
        # Vertical / Jump
        self.player.velocity.y += GRAVITY.y * dt
        
        if self.player.is_on_floor:
            # Landing / Grounded
            if self.player.velocity.y > 0:
                self.player.velocity.y = 0
            
            if kn.key.is_just_pressed(kn.K_SPACE):
                self.player.velocity.y = JUMP_FORCE
        
        # Bloom Power
        if kn.mouse.is_just_pressed(kn.M_LEFT):
            if self.essence >= BLOOM_COST:
                mouse_screen = kn.mouse.get_pos()
                mouse_world = self.camera.screen_to_world(mouse_screen)
                
                if self.player.pos.distance_to(mouse_world) < 400:
                    new_plat = DecayingPlatform(self.world, mouse_world, kn.Vec2(160, 40), self.atlas)
                    self.platforms.append(new_plat)
                    self.essence -= BLOOM_COST

    def update(self, dt):
        self.player.move_and_slide(dt)
        # Smooth camera following
        target_x = max(WIDTH//2, self.player.pos.x)
        self.camera.transform.pos.x = target_x
        
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
        
        # 1. Parallax BG (Screen Space)
        self.camera.unset()
        for i in range(1, 4):
            scroll_x = self.camera.transform.pos.x * (0.05 * i)
            color = kn.Color(20 * i, 20 * i, 20 * i)
            for j in range(-2, 10):
                kn.draw.rect(kn.Rect((j * 400) - (scroll_x % 400), 100 + i * 50, 100, 600), color)
        
        # 2. World Objects (World Space)
        self.camera.set()
        
        # Stable Grounds
        for g in [self.ground, self.goal_ground]:
            kn.draw.rect(kn.Rect(g.pos.x - 500, g.pos.y - 20, 1000, 40), kn.Color("#222"))
        
        # Goal Marker
        kn.draw.rect(kn.Rect(GOAL_X - 20, HEIGHT - 160, 40, 120), kn.Color("#00ff88"))

        for plat in self.platforms: plat.draw(self.camera)
        for spark in self.sparks: spark.draw(self.camera)
            
        # Draw Player
        if self.atlas:
            self.atlas.clip_area = CHAR_RECT
            # Draw at world position!
            kn.renderer.draw(self.atlas, kn.Transform(pos=self.player.pos))
        else:
            kn.draw.rect(kn.Rect(self.player.pos.x - 18, self.player.pos.y - 30, 36, 60), kn.Color("#00ff88"))
        
        # 3. UI (Screen Space)
        self.camera.unset()
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

if __name__ == "__main__":
    game = Game()
    game.run()
