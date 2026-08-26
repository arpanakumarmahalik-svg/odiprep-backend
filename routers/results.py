from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Annotated, List
import os
import uuid
import json
from datetime import datetime
from services.gemini import (
    read_all_answer_sheets,
    match_answers_to_questions,
    evaluate_answers
)
from services.supabase_service import save_test_history

router = APIRouter()

ANSWER_SHEETS_FOLDER = "answer_sheets"


def run_evaluation(test_data: dict, saved_photos: list) -> dict:
    """
    Full evaluation pipeline:
    Read handwriting → Match answers → Evaluate marks
    """
    test_type = test_data["test_type"]
    sections_with_answers = test_data["sections_with_answers"]

    # Step 1: Get all photo paths
    photo_paths = [p["path"] for p in saved_photos]

    # Step 2: Read all handwriting
    print("Reading handwriting from photos...")
    extracted_text = read_all_answer_sheets(photo_paths)

    if not extracted_text:
        raise Exception("Could not extract text from answer sheet photos.")

    # Step 3: Get questions based on test type
    if test_type == "scetvt":
        section_a_qs = sections_with_answers["section_a"]["questions"]
        section_b_qs = sections_with_answers["section_b"]["questions"]
        section_c_qs = sections_with_answers["section_c"]["questions"]
        all_questions = section_a_qs + section_b_qs + section_c_qs
        total_marks = 70

    elif test_type == "internal":
        all_questions = sections_with_answers["internal"]["questions"]
        total_marks = 20

    else:
        all_questions = []
        total_marks = 0

    # Step 4: Match answers to questions
    print("Matching answers to questions...")
    matched = match_answers_to_questions(extracted_text, all_questions, test_type)

    # Step 5: Evaluate and assign marks
    print("Evaluating answers...")
    evaluation = evaluate_answers(matched, all_questions, test_type)

    # Step 6: Fill in unattempted questions with 0 marks
    evaluated_q_nos = [q["question_no"] for q in evaluation["evaluated_questions"]]

    for q in all_questions:
        if q["question_no"] not in evaluated_q_nos:
            evaluation["evaluated_questions"].append({
                "question_no": q["question_no"],
                "question": q["question"],
                "student_answer": "Not attempted",
                "expected_answer": q.get("expected_answer", ""),
                "marks_awarded": 0,
                "marks_total": q["marks"],
                "feedback": "Not attempted — 0 marks awarded."
            })

    # Step 7: Sort by question number
    evaluation["evaluated_questions"].sort(key=lambda x: x["question_no"])

    # Step 8: Recalculate totals correctly
    total_awarded = sum(q["marks_awarded"] for q in evaluation["evaluated_questions"])
    total_possible = sum(q["marks_total"] for q in evaluation["evaluated_questions"])
    percentage = round(
        (total_awarded / total_possible) * 100, 1
    ) if total_possible > 0 else 0

    evaluation["total_awarded"] = total_awarded
    evaluation["total_possible"] = total_possible
    evaluation["percentage"] = percentage

    # Step 9: Section breakdown for SCETVT
    if test_type == "scetvt":
        section_a_nos = [q["question_no"] for q in section_a_qs]
        section_b_nos = [q["question_no"] for q in section_b_qs]
        section_c_nos = [q["question_no"] for q in section_c_qs]

        def section_score(evaluated, q_nos):
            qs = [q for q in evaluated if q["question_no"] in q_nos]
            return {
                "score": sum(q["marks_awarded"] for q in qs),
                "total": sum(q["marks_total"] for q in qs)
            }

        evaluation["section_breakdown"] = {
            "section_a": section_score(
                evaluation["evaluated_questions"], section_a_nos
            ),
            "section_b": section_score(
                evaluation["evaluated_questions"], section_b_nos
            ),
            "section_c": section_score(
                evaluation["evaluated_questions"], section_c_nos
            )
        }

    evaluation["test_type"] = test_type
    evaluation["subject"] = test_data["subject"]
    evaluation["total_marks"] = total_marks

    return evaluation


@router.post("/submit-test")
async def submit_test(
    test_id: Annotated[str, Form()],
    answer_sheets: Annotated[List[UploadFile], File()]
):
    # Step 1: Check test exists
    test_path = os.path.join("tests", f"{test_id}.json")
    if not os.path.exists(test_path):
        raise HTTPException(
            status_code=404,
            detail=f"Test with ID {test_id} not found."
        )

    # Step 2: Load test data
    with open(test_path, "r") as f:
        test_data = json.load(f)

    # Step 3: Check test is still active
    if test_data["status"] != "active":
        raise HTTPException(
            status_code=400,
            detail=f"This test is already {test_data['status']}."
        )

    # Step 4: Validate image files
    allowed_image_types = [
        "image/jpeg",
        "image/png",
        "image/jpg",
        "image/webp"
    ]
    for sheet in answer_sheets:
        if sheet.content_type not in allowed_image_types:
            raise HTTPException(
                status_code=400,
                detail=f"Only image files allowed. Got: {sheet.content_type}"
            )

    # Step 5: Save uploaded photos
    submission_id = str(uuid.uuid4())
    saved_photos = []
    submission_folder = os.path.join(ANSWER_SHEETS_FOLDER, submission_id)
    os.makedirs(submission_folder, exist_ok=True)

    for index, sheet in enumerate(answer_sheets):
        content = await sheet.read()
        extension = sheet.filename.split(".")[-1].lower()
        photo_filename = f"page_{index + 1}.{extension}"
        photo_path = os.path.join(submission_folder, photo_filename)

        with open(photo_path, "wb") as f:
            f.write(content)

        saved_photos.append({
            "page_number": index + 1,
            "filename": photo_filename,
            "path": photo_path,
            "size_kb": round(len(content) / 1024, 2)
        })

    print(f"Saved {len(saved_photos)} photos for test {test_id}")

    # Step 6: Update status to submitted
    test_data["status"] = "submitted"
    test_data["submitted_at"] = datetime.utcnow().isoformat()
    test_data["submission_id"] = submission_id
    test_data["answer_sheet_photos"] = saved_photos

    with open(test_path, "w") as f:
        json.dump(test_data, f, indent=2)

    # Step 7: Start evaluation automatically
    print("Starting evaluation...")
    try:
        evaluation_result = run_evaluation(test_data, saved_photos)

        # Save results into test file
        test_data["status"] = "evaluated"
        test_data["results"] = evaluation_result
        test_data["evaluated_at"] = datetime.utcnow().isoformat()

        with open(test_path, "w") as f:
            json.dump(test_data, f, indent=2)

        print(f"Evaluation complete! Score: {evaluation_result['total_awarded']}/{evaluation_result['total_possible']}")

        # Step 8: Save to Supabase test history
        save_test_history(
            user_id=test_data.get("user_id", "anonymous"),
            test_id=test_id,
            subject=test_data["subject"],
            test_type=test_data["test_type"],
            total_score=float(evaluation_result["total_awarded"]),
            total_marks=int(evaluation_result["total_possible"]),
            percentage=float(evaluation_result["percentage"]),
            status="evaluated"
        )

    except Exception as e:
        print(f"Evaluation error: {e}")

    return {
        "submission_id": submission_id,
        "test_id": test_id,
        "subject": test_data["subject"],
        "pages_received": len(saved_photos),
        "status": test_data["status"],
        "message": "Answer sheets received and evaluation complete! Call /get-results to see your marks."
    }


@router.get("/get-results/{test_id}")
def get_results(test_id: str):
    test_path = os.path.join("tests", f"{test_id}.json")

    if not os.path.exists(test_path):
        raise HTTPException(
            status_code=404,
            detail=f"Test with ID {test_id} not found."
        )

    with open(test_path, "r") as f:
        test_data = json.load(f)

    if test_data["status"] == "active":
        raise HTTPException(
            status_code=400,
            detail="This test has not been submitted yet."
        )

    if test_data["status"] == "submitted":
        return {
            "test_id": test_id,
            "status": "submitted",
            "message": "Evaluation in progress — check back shortly."
        }

    if test_data["status"] == "evaluated":
        results = test_data["results"]
        return {
            "test_id": test_id,
            "subject": test_data["subject"],
            "test_type": test_data["test_type"],
            "status": "evaluated",
            "submitted_at": test_data.get("submitted_at"),
            "evaluated_at": test_data.get("evaluated_at"),
            "total_score": results["total_awarded"],
            "total_marks": results["total_possible"],
            "percentage": results["percentage"],
            "section_breakdown": results.get("section_breakdown", {}),
            "questions": results["evaluated_questions"]
        }

    raise HTTPException(status_code=400, detail="Unexpected test status.")