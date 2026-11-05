import os
from openai import OpenAI  # pip install openai
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
# load_dotenv(Path("D:\\fall26\ml-industry\project\.env"))
# # print(os.getenv("MISTRAL_API_KEY"))

# client = OpenAI(
#     base_url="https://api.mistral.ai/v1",
#     api_key=os.environ["MISTRAL_API_KEY"],
# )
# r = client.chat.completions.create(
#     model="mistral-small-latest",
#     messages=[{"role": "user", "content": "Hello, Mistral!"}],
# )
# print(r.choices[0].message.content)



#GROQ
from groq import Groq

# The client automatically retrieves the key from os.environ.get("GROQ_API_KEY")
client = Groq()

completion = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    temperature=0,
    reasoning_effort="low",

    messages=[
        {
            "role": "user",
            "content": "Explain LLM inference latency in one sentence."
        }
    ],
   
)

print(completion.choices[0].message.content)