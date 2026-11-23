from streamlit.testing.v1 import AppTest


def test_app_loads():
    at = AppTest.from_file("app/streamlit_app.py")
    at.run()
    assert not at.exception
