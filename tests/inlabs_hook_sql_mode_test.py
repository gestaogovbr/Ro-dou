"""Tests for the legacy PostgreSQL INLABS search mode."""


from hooks.inlabs_hook_sql_mode import INLABSSQLModeHook

def test_generate_sql_escapes_apostrophe_in_search_term():
    queries = INLABSSQLModeHook._generate_sql(
        {
            "texto": ["Sant'Anna"],
            "pubdate": ["2026-09-23"],
        }
    )

    assert r"dou_inlabs.unaccent('\ySant''Anna\y')" in queries["select"]
