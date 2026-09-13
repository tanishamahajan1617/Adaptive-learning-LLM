import os
import ast
import math
import json
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from src.prompt.manim_prompt import MANIM_GENERATION_PROMPT


# ============================================================
# PATH / ENV
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError(
        f"GROQ_API_KEY not found. "
        f"Please add GROQ_API_KEY to {BASE_DIR / '.env'}"
    )


# ============================================================
# LLM
# ============================================================

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    groq_api_key=api_key,
    temperature=0.1,
)


# ============================================================
# CONFIG
# ============================================================

ALLOWED_ACTIONS = {
    "Create",
    "WriteText",
    "FadeIn",
    "FadeOut",
    "Move",
    "MoveToTarget",
    "Transform",
    "ReplacementTransform",
    "Indicate",
    "Highlight",
    "Compare",
    "Swap",
    "Split",
    "Merge",
    "Connect",
    "Disconnect",
    "Remove",
}


FORBIDDEN_IMPORTS = {
    "numpy",
    "np",
    "cv2",
    "torch",
    "tensorflow",
    "pandas",
    "scipy",
    "requests",
    "matplotlib",
    "plotly",
    "PIL",
    "os",
    "sys",
    "subprocess",
    "pathlib",
    "json",
    "re",
    "math",
}


FORBIDDEN_NAMES = {
    "Tex",
    "MathTex",
    "ImageMobject",
    "SVGMobject",
}


FORBIDDEN_PATTERNS = [
    ".normalize(",
    "rotate_vector(",
    "eval(",
    "exec(",
    "__import__(",
    "open(",
    "subprocess",
]


# Keep generated code reasonably compact.
# This prevents a runaway LLM response from becoming a huge file.
MAX_GENERATED_CODE_CHARS = 30000


# ============================================================
# HELPERS
# ============================================================

def _is_close(a, b):
    return math.isclose(
        float(a),
        float(b),
        abs_tol=1e-6,
    )


def _extract_string_subscript(node):
    """
    Extract:

        objects["some_id"]

    -> "some_id"

    """
    if not isinstance(node, ast.Subscript):
        return None

    slice_node = node.slice

    if isinstance(slice_node, ast.Constant):
        if isinstance(slice_node.value, str):
            return slice_node.value

    return None


def _get_known_object_ids(scene_json):
    known_ids = set()

    for scene in scene_json.get("scenes", []):
        for obj in scene.get("objects", []):
            if not isinstance(obj, dict):
                continue

            object_id = obj.get("id")

            if object_id:
                known_ids.add(str(object_id))

    return known_ids


# ============================================================
# CLEAN LLM OUTPUT
# ============================================================

def clean_generated_code(code: str) -> str:

    if not isinstance(code, str):
        raise ValueError(
            "Manim generator returned non-string output."
        )

    code = code.strip()

    # Remove markdown fences if the model ignores the instruction.
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
        flags=re.IGNORECASE,
    )

    code = code.strip()

    # Remove accidental text before the Manim import.
    manim_import = "from manim import *"

    import_position = code.find(manim_import)

    if import_position > 0:
        code = code[import_position:]

    # If model returned "import manim" instead, leave validation
    # to reject it rather than silently modifying it.

    return code.strip()


# ============================================================
# VALIDATE VIDEO PLAN
# ============================================================

def validate_video_plan(scene_json: dict):

    if not isinstance(scene_json, dict):
        raise ValueError(
            "Scene JSON must be a dictionary."
        )

    scenes = scene_json.get("scenes")

    if not isinstance(scenes, list):
        raise ValueError(
            "Scene JSON must contain a 'scenes' list."
        )

    if not scenes:
        raise ValueError(
            "Scene JSON contains no scenes."
        )

    for scene_index, scene in enumerate(scenes):

        scene_number = scene_index + 1

        if not isinstance(scene, dict):
            raise ValueError(
                f"Scene {scene_number} must be an object."
            )

        duration = scene.get(
            "audio_duration",
            scene.get("duration"),
        )

        if duration is None:
            raise ValueError(
                f"Scene {scene_number} is missing "
                f"'audio_duration'."
            )

        try:
            duration = float(duration)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Scene {scene_number}: "
                f"audio_duration must be numeric."
            ) from exc

        if duration <= 0:
            raise ValueError(
                f"Scene {scene_number}: "
                f"audio_duration must be greater than 0."
            )

        scene["audio_duration"] = duration

        # ----------------------------------------------------
        # Objects
        # ----------------------------------------------------

        objects = scene.get("objects", [])

        if not isinstance(objects, list):
            raise ValueError(
                f"Scene {scene_number}: "
                f"'objects' must be a list."
            )

        object_ids = set()

        for obj_index, obj in enumerate(objects):

            if not isinstance(obj, dict):
                raise ValueError(
                    f"Scene {scene_number}: "
                    f"object {obj_index + 1} must be an object."
                )

            object_id = str(
                obj.get("id", "")
            ).strip()

            if not object_id:
                raise ValueError(
                    f"Scene {scene_number}: "
                    f"object {obj_index + 1} has no id."
                )

            if object_id in object_ids:
                raise ValueError(
                    f"Scene {scene_number}: "
                    f"duplicate object id '{object_id}'."
                )

            object_ids.add(object_id)

        # ----------------------------------------------------
        # Teaching beats
        # ----------------------------------------------------

        beats = scene.get("teaching_beats")

        if not isinstance(beats, list):
            raise ValueError(
                f"Scene {scene_number}: "
                f"teaching_beats must be a list."
            )

        if not beats:
            raise ValueError(
                f"Scene {scene_number}: "
                f"teaching_beats cannot be empty."
            )

        previous_end = 0.0
        beat_ids = set()

        for beat_index, beat in enumerate(beats):

            beat_number = beat_index + 1

            if not isinstance(beat, dict):
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number} must be an object."
                )

            # ------------------------------------------------
            # Beat ID
            # ------------------------------------------------

            beat_id = str(
                beat.get("beat_id", "")
            ).strip()

            if not beat_id:
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    f"beat_id is missing."
                )

            if beat_id in beat_ids:
                raise ValueError(
                    f"Scene {scene_number}: "
                    f"duplicate beat_id '{beat_id}'."
                )

            beat_ids.add(beat_id)

            # ------------------------------------------------
            # Timing
            # ------------------------------------------------

            required_timing = [
                "start_time",
                "end_time",
                "duration",
            ]

            missing = [
                field
                for field in required_timing
                if field not in beat
            ]

            if missing:
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    f"missing timing fields {missing}."
                )

            try:
                start_time = float(
                    beat["start_time"]
                )

                end_time = float(
                    beat["end_time"]
                )

                beat_duration = float(
                    beat["duration"]
                )

            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    f"timing values must be numeric."
                ) from exc

            if start_time < 0:
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    f"start_time cannot be negative."
                )

            if end_time > duration + 1e-6:
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    f"end_time {end_time} exceeds "
                    f"scene duration {duration}."
                )

            if start_time >= end_time:
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    f"start_time must be smaller than end_time."
                )

            expected_duration = (
                end_time - start_time
            )

            if not math.isclose(
                beat_duration,
                expected_duration,
                abs_tol=0.01,
            ):
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    f"duration does not match "
                    f"start_time/end_time."
                )

            if not math.isclose(
                start_time,
                previous_end,
                abs_tol=0.01,
            ):
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    f"timeline is not contiguous. "
                    f"Expected {previous_end}, "
                    f"got {start_time}."
                )

            previous_end = end_time

            # ------------------------------------------------
            # Required semantic fields
            # ------------------------------------------------

            if "visual_action" not in beat:
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    f"missing visual_action."
                )

            if "target" not in beat:
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    f"missing target."
                )

            animations = beat.get("animations")

            if not isinstance(animations, list):
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    f"'animations' must be a list."
                )

            # ------------------------------------------------
            # Animation validation
            # ------------------------------------------------

            for animation_index, animation in enumerate(
                animations
            ):

                if not isinstance(animation, dict):
                    raise ValueError(
                        f"Scene {scene_number}, "
                        f"Beat {beat_number}, "
                        f"Animation {animation_index + 1} "
                        f"must be an object."
                    )

                action = animation.get("action")

                if action not in ALLOWED_ACTIONS:
                    raise ValueError(
                        f"Scene {scene_number}, "
                        f"Beat {beat_number}, "
                        f"Animation {animation_index + 1}: "
                        f"unsupported action '{action}'."
                    )

                if "target" not in animation:
                    raise ValueError(
                        f"Scene {scene_number}, "
                        f"Beat {beat_number}, "
                        f"Animation {animation_index + 1}: "
                        f"missing target."
                    )

                if "parameters" not in animation:
                    raise ValueError(
                        f"Scene {scene_number}, "
                        f"Beat {beat_number}, "
                        f"Animation {animation_index + 1}: "
                        f"missing parameters."
                    )

        # ----------------------------------------------------
        # Full timeline coverage
        # ----------------------------------------------------

        if not _is_close(
            previous_end,
            duration,
        ):
            raise ValueError(
                f"Scene {scene_number}: "
                f"teaching beats do not cover "
                f"the complete audio duration. "
                f"Last beat ends at "
                f"{previous_end:.3f}s, "
                f"audio duration is "
                f"{duration:.3f}s."
            )


# ============================================================
# COMPACT PAYLOAD
# ============================================================

def build_compact_payload(scene_json: dict) -> dict:

    compact_scenes = []

    for scene in scene_json["scenes"]:

        compact_scene = {
            "scene_id": scene.get("scene_id"),
            "duration": scene.get(
                "audio_duration",
                scene.get("duration"),
            ),
            "camera": scene.get("camera", {}),
            "objects": scene.get("objects", []),
            "teaching_beats": [],
        }

        for beat in scene.get(
            "teaching_beats",
            [],
        ):

            compact_beat = {
                "beat_id": beat.get("beat_id"),
                "sequence": beat.get("sequence"),
                "visual_action": beat.get(
                    "visual_action"
                ),
                "target": beat.get("target"),
                "start_time": beat.get("start_time"),
                "end_time": beat.get("end_time"),
                "duration": beat.get("duration"),
                "animations": beat.get(
                    "animations",
                    [],
                ),
            }

            compact_scene["teaching_beats"].append(
                compact_beat
            )

        compact_scenes.append(
            compact_scene
        )

    return {
        "scenes": compact_scenes
    }


# ============================================================
# OBJECT REGISTRY VALIDATION
# ============================================================

def validate_object_registry_usage(
    tree,
    known_object_ids=None,
):
    """
    Validate registry usage without requiring every JSON object
    to be registered.

    Why?

    Because objects are intentionally introduced only when their
    teaching beat occurs.

    Therefore, an object may legitimately appear later in code.
    """

    known_object_ids = set(
        known_object_ids or []
    )

    registered_ids = set()

    # --------------------------------------------------------
    # Collect registry assignments
    # --------------------------------------------------------

    for node in ast.walk(tree):

        if not isinstance(node, ast.Assign):
            continue

        for target in node.targets:

            if not isinstance(
                target,
                ast.Subscript,
            ):
                continue

            if not isinstance(
                target.value,
                ast.Name,
            ):
                continue

            if target.value.id != "objects":
                continue

            object_id = _extract_string_subscript(
                target
            )

            if object_id:
                registered_ids.add(object_id)

    # --------------------------------------------------------
    # Detect standalone registry lookups
    # --------------------------------------------------------

    for node in ast.walk(tree):

        if not isinstance(node, ast.Expr):
            continue

        value = node.value

        if not isinstance(
            value,
            ast.Subscript,
        ):
            continue

        if not isinstance(
            value.value,
            ast.Name,
        ):
            continue

        if value.value.id != "objects":
            continue

        object_id = _extract_string_subscript(
            value
        )

        if object_id:

            raise ValueError(
                "Generated Manim code contains "
                "a standalone registry lookup: "
                f"objects[{object_id!r}]. "
                "Use it inside a Manim operation."
            )

    # --------------------------------------------------------
    # Informational warning only
    # --------------------------------------------------------

    missing_registry = (
        known_object_ids - registered_ids
    )

    if missing_registry:

        print(
            "INFO: Some lesson objects are not "
            "registered yet in the generated code:"
        )

        for object_id in sorted(
            missing_registry
        ):
            print(f"  - {object_id}")


# ============================================================
# GENERATED CODE VALIDATION
# ============================================================

def validate_generated_code(
    code: str,
    known_object_ids=None,
):

    if not isinstance(code, str):
        raise ValueError(
            "Generated Manim code must be a string."
        )

    if len(code) > MAX_GENERATED_CODE_CHARS:
        raise ValueError(
            "Generated Manim code is excessively large "
            f"({len(code)} characters). "
            "The generator should produce compact direct Manim code."
        )

    # --------------------------------------------------------
    # First line
    # --------------------------------------------------------

    lines = code.splitlines()

    if not lines:
        raise ValueError(
            "Generated Manim code is empty."
        )

    if lines[0].strip() != "from manim import *":
        raise ValueError(
            "Generated Manim code must start exactly with "
            "'from manim import *'."
        )

    # --------------------------------------------------------
    # Forbidden patterns
    # --------------------------------------------------------

    for pattern in FORBIDDEN_PATTERNS:

        if pattern in code:
            raise ValueError(
                "Generated code contains "
                f"forbidden pattern: {pattern}"
            )

    # --------------------------------------------------------
    # Parse Python
    # --------------------------------------------------------

    try:
        tree = ast.parse(code)

    except SyntaxError as exc:

        raise ValueError(
            "Generated Manim code contains "
            f"a Python syntax error: {exc}"
        ) from exc

    # --------------------------------------------------------
    # Import validation
    # --------------------------------------------------------

    imported_modules = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:
                imported_modules.append(
                    alias.name
                )

        elif isinstance(node, ast.ImportFrom):

            if node.module:
                imported_modules.append(
                    node.module
                )

    for module in imported_modules:

        root_module = module.split(".")[0]

        if root_module != "manim":
            raise ValueError(
                "Generated code contains "
                f"forbidden import: {module}"
            )

    # --------------------------------------------------------
    # Scene class validation
    # --------------------------------------------------------

    scene_classes = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.ClassDef,
        ):
            continue

        inherits_scene = any(
            isinstance(base, ast.Name)
            and base.id == "Scene"
            for base in node.bases
        )

        if inherits_scene:
            scene_classes.append(node)

    if len(scene_classes) != 1:
        raise ValueError(
            "Generated code must contain "
            "exactly one Scene subclass."
        )

    scene_class = scene_classes[0]

    if scene_class.name != "GeneratedScene":
        raise ValueError(
            "The Scene class must be "
            "named 'GeneratedScene'."
        )

    # --------------------------------------------------------
    # construct()
    # --------------------------------------------------------

    construct_methods = [
        node
        for node in scene_class.body
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == "construct"
        )
    ]

    if len(construct_methods) != 1:
        raise ValueError(
            "GeneratedScene must contain "
            "exactly one construct() method."
        )

    # --------------------------------------------------------
    # No additional methods
    # --------------------------------------------------------

    extra_methods = [
        node
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
        names = [
            node.name
            for node in extra_methods
        ]

        raise ValueError(
            "GeneratedScene must not contain "
            f"additional helper methods: {names}"
        )

    # --------------------------------------------------------
    # Forbidden Manim classes
    # --------------------------------------------------------

    for node in ast.walk(tree):

        if (
            isinstance(node, ast.Name)
            and node.id in FORBIDDEN_NAMES
        ):
            raise ValueError(
                "Generated code uses "
                f"forbidden Manim object: {node.id}"
            )

    # --------------------------------------------------------
    # Additional Scene subclasses
    # --------------------------------------------------------

    for node in ast.walk(tree):

        if (
            isinstance(node, ast.ClassDef)
            and node is not scene_class
        ):

            inherits_scene = any(
                isinstance(base, ast.Name)
                and base.id == "Scene"
                for base in node.bases
            )

            if inherits_scene:
                raise ValueError(
                    "Generated code contains "
                    "more than one Scene subclass."
                )

    # --------------------------------------------------------
    # Registry
    # --------------------------------------------------------

    validate_object_registry_usage(
        tree,
        known_object_ids=known_object_ids,
    )

    return True


# ============================================================
# REPAIR PROMPT
# ============================================================

def build_repair_prompt(
    code: str,
    error_message: str,
) -> str:

    return f"""
You generated invalid Manim Community Edition Python code.

Validation error:

{error_message}

Fix ONLY the problem that caused the validation failure.

Return ONLY the COMPLETE corrected Python file.

==================================================
STRICT REQUIREMENTS
==================================================

First line:

from manim import *

Exactly one class:

class GeneratedScene(Scene):

Exactly one method:

def construct(self):

No other Scene subclass.

No helper classes.

No helper methods.

No generic rendering framework.

No object factory.

No animation engine.

No definitions dictionary.

No imports other than:

from manim import *

Do not use:

Tex
MathTex
ImageMobject
SVGMobject
eval
exec
open
__import__

Do not use filesystem operations.

Do not use external libraries.

Do not add decorative objects.

Do not change the teaching sequence.

Do not remove teaching beats.

Do not create future objects early.

Maintain persistent object registry:

objects = {{}}

Correct:

box = Rectangle(...)
objects["box"] = box

Then:

self.play(Create(objects["box"]))

Never write:

objects["box"]

as a standalone statement.

All parentheses, brackets, braces and strings MUST be closed.

Keep the code compact.

Do NOT truncate the response.

Return COMPLETE Python code only.

==================================================
INVALID CODE
==================================================

{code}

==================================================
END INVALID CODE
==================================================
"""


# ============================================================
# CALL LLM
# ============================================================

def _call_llm(prompt: str) -> str:

    response = llm.invoke(prompt)

    code = response.content

    if not isinstance(code, str):
        raise ValueError(
            "Groq returned non-string Manim code."
        )

    return code


# ============================================================
# GENERATE MANIM CODE
# ============================================================

def generate_manim_code(scene_json: dict) -> str:

    # --------------------------------------------------------
    # 1. Validate lesson JSON
    # --------------------------------------------------------

    print("Validating scene plan...")

    validate_video_plan(scene_json)

    # --------------------------------------------------------
    # 2. Compact payload
    # --------------------------------------------------------

    print("Building compact Manim payload...")

    compact_payload = build_compact_payload(
        scene_json
    )

    scene_json_text = json.dumps(
        compact_payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    # --------------------------------------------------------
    # 3. Build prompt
    # --------------------------------------------------------

    prompt = MANIM_GENERATION_PROMPT.replace(
        "__SCENE_JSON__",
        scene_json_text,
    )

    # --------------------------------------------------------
    # 4. First generation
    # --------------------------------------------------------

    print("Calling Groq Manim generator...")

    raw_code = _call_llm(prompt)

    raw_response_path = (
        BASE_DIR / "raw_manim_response.txt"
    )

    with open(
        raw_response_path,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(raw_code)

    print(
        f"Raw Manim response saved to: "
        f"{raw_response_path}"
    )

    code = clean_generated_code(
        raw_code
    )

    # --------------------------------------------------------
    # 5. Validate first generation
    # --------------------------------------------------------

    known_object_ids = _get_known_object_ids(
        compact_payload
    )

    print("Validating generated Manim code...")

    try:

        validate_generated_code(
            code,
            known_object_ids=known_object_ids,
        )

        print(
            "Generated Manim code passed validation."
        )

        return code

    except ValueError as first_error:

        error_message = str(first_error)

        print(
            "\nGenerated code failed validation:"
        )
        print(error_message)

    # --------------------------------------------------------
    # 6. Automatic repair
    # --------------------------------------------------------

    print(
        "\nAttempting automatic Manim code repair..."
    )

    repair_prompt = build_repair_prompt(
        code=code,
        error_message=error_message,
    )

    repaired_raw_code = _call_llm(
        repair_prompt
    )

    repaired_code = clean_generated_code(
        repaired_raw_code
    )

    # --------------------------------------------------------
    # 7. Validate repaired code
    # --------------------------------------------------------

    print(
        "Validating repaired Manim code..."
    )

    validate_generated_code(
        repaired_code,
        known_object_ids=known_object_ids,
    )

    # --------------------------------------------------------
    # 8. Save repaired response
    # --------------------------------------------------------

    repaired_path = (
        BASE_DIR
        / "repaired_manim_response.txt"
    )

    with open(
        repaired_path,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(repaired_code)

    print(
        f"Repaired Manim code saved to: "
        f"{repaired_path}"
    )

    print(
        "Repaired Manim code passed validation."
    )

    return repaired_code


# ============================================================
# SAVE MANIM CODE
# ============================================================

def save_manim_code(
    code: str,
    output_path: str,
):

    output_file = os.path.abspath(
        output_path
    )

    output_directory = os.path.dirname(
        output_file
    )

    if output_directory:
        os.makedirs(
            output_directory,
            exist_ok=True,
        )

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as file:

        file.write(code)

    print(
        "Manim code saved to: "
        f"{output_file}"
    )