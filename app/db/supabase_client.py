def create_supabase_client(url: str, key: str):
    from supabase import create_client

    return create_client(url, key)
