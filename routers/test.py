from fastapi import APIRouter, HTTPException
from models.schemas import GenerateTestRequest
from services.file_parser import extract_text
from services.lockout import check_lock_status
from services.exam_builder import (
    generate_section_a, generate_section_b, generate_section_c,
    generate_internal_exam, generate_viva_questions
)
import json
import uuid
import os
from datetime import datetime

router = APIRouter()


def strip_answers(questions):
    return [
        {
            "question_no": q["question_no"],
            "question": q["question"],
            "marks": q["marks"]
        }
        for q in questions
    ]


def strip_internal_answers(questions):
    return [
        {
            "question_no": q["question_no"],
            "option_a": {"question": q["option_a"]["question"]},
            "option_b": {"question": q["option_b"]["question"]},
            "marks": q["marks"]
        }
        for q in questions
    ]


@router.post("/generate-test")
def generate_test(request: GenerateTestRequest):

    # Step 1: Find the uploaded file
    upload_folder = "uploads"
    matched_file = None

    for filename in os.listdir(upload_folder):
        if filename.startswith(request.file_id):
            matched_file = os.path.join(upload_folder, filename)
            break

    if not matched_file:
        raise HTTPException(
            status_code=404,
            detail=f"File with ID {request.file_id} not found."
        )

    # Step 2: Extract text
    notes_text = extract_text(matched_file)
    if not notes_text:
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from the file."
        )
    
        # Step 2.5: Check if subject is locked (SCETVT and Internal only)
    if request.test_type in ["scetvt", "internal"]:
        if request.user_id:
            lock = check_lock_status(
                user_id=request.user_id,
                subject=request.subject
            )
            if lock["locked"]:
                raise HTTPException(
                    status_code=403,
                    detail=f"Subject '{request.subject}' is locked for {lock['time_remaining']} due to an exam violation. Please wait before trying again."
                )

    # Step 3: Generate questions based on test type
    print(f"Generating {request.test_type} exam for: {request.subject}")

    if request.test_type == "scetvt":
        print("Generating Section A...")
        section_a = generate_section_a(notes_text)
        print("Generating Section B...")
        section_b = generate_section_b(notes_text)
        print("Generating Section C...")
        section_c = generate_section_c(notes_text)

        questions_only = {
            "section_a": {
                "title": "Section A",
                "instruction": "Answer all 10 questions. 2 marks each.",
                "questions": strip_answers(section_a)
            },
            "section_b": {
                "title": "Section B",
                "instruction": "Answer any 6 out of 7 questions. 5 marks each.",
                "questions": strip_answers(section_b)
            },
            "section_c": {
                "title": "Section C",
                "instruction": "Answer any 2 out of 4 questions. 10 marks each.",
                "questions": strip_answers(section_c)
            }
        }
        with_answers = {
            "section_a": {"title": "Section A", "questions": section_a},
            "section_b": {"title": "Section B", "questions": section_b},
            "section_c": {"title": "Section C", "questions": section_c}
        }
        total_marks = 70
        duration_hours = 3
        total_q = len(section_a) + len(section_b) + len(section_c)

    elif request.test_type == "internal":
        print("Generating Internal Exam questions...")
        internal_questions = generate_internal_exam(notes_text)

        questions_only = {
            "internal": {
                "title": "Internal Exam",
                "instruction": "Answer any 4 out of 8 questions. For each question, answer either option (a) or (b). 5 marks each.",
                "questions": strip_internal_answers(internal_questions)
            }
        }
        with_answers = {
            "internal": {
                "title": "Internal Exam",
                "questions": internal_questions
            }
        }
        total_marks = 20
        duration_hours = 1
        total_q = len(internal_questions)

    elif request.test_type == "viva":
        print("Generating Viva questions...")
        viva_questions = generate_viva_questions(notes_text)

        questions_only = {
            "viva": {
                "title": "Practical Viva Prep",
                "instruction": "Choose the correct answer for each question.",
                "questions": viva_questions
            }
        }
        with_answers = questions_only
        total_marks = 0
        duration_hours = 0
        total_q = len(viva_questions)

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid test_type. Use: scetvt, internal, or viva"
        )

    # Step 4: Build and save test
    test_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    full_test = {
        "test_id": test_id,
        "subject": request.subject,
        "test_type": request.test_type,
        "file_id": request.file_id,
        "total_marks": total_marks,
        "duration_hours": duration_hours,
        "status": "active",
        "created_at": created_at,
        "sections_with_answers": with_answers,
        "sections": questions_only
    }

    test_path = os.path.join("tests", f"{test_id}.json")
    with open(test_path, "w") as f:
        json.dump(full_test, f, indent=2)

    print(f"Test saved: {test_id}")

    return {
        "test_id": test_id,
        "subject": request.subject,
        "test_type": request.test_type,
        "total_marks": total_marks,
        "duration_hours": duration_hours,
        "status": "active",
        "created_at": created_at,
        "total_questions": total_q,
        "message": "Test generated successfully!"
    }


@router.get("/get-test/{test_id}")
def get_test(test_id: str):
    test_path = os.path.join("tests", f"{test_id}.json")

    if not os.path.exists(test_path):
        raise HTTPException(
            status_code=404,
            detail=f"Test with ID {test_id} not found."
        )

    with open(test_path, "r") as f:
        test_data = json.load(f)

    return {
        "test_id": test_data["test_id"],
        "subject": test_data["subject"],
        "test_type": test_data["test_type"],
        "total_marks": test_data["total_marks"],
        "duration_hours": test_data["duration_hours"],
        "status": test_data["status"],
        "created_at": test_data["created_at"],
        "sections": test_data["sections"]
    }