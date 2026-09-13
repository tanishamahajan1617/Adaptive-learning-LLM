from manim import *

class GeneratedScene(Scene):
    def construct(self):
        objects = {}
        elapsed = 0.0

        # Beat 1
        title = Text("Tree Structure", font_size=48).move_to(np.array([0, 3.5, 0]))
        objects["title_text"] = title
        root_circle = Circle(radius=0.5, color=BLACK).set_fill(WHITE, opacity=1)
        root_label = Text("Root (Level 1)", font_size=24).next_to(root_circle, DOWN)
        root = VGroup(root_circle, root_label).move_to(np.array([0, 2.0, 0]))
        objects["root"] = root

        self.play(Create(objects["title_text"]), Create(objects["root"]))
        self.wait(2)