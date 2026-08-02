import google.generativeai as genai
genai.configure(api_key="YOUR_API_KEY_HERE")

model = genai.GenerativeModel("gemini-3.6-flash")

def generate_video_script(retrieved_chunks):

    context = ""

    for chunk in retrieved_chunks:
        context += chunk["content"] + "\n\n"

    prompt = f"""
You are an expert educational video script writer.

Use ONLY the context below.

Write a natural video narration that sounds like a YouTube educational video.

Instructions:
- Begin with an engaging introduction.
- Explain concepts step by step.
- Use simple English.
- Add smooth transitions between topics.
- Do NOT use Markdown.
- Do NOT use headings such as **Title**, **Length**, or bullet points.
- End with a short conclusion thanking the viewer.
- The script should be around 2 minutes long.

Context:
{context}
"""

    # Send prompt to Gemini here
    response = model.generate_content(prompt)

    script = response.text

    return script
