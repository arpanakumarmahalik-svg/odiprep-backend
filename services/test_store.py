from services.supabase_service import supabase


def save_test(test_data: dict) -> None:
    supabase.table("tests").upsert({
        "test_id": test_data["test_id"],
        "user_id": test_data.get("user_id", "anonymous"),
        "subject": test_data.get("subject"),
        "test_type": test_data.get("test_type"),
        "file_id": test_data.get("file_id"),
        "status": test_data.get("status", "active"),
        "created_at": test_data.get("created_at"),
        "data": test_data,
    }).execute()


def load_test(test_id: str):
    result = (
        supabase.table("tests")
        .select("data")
        .eq("test_id", test_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]["data"]


def update_test(test_data: dict) -> None:
    save_test(test_data)