
"""
Direct LLM → Manim Python generator.

Architecture:

Lesson JSON
    ↓
Groq LLM
    ↓
Complete Manim Python code
    ↓
AST / safety validation
    ↓
generated_scene.py
    ↓
Manim render

The LLM directly generates the Manim code.
No visual-plan JSON.
No deterministic object renderer.
"""

import ast
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_groq import ChatGroq


# ============================================================
# PATH / CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not found in .env")


MODEL_NAME = "openai/gpt-oss-120b"

llm = ChatGroq(
    model=MODEL_NAME,
    temperature=0.1,
)


MAX_GENERATED_CODE_CHARS = 50000


# ============================================================
# MANIM GENERATION PROMPT
# ============================================================

MANIM_GENERATION_PROMPT = r"""
You are an expert educational animation programmer using Manim Community Edition.

Your task is to generate COMPLETE, EXECUTABLE Manim Python code for an educational
video based on the lesson information provided below.

IMPORTANT:

You MUST generate Python code directly.

Do NOT generate JSON.
Do NOT generate a visual plan.
Do NOT explain your answer.
Do NOT wrap the code in markdown fences.
Return ONLY the complete Python source code.

============================================================
OUTPUT REQUIREMENTS
============================================================

The output MUST:

1. Start exactly with:

from manim import *

2. Define exactly one scene class:

class GeneratedScene(Scene):

3. Put all animation logic inside:

def construct(self):

4. The code must be directly executable with:

manim generated_scene.py GeneratedScene

5. Use actual Manim animations such as:

self.play(Write(...))
self.play(Create(...))
self.play(FadeIn(...))
self.play(FadeOut(...))
self.play(Transform(...))
self.play(Indicate(...))
self.play(obj.animate.move_to(...))

6. The video must contain meaningful visual explanations.

7. Use simple Manim objects that work reliably:

Text
Rectangle
RoundedRectangle
Circle
Dot
Line
Arrow
VGroup
SurroundingRectangle

8. For mathematical expressions, prefer Text unless a simple mathematical
expression can safely be represented otherwise.

9. Do NOT use:

Tex
MathTex
ImageMobject
SVGMobject

10. Do NOT use external files, external imports, network calls, shell commands,
subprocesses, eval, exec, open, or arbitrary Python execution.

11. Do NOT use:

.normalize()
rotate_vector()

12. Do NOT use any imports except:

from manim import *

13. Keep the code concise and robust.

14. Do not create helper classes.

15. Do not create additional Scene classes.

16. The class name MUST be exactly:

GeneratedScene

============================================================
EDUCATIONAL VISUALIZATION RULES
============================================================

The animation should actually teach the concept.

Do not merely display the narration as text.

Use visual objects appropriate to the concept.

Examples:

For a stack:
- represent elements as rectangles
- arrange them vertically
- show push/pop visually
- use arrows or labels when useful

For a queue:
- represent elements horizontally
- show enqueue/dequeue movement

For a tree:
- use circles for nodes
- connect nodes using lines
- animate traversal

For an array:
- use rectangles/cells
- label elements
- highlight indexes

For sorting:
- show elements as bars or boxes
- animate swaps

For algorithms:
- show the important data structures
- highlight the current operation
- show transitions between states

For OS concepts:
- show processes, memory, CPU, files, etc. using simple shapes and labels.

For networking:
- show nodes and arrows representing communication.

For ML concepts:
- use simple boxes, arrows, labels, and graphs where appropriate.

The exact visualization must depend on the lesson topic.

============================================================
TIMING
============================================================

The lesson contains scene and beat timing.

Try to respect the provided beat durations.

Use self.wait() when necessary so the scene approximately follows
the supplied timing.

Do not make animations excessively fast.

============================================================
MULTI-SCENE RULE
============================================================

The lesson may contain multiple scenes.

Because Manim will render ONE GeneratedScene:

- implement all lesson scenes sequentially inside construct()
- after finishing a scene, use self.clear() before starting the next scene
- do not create multiple Scene classes

============================================================
CODE QUALITY
============================================================

Prefer straightforward code such as:

title = Text("...")
self.play(Write(title))

box = RoundedRectangle(...)
box.move_to(...)
self.play(Create(box))

label = Text("...")
label.move_to(box.get_center())
self.play(Write(label))

Use VGroup when grouping related objects.

Keep object references in normal Python variables.

Avoid unnecessarily complicated abstractions.

Do not generate thousands of lines.

============================================================
LESSON INPUT
============================================================

Below is the lesson information.

Generate the complete Manim Python source code based on it.

__LESSON_JSON__

============================================================
FINAL INSTRUCTION
============================================================

Return ONLY Python code.

The first line MUST be:

from manim import *
"""


# ============================================================
# BASIC HELPERS
# ============================================================

def _call_llm(prompt: str) -> str:
    """Call Groq and return plain text."""

    response = llm.invoke(prompt)

    content = getattr(
        response,
        "content",
        response,
    )

    if isinstance(content, list):
        content = "".join(
            str(item)
            for item in content
        )

    return str(content).strip()


def _clean_code(code: str) -> str:
    """
    Remove accidental markdown fences or surrounding text.
    """

    if not isinstance(code, str):
        raise ValueError(
            "LLM response is not a string."
        )

    code = code.strip()

    # Remove markdown fences.
    code = re.sub(
        r"^```(?:python)?\s*",
        "",
        code,
        flags=re.IGNORECASE,
    )

    code = re.sub(
        r"\s*```$",
        "",
        code,
    )

    code = code.strip()

    # If the model added text before the import,
    # keep everything starting from the Manim import.
    import_index = code.find("from manim import *")

    if import_index > 0:
        code = code[import_index:]

    return code.strip()


# ============================================================
# LESSON PAYLOAD
# ============================================================

def _build_llm_payload(video_plan: dict) -> dict:
    """
    Build a compact representation of the lesson.

    We intentionally remove long narration text because narration is
    already handled separately by TTS.

    The LLM mainly needs:
    - topic
    - learning objective
    - scene information
    - visual descriptions
    - beat actions
    - timing
    """

    payload = {
        "video_title": video_plan.get(
            "video_title",
            "",
        ),
        "subject": video_plan.get(
            "subject",
            "",
        ),
        "emotion": video_plan.get(
            "emotion",
            "",
        ),
        "learning_objective": video_plan.get(
            "learning_objective",
            "",
        ),
        "scenes": [],
    }

    for scene in video_plan.get(
        "scenes",
        [],
    ):

        scene_payload = {
            "scene_id": scene.get(
                "scene_id"
            ),
            "scene_title": scene.get(
                "scene_title",
                "",
            ),
            "learning_goal": scene.get(
                "learning_goal",
                "",
            ),
            "duration": scene.get(
                "duration",
                0,
            ),
            "visual_description": scene.get(
                "visual_description",
                "",
            ),
            "objects": [],
            "beats": [],
        }

        # ----------------------------------------------------
        # Objects
        # ----------------------------------------------------

        for obj in scene.get(
            "objects",
            [],
        ):

            if not isinstance(obj, dict):
                continue

            scene_payload["objects"].append({
                "id": obj.get("id"),
                "type": obj.get(
                    "type",
                    "",
                ),
                "label": obj.get(
                    "label",
                    "",
                ),
                "position": obj.get(
                    "position",
                    "center",
                ),
                "relative_to": obj.get(
                    "relative_to"
                ),
            })

        # ----------------------------------------------------
        # Teaching beats
        # ----------------------------------------------------

        for index, beat in enumerate(
            scene.get(
                "teaching_beats",
                [],
            ),
            start=1,
        ):

            if not isinstance(beat, dict):
                continue

            duration = float(
                beat.get(
                    "duration",
                    0,
                )
                or 0
            )

            if not duration:

                start = float(
                    beat.get(
                        "start_time",
                        beat.get(
                            "start_ratio",
                            0,
                        )
                        * scene_payload["duration"],
                    )
                    or 0
                )

                end = float(
                    beat.get(
                        "end_time",
                        beat.get(
                            "end_ratio",
                            1,
                        )
                        * scene_payload["duration"],
                    )
                    or 0
                )

                duration = max(
                    0,
                    end - start,
                )

            animations = []

            for animation in beat.get(
                "animations",
                [],
            ):

                if not isinstance(
                    animation,
                    dict,
                ):
                    continue

                animations.append({
                    "action": animation.get(
                        "action"
                    ),
                    "target": animation.get(
                        "target"
                    ),
                    "parameters": animation.get(
                        "parameters",
                        {},
                    ),
                })

            scene_payload["beats"].append({
                "beat_id": beat.get(
                    "beat_id",
                    f"scene_{scene_payload['scene_id']}_beat_{index}",
                ),
                "sequence": beat.get(
                    "sequence",
                    index,
                ),
                "visual_action": beat.get(
                    "visual_action",
                    "",
                ),
                "target": beat.get(
                    "target",
                    "",
                ),
                "duration": duration,
                "animations": animations,
            })

        payload["scenes"].append(
            scene_payload
        )

    return payload


# ============================================================
# LESSON VALIDATION
# ============================================================

def validate_video_plan(
    video_plan: dict,
) -> None:
    """
    Validate the lesson JSON before sending it to Groq.
    """

    if not isinstance(
        video_plan,
        dict,
    ):
        raise ValueError(
            "Video plan must be a dictionary."
        )

    scenes = video_plan.get(
        "scenes"
    )

    if not isinstance(
        scenes,
        list,
    ) or not scenes:

        raise ValueError(
            "Video plan must contain at least one scene."
        )

    for index, scene in enumerate(
        scenes,
        start=1,
    ):

        if not isinstance(
            scene,
            dict,
        ):
            raise ValueError(
                f"Scene {index} must be an object."
            )

        scene_id = scene.get(
            "scene_id"
        )

        if scene_id is None:
            raise ValueError(
                f"Scene {index} is missing scene_id."
            )

        duration = float(
            scene.get(
                "duration",
                0,
            )
            or 0
        )

        if duration <= 0:
            raise ValueError(
                f"Scene {scene_id} has invalid duration."
            )

        beats = scene.get(
            "teaching_beats",
            [],
        )

        if not isinstance(
            beats,
            list,
        ) or not beats:

            raise ValueError(
                f"Scene {scene_id} has no teaching beats."
            )


# ============================================================
# GENERATED CODE VALIDATION
# ============================================================

def validate_generated_code(
    code: str,
) -> None:
    """
    Validate LLM-generated Manim Python.

    This does NOT try to understand the animation.
    It only checks that the generated code is structurally safe
    and suitable for Manim execution.
    """

    if not isinstance(
        code,
        str,
    ):
        raise ValueError(
            "Generated Manim code must be a string."
        )

    if not code.strip():
        raise ValueError(
            "Generated Manim code is empty."
        )

    if len(code) > MAX_GENERATED_CODE_CHARS:
        raise ValueError(
            "Generated Manim code is too large."
        )

    lines = code.strip().splitlines()

    # --------------------------------------------------------
    # Required import
    # --------------------------------------------------------

    if lines[0].strip() != "from manim import *":
        raise ValueError(
            "Generated code must start with "
            "'from manim import *'."
        )

    # --------------------------------------------------------
    # Forbidden Python operations
    # --------------------------------------------------------

    forbidden_patterns = [
        "eval(",
        "exec(",
        "__import__(",
        "open(",
        "subprocess",
        "os.system",
        "os.popen",
        "requests.",
        "urllib.",
        "socket.",
        ".normalize(",
        "rotate_vector(",
    ]

    for pattern in forbidden_patterns:

        if pattern in code:
            raise ValueError(
                f"Generated code contains forbidden pattern: "
                f"{pattern}"
            )

    # --------------------------------------------------------
    # Python syntax
    # --------------------------------------------------------

    try:
        tree = ast.parse(code)

    except SyntaxError as exc:

        raise ValueError(
            "Generated Manim code contains a Python "
            f"syntax error: {exc}"
        ) from exc

    # --------------------------------------------------------
    # Imports
    # --------------------------------------------------------

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                if alias.name != "manim":

                    raise ValueError(
                        f"Forbidden import: {alias.name}"
                    )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            if node.module != "manim":

                raise ValueError(
                    f"Forbidden import from: "
                    f"{node.module}"
                )

    # --------------------------------------------------------
    # Scene classes
    # --------------------------------------------------------

    scene_classes = [
        node
        for node in tree.body
        if isinstance(
            node,
            ast.ClassDef,
        )
    ]

    if len(scene_classes) != 1:

        raise ValueError(
            "Generated code must contain exactly "
            "one class."
        )

    scene_class = scene_classes[0]

    if scene_class.name != "GeneratedScene":

        raise ValueError(
            "Scene class must be named GeneratedScene."
        )

    # --------------------------------------------------------
    # construct()
    # --------------------------------------------------------

    construct_methods = [
        node
        for node in scene_class.body
        if isinstance(
            node,
            ast.FunctionDef,
        )
        and node.name == "construct"
    ]

    if len(construct_methods) != 1:

        raise ValueError(
            "GeneratedScene must contain exactly "
            "one construct() method."
        )

    # --------------------------------------------------------
    # No extra methods
    # --------------------------------------------------------

    extra_methods = [
        node.name
        for node in scene_class.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
        and node.name != "construct"
    ]

    if extra_methods:

        raise ValueError(
            f"Unexpected Scene methods: "
            f"{extra_methods}"
        )

    # --------------------------------------------------------
    # Forbidden Manim classes
    # --------------------------------------------------------

    forbidden_names = {
        "Tex",
        "MathTex",
        "ImageMobject",
        "SVGMobject",
    }

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Name,
        ):

            if node.id in forbidden_names:

                raise ValueError(
                    f"Forbidden Manim object: "
                    f"{node.id}"
                )

        if isinstance(
            node,
            ast.Attribute,
        ):

            if node.attr in forbidden_names:

                raise ValueError(
                    f"Forbidden Manim object: "
                    f"{node.attr}"
                )

    # --------------------------------------------------------
    # Require animation
    # --------------------------------------------------------

    play_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            ast.Call,
        )
        and isinstance(
            node.func,
            ast.Attribute,
        )
        and node.func.attr == "play"
    ]

    if not play_calls:

        raise ValueError(
            "Generated code contains no self.play() calls."
        )

    # --------------------------------------------------------
    # Require construct to use self
    # --------------------------------------------------------

    construct = construct_methods[0]

    has_self_play = False

    for node in ast.walk(construct):

        if isinstance(
            node,
            ast.Call,
        ):

            if (
                isinstance(
                    node.func,
                    ast.Attribute,
                )
                and isinstance(
                    node.func.value,
                    ast.Name,
                )
                and node.func.value.id == "self"
                and node.func.attr == "play"
            ):
                has_self_play = True
                break

    if not has_self_play:

        raise ValueError(
            "construct() does not contain "
            "self.play()."
        )

    # --------------------------------------------------------
    # run_time validation
    # --------------------------------------------------------

    for node in play_calls:

        for keyword in node.keywords:

            if keyword.arg != "run_time":
                continue

            if isinstance(
                keyword.value,
                ast.Constant,
            ):

                try:
                    value = float(
                        keyword.value.value
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    continue

                if value <= 0:

                    raise ValueError(
                        "self.play() contains "
                        "invalid run_time."
                    )


# ============================================================
# DIRECT MANIM GENERATION
# ============================================================

def _generate_direct_manim_code(
    video_plan: dict,
) -> str:
    """
    Ask Groq to directly generate complete Manim Python.
    """

    payload = _build_llm_payload(
        video_plan
    )

    payload_text = str(
        payload
    )

    prompt = MANIM_GENERATION_PROMPT.replace(
        "__LESSON_JSON__",
        payload_text,
    )

    print(
        "Calling Groq for direct Manim code..."
    )

    raw_response = _call_llm(
        prompt
    )

    print(
        "Cleaning generated Manim code..."
    )

    code = _clean_code(
        raw_response
    )

    return code


# ============================================================
# CODE REPAIR
# ============================================================

def _repair_generated_code(
    video_plan: dict,
    invalid_code: str,
    error: Exception,
) -> str:
    """
    Ask Groq to repair its previously generated Python code.
    """

    payload = _build_llm_payload(
        video_plan
    )

    repair_prompt = f"""
You are repairing a Manim Python program.

Return ONLY the complete corrected Python source code.

Do NOT return JSON.
Do NOT explain anything.
Do NOT use markdown fences.

The code must start exactly with:

from manim import *

The code must contain exactly:

class GeneratedScene(Scene):

with exactly one construct() method.

The program must be executable with:

manim generated_scene.py GeneratedScene

The previous generated code was:

{invalid_code[:30000]}

The validation error was:

{str(error)}

The lesson information is:

{payload}

Fix the code while preserving the educational meaning.

IMPORTANT:

- Use only `from manim import *`
- No external imports
- No Tex
- No MathTex
- No ImageMobject
- No SVGMobject
- No eval
- No exec
- No open
- No subprocess
- No network calls
- No shell commands
- No `.normalize()`
- No `rotate_vector()`
- Include actual `self.play(...)` calls
- Keep the implementation concise
- If there are multiple scenes, implement them sequentially inside construct()
- Use `self.clear()` between scenes
- Return ONLY Python code

Previous code:

{invalid_code[:30000]}
"""

    print(
        "Asking Groq to repair generated Manim code..."
    )

    repaired_response = _call_llm(
        repair_prompt
    )

    repaired_code = _clean_code(
        repaired_response
    )

    return repaired_code


# ============================================================
# PUBLIC API
# ============================================================

def generate_manim_code(
    video_plan: dict,
) -> str:
    """
    Public entry point used by VideoService.
    """

    print(
        "Validating lesson plan..."
    )

    validate_video_plan(
        video_plan
    )

    # --------------------------------------------------------
    # First generation attempt
    # --------------------------------------------------------

    print(
        "Generating Manim code directly with Groq..."
    )

    code = _generate_direct_manim_code(
        video_plan
    )

    # --------------------------------------------------------
    # First validation
    # --------------------------------------------------------

    try:

        print(
            "Validating generated Manim code..."
        )

        validate_generated_code(
            code
        )

    except Exception as first_error:

        print(
            "Generated code failed validation:"
        )

        print(
            first_error
        )

        # ----------------------------------------------------
        # Repair
        # ----------------------------------------------------

        try:

            code = _repair_generated_code(
                video_plan,
                code,
                first_error,
            )

            print(
                "Validating repaired Manim code..."
            )

            validate_generated_code(
                code
            )

        except Exception as repair_error:

            raise RuntimeError(
                "Groq failed to generate valid Manim code.\n"
                f"Original error: {first_error}\n"
                f"Repair error: {repair_error}"
            ) from repair_error

    print(
        "Generated Manim code passed validation."
    )

    return code


# ============================================================
# SAVE
# ============================================================

def save_manim_code(
    code: str,
    output_path: str,
) -> None:

    path = Path(
        output_path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        code,
        encoding="utf-8",
    )

    print(
        f"Manim code saved: {path}"
    )


# ============================================================
# COMPATIBILITY HELPER
# ============================================================

def clean_generated_code(
    code: str,
) -> str:
    """
    Compatibility helper for VideoService.

    VideoService already calls this function,
    so we keep it even though the generator itself
    also cleans the LLM response.
    """

    return _clean_code(
        code
    )

