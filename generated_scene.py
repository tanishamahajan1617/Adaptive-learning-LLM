from manim import *

class GeneratedScene(Scene):
    def construct(self):
        # ==================== Scene 1: Node Structure ====================
        # Node rectangle with label
        node_rect = RoundedRectangle(width=2, height=1, color=WHITE)
        node_rect.move_to(ORIGIN)
        node_label = Text("Node")
        node_label.move_to(node_rect.get_center())
        node = VGroup(node_rect, node_label)

        # Info text above the node
        info = Text("info: 8")
        info.move_to(node_rect.get_top() + UP * 0.5)

        # Next pointer arrow to the right
        next_arrow = Arrow(start=node_rect.get_right(), end=node_rect.get_right() + RIGHT * 1.5, buff=0)
        next_label = Text("next")
        next_label.scale(0.5)
        next_label.next_to(next_arrow, UP)

        # Beat 1: display node, info, and next pointer
        self.play(Create(node))
        self.play(Write(info))
        self.play(Create(next_arrow), Write(next_label))
        self.wait(7.849)

        # Beat 2: highlight the next pointer
        self.play(Indicate(next_arrow))
        self.wait(7.848)

        # Prev pointer arrow to the left (added later)
        prev_arrow = Arrow(start=node_rect.get_left(), end=node_rect.get_left() + LEFT * 1.5, buff=0)
        prev_label = Text("prev")
        prev_label.scale(0.5)
        prev_label.next_to(prev_arrow, UP)

        # Beat 3: add the prev pointer
        self.play(Create(prev_arrow), Write(prev_label))
        self.wait(8.087)

        # Clear scene before next part
        self.clear()
        self.wait(1)

        # ==================== Scene 2: Doubly Linked List Operations ====================
        # Old tail node (value 8)
        old_rect = RoundedRectangle(width=2, height=1, color=WHITE)
        old_rect.move_to([-2, 0, 0])
        old_label = Text("Node (8)")
        old_label.move_to(old_rect.get_center())
        old_node = VGroup(old_rect, old_label)

        # Tail pointer above old node
        tail_arrow = Arrow(start=old_rect.get_top() + UP * 0.5, end=old_rect.get_top(), buff=0)
        tail_label = Text("tail")
        tail_label.scale(0.5)
        tail_label.next_to(tail_arrow, UP)

        # New tail node (value 10)
        new_rect = RoundedRectangle(width=2, height=1, color=WHITE)
        new_rect.move_to([2, 0, 0])
        new_label = Text("Node (10)")
        new_label.move_to(new_rect.get_center())
        new_node = VGroup(new_rect, new_label)

        # Prev connection from new node to old node
        prev_conn = Arrow(start=new_rect.get_left(), end=old_rect.get_right(), buff=0)
        prev_conn_label = Text("prev")
        prev_conn_label.scale(0.5)
        prev_conn_label.next_to(prev_conn, UP)

        # Beat 1: create old node, tail pointer, new node, and prev connection
        self.play(Create(old_node))
        self.play(Create(tail_arrow), Write(tail_label))
        self.play(Create(new_node))
        self.play(Create(prev_conn), Write(prev_conn_label))
        self.wait(9.526)

        # Next connection from old node to new node
        next_conn = Arrow(start=old_rect.get_right(), end=new_rect.get_left(), buff=0)
        next_conn_label = Text("next")
        next_conn_label.scale(0.5)
        next_conn_label.next_to(next_conn, UP)

        # Beat 2: move tail pointer to new node and create next connection
        self.play(
            tail_arrow.animate.move_to(new_rect.get_top() + UP * 0.5),
            tail_label.animate.move_to(tail_arrow.get_top() + UP * 0.2)
        )
        self.play(Create(next_conn), Write(next_conn_label))
        self.wait(9.525)

        # Complexity label
        complexity = Text("Time Complexity: O(1)")
        complexity.move_to([0, -2.5, 0])

        # Beat 3: display complexity text
        self.play(Write(complexity))
        self.wait(6.351)

        # Beat 4: indicate the tail pointer
        self.play(Indicate(tail_arrow))
        self.wait(6.35)