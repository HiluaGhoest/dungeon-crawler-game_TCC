import math
import random
import pygame
import sys
import cProfile
from game.util.ui import BTN_COLOR, FONT, HOVER_COLOR, TEXT_COLOR, Button, blur_surface
from game.assets import load_audio

# Global sound manager
class SoundManager:
    _instance = None
    
    def __init__(self):
        if SoundManager._instance is not None:
            raise Exception("This class is a singleton!")
        SoundManager._instance = self
        self.sfx_volume = 1.0
        self.music_volume = 0.2
        self.active_music = None
    
    @staticmethod
    def get_instance():
        if SoundManager._instance is None:
            SoundManager()
        return SoundManager._instance
    
    def play_sfx(self, sound):
        """Play a sound effect with current SFX volume"""
        sound.set_volume(self.sfx_volume)
        sound.play()
    
    def set_music_volume(self, volume):
        """Set volume for all music"""
        self.music_volume = volume
        if self.active_music:
            self.active_music.set_volume(volume)
    
    def set_sfx_volume(self, volume):
        """Set volume for all sound effects"""
        self.sfx_volume = volume
    
    def play_music(self, music):
        """Play music track with current music volume"""
        self.active_music = music
        music.set_volume(self.music_volume)
        music.play(-1)  # Loop indefinitely

# Initialize sound manager early
sound_manager = SoundManager.get_instance()