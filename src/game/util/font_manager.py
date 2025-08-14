import pygame
import os

# Caminho para a pasta de fontes
FONT_DIR = os.path.join(os.path.dirname(__file__), 'fonts')

# Carregamento centralizado das fontes
pygame.font.init()

FONTS = {
    'cinzel_black': pygame.font.Font(os.path.join(FONT_DIR, 'CinzelDecorative-Black.ttf'), 32),
    'cinzel_bold': pygame.font.Font(os.path.join(FONT_DIR, 'CinzelDecorative-Bold.ttf'), 32),
    'cinzel_regular': pygame.font.Font(os.path.join(FONT_DIR, 'CinzelDecorative-Regular.ttf'), 32),
}

def get_font(name: str):
    """Retorna o objeto de fonte pelo nome."""
    return FONTS.get(name)
