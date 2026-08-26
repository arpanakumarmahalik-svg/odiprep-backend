from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.lockout import report_violation, check_lock_status, get_all_lockouts
from services.supabase_service import get_test_history, get_dashboard_stats

router = APIRouter()


class ViolationRequest(BaseModel):
    user_id: str
    subject: str
    test_id: str


@router.post("/report-violation")
def report_exam_violation(request: ViolationRequest):
    """
    Called immediately when a student switches tabs during exam.
    Ends the test and locks the subject for 3 hours.
    """
    result = report_violation(
        user_id=request.user_id,
        subject=request.subject,
        test_id=request.test_id
    )

    if "error" in result:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record violation: {result['error']}"
        )

    return result


@router.get("/lock-status/{user_id}/{subject}")
def get_lock_status(user_id: str, subject: str):
    """
    Check if a subject is locked for a student.
    Frontend calls this before allowing a new test to start.
    """
    return check_lock_status(user_id=user_id, subject=subject)


@router.get("/all-lockouts/{user_id}")
def get_student_lockouts(user_id: str):
    """
    Get all active lockouts for a student.
    Used on dashboard to show locked/available subjects.
    """
    lockouts = get_all_lockouts(user_id=user_id)
    return {
        "user_id": user_id,
        "active_lockouts": lockouts,
        "total_locked": len(lockouts)
    }


@router.get("/test-history/{user_id}")
def fetch_test_history(user_id: str):
    """
    Get all past tests for a student.
    Used on the Test History page.
    """
    history = get_test_history(user_id)
    return {
        "user_id": user_id,
        "total_tests": len(history),
        "history": history
    }


@router.get("/dashboard-stats/{user_id}")
def fetch_dashboard_stats(user_id: str):
    """
    Get dashboard summary stats for a student.
    Used on the Dashboard page.
    """
    return get_dashboard_stats(user_id)