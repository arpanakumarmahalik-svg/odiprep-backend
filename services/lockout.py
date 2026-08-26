from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import os

load_dotenv()

# Connect to Supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


def report_violation(user_id: str, subject: str, test_id: str) -> dict:
    """
    Called when a student switches tabs during an exam.
    Locks that subject for 3 hours for that student.
    """
    try:
        locked_until = datetime.now(timezone.utc) + timedelta(hours=3)
        locked_until_str = locked_until.isoformat()

        existing = supabase.table("exam_lockouts").select("*").eq(
            "user_id", user_id
        ).eq(
            "subject", subject
        ).execute()

        if existing.data:
            supabase.table("exam_lockouts").update({
                "locked_until": locked_until_str,
                "test_id": test_id
            }).eq(
                "user_id", user_id
            ).eq(
                "subject", subject
            ).execute()
        else:
            supabase.table("exam_lockouts").insert({
                "user_id": user_id,
                "subject": subject,
                "test_id": test_id,
                "locked_until": locked_until_str
            }).execute()

        return {
            "locked": True,
            "subject": subject,
            "locked_until": locked_until_str,
            "message": f"Subject '{subject}' locked for 3 hours due to exam violation."
        }

    except Exception as e:
        print(f"Lockout error: {type(e).__name__}: {e}")
        return {"locked": False, "error": str(e)}


def check_lock_status(user_id: str, subject: str) -> dict:
    """
    Check if a subject is currently locked for a student.
    """
    try:
        now = datetime.now(timezone.utc)

        result = supabase.table("exam_lockouts").select("*").eq(
            "user_id", user_id
        ).eq(
            "subject", subject
        ).execute()

        if not result.data:
            return {
                "locked": False,
                "subject": subject,
                "message": "Subject is available for testing."
            }

        lockout = result.data[0]
        locked_until = datetime.fromisoformat(lockout["locked_until"])

        if now >= locked_until:
            supabase.table("exam_lockouts").delete().eq(
                "user_id", user_id
            ).eq(
                "subject", subject
            ).execute()

            return {
                "locked": False,
                "subject": subject,
                "message": "Subject is available for testing."
            }

        time_remaining = locked_until - now
        hours = int(time_remaining.total_seconds() // 3600)
        minutes = int((time_remaining.total_seconds() % 3600) // 60)
        seconds = int(time_remaining.total_seconds() % 60)

        return {
            "locked": True,
            "subject": subject,
            "locked_until": lockout["locked_until"],
            "time_remaining": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "message": f"Subject '{subject}' is locked for {hours}h {minutes}m {seconds}s."
        }

    except Exception as e:
        print(f"Lock status error: {type(e).__name__}: {e}")
        return {"locked": False, "error": str(e)}


def get_all_lockouts(user_id: str) -> list:
    """
    Get all current lockouts for a student.
    """
    try:
        now = datetime.now(timezone.utc)

        result = supabase.table("exam_lockouts").select("*").eq(
            "user_id", user_id
        ).execute()

        active_lockouts = []

        for lockout in result.data:
            locked_until = datetime.fromisoformat(lockout["locked_until"])

            if now < locked_until:
                time_remaining = locked_until - now
                hours = int(time_remaining.total_seconds() // 3600)
                minutes = int((time_remaining.total_seconds() % 3600) // 60)
                seconds = int(time_remaining.total_seconds() % 60)

                active_lockouts.append({
                    "subject": lockout["subject"],
                    "locked_until": lockout["locked_until"],
                    "time_remaining": f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                })
            else:
                supabase.table("exam_lockouts").delete().eq(
                    "id", lockout["id"]
                ).execute()

        return active_lockouts

    except Exception as e:
        print(f"Get lockouts error: {type(e).__name__}: {e}")
        return []