from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import base64
import json

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def ask_gemini(prompt: str) -> str:
    """
    Send a text prompt to Gemini and get a response.
    Used for exam generation.
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"Gemini error: {type(e).__name__}: {e}")
        return ""


def read_handwriting_from_image(image_path: str) -> str:
    """
    Send a photo of handwritten answers to Gemini Vision.
    Gemini reads the handwriting and returns the text.
    """
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        extension = image_path.split(".")[-1].lower()
        mime_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp"
        }
        mime_type = mime_map.get(extension, "image/jpeg")

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(
                    data=base64.b64decode(image_data),
                    mime_type=mime_type
                ),
                types.Part.from_text(
                    text="""This is a photo of a student's handwritten exam answer sheet.

Please read all the handwritten text carefully and extract it exactly as written.

Important instructions:
- Read every word including question numbers the student wrote
- Keep the question numbers (like Q1, Q2, 1., 2. etc.) as they appear
- If a word is unclear, make your best guess
- Return ONLY the extracted text, nothing else
- Do not add any explanation or commentary"""
                )
            ]
        )
        return response.text

    except Exception as e:
        print(f"Gemini Vision error: {type(e).__name__}: {e}")
        return ""


def read_all_answer_sheets(photo_paths: list) -> str:
    """
    Read handwriting from multiple photos and combine into one text.
    """
    all_text = ""

    for index, photo_path in enumerate(photo_paths):
        print(f"Reading page {index + 1} of {len(photo_paths)}...")
        page_text = read_handwriting_from_image(photo_path)

        if page_text:
            all_text += f"\n--- Page {index + 1} ---\n"
            all_text += page_text
            all_text += "\n"

    return all_text.strip()


def match_answers_to_questions(
    extracted_text: str,
    questions: list,
    test_type: str = "scetvt"
) -> list:
    """
    Takes raw extracted handwriting text and matches
    each answer to its correct question number.
    Returns a list of matched answers — one per question.
    """
    try:
        # Build question list for the prompt
        question_list = ""
        for q in questions:
            question_list += f"Q{q['question_no']}. {q['question']}\n"

        prompt = f"""
You are an AI assistant helping evaluate a student's handwritten exam answers.

Below is the raw text extracted from the student's handwritten answer sheets.
Match each answer to its correct question number based on the questions list provided.

Questions in the exam:
{question_list}

Raw extracted text from student's answer sheets:
{extracted_text}

Instructions:
- Match each written answer to its question number
- Each question number should appear ONLY ONCE in your output
- If the same question number appears multiple times in the text, pick the answer that best matches the question content
- If a question has no answer written, set answer as "Not attempted"
- Keep the student's answer exactly as written — do not correct or improve it
- Do NOT duplicate any question number in your output
- Return exactly {len(questions)} items — one per question

Return ONLY a valid JSON array in this exact format, nothing else:
[
  {{
    "question_no": 1,
    "question": "The full question text here",
    "student_answer": "The student's best matching handwritten answer here"
  }}
]
"""
        response = ask_gemini(prompt)

        # Clean response
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        response = response.strip()

        matched = json.loads(response)

        # Remove duplicates — keep only the first occurrence of each question_no
        seen = set()
        unique_matched = []
        for item in matched:
            q_no = item["question_no"]
            if q_no not in seen:
                seen.add(q_no)
                unique_matched.append(item)

        return unique_matched

    except Exception as e:
        print(f"Error matching answers: {type(e).__name__}: {e}")
        return []


def evaluate_answers(
    matched_answers: list,
    questions_with_answers: list,
    test_type: str = "scetvt"
) -> dict:
    """
    Compare student answers against expected answers.
    Assign marks and give feedback for each question.
    """
    try:
        # Build the evaluation data
        evaluation_data = ""

        for matched in matched_answers:
            q_no = matched["question_no"]

            # Find expected answer for this question
            expected = next(
                (q for q in questions_with_answers
                 if q["question_no"] == q_no),
                None
            )

            if expected:
                evaluation_data += f"""
Question {q_no} ({expected['marks']} marks):
Question: {expected['question']}
Expected answer: {expected['expected_answer']}
Student's answer: {matched['student_answer']}
---
"""

        prompt = f"""
You are a strict but fair SCETVT polytechnic exam evaluator.

Evaluate each student answer below against the expected answer.
Assign marks fairly and provide clear feedback explaining why marks were cut (if any).

{evaluation_data}

Rules for marking:
- Award full marks if the answer covers all key points
- Award partial marks if some key points are covered
- Award 0 if the answer is completely wrong or not attempted
- Be strict but fair — partial credit is allowed
- Feedback must clearly state what was missing or wrong
- If student answer is "Not attempted" — award 0 marks and say "Not attempted"

Return ONLY a valid JSON array in this exact format, nothing else:
[
  {{
    "question_no": 1,
    "question": "Full question text",
    "student_answer": "What the student wrote",
    "expected_answer": "The correct answer",
    "marks_awarded": 2,
    "marks_total": 2,
    "feedback": "Correct and complete answer."
  }},
  {{
    "question_no": 2,
    "question": "Full question text",
    "student_answer": "What the student wrote",
    "expected_answer": "The correct answer",
    "marks_awarded": 1,
    "marks_total": 2,
    "feedback": "1 mark cut — only one condition mentioned instead of two."
  }}
]
"""
        response = ask_gemini(prompt)

        # Clean response
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        response = response.strip()

        evaluated = json.loads(response)

        # Calculate scores
        total_awarded = sum(q["marks_awarded"] for q in evaluated)
        total_possible = sum(q["marks_total"] for q in evaluated)
        percentage = round(
            (total_awarded / total_possible) * 100, 1
        ) if total_possible > 0 else 0

        return {
            "evaluated_questions": evaluated,
            "total_awarded": total_awarded,
            "total_possible": total_possible,
            "percentage": percentage
        }

    except Exception as e:
        print(f"Error evaluating answers: {type(e).__name__}: {e}")
        return {
            "evaluated_questions": [],
            "total_awarded": 0,
            "total_possible": 0,
            "percentage": 0
        }