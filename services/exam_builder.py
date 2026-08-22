from services.gemini import ask_gemini
import json


def generate_section_a(notes_text: str) -> list:
    prompt = f"""
You are an expert exam paper setter for SCETVT Odisha polytechnic exams.

Using the study notes below, generate exactly 10 short-answer questions for Section A.

Rules:
- Each question must be answerable in 2 to 4 sentences
- Each question carries 2 marks
- Questions must come directly from the notes content
- Do not repeat similar questions
- Use simple, clear language for polytechnic students

Return ONLY a valid JSON array in this exact format, nothing else:
[
  {{
    "question_no": 1,
    "question": "Write your question here?",
    "marks": 2,
    "expected_answer": "Write the correct short answer here."
  }}
]

Study Notes:
{notes_text[:3000]}
"""
    response = ask_gemini(prompt)
    return parse_json_response(response, "Section A")


def generate_section_b(notes_text: str) -> list:
    prompt = f"""
You are an expert exam paper setter for SCETVT Odisha polytechnic exams.

Using the study notes below, generate exactly 7 questions for Section B.

Rules:
- Each question requires a medium-length answer (1 paragraph)
- Each question carries 5 marks
- Questions must come directly from the notes content
- Do not repeat questions from Section A
- Use simple, clear language for polytechnic students

Return ONLY a valid JSON array in this exact format, nothing else:
[
  {{
    "question_no": 1,
    "question": "Write your question here?",
    "marks": 5,
    "expected_answer": "Write the correct detailed answer here."
  }}
]

Study Notes:
{notes_text[:3000]}
"""
    response = ask_gemini(prompt)
    return parse_json_response(response, "Section B")


def generate_section_c(notes_text: str) -> list:
    prompt = f"""
You are an expert exam paper setter for SCETVT Odisha polytechnic exams.

Using the study notes below, generate exactly 4 questions for Section C.

Rules:
- Each question requires a long, detailed answer
- Each question carries 10 marks
- Questions must be broad enough to require detailed explanation
- Questions must come directly from the notes content
- Use simple, clear language for polytechnic students

Return ONLY a valid JSON array in this exact format, nothing else:
[
  {{
    "question_no": 1,
    "question": "Write your question here?",
    "marks": 10,
    "expected_answer": "Write the correct long detailed answer here."
  }}
]

Study Notes:
{notes_text[:3000]}
"""
    response = ask_gemini(prompt)
    return parse_json_response(response, "Section C")


def generate_internal_exam(notes_text: str) -> list:
    prompt = f"""
You are an expert exam paper setter for SCETVT Odisha polytechnic internal exams.

Using the study notes below, generate exactly 8 questions for an Internal Exam.

Rules:
- Each question number has TWO choices: option (a) and option (b)
- Both options in a question must cover similar topics but be worded differently
- Each question carries 5 marks
- Student will attempt any 4 questions out of 8
- Questions must come directly from the notes content

Return ONLY a valid JSON array in this exact format, nothing else:
[
  {{
    "question_no": 1,
    "option_a": {{
      "question": "Write option A question here?",
      "expected_answer": "Write correct answer for option A here."
    }},
    "option_b": {{
      "question": "Write option B question here?",
      "expected_answer": "Write correct answer for option B here."
    }},
    "marks": 5
  }}
]

Study Notes:
{notes_text[:3000]}
"""
    response = ask_gemini(prompt)
    return parse_json_response(response, "Internal Exam")


def generate_viva_questions(notes_text: str) -> list:
    prompt = f"""
You are an expert viva examiner for SCETVT Odisha polytechnic practical exams.

Using the study notes below, generate exactly 15 multiple choice viva questions.

Rules:
- Each question must have exactly 4 options (A, B, C, D)
- Only one option must be correct
- Questions should test understanding, not just memory
- Keep questions short and clear
- Questions must come directly from the notes content

Return ONLY a valid JSON array in this exact format, nothing else:
[
  {{
    "question_no": 1,
    "question": "Write your viva question here?",
    "options": {{
      "A": "First option",
      "B": "Second option",
      "C": "Third option",
      "D": "Fourth option"
    }},
    "correct_answer": "A",
    "explanation": "Short explanation of why this answer is correct."
  }}
]

Study Notes:
{notes_text[:3000]}
"""
    response = ask_gemini(prompt)
    return parse_json_response(response, "Viva")


def parse_json_response(response: str, section_name: str) -> list:
    """Clean and parse Gemini's JSON response"""
    response = response.strip()
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]
    response = response.strip()

    try:
        return json.loads(response)
    except Exception as e:
        print(f"Error parsing {section_name} questions: {e}")
        print(f"Raw response: {response}")
        return []