import pygame
import math
import random
import time

# Global performance settings
PERFORMANCE_MODE = "balanced"  # "fast", "balanced", "quality"
_light_time = 0


LIGHT_MASK_CACHE = {}

def get_cached_light_mask(radius, performance_mode):
    key = (radius, performance_mode)
    if key not in LIGHT_MASK_CACHE:
        LIGHT_MASK_CACHE[key] = create_light_mask(radius)  # Grayscale base
    return LIGHT_MASK_CACHE[key]

def set_light_performance_mode(mode):
    global PERFORMANCE_MODE
    if mode in ["fast", "balanced", "quality"]:
        PERFORMANCE_MODE = mode
    else:
        print(f"Invalid performance mode: {mode}. Use 'fast', 'balanced', or 'quality'")

def get_light_performance_mode():
    return PERFORMANCE_MODE

def create_light_mask(radius):
    """Create a radial gradient light mask with soft edges"""
    size = radius * 2
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    
    # Quality settings
    steps = 30 if PERFORMANCE_MODE == "fast" else 40 if PERFORMANCE_MODE == "balanced" else 60
    
    for r in range(radius, 0, -max(1, radius//steps)):
        # More gradual falloff to reduce hot spot
        normalized_r = r / radius
        fade = 1.0 - (normalized_r ** 1.5)  # Use power of 1.5 for smoother transition
        
        # More conservative alpha to prevent over-brightness
        alpha = int(120 * (normalized_r ** 1.0))  # Reduced base alpha for smoother breathing
        
        c = (
            min(255, 255 * fade * 1),  # Lower intensity for dimmer core
            min(255, 255 * fade * 1),
            min(255, 255 * fade * 1),
            alpha
        )
        pygame.draw.circle(mask, c, (radius, radius), r)
    
    return mask

def calculate_shadow_polygon(light_pos, wall, light_radius):
    """Calculate shadow polygon for a wall segment"""
    # Convert wall to line segments
    segments = [
        ((wall.left, wall.top), (wall.right, wall.top)),    # Top
        ((wall.right, wall.top), (wall.right, wall.bottom)), # Right
        ((wall.right, wall.bottom), (wall.left, wall.bottom)), # Bottom
        ((wall.left, wall.bottom), (wall.left, wall.top))    # Left
    ]
    
    shadow_polygons = []
    lx, ly = light_pos
    
    for p1, p2 in segments:
        # Vector from light to points
        v1 = (p1[0] - lx, p1[1] - ly)
        v2 = (p2[0] - lx, p2[1] - ly)
        
        # Normalize and extend beyond light radius
        length1 = max(0.001, math.hypot(*v1))
        length2 = max(0.001, math.hypot(*v2))
        
        # Extended points (2x light radius to ensure coverage)
        ext1 = (lx + v1[0]/length1 * light_radius * 2, 
                ly + v1[1]/length1 * light_radius * 2)
        ext2 = (lx + v2[0]/length2 * light_radius * 2, 
                ly + v2[1]/length2 * light_radius * 2)
        
        shadow_polygons.append((p1, p2, ext2, ext1))
    
    return shadow_polygons

def render_volumetric_light(surface, px, py, radius=180, color=(255, 255, 180), breathing_intensity=0.15, 
                           flicker_intensity=0.08, wall_rects=None, performance_mode=None):
    global _light_time
    _light_time += 0.016  # ~60 FPS
    
    if performance_mode is None:
        performance_mode = PERFORMANCE_MODE
        
    # Breathing effect - affects intensity, not size
    breathing_offset = math.cos(_light_time * 1.2) * breathing_intensity  # Use cos for smoother start
    
    # Flicker effect - affects intensity
    flicker_base = math.sin(_light_time * 6.0) * 0.3 + 0.7  # Smooth base wave
    flicker_noise = (random.random() * 0.4 + 0.8)  # Less random variation
    flicker_offset = flicker_base * flicker_noise * flicker_intensity
    
    # Use a slightly larger radius for the surface to prevent black holes
    surface_radius = radius + 10  # Always 10 pixels larger than requested
    effective_radius = surface_radius  # Surface size stays constant
    
    # Calculate intensity multiplier instead of changing radius
    intensity_multiplier = 1.0 + breathing_offset + (flicker_offset * 0.3)
    intensity_multiplier = max(0.6, min(1.4, intensity_multiplier))  # Clamp between 60% and 140%
    
    # Apply intensity to color
    adjusted_color = (
        min(255, int(color[0] * intensity_multiplier)),
        min(255, int(color[1] * intensity_multiplier)),
        min(255, int(color[2] * intensity_multiplier))
    )
    
    # Create light surface with fixed size
    light_size = effective_radius * 2
    light_surface = pygame.Surface((light_size, light_size), pygame.SRCALPHA)
    rays_only_surface = None
    
    # ====== CACHED LIGHT MASK SECTION ======
    # Get cached base mask (grayscale)
    base_mask = get_cached_light_mask(effective_radius, performance_mode)
    
    # Create a tinted version of the mask
    tinted_mask = base_mask.copy()
    color_surf = pygame.Surface(tinted_mask.get_size(), pygame.SRCALPHA)
    color_surf.fill(adjusted_color)
    tinted_mask.blit(color_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    # ====== END CACHED SECTION ======
    
    # Draw the base light
    light_surface.blit(tinted_mask, (0, 0))
    
    # Add rays for volumetric effect (more subtle)
    if performance_mode != "fast":
        rays = 16 if performance_mode == "balanced" else 24  # Reduced ray count
        ray_surface = pygame.Surface((light_size, light_size), pygame.SRCALPHA)
        for i in range(rays):
            angle = 2 * math.pi * i / rays + random.uniform(-0.1, 0.1)
            length = effective_radius * (0.6 + 0.3 * random.random())
            end_x = effective_radius + length * math.cos(angle)
            end_y = effective_radius + length * math.sin(angle)
            alpha = int((15 if performance_mode == "balanced" else 25) * intensity_multiplier)
            ray_color = (
                int(adjusted_color[0] * 0.7),
                int(adjusted_color[1] * 0.7),
                int(adjusted_color[2] * 0.7),
                max(5, alpha)
            )
            pygame.draw.line(
                ray_surface,
                ray_color,
                (effective_radius, effective_radius),
                (end_x, end_y),
                1
            )
        # Save rays only surface for masking
        rays_only_surface = ray_surface.copy()
        # Use normal blending instead of additive for subtler effect
        light_surface.blit(ray_surface, (0, 0), special_flags=pygame.BLEND_ALPHA_SDL2)
    
    # Handle wall shadows with optimization for large numbers of walls
    if wall_rects:
        # Limit the number of walls processed for shadows to improve performance
        max_walls_for_shadows = 50 if performance_mode == "fast" else 100 if performance_mode == "balanced" else 200
        
        # Sort walls by distance from light and only process the closest ones
        if len(wall_rects) > max_walls_for_shadows:
            walls_with_distance = []
            for wall in wall_rects:
                # Calculate approximate distance from light to wall center (using squared distance to avoid sqrt)
                wall_center_x = wall.x + wall.width // 2
                wall_center_y = wall.y + wall.height // 2
                dist_sq = (wall_center_x - px) ** 2 + (wall_center_y - py) ** 2
                walls_with_distance.append((dist_sq, wall))
            
            # Sort by distance and take only the closest walls
            walls_with_distance.sort(key=lambda x: x[0])
            processed_walls = [wall for _, wall in walls_with_distance[:max_walls_for_shadows]]
        else:
            processed_walls = wall_rects
        
        shadow_surface = pygame.Surface((light_size, light_size), pygame.SRCALPHA)
        shadow_surface.fill((0, 0, 0, 0))
        
        for wall in processed_walls:
            if not wall.collidepoint(px, py):  # Only cast shadows if light isn't inside wall
                shadow_polys = calculate_shadow_polygon(
                    (px, py), 
                    wall, 
                    effective_radius
                )
                
                for poly in shadow_polys:
                    # Convert to light surface coordinates
                    local_poly = []
                    for point in poly:
                        local_poly.append((
                            point[0] - (px - effective_radius),
                            point[1] - (py - effective_radius)
                        ))
                    
                    pygame.draw.polygon(
                        shadow_surface, 
                        (0, 0, 0, 220),  # Semi-transparent black
                        local_poly
                    )
        
        # Apply shadows to light
        light_surface.blit(shadow_surface, (0, 0))
    
    # Draw light to main surface
    if surface is not None:
        surface.blit(
            light_surface, 
            (px - effective_radius, py - effective_radius),
            special_flags=pygame.BLEND_RGBA_ADD
        )
    # Optionally return rays_only_surface for masking
    return light_surface, rays_only_surface, effective_radius

# Predefined light types with optimized parameters
def create_torch_light(surface, px, py, radius=120, wall_rects=None):
    return render_volumetric_light(
        surface, px, py, radius, 
        color=(255, 180, 100),
        breathing_intensity=0.25,
        flicker_intensity=0.15,
        wall_rects=wall_rects,
        performance_mode=PERFORMANCE_MODE
    )

def create_magical_light(surface, px, py, radius=200, wall_rects=None):
    return render_volumetric_light(
        surface, px, py, radius,
        color=(150, 200, 255),
        breathing_intensity=0.3,
        flicker_intensity=0.05,
        wall_rects=wall_rects,
        performance_mode=PERFORMANCE_MODE
    )

def create_candle_light(surface, px, py, radius=80, wall_rects=None):
    return render_volumetric_light(
        surface, px, py, radius,
        color=(255, 220, 150),
        breathing_intensity=0.1,
        flicker_intensity=0.2,
        wall_rects=wall_rects,
        performance_mode=PERFORMANCE_MODE
    )

def create_campfire_light(surface, px, py, radius=250, wall_rects=None):
    return render_volumetric_light(
        surface, px, py, radius,
        color=(255, 160, 80),
        breathing_intensity=0.35,
        flicker_intensity=0.25,
        wall_rects=wall_rects,
        performance_mode=PERFORMANCE_MODE
    )

def create_cinematic_torch(surface, px, py, radius=150, wall_rects=None):
    return render_volumetric_light(
        surface, px, py, radius,
        color=(255, 180, 100),
        breathing_intensity=0.3,
        flicker_intensity=0.18,
        wall_rects=wall_rects,
        performance_mode="quality"
    )

def create_soft_player_light(surface, px, py, radius=180, wall_rects=None, return_light_surface=False, return_rays_surface=False):
    """Create a soft, ambient light suitable for the player. If return_light_surface is True, returns the light surface instead of drawing it."""
    if not return_light_surface and not return_rays_surface:
        return render_volumetric_light(
            surface, px, py, radius,
            color=(100, 100, 70),  # Dimmer, more transparent light
            breathing_intensity=0.05,  # Subtle breathing
            flicker_intensity=0.3,   # Reduced flicker
            wall_rects=wall_rects,
            performance_mode="balanced"
        )
    else:
        import pygame
        light_size = (radius + 10) * 2
        temp_surface = pygame.Surface((light_size, light_size), pygame.SRCALPHA)
        light_surface, rays_surface, effective_radius = render_volumetric_light(
            temp_surface, radius + 10, radius + 10, radius,
            color=(100, 100, 70),
            breathing_intensity=0.05,
            flicker_intensity=0.3,
            wall_rects=wall_rects,
            performance_mode="balanced"
        )
        if return_rays_surface:
            return rays_surface, (px - (radius + 10), py - (radius + 10))
        else:
            return light_surface, (px - (radius + 10), py - (radius + 10))

def create_stable_player_light(surface, px, py, radius=180, wall_rects=None):
    """Create a completely stable light for the player - no breathing or flicker"""
    return render_volumetric_light(
        surface, px, py, radius,
        color=(240, 240, 200),  # Softer, warmer white
        breathing_intensity=0.0,  # No breathing
        flicker_intensity=0.0,   # No flicker
        wall_rects=wall_rects,
        performance_mode="balanced"
    )