from PyQt6.QtWidgets import QApplication, QLabel

def main():
    app = QApplication([])
    label = QLabel('¡Hola, mundo PyQt6!')
    label.resize(200, 100)
    label.show()
    app.exec()
    

if __name__ == "__main__":
    main()