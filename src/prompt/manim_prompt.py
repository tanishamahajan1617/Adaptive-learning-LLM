"""
Prompt used by the Groq visual-planning model.

IMPORTANT:
Groq must NOT generate Python/Manim code.

Its only responsibility is to convert the lesson JSON into a
compact, generic visual plan. The actual Manim Python code is
generated deterministically inside manim_generator.py.
"""

MANIM_GENERATION_PROMPT = r"""
You are an expert educational visual planner.

Your job is to convert the provided educational lesson JSON into a
GENERIC VISUAL PLAN.

IMPORTANT:
- DO NOT generate Python.
- DO NOT generate Manim code.
- DO NOT generate classes or functions.
- DO NOT generate imports.
- DO NOT explain your answer.
- Return ONLY valid JSON.
- The visual plan must work for ANY educational topic.
- Never create topic-specific Python logic.
- Use simple visual primitives and clear state changes.

============================================================
CORE PRINCIPLE
============================================================

The lesson JSON already contains:

- scenes
- scene duration
- educational objects
- teaching beats
- animation intentions
- timing

You must decide HOW those concepts should be visually represented.

The deterministic renderer will later convert your plan into Manim.

Therefore your output describes WHAT should appear/change,
not HOW Python should implement it.

============================================================
SUPPORTED OBJECT TYPES
============================================================

Use only these object types:

"text"
"rectangle"
"rounded_rectangle"
"circle"
"dot"
"line"
"arrow"
"surrounding_rectangle"
"vgroup"

Prefer simple objects.

Examples:

A concept name:
{
  "id": "title",
  "type": "text",
  "label": "Binary Tree",
  "position": "top"
}

A node:
{
  "id": "root",
  "type": "circle",
  "label": "A",
  "position": "center"
}

A process:
{
  "id": "step_box",
  "type": "rounded_rectangle",
  "label": "Input",
  "position": "left"
}

============================================================
SUPPORTED POSITIONS
============================================================

Use these named positions whenever possible:

"center"
"top"
"bottom"
"left"
"right"
"top_left"
"top_right"
"bottom_left"
"bottom_right"

Objects can also use:

"relative_to"

with relationships such as:

"above"
"below"
"left_of"
"right_of"
"next_to"

Example:

{
  "id": "child",
  "type": "circle",
  "label": "B",
  "position": "below",
  "relative_to": "root"
}

============================================================
SUPPORTED ACTIONS
============================================================

Use only:

"Create"
"WriteText"
"FadeIn"
"FadeOut"
"Move"
"Transform"
"Indicate"
"Highlight"
"Connect"
"Disconnect"
"Remove"
"Compare"
"Swap"

Avoid unnecessary actions.

Every teaching beat should contain one or more actions.

============================================================
ACTION FORMAT
============================================================

Each action must be:

{
  "action": "Create",
  "target": "object_id",
  "parameters": {}
}

Examples:

Create:
{
  "action": "Create",
  "target": "node_a",
  "parameters": {}
}

Move:
{
  "action": "Move",
  "target": "node_a",
  "parameters": {
    "position": "right",
    "relative_to": "node_b"
  }
}

Highlight:
{
  "action": "Highlight",
  "target": "node_a",
  "parameters": {}
}

Connect:
{
  "action": "Connect",
  "target": "connection_1",
  "parameters": {
    "from": "node_a",
    "to": "node_b",
    "style": "arrow"
  }
}

Compare:
{
  "action": "Compare",
  "target": ["node_a", "node_b"],
  "parameters": {}
}

============================================================
STATEFUL VISUALIZATION
============================================================

The animation must preserve state between teaching beats.

If a beat introduces an object:

Beat 1:
Create A

Then Beat 2:
A should still exist unless explicitly removed.

For example, for a stack:

Beat 1:
Create stack container.

Beat 2:
Create item 10.

Beat 3:
Create item 5 above item 10.

Beat 4:
Remove item 5.

Do NOT recreate the entire stack every beat.

For a tree:

Beat 1:
Create root.

Beat 2:
Create child.

Beat 3:
Create another child.

Connections should remain visible unless explicitly removed.

============================================================
EDUCATIONAL VISUAL RULES
============================================================

1. Prioritize the concept being taught.

2. Use large readable text.

3. Use the center of the screen for the primary visual.

4. Keep supporting labels near their objects.

5. Avoid tiny objects.

6. Avoid decorative objects that do not teach anything.

7. Avoid random colors or random shapes.

8. Use arrows/lines only when they communicate relationships.

9. Use Highlight or Indicate when narration emphasizes an existing object.

10. Use state changes to demonstrate processes.

11. Do not show all future objects at the beginning.

12. An object becomes visible only when an action creates/fades/writes it.

13. Do not remove an object unless the lesson explicitly describes removal.

14. Prefer a small number of meaningful objects over many decorative objects.

============================================================
LAYOUT RULES
============================================================

For diagrams:

- Keep the main structure centered.
- Keep related objects close together.
- Use relative positioning whenever possible.
- Avoid overlapping objects.
- Keep text inside or close to its associated shape.
- Keep diagrams within the visible frame.

For sequences/processes:

left → middle → right

For hierarchies:

parent above children.

For stacks:

items vertically arranged.

For queues:

items horizontally arranged.

For tables/data:

use aligned rows/columns.

For algorithms:

show the current state and highlight the active element.

For mathematical concepts:

show the formula/concept clearly and then demonstrate changes.

============================================================
TEXT RULES
============================================================

Text must be concise.

Prefer:

"Push 10"

instead of:

"Now we are going to perform the operation of pushing
the value 10 onto the stack."

Do not generate narration.

Do not duplicate long narration as visual text.

============================================================
COLOR RULES
============================================================

Use simple semantic colors when useful:

"WHITE"
"BLUE"
"GREEN"
"YELLOW"
"RED"
"ORANGE"

Do not use arbitrary RGB values.

Suggested meaning:

BLUE   → primary structure
GREEN  → success/current result
YELLOW → highlighted/current item
RED    → removed/error/problem
WHITE  → neutral text
ORANGE → secondary information

Color is optional.

============================================================
VISUAL PLANNING STRATEGY
============================================================

For every scene:

1. Identify the central educational idea.
2. Identify which objects are actually needed.
3. Place them clearly.
4. Map each teaching beat to visual state changes.
5. Preserve state between beats.
6. Use the minimum number of actions necessary.
7. Ensure the final beat represents the final state described by the lesson.

============================================================
OUTPUT FORMAT
============================================================

Return exactly this JSON structure:

{
  "scenes": [
    {
      "scene_id": 1,

      "objects": [
        {
          "id": "object_id",
          "type": "text",
          "label": "Example",
          "position": "center",
          "relative_to": null,
          "style": {
            "color": "WHITE",
            "font_size": 42,
            "scale": 1.0
          }
        }
      ],

      "beats": [
        {
          "beat_id": "scene_1_beat_1",

          "actions": [
            {
              "action": "Create",
              "target": "object_id",
              "parameters": {}
            }
          ]
        }
      ]
    }
  ]
}

============================================================
STRICT REQUIREMENTS
============================================================

- Output ONLY JSON.
- No markdown fences.
- No comments.
- No explanation.
- No Python.
- No Manim code.
- No imports.
- No functions.
- No classes.
- Do not invent narration.
- Do not invent unrelated educational content.
- Preserve the scene IDs.
- Preserve the beat IDs.
- Every target must refer to a defined object unless the action is
  Connect/Disconnect and the target is a connection identifier.
- Do not create objects that are not educationally useful.
- Do not make every object visible at scene start.
- Respect the teaching sequence.

============================================================
LESSON JSON
============================================================

__SCENE_JSON__
"""