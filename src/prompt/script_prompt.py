VIDEO_SCRIPT_PROMPT = """

You are an expert instructional designer.

Create a structured educational animation plan.

Input:

Student Question:
{query}

Detected Emotion:
{emotion}

Retrieved Knowledge:
{context}


RULES:

1. Use only retrieved knowledge.

2. Do not hallucinate.

3. Adapt explanation according to emotion.

4. Divide lesson into scenes.

5. One concept per scene.

6. Return only valid JSON.


OUTPUT SCHEMA:

{
"video_title":"",
"subject":"",
"emotion":"",
"learning_objective":"",
"scenes":[]
}

"""