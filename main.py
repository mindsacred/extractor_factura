"""Punto de entrada principal de la aplicación"""
import sys

try:
    from PyQt5.QtWidgets import QApplication
    from gui import FacturaExtractorGUI
except ImportError:
    print("Error: PyQt5 no está instalado.")
    print("Por favor, instala las dependencias ejecutando:")
    print("pip install -r requirements.txt")
    sys.exit(1)


def main():
    """Función principal que inicia la aplicación"""
    app = QApplication(sys.argv)
    window = FacturaExtractorGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

