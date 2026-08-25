from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


def save_test_history(
    user_id: str,
    test_id: str,
    subject: str,
    test_type: str,
    total_score: float,
    total_marks: int,
    percentage: float,
    status: str
) -> dict:
    """
    Save a completed test record to Supabase test_history table.
    Used for dashboard stats and history page.
    """
    try:
        result = supabase.table("test_history").insert({
            "user_id": user_id,
            "test_id": test_id,
            "subject": subject,
            "test_type": test_type,
            "total_score": total_score,
            "total_marks": total_marks,
            "percentage": percentage,
            "status": status
        }).execute()

        print(f"Test history saved for user {user_id}")
        return {"saved": True}

    except Exception as e:
        print(f"Error saving test history: {type(e).__name__}: {e}")
        return {"saved": False, "error": str(e)}


def get_test_history(user_id: str) -> list:
    """
    Get all test history for a student.
    Used for dashboard and history page.
    """
    try:
        result = supabase.table("test_history").select("*").eq(
            "user_id", user_id
        ).order(
            "created_at", desc=True
        ).execute()

        return result.data

    except Exception as e:
        print(f"Error fetching test history: {type(e).__name__}: {e}")
        return []


def get_dashboard_stats(user_id: str) -> dict:
    """
    Get summary stats for the dashboard.
    Returns total tests, average score, best score.
    """
    try:
        history = get_test_history(user_id)

        if not history:
            return {
                "total_tests": 0,
                "average_score": 0,
                "best_score": 0,
                "recent_tests": []
            }

        total_tests = len(history)
        percentages = [h["percentage"] for h in history if h["percentage"]]
        average_score = round(sum(percentages) / len(percentages), 1) if percentages else 0
        best_score = max(percentages) if percentages else 0

        return {
            "total_tests": total_tests,
            "average_score": average_score,
            "best_score": best_score,
            "recent_tests": history[:3]
        }

    except Exception as e:
        print(f"Error getting dashboard stats: {type(e).__name__}: {e}")
        return {
            "total_tests": 0,
            "average_score": 0,
            "best_score": 0,
            "recent_tests": []
        }