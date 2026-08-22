from pydantic import BaseModel
from typing import Optional

class Question(BaseModel):
    question_no: int
    question: str
    marks: int

class QuestionWithAnswer(BaseModel):
    question_no: int
    question: str
    marks: int
    expected_answer: str

class Section(BaseModel):
    title: str
    instruction: str
    questions: list[Question]

class SectionWithAnswers(BaseModel):
    title: str
    instruction: str
    questions: list[QuestionWithAnswer]

class TestPaper(BaseModel):
    test_id: str
    subject: str
    test_type: str
    file_id: str
    total_marks: int
    duration_hours: int
    status: str
    created_at: str
    sections: dict

class GenerateTestRequest(BaseModel):
    file_id: str
    subject: str
    test_type: str = "scetvt"
    user_id: Optional[str] = None  # used for lockout check