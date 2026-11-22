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


def _clean_internal_groups(groups) -> list:
    """
    Check and clean the Internal Exam structure.
    Returns exactly 4 groups, each with option_a and option_b (8 questions total).
    Returns [] if the structure is wrong.
    """
    if not isinstance(groups, list) or len(groups) < 4:
        return []

    cleaned = []
    for group in groups[:4]:
        if not isinstance(group, dict):
            return []

        option_a = group.get("option_a")
        option_b = group.get("option_b")

        if not isinstance(option_a, dict) or not isinstance(option_b, dict):
            return []

        question_a = str(option_a.get("question", "")).strip()
        question_b = str(option_b.get("question", "")).strip()

        if not question_a or not question_b:
            return []

        cleaned.append({
            "question_no": len(cleaned) + 1,
            "option_a": {
                "question": question_a,
                "expected_answer": str(option_a.get("expected_answer", "")).strip()
            },
            "option_b": {
                "question": question_b,
                "expected_answer": str(option_b.get("expected_answer", "")).strip()
            },
            "marks": 5
        })

    return cleaned


def generate_internal_exam(notes_text: str) -> list:
    prompt = f"""
You are an expert exam paper setter for SCETVT Odisha polytechnic internal exams.

Using the study notes below, create an Internal Exam with exactly 4 groups.
Each group has exactly 2 alternative questions: question (a) and question (b).
So the paper has exactly 8 questions in total (4 groups x 2 questions).

Rules:
- Create exactly 4 groups. Not more, not less.
- Each group has exactly 2 questions: option_a and option_b
- The student will choose only ONE question from each group
- Both questions in a group must cover a similar topic but be worded differently
- Different groups must cover different parts of the notes
- Each question carries 5 marks
- Questions must come directly from the notes content
- Use simple, clear language for polytechnic students

Return ONLY a valid JSON array with exactly 4 items, in this exact format, nothing else:
[
  {{
    "question_no": 1,
    "option_a": {{
      "question": "Write question 1(a) here?",
      "expected_answer": "Write correct answer for 1(a) here."
    }},
    "option_b": {{
      "question": "Write question 1(b) here?",
      "expected_answer": "Write correct answer for 1(b) here."
    }},
    "marks": 5
  }}
]

Study Notes:
{notes_text[:3000]}
"""
    for attempt in range(1, 4):
        response = ask_gemini(prompt)
        groups = _clean_internal_groups(
            parse_json_response(response, "Internal Exam")
        )
        if groups:
            return groups
        print(f"Internal Exam structure invalid (attempt {attempt}/3). Retrying...")

    return []


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