import pytest

pytest.importorskip('PyQt6')
from PyQt6.QtWidgets import QApplication, QLabel


@pytest.fixture
def app():
    app = QApplication([])
    yield app
    app.quit()


def test_hello_world_gui(app):
    label = QLabel('¡Hola, mundo PyQt6!')
    assert label.text() == '¡Hola, mundo PyQt6!'
