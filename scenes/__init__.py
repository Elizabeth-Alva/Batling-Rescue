"""Escenas del juego."""


class Scene:
    def __init__(self, game):
        self.game = game

    def enter(self):
        pass

    def handle(self, ev):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        pass
