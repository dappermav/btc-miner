import json
import math
import os
import random
import sys
import numpy as np
import pygame

# Initialize Pygame and Mixer for procedural audio
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=1)

# Base Design Dimensions (Used for scaling math)
BASE_WIDTH, WIDTH = 900, 900
BASE_HEIGHT, HEIGHT = 740, 740

# --- VULKAN-FIRST RENDERING WITH OPENGL FALLBACK ---
renderer_used = None
screen = None

try:
    print("Attempting to initialize Vulkan rendering backend...")
    os.environ['SDL_RENDER_DRIVER'] = 'vulkan'
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE | pygame.DOUBLEBUF)
    renderer_used = "Vulkan"
    print("Successfully initialized using Vulkan backend.")
except Exception as e:
    print(f"Vulkan initialization failed: {e}")
    print("Falling back to OpenGL backend...")
    try:
        os.environ['SDL_RENDER_DRIVER'] = 'opengl'
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE | pygame.DOUBLEBUF | pygame.OPENGL)
        renderer_used = "OpenGL"
        print("Successfully initialized using OpenGL fallback.")
    except Exception as opengl_error:
        print(f"OpenGL fallback failed: {opengl_error}. Defaulting to software rendering.")
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        renderer_used = "Software"

pygame.display.set_caption(f"Crypto Miner Extreme - [Renderer: {renderer_used}]")
clock = pygame.time.Clock()

# Colors (RGB)
BG_COLOR = (13, 17, 23)
PANEL_COLOR = (22, 27, 34)
BORDER_COLOR = (48, 54, 61)
TEXT_COLOR = (201, 209, 217)
ACCENT_ORANGE = (247, 147, 26)
ACCENT_GREEN = (46, 160, 67)
ACCENT_BLUE = (88, 166, 255)
ACCENT_GOLD = (255, 215, 0)
ACCENT_RED = (255, 69, 0)
WHITE = (255, 255, 255)

# Save File Path
SAVE_FILE = "savegame.json"

# Upgrades Definition
upgrades = [
    {"name": "USB ASIC Miner", "desc": "+3 H/s", "cost": 15.0, "base_cost": 15.0, "power": 3.0, "count": 0, "mult": 1.15},
    {"name": "GTX Gaming Rig", "desc": "+15 H/s", "cost": 85.0, "base_cost": 85.0, "power": 15.0, "count": 0, "mult": 1.17},
    {"name": "Server Rack", "desc": "+80 H/s", "cost": 450.0, "base_cost": 450.0, "power": 80.0, "count": 0, "mult": 1.20},
    {"name": "Quantum Core", "desc": "+400 H/s", "cost": 2200.0, "base_cost": 2200.0, "power": 400.0, "count": 0, "mult": 1.22},
    {"name": "Neural Mining Cluster", "desc": "+1,800 H/s", "cost": 12000.0, "base_cost": 12000.0, "power": 1800.0, "count": 0, "mult": 1.24},
    {"name": "Dyson Swarm Node", "desc": "+8,500 H/s", "cost": 65000.0, "base_cost": 65000.0, "power": 8500.0, "count": 0, "mult": 1.26},
    {"name": "Dark Matter Rig", "desc": "+40,000 H/s", "cost": 350000.0, "base_cost": 350000.0, "power": 40000.0, "count": 0, "mult": 1.28},
    {"name": "Singularity Engine", "desc": "+200,000 H/s", "cost": 2000000.0, "base_cost": 2000000.0, "power": 200000.0, "count": 0, "mult": 1.30},
]

# Game State Variables
btc = 0.0000
usd = 10.0
hash_rate = 2.0
block_progress = 0.0
block_target = 80.0
level = 1
blocks_mined = 0
blocks_needed_for_level = 4

btc_price = 45000.0
price_timer = 0

flash_timer = 0
shake_timer = 0
shake_intensity = 0

particles = []
floating_texts = []

# --- FONTS INITIALIZED ONCE (Eliminates Lag) ---
FONT_SM = pygame.font.SysFont("Segoe UI", 15)
FONT_MD = pygame.font.SysFont("Segoe UI", 18, bold=True)
FONT_LG = pygame.font.SysFont("Segoe UI", 24, bold=True)
FONT_TITLE = pygame.font.SysFont("Segoe UI", 32, bold=True)

# Pre-created flash surface for screen visual effects
flash_surface = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))
flash_surface.fill(WHITE)


def save_game():
    data = {
        "btc": btc, "usd": usd, "hash_rate": hash_rate,
        "block_progress": block_progress, "block_target": block_target,
        "level": level, "blocks_mined": blocks_mined,
        "blocks_needed_for_level": blocks_needed_for_level,
        "upgrades": [{"count": up["count"], "cost": up["cost"]} for up in upgrades],
    }
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving game: {e}")


def load_game():
    global btc, usd, hash_rate, block_progress, block_target, level, blocks_mined, blocks_needed_for_level
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                btc = data.get("btc", 0.0000)
                usd = data.get("usd", 10.0)
                hash_rate = data.get("hash_rate", 2.0)
                block_progress = data.get("block_progress", 0.0)
                block_target = data.get("block_target", 80.0)
                level = data.get("level", 1)
                blocks_mined = data.get("blocks_mined", 0)
                blocks_needed_for_level = data.get("blocks_needed_for_level", 4)

                saved_upgrades = data.get("upgrades", [])
                for i, saved_up in enumerate(saved_upgrades):
                    if i < len(upgrades):
                        upgrades[i]["count"] = saved_up.get("count", 0)
                        upgrades[i]["cost"] = saved_up.get("cost", upgrades[i]["base_cost"])
        except Exception as e:
            print(f"Error loading save file: {e}")

load_game()


def generate_sound(freq, duration, sound_type="sine"):
    sample_rate = 22050
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    if sound_type == "sine":
        wave = np.sin(2 * np.pi * freq * t)
    elif sound_type == "square":
        wave = np.sign(np.sin(2 * np.pi * freq * t))
    elif sound_type == "noise":
        wave = np.random.uniform(-1, 1, t.shape)
    envelope = np.linspace(1, 0, len(wave))
    wave = wave * envelope
    audio = (wave * 32767).astype(np.int16)
    return pygame.mixer.Sound(buffer=audio)


try:
    click_snd = generate_sound(440, 0.05, "sine")
    upgrade_snd = generate_sound(880, 0.1, "square")
    levelup_snd = generate_sound(587, 0.4, "sine")
    bomb_snd = generate_sound(120, 0.5, "noise")
    sell_snd = generate_sound(750, 0.08, "sine")
except Exception:
    click_snd = upgrade_snd = levelup_snd = bomb_snd = sell_snd = None


class Particle:
    def __init__(self, x, y, color, speed_mult=1.0):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(3, 12) * speed_mult
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.life = random.randint(20, 40)
        self.size = random.randint(4, 9)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2
        self.life -= 1

    def draw(self, surface, sx, sy):
        if self.life > 0:
            pygame.draw.circle(surface, self.color, (int(self.x * sx), int(self.y * sy)), max(1, int(self.size * sx)))


class FloatingText:
    def __init__(self, x, y, text, color, scale_up=False):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = 40
        self.scale_up = scale_up

    def update(self):
        self.y -= 2.2
        self.life -= 1

    def draw(self, surface, sx, sy):
        if self.life > 0:
            current_font = FONT_LG if self.scale_up else FONT_MD
            txt_surface = current_font.render(self.text, True, self.color)
            surface.blit(txt_surface, (int(self.x * sx), int(self.y * sy)))


def trigger_earthquake(intensity=30, flash=40):
    global shake_timer, shake_intensity, flash_timer
    shake_timer = 25
    shake_intensity = intensity
    flash_timer = flash
    if bomb_snd:
        bomb_snd.play()


def trigger_levelup_effects():
    global shake_timer, shake_intensity, flash_timer
    shake_timer = 20
    shake_intensity = 15
    flash_timer = 25
    if levelup_snd:
        levelup_snd.play()


# Main Game Loop
running = True
while running:
    dt = clock.tick(60) / 1000.0

    current_width, current_height = screen.get_size()
    sx = current_width / BASE_WIDTH
    sy = current_height / BASE_HEIGHT

    price_timer += dt
    if price_timer >= 4.0:
        price_timer = 0
        btc_price = max(10000.0, btc_price + random.uniform(-1500.0, 1500.0))

    mine_btn_rect = pygame.Rect(int(30 * sx), int(310 * sy), int(410 * sx), int(80 * sy))
    sell_btn_rect = pygame.Rect(int(30 * sx), int(405 * sy), int(410 * sx), int(55 * sy))

    raw_mouse_pos = pygame.mouse.get_pos()
    mouse_pos = (raw_mouse_pos[0] / sx, raw_mouse_pos[1] / sy)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_game()
            running = False

        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE | pygame.DOUBLEBUF)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if mine_btn_rect.collidepoint(raw_mouse_pos):
                    is_crit = random.random() < 0.01
                    if is_crit:
                        boost_val = 150.0
                        trigger_earthquake(intensity=30, flash=30)
                        for _ in range(30):
                            particles.append(Particle(mouse_pos[0], mouse_pos[1], random.choice([ACCENT_GOLD, ACCENT_RED, WHITE]), speed_mult=2.0))
                        floating_texts.append(FloatingText(mouse_pos[0] - 70, mouse_pos[1] - 40, "💣 CRITICAL BOMB! 💥", ACCENT_RED, scale_up=True))
                    else:
                        boost_val = 10.0
                        if click_snd:
                            click_snd.play()
                        for _ in range(5):
                            particles.append(Particle(mouse_pos[0], mouse_pos[1], ACCENT_ORANGE))
                    block_progress += boost_val

                elif sell_btn_rect.collidepoint(raw_mouse_pos):
                    if btc > 0.000001:
                        earned_usd = btc * btc_price
                        usd += earned_usd
                        btc = 0.0
                        if sell_snd:
                            sell_snd.play()
                        for _ in range(15):
                            particles.append(Particle(sell_btn_rect.centerx / sx, sell_btn_rect.centery / sy, ACCENT_GREEN))
                        floating_texts.append(FloatingText((sell_btn_rect.x + 30) / sx, (sell_btn_rect.y - 20) / sy, f"+${earned_usd:.2f} USD", ACCENT_GREEN, scale_up=True))
                        save_game()

                for i, up in enumerate(upgrades):
                    btn_rect = pygame.Rect(int(475 * sx), int((115 + (i * 74)) * sy), int(395 * sx), int(70 * sy))
                    if btn_rect.collidepoint(raw_mouse_pos):
                        if usd >= up["cost"]:
                            usd -= up["cost"]
                            up["count"] += 1
                            hash_rate += up["power"]
                            up["cost"] = up["base_cost"] * (up["mult"] ** up["count"])

                            if upgrade_snd:
                                upgrade_snd.play()
                            for _ in range(8):
                                particles.append(Particle(btn_rect.centerx / sx, btn_rect.centery / sy, ACCENT_BLUE))
                            floating_texts.append(FloatingText((btn_rect.x + 20) / sx, (btn_rect.y - 15) / sy, f"+{up['power']} H/s", ACCENT_BLUE))
                            save_game()

    if hash_rate > 0:
        block_progress += hash_rate * dt

    if block_progress >= block_target:
        block_progress = 0
        blocks_mined += 1
        reward = 0.0002 + (hash_rate * 0.000005)
        btc += reward

        floating_texts.append(FloatingText(BASE_WIDTH // 2 - 110, BASE_HEIGHT // 2 - 30, f"🎉 Block Mined! +{reward:.6f} BTC", ACCENT_GREEN))

        if blocks_mined >= blocks_needed_for_level:
            blocks_mined = 0
            level += 1
            blocks_needed_for_level = int(blocks_needed_for_level * 1.4)
            trigger_levelup_effects()

            for _ in range(30):
                particles.append(Particle(BASE_WIDTH // 2, BASE_HEIGHT // 2, ACCENT_GOLD, speed_mult=2.0))
            floating_texts.append(FloatingText(BASE_WIDTH // 2 - 130, BASE_HEIGHT // 2 - 90, f"🌟 LEVEL UP! (Lv. {level}) 🌟", ACCENT_GOLD, scale_up=True))
        save_game()

    if flash_timer > 0:
        flash_timer -= 1
    if shake_timer > 0:
        shake_timer -= 1

    for p in particles[:]:
        p.update()
        if p.life <= 0:
            particles.remove(p)

    for ft in floating_texts[:]:
        ft.update()
        if ft.life <= 0:
            floating_texts.remove(ft)

    shake_x = random.randint(-shake_intensity, shake_intensity) if shake_timer > 0 else 0
    shake_y = random.randint(-shake_intensity, shake_intensity) if shake_timer > 0 else 0

    screen.fill(BG_COLOR)

    # Title Header
    title_surf = FONT_TITLE.render(f"⚡ CRYPTO MINER (Lv. {level}) ⚡", True, ACCENT_ORANGE)
    screen.blit(title_surf, (current_width // 2 - title_surf.get_width() // 2 + shake_x, int(15 * sy) + shake_y))

    # FPS METER
    fps_val = int(clock.get_fps())
    fps_surf = FONT_SM.render(f"FPS: {fps_val}", True, ACCENT_GREEN)
    screen.blit(fps_surf, (current_width - int(80 * sx) + shake_x, int(15 * sy) + shake_y))

    # LEFT PANEL
    left_panel = pygame.Rect(int(15 * sx), int(75 * sy), int(440 * sx), int(645 * sy))
    pygame.draw.rect(screen, PANEL_COLOR, left_panel, border_radius=int(12 * sy))
    pygame.draw.rect(screen, BORDER_COLOR, left_panel, max(1, int(2 * sy)), border_radius=int(12 * sy))

    usd_surf = FONT_LG.render(f"USD: ${usd:,.2f}", True, ACCENT_GREEN)
    btc_surf = FONT_MD.render(f"BTC Wallet: {btc:.6f} BTC", True, ACCENT_ORANGE)
    market_surf = FONT_SM.render(f"Live Market: 1 BTC = ${btc_price:,.2f} USD", True, TEXT_COLOR)
    hash_surf = FONT_SM.render(f"Hash Rate: {hash_rate:.1f} H/s  |  Level: {blocks_mined}/{blocks_needed_for_level} Blocks", True, WHITE)

    screen.blit(usd_surf, (int(30 * sx) + shake_x, int(95 * sy) + shake_y))
    screen.blit(btc_surf, (int(30 * sx) + shake_x, int(130 * sy) + shake_y))
    screen.blit(market_surf, (int(30 * sx) + shake_x, int(158 * sy) + shake_y))
    screen.blit(hash_surf, (int(30 * sx) + shake_x, int(185 * sy) + shake_y))

    # Progress Bar
    bar_bg = pygame.Rect(int(30 * sx), int(225 * sy), int(410 * sx), int(24 * sy))
    pygame.draw.rect(screen, (33, 38, 45), bar_bg, border_radius=int(6 * sy))
    fill_width = min(bar_bg.width, (block_progress / block_target) * bar_bg.width)
    bar_fill = pygame.Rect(bar_bg.x, bar_bg.y, fill_width, bar_bg.height)
    pygame.draw.rect(screen, ACCENT_GREEN, bar_fill, border_radius=int(6 * sy))
    pygame.draw.rect(screen, BORDER_COLOR, bar_bg, max(1, int(2 * sy)), border_radius=int(6 * sy))

    prog_text = FONT_SM.render(f"Mining Block: {int(block_progress)}/{int(block_target)}", True, WHITE)
    screen.blit(prog_text, (bar_bg.centerx - prog_text.get_width() // 2 + shake_x, bar_bg.centery - prog_text.get_height() // 2 + shake_y))

    # Turbo Boost Button
    is_hover = mine_btn_rect.collidepoint(raw_mouse_pos)
    btn_color = (255, 184, 77) if is_hover else ACCENT_ORANGE
    pygame.draw.rect(screen, btn_color, mine_btn_rect, border_radius=int(10 * sy))
    btn_text = FONT_LG.render("🚀 TURBO BOOST", True, (13, 17, 23))
    screen.blit(btn_text, (mine_btn_rect.centerx - btn_text.get_width() // 2 + shake_x, mine_btn_rect.centery - btn_text.get_height() // 2 + shake_y))

    # Sell BTC Button
    sell_hover = sell_btn_rect.collidepoint(raw_mouse_pos)
    sell_color = (60, 190, 85) if sell_hover else ACCENT_GREEN
    pygame.draw.rect(screen, sell_color, sell_btn_rect, border_radius=int(10 * sy))
    sell_text = FONT_MD.render("💵 SELL ALL BTC FOR USD", True, (13, 17, 23))
    screen.blit(sell_text, (sell_btn_rect.centerx - sell_text.get_width() // 2 + shake_x, sell_btn_rect.centery - sell_text.get_height() // 2 + shake_y))

    tip_surf = FONT_SM.render("1% chance on Turbo Boost for an earthquake bomb!", True, (139, 148, 158))
    screen.blit(tip_surf, (int(30 * sx) + shake_x, int(475 * sy) + shake_y))

    # RIGHT PANEL (Upgrades Shop)
    right_panel = pygame.Rect(int(460 * sx), int(75 * sy), int(425 * sx), int(645 * sy))
    pygame.draw.rect(screen, PANEL_COLOR, right_panel, border_radius=int(12 * sy))
    pygame.draw.rect(screen, BORDER_COLOR, right_panel, max(1, int(2 * sy)), border_radius=int(12 * sy))

    store_title = FONT_MD.render("Hardware Store (Buy with USD)", True, TEXT_COLOR)
    screen.blit(store_title, (int(485 * sx) + shake_x, int(90 * sy) + shake_y))

    for i, up in enumerate(upgrades):
        btn_rect = pygame.Rect(int(475 * sx), int((115 + (i * 74)) * sy), int(395 * sx), int(70 * sy))
        can_afford = usd >= up["cost"]
        box_color = (33, 38, 45) if can_afford else (20, 24, 29)
        border_col = ACCENT_GREEN if can_afford else BORDER_COLOR

        pygame.draw.rect(screen, box_color, btn_rect, border_radius=int(8 * sy))
        pygame.draw.rect(screen, border_col, btn_rect, max(1, int(2 * sy)), border_radius=int(8 * sy))

        name_surf = FONT_SM.render(f"{up['name']} (x{up['count']})", True, WHITE if can_afford else (100, 100, 100))
        desc_surf = FONT_SM.render(f"{up['desc']}  |  Cost: ${up['cost']:,.2f}", True, ACCENT_GREEN if can_afford else (100, 100, 100))

        screen.blit(name_surf, (btn_rect.x + int(12 * sx) + shake_x, btn_rect.y + int(12 * sy) + shake_y))
        screen.blit(desc_surf, (btn_rect.x + int(12 * sx) + shake_x, btn_rect.y + int(38 * sy) + shake_y))

    for p in particles:
        p.draw(screen, sx, sy)
    for ft in floating_texts:
        ft.draw(screen, sx, sy)

    if flash_timer > 0:
        scaled_flash = pygame.transform.scale(flash_surface, (current_width, current_height))
        scaled_flash.set_alpha(min(255, flash_timer * 12))
        screen.blit(scaled_flash, (0, 0))

    pygame.display.flip()

pygame.quit()
sys.exit()