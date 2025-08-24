def test_import_main():
    """Basic import smoke test for application entry point."""
    import importlib
    assert importlib.import_module("app.main")
