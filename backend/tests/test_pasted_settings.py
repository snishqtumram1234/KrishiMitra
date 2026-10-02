from app.config import Settings


def test_pasted_key_and_url_lose_stray_whitespace_and_quotes():
    s = Settings(_env_file=None, supabase_service_key=' "abc.def\n ghi" \n', supabase_url=" https://x.supabase.co \n")
    assert s.supabase_service_key == "abc.defghi"
    assert s.supabase_url == "https://x.supabase.co"
