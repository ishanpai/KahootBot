import asyncio
import re
from openai import OpenAI
import aiohttp
from dotenv import load_dotenv
from kahoot import KahootClient
from kahoot.packets.server.question_start import QuestionStartPacket
from kahoot.packets.impl.respond import RespondPacket
from functools import partial
import os

load_dotenv()

MODEL = "llama3.1:8b"
ENDPOINT = 'http://localhost:11434'
CHAT_URL=f"{ENDPOINT}/v1/chat/completions"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

async def handle_question_dumb(packet: QuestionStartPacket, client: KahootClient):
    question_number: int = packet.game_block_index
    question_text = packet.content["title"]
    choices = packet.content["choices"]
    choices_text = "\n".join([f"<CHOICE_{i}>\n{choice}\n</CHOICE_{i}>" for i, choice in enumerate(choices)])
    prompt = f"""
    <SYSTEM_INSTRUCTIONS>
        You are an expert in AI, AI infra and the AI ecosystem that answers kahoot questions quickly and accurately.
        You will only be asked to answer multiple choice questions.
        Your goal is to select the most appropritate question from the available choices.
        The questions will primarily be about the following companies: Dell, NVIDIA, SUSE, Rafay, Litmus AI, ReN3, ClearML, run:ai, h2o ai, red hat, openshift, Rancher
        The following ideas will be useful:
        - Dell AI Factory
        - Kubernetes
        - open-source
    
        <INPUT_FORMAT>
            <QUESTION>
                The question that we need to answer
            </QUESTION>
            <CHOICE_0>
                The first option
            </CHOICE_0>
            <CHOICE_1>
                The second option
            </CHOICE_1>
            ...
        </INPUT_FORMAT>

        <REQUIRED_RESPONSE_FORMAT>
            Always respond with only the index of the correct choice. Nothing more.
            We do not need any explanations or any reasoning.
        </REQUIRED_RESPONSE_FORMAT>

        <EXAMPLE>
            <INPUT>
                <QUESTION>
                    This is a question
                </QUESTION>
                <CHOICE_0>
                    This is a wrong answer
                </CHOICE_0>
                <CHOICE_1>
                    This is the correct answer
                </CHOICE_1>
                <CHOICE_2>
                    This is a wrong answer
                </CHOICE_2>
                <CHOICE_3>
                    This is a wrong answer
                </CHOICE_3>
            </INPUT>

            <GOOD_OUTPUT>
                1
            <GOOD_OUTPUT>

            <BAD_OUTPUT>
                The answer is 3 because...
            </BAD_OUTPUT>
        </EXAMPLE>

        <FINAL_INSTRUCTIONS>
            Base your answer on the given question and use the good output as an example.
            Never respond with more than a single index as the output.
        </FINAL_INSTRUCTIONS>

        <SPECIAL_INSTRUCTIONS>
            If there is an option like 'None of the above', or 'All of the above',
            the answer is usually that. Unless you have strong reasons otherwise, please use that as a baseline.
        </SPECIAL_INSTRUCTIONS>

    </SYSTEM_INSTRUCTIONS>

    <INPUT>
        <QUESTION>
            {question_text}
        </QUESTION>
        
        {choices_text}
    </INPUT>
        """
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=5,
        )
        answer_text = completion.choices[0].message.content.strip()
        print(f"LLM response: {answer_text}")
        answer_index = extract_index(answer_text)
    except Exception as e:
        print(f"❌ Error getting LLM response: {e}")
        answer_index = 0

    await client.send_packet(RespondPacket(client.game_pin, answer_index, question_number))

def extract_index(text):
    match = re.search(r"\d+", text)
    return int(match.group()) if match else 0

async def amain():
    client: KahootClient = KahootClient()

    client.on("question_start", partial(handle_question_dumb, client=client))

    await client.join_game(672664, "Galaxy20o")
    print(" Sent join request")

if __name__ == "__main__":
    asyncio.run(amain())
