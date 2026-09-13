
import os
import json
import math

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


# ============================================================
# ENV
# ============================================================

load_dotenv(".venv")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found. "
        "Please add GEMINI_API_KEY to your .env file."
    )


# ============================================================
# LLM
# ============================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    google_api_key=api_key,
)


# ============================================================
# VIDEO SCRIPT PROMPT
# ============================================================

VIDEO_SCRIPT_PROMPT = r"""
You are an expert educational video lesson planner.

Your task is to convert the student's question and retrieved
knowledge into a structured educational animation plan.

==================================================
CORE RULE
==================================================

Use ONLY the retrieved knowledge.

Do NOT invent facts.

Do NOT add information that is not supported by the retrieved
knowledge.

The teaching plan must directly answer the student's question.

==================================================
EMOTION ADAPTATION
==================================================

The detected emotion is provided as input.

Neutral:
- normal explanation
- balanced pacing
- clear visuals

Frustrated:
- simplify the explanation
- use smaller concepts
- use slower, clearer visual steps
- avoid unnecessary complexity

Bored:
- keep explanations short
- use dynamic but meaningful visual changes
- avoid long static explanations

Confident:
- provide deeper technical explanation when supported
- include more detailed visual reasoning
- add a challenge or deeper question when supported

Do NOT change factual content based on emotion.

==================================================
SCENES
==================================================

Create multiple scenes when useful.

Each scene should represent one coherent part of the lesson.

Every scene MUST contain:

video_title
subject
emotion
learning_objective
estimated_duration
scenes
summary
quiz

Each scene MUST contain:

scene_id
scene_title
learning_goal
duration
narration
visual_description
teaching_beats
camera
objects

==================================================
TEACHING BEATS
==================================================

Teaching beats are the most important part of the output.

Create a separate beat whenever the explanation introduces:

1. a new concept
2. a new object
3. a new state
4. an operation
5. an important visual change

Do NOT put an entire multi-step explanation into one beat.

For every beat provide:

beat_id
sequence
narration
visual_action
target
state_before
state_after
start_ratio
end_ratio
animations

==================================================
BEAT MEANING
==================================================

narration:
What is being explained verbally.

visual_action:
What the learner should see while hearing that narration.

target:
The exact logical object affected by the visual action.

state_before:
The expected visual state before the beat.

state_after:
The expected visual state after the beat.

animations:
The exact visual operations needed to produce the state change.

==================================================
TIMELINE
==================================================

Teaching beats must cover the complete scene.

The first beat MUST start at:

0.0

The final beat MUST end at:

1.0

Beats MUST be contiguous.

Example:

Beat 1:
0.0 -> 0.30

Beat 2:
0.30 -> 0.65

Beat 3:
0.65 -> 1.0

There must be:

NO gaps

NO overlaps

NO negative values

start_ratio must always be smaller than end_ratio.

==================================================
ANIMATIONS
==================================================

Every animation MUST contain:

action
target
parameters

Allowed actions:

Create
WriteText
FadeIn
FadeOut
Move
MoveToTarget
Transform
ReplacementTransform
Indicate
Highlight
Compare
Swap
Split
Merge
Connect
Disconnect
Remove

Use ONLY these actions.

Every animation MUST have a clear educational purpose.

Do NOT add decorative animations.

==================================================
OBJECTS
==================================================

Objects define logical identities.

They do NOT mean every object should be visible at the beginning.

Future objects MUST remain invisible until their corresponding
beat introduces them.

Example:

If a stack eventually contains:

10
5

do NOT show both at the beginning.

Instead:

Beat 1:
show empty stack

Beat 2:
create 10

Beat 3:
create 5

Objects MUST have:

id
type
label
position
relative_to

Use the following object types when appropriate:

text
circle
rectangle
node
edge
arrow
pointer
array
stack
queue
tree
graph
memory
process
resource
cpu
disk
character

==================================================
STATE PRESERVATION
==================================================

The visualization must evolve incrementally.

Do NOT rebuild the complete structure after every beat.

If a previous beat creates an object and the next beat does not
modify it, keep it unchanged.

Example:

Current stack:

10

Next beat:

push 5

Correct:

keep 10
add 5

Incorrect:

remove 10
rebuild 10
add 5

==================================================
TARGET FIDELITY
==================================================

The target of an animation must match the object affected.

If target is:

element_10

then the animation must affect element_10.

Do NOT silently change the target.

Do NOT animate unrelated objects.

==================================================
NARRATION / VISUAL SYNCHRONIZATION
==================================================

The relationship MUST be:

narration
    ->
visual_action
    ->
animation

Example:

narration:
"Now we push 10 onto the stack."

visual_action:
"Add element_10 to the top of the stack."

target:
"element_10"

animation:
Create element_10

The visual action must make the narration understandable even
without seeing the audio.

==================================================
SCENE-LEVEL ANIMATIONS
==================================================

Do NOT create a scene-level "animations" field.

ALL animations MUST be inside teaching_beats.

==================================================
CAMERA
==================================================

Default camera:

type = static
zoom = 1.0

Only use camera movement when it provides educational value.

==================================================
TEXT
==================================================

Use short educational labels.

Do NOT put the complete narration on screen.

Do NOT create large paragraphs.

==================================================
OUTPUT
==================================================

Return ONLY valid JSON.

Do NOT return Markdown.

Do NOT return code fences.

Do NOT return explanations.

Do NOT return Python.

==================================================
INPUT
==================================================

Student Question:
{query}

Detected Emotion:
{emotion}

Retrieved Knowledge:
{context}
"""


# ============================================================
# HELPERS
# ============================================================

def validate_ratio(
    value,
    scene_number,
    beat_number,
    field_name,
):
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"Scene {scene_number}, Beat {beat_number}: "
            f"{field_name} must be numeric."
        )

    if not 0.0 <= value <= 1.0:
        raise ValueError(
            f"Scene {scene_number}, Beat {beat_number}: "
            f"{field_name} must be between 0 and 1."
        )

    return value


# ============================================================
# VALIDATE GENERATED SCRIPT
# ============================================================

def validate_video_script(response: dict):

    if not isinstance(response, dict):
        raise ValueError(
            "Video script generator returned invalid JSON."
        )

    if "scenes" not in response:
        raise ValueError(
            "Generated video script does not contain 'scenes'."
        )

    scenes = response["scenes"]

    if not isinstance(scenes, list):
        raise ValueError(
            "'scenes' must be a list."
        )

    if not scenes:
        raise ValueError(
            "Generated video script contains no scenes."
        )

    for scene_index, scene in enumerate(scenes):

        scene_number = scene_index + 1

        if not isinstance(scene, dict):
            raise ValueError(
                f"Scene {scene_number} must be an object."
            )

        # ----------------------------------------------------
        # Required scene fields
        # ----------------------------------------------------

        required_scene_fields = [
            "teaching_beats",
            "objects",
            "camera",
        ]

        missing = [
            field
            for field in required_scene_fields
            if field not in scene
        ]

        if missing:
            raise ValueError(
                f"Scene {scene_number} missing: {missing}"
            )

        # ----------------------------------------------------
        # Scene-level animations forbidden
        # ----------------------------------------------------

        if "animations" in scene:
            del scene["animations"]

        # ----------------------------------------------------
        # Teaching beats
        # ----------------------------------------------------

        beats = scene["teaching_beats"]

        if not isinstance(beats, list):
            raise ValueError(
                f"Scene {scene_number}: "
                "teaching_beats must be a list."
            )

        if not beats:
            raise ValueError(
                f"Scene {scene_number}: "
                "teaching_beats cannot be empty."
            )

        previous_sequence = 0
        previous_end_ratio = 0.0
        beat_ids = set()

        # ====================================================
        # BEAT VALIDATION
        # ====================================================

        for beat_index, beat in enumerate(beats):

            beat_number = beat_index + 1

            if not isinstance(beat, dict):
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number} must be an object."
                )

            required_fields = [
                "beat_id",
                "sequence",
                "narration",
                "visual_action",
                "target",
                "state_before",
                "state_after",
                "start_ratio",
                "end_ratio",
                "animations",
            ]

            missing = [
                field
                for field in required_fields
                if field not in beat
            ]

            if missing:
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number} missing: {missing}"
                )

            # ------------------------------------------------
            # Beat ID
            # ------------------------------------------------

            beat_id = str(
                beat["beat_id"]
            ).strip()

            if not beat_id:
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    "beat_id cannot be empty."
                )

            if beat_id in beat_ids:
                raise ValueError(
                    f"Scene {scene_number}: "
                    f"duplicate beat_id '{beat_id}'."
                )

            beat_ids.add(beat_id)

            # ------------------------------------------------
            # Sequence
            # ------------------------------------------------

            try:
                sequence = int(
                    beat["sequence"]
                )
            except (TypeError, ValueError):
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    "sequence must be an integer."
                )

            if sequence <= previous_sequence:
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    "sequence must be strictly increasing."
                )

            previous_sequence = sequence

            # ------------------------------------------------
            # Ratios
            # ------------------------------------------------

            start_ratio = validate_ratio(
                beat["start_ratio"],
                scene_number,
                beat_number,
                "start_ratio",
            )

            end_ratio = validate_ratio(
                beat["end_ratio"],
                scene_number,
                beat_number,
                "end_ratio",
            )

            beat["start_ratio"] = start_ratio
            beat["end_ratio"] = end_ratio

            if start_ratio >= end_ratio:
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    "start_ratio must be smaller "
                    "than end_ratio."
                )

            # ------------------------------------------------
            # Contiguous timeline
            # ------------------------------------------------

            if not math.isclose(
                start_ratio,
                previous_end_ratio,
                abs_tol=1e-6,
            ):
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    "timeline is not contiguous. "
                    f"Expected {previous_end_ratio}, "
                    f"got {start_ratio}."
                )

            previous_end_ratio = end_ratio

            # ------------------------------------------------
            # Animations
            # ------------------------------------------------

            animations = beat["animations"]

            if not isinstance(
                animations,
                list,
            ):
                raise ValueError(
                    f"Scene {scene_number}, "
                    f"Beat {beat_number}: "
                    "animations must be a list."
                )

            for animation_index, animation in enumerate(
                animations
            ):

                if not isinstance(
                    animation,
                    dict,
                ):
                    raise ValueError(
                        f"Scene {scene_number}, "
                        f"Beat {beat_number}, "
                        f"Animation {animation_index + 1} "
                        "must be an object."
                    )

                required_animation_fields = [
                    "action",
                    "target",
                    "parameters",
                ]

                missing_animation_fields = [
                    field
                    for field in required_animation_fields
                    if field not in animation
                ]

                if missing_animation_fields:
                    raise ValueError(
                        f"Scene {scene_number}, "
                        f"Beat {beat_number}, "
                        f"Animation {animation_index + 1} "
                        f"missing: "
                        f"{missing_animation_fields}"
                    )

        # ====================================================
        # FULL TIMELINE
        # ====================================================

        first_start = float(
            beats[0]["start_ratio"]
        )

        last_end = float(
            beats[-1]["end_ratio"]
        )

        if not math.isclose(
            first_start,
            0.0,
            abs_tol=1e-6,
        ):
            raise ValueError(
                f"Scene {scene_number}: "
                "first beat must start at 0.0."
            )

        if not math.isclose(
            last_end,
            1.0,
            abs_tol=1e-6,
        ):
            raise ValueError(
                f"Scene {scene_number}: "
                "last beat must end at 1.0."
            )

    return response


# ============================================================
# GENERATE VIDEO SCRIPT
# ============================================================

def generate_video_script(
    query: str,
    retrieved_chunks,
    emotion,
):

    # ========================================================
    # RETRIEVED CONTEXT
    # ========================================================

    context_parts = []

    for chunk in retrieved_chunks:

        if isinstance(chunk, dict):
            content = chunk.get(
                "content",
                "",
            )
        else:
            content = str(chunk)

        if content:
            context_parts.append(
                content
            )

    context = "\n\n".join(
        context_parts
    )

    # ========================================================
    # EMOTION
    # ========================================================

    if isinstance(emotion, dict):

        emotion_state = emotion.get(
            "state",
            "Neutral",
        )

    else:

        emotion_state = str(
            emotion
        )

    # ========================================================
    # BUILD PROMPT
    # ========================================================

    prompt = VIDEO_SCRIPT_PROMPT.format(
        query=query,
        emotion=emotion_state,
        context=context,
    )

    # ========================================================
    # DEBUG
    # ========================================================

    print(
        f"Prompt length: {len(prompt)} characters"
    )

    # ========================================================
    # GEMINI
    # ========================================================

    response = llm.invoke(
        prompt
    )

    raw_content = response.content

    # ========================================================
    # DEBUG RAW RESPONSE
    # ========================================================

    with open(
        "raw_script_response.txt",
        "w",
        encoding="utf-8",
    ) as file:

        file.write(
            str(raw_content)
        )

    # ========================================================
    # EXTRACT TEXT
    # ========================================================

    if isinstance(
        raw_content,
        list,
    ):

        text_parts = []

        for item in raw_content:

            if isinstance(
                item,
                dict,
            ):

                text_parts.append(
                    str(
                        item.get(
                            "text",
                            "",
                        )
                    )
                )

            else:

                text_parts.append(
                    str(item)
                )

        raw_content = "".join(
            text_parts
        )

    raw_content = str(
        raw_content
    ).strip()

    # ========================================================
    # REMOVE MARKDOWN FENCES IF GEMINI ADDS THEM
    # ========================================================

    if raw_content.startswith(
        "```"
    ):

        raw_content = raw_content.replace(
            "```json",
            "",
            1,
        )

        raw_content = raw_content.replace(
            "```",
            "",
        )

        raw_content = raw_content.strip()

    # ========================================================
    # PARSE JSON
    # ========================================================

    try:

        result = json.loads(
            raw_content
        )

    except json.JSONDecodeError as exc:

        raise ValueError(
            "Gemini returned invalid JSON. "
            "Check raw_script_response.txt "
            "for the complete response."
        ) from exc

    # ========================================================
    # VALIDATE
    # ========================================================

    validate_video_script(
        result
    )

    return result


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "script_generator.py loaded successfully."
    )
