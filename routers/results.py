from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Annotated, List
import os
import json
import uuid
from datetime import datetime
from services.gemini import (
    read_all_answer_sheets,
    match_answers_to_questions,
    evaluate_answers
)
from services.supabase_service import save_test_history
from services.test_store import load_test, update_test

router = APIRouter()

ANSWER_SHEETS_FOLDER = "answer_sheets"


def build_internal_questions(groups: list, selections: dict):
    """
    Build the question lists for an Internal exam.
    Returns (all_questions, questions_to_grade).
    - all_questions: one entry per group (4 total)
    - questions_to_grade: only the groups where the student chose (a) or (b)
    """
    all_questions = []
    questions_to_grade = []

    for group in groups:
        group_no = group["question_no"]
        choice = selections.get(str(group_no))

        if choice in ("a", "b"):
            option = group["option_a"] if choice == "a" else group["option_b"]
            item = {
                "question_no": group_no,
                "question": f"({choice}) {option['question']}",
                "expected_answer": option.get("expected_answer", ""),
                "marks": group.get("marks", 5),
            }
            all_questions.append(item)
            questions_to_grade.append(item)
        else:
            all_questions.append({
                "question_no": group_no,
                "question": (
                    f"Not selected. (a) {group['option_a']['question']} "
                    f"OR (b) {group['option_b']['question']}"
                ),
                "expected_answer": "",
                "marks": group.get("marks", 5),
            })

    return all_questions, questions_to_grade


def run_evaluation(test_data: dict, saved_photos: list, selections: dict) -> dict:
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
        questions_to_grade = all_questions
        total_marks = 70

    elif test_type == "internal":
        groups = sections_with_answers["internal"]["questions"]
        all_questions, questions_to_grade = build_internal_questions(
            groups, selections
        )
        total_marks = 20

    else:
        all_questions = []
        questions_to_grade = []
        total_marks = 0

    # Step 4 and 5: Match answers and evaluate (only chosen questions)
    if questions_to_grade:
        print("Matching answers to questions...")
        matched = match_answers_to_questions(
            extracted_text, questions_to_grade, test_type
        )

        print("Evaluating answers...")
        evaluation = evaluate_answers(matched, questions_to_grade, test_type)
    else:
        evaluation = {"evaluated_questions": []}

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
    photos: Annotated[List[UploadFile], File()],
    selections: Annotated[str, Form()] = ""
):
    # Step 1 and 2: Load test data
    test_data = load_test(test_id)
    if not test_data:
        raise HTTPException(
            status_code=404,
            detail=f"Test with ID {test_id} not found."
        )

    # Step 3: Check test is still active
    if test_data["status"] != "active":
        raise HTTPException(
            status_code=400,
            detail=f"This test is already {test_data['status']}."
        )

    # Step 3.5: Validate Internal exam selections
    # Format: {"1": "a", "2": "b", "3": "a", "4": "b"}
    parsed_selections = {}
    if test_data["test_type"] == "internal":
        if selections:
            try:
                parsed_selections = json.loads(selections)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid selections format."
                )

        if not isinstance(parsed_selections, dict):
            raise HTTPException(
                status_code=400,
                detail="Invalid selections format."
            )

        valid_groups = {
            str(g["question_no"])
            for g in test_data["sections_with_answers"]["internal"]["questions"]
        }
        for group_no, choice in parsed_selections.items():
            if group_no not in valid_groups or choice not in ("a", "b"):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid selection. Choose only (a) or (b) for each