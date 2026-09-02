import os
from pathlib import Path

from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.prompt.manim_prompt import MANIM_GENERATION_PROMPT


load_dotenv(".venv")

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found.")


llm = ChatGroq(
    model="openai/gpt-oss-120b",
    groq_api_key=api_key,
    temperature=0.1,
)


parser = StrOutputParser()


def generate_manim_code(scene_json):

    prompt = ChatPromptTemplate.from_template(
        MANIM_GENERATION_PROMPT
    )

    chain = prompt | llm | parser

    response = chain.invoke(
        {
            "scene_json": scene_json
        }
    )

    return response


def clean_manim_code(code: str):

    code = code.replace("```python", "")
    code = code.replace("```", "")
    code = code.strip()

    if not code.startswith("from manim import"):
        code = "from manim import *\n\n" + code

    return code


def save_manim_file(
    code: str,
    filename="generated_scene.py"
):

    path = Path(filename).resolve()

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(code)

    return str(path)