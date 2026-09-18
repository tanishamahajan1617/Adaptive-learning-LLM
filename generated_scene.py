from manim import *

class GeneratedScene(Scene):
    def construct(self):
        # ---------- Scene 1: Tree Structure ----------
        # Create root node A
        root_circle = Circle(radius=0.5, color=WHITE, fill_opacity=0.5).move_to([0, 3, 0])
        root_label = Text("Root (A)", font_size=24).move_to(root_circle.get_center())
        root_node = VGroup(root_circle, root_label)

        self.play(Create(root_circle, run_time=1.0), Write(root_label, run_time=1.0))
        self.wait(2.774)  # beat duration 3.774 - animation time

        # Create child nodes B and C
        b_circle = Circle(radius=0.5, color=WHITE, fill_opacity=0.5).move_to([-2, 1, 0])
        b_label = Text("B", font_size=24).move_to(b_circle.get_center())
        child_b = VGroup(b_circle, b_label)

        c_circle = Circle(radius=0.5, color=WHITE, fill_opacity=0.5).move_to([2, 1, 0])
        c_label = Text("C (Leaf)", font_size=24).move_to(c_circle.get_center())
        child_c = VGroup(c_circle, c_label)

        self.play(Create(b_circle, run_time=0.5), Write(b_label, run_time=0.5))
        self.play(Create(c_circle, run_time=0.5), Write(c_label, run_time=0.5))

        # Connect arcs A-B and A-C
        edge_ab = Line(start=root_circle.get_center(), end=b_circle.get_center(), color=GRAY)
        edge_ac = Line(start=root_circle.get_center(), end=c_circle.get_center(), color=GRAY)

        self.play(Create(edge_ab), Create(edge_ac))
        self.wait(3.774 - (0.5+0.5+0.5+0.5+1.0))  # remaining time of beat 2

        # Highlight root and write description
        self.play(Indicate(root_node, color=YELLOW))
        label_root = Text("Root: Top node (no parent)", font_size=24).move_to([0, 3.8, 0])
        self.play(Write(label_root, run_time=0.8))
        self.wait(3.774 - 0.8)  # remaining of beat 3

        # Add leaf node D under B
        d_circle = Circle(radius=0.5, color=WHITE, fill_opacity=0.5).move_to([-2, -1, 0])
        d_label = Text("D (Leaf)", font_size=24).move_to(d_circle.get_center())
        leaf_d = VGroup(d_circle, d_label)

        self.play(Create(d_circle, run_time=0.5), Write(d_label, run_time=0.5))

        # Connect B-D
        edge_bd = Line(start=b_circle.get_center(), end=d_circle.get_center(), color=GRAY)
        self.play(Create(edge_bd))

        # Highlight leaf nodes C and D in green
        self.play(Indicate(child_c, color=GREEN), Indicate(leaf_d, color=GREEN))

        # Write leaf description
        label_leaf = Text("Leaves: Terminal nodes (no children)", font_size=24).move_to([0, -2.2, 0])
        self.play(Write(label_leaf, run_time=0.8))
        self.wait(3.774 - 0.8)  # remaining of beat 4

        # Pause before next scene
        self.wait(1)
        self.clear()

        # ---------- Scene 2: Paths, Levels, and Height ----------
        # Create nodes A, B, C in a vertical line
        a_circle = Circle(radius=0.4, color=WHITE, fill_opacity=0.5).move_to([-1, 2, 0])
        a_label = Text("A (Root)", font_size=24).move_to(a_circle.get_center())
        node_a = VGroup(a_circle, a_label)

        b_circle = Circle(radius=0.4, color=WHITE, fill_opacity=0.5).move_to([-1, 0, 0])
        b_label = Text("B", font_size=24).move_to(b_circle.get_center())
        node_b = VGroup(b_circle, b_label)

        c_circle = Circle(radius=0.4, color=WHITE, fill_opacity=0.5).move_to([-1, -2, 0])
        c_label = Text("C", font_size=24).move_to(c_circle.get_center())
        node_c = VGroup(c_circle, c_label)

        self.play(Create(a_circle, run_time=0.4), Write(a_label, run_time=0.4))
        self.play(Create(b_circle, run_time=0.4), Write(b_label, run_time=0.4))
        self.play(Create(c_circle, run_time=0.4), Write(c_label, run_time=0.4))

        # Connect arcs A-B and B-C
        edge_ab2 = Line(start=a_circle.get_center(), end=b_circle.get_center(), color=GRAY)
        edge_bc2 = Line(start=b_circle.get_center(), end=c_circle.get_center(), color=GRAY)

        self.play(Create(edge_ab2), Create(edge_bc2))

        # Indicate node C (deepest node)
        self.play(Indicate(node_c, color=ORANGE))
        self.wait(4.738 - (0.4+0.4+0.4+1.0))  # remaining of beat 1

        # Write level texts
        level1_text = Text("Level 1 (Root)", font_size=24).move_to([2, 2, 0])
        level2_text = Text("Level 2 (1 arc + 1)", font_size=24).move_to([2, 0, 0])
        level3_text = Text("Level 3 (2 arcs + 1) -> Height = 3", font_size=24).move_to([2, -2, 0])

        self.play(Write(level1_text, run_time=0.5))
        self.play(Write(level2_text, run_time=0.5))
        self.play(Write(level3_text, run_time=0.5))
        self.wait(4.737 - 1.5)  # remaining of beat 2

        # Highlight Level 3 text to indicate height
        self.play(Indicate(level3_text, color=YELLOW))
        self.wait(4.061 - 1.0)  # remaining of beat 3

        # End of video
        self.wait(2)