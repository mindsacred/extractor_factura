"""Interfaz gráfica para el extractor de facturas"""
import os
from pathlib import Path
from typing import Optional

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QFileDialog, QMessageBox, QTextEdit,
        QTableWidget, QTableWidgetItem, QTabWidget, QLineEdit, QStatusBar
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False

from models import Factura
from pdf_extractor import PDFExtractor
from excel_generator import ExcelGenerator


class FacturaExtractorGUI(QMainWindow):
    """Interfaz gráfica principal para el extractor de facturas"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Extractor de Facturas PDF")
        self.setGeometry(100, 100, 1000, 750)
        
        self.factura_actual: Optional[Factura] = None
        self.pdf_path: Optional[str] = None
        self.facturas_cargadas: list = []  # Lista de facturas cargadas en memoria
        self.facturas_info: list = []  # Lista con info de cada factura (path, nombre archivo)
        
        # Inicializar componentes
        self.extractor = None
        self.generador = None
        
        try:
            # Intentar cargar configuración desde config.py
            try:
                from config import (RUTA_TESSERACT, IDIOMA_OCR, OCR_PSM, OCR_DPI, OCR_CONFIG,
                                  USAR_AZURE_OPENAI, MODELO_AZURE, AZURE_ENDPOINT, 
                                  AZURE_API_KEY, AZURE_API_VERSION)
                ruta_tesseract = RUTA_TESSERACT
                idioma_ocr = IDIOMA_OCR
                ocr_psm = OCR_PSM
                ocr_dpi = OCR_DPI
                ocr_config = OCR_CONFIG
                usar_azure_openai = USAR_AZURE_OPENAI
                modelo_azure = MODELO_AZURE
                azure_endpoint = AZURE_ENDPOINT
                azure_api_key = AZURE_API_KEY
                azure_api_version = AZURE_API_VERSION
            except ImportError:
                ruta_tesseract = None
                idioma_ocr = 'spa+eng'
                ocr_psm = '6'
                ocr_dpi = 300
                ocr_config = None
                usar_azure_openai = False
                modelo_azure = 'gpt-4o-mini'
                azure_endpoint = None
                azure_api_key = None
                azure_api_version = '2024-02-15-preview'
            
            # Si no está en config, intentar desde variable de entorno
            if not ruta_tesseract:
                ruta_tesseract = os.environ.get('TESSERACT_CMD')
            
            # Si aún no está, intentar rutas comunes
            if not ruta_tesseract:
                rutas_comunes = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                ]
                for ruta in rutas_comunes:
                    if os.path.exists(ruta):
                        ruta_tesseract = ruta
                        break
            
            self.extractor = PDFExtractor(
                ruta_tesseract=ruta_tesseract, 
                idioma_ocr=idioma_ocr,
                ocr_psm=ocr_psm,
                ocr_dpi=ocr_dpi,
                ocr_config=ocr_config,
                usar_azure_openai=usar_azure_openai,
                modelo_azure=modelo_azure,
                azure_endpoint=azure_endpoint,
                azure_api_key=azure_api_key,
                azure_api_version=azure_api_version
            )
            self.generador = ExcelGenerator()
        except ImportError as e:
            QMessageBox.critical(
                self,
                "Error de Dependencias",
                f"Error al cargar dependencias:\n{e}\n\n"
                "Por favor, instala las dependencias ejecutando:\n"
                "pip install -r requirements.txt"
            )
            return
        
        self._crear_interfaz()
    
    def _crear_interfaz(self):
        """Crea los componentes de la interfaz"""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Título
        title_label = QLabel("Extractor de Facturas PDF")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Frame de selección de archivo
        file_layout = QHBoxLayout()
        
        file_label = QLabel("Archivos PDF:")
        file_layout.addWidget(file_label)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("Ningún archivo seleccionado")
        file_layout.addWidget(self.file_path_edit)
        
        btn_select = QPushButton("Seleccionar PDF(s)")
        btn_select.clicked.connect(self._seleccionar_archivos)
        file_layout.addWidget(btn_select)
        
        self.btn_extract = QPushButton("Extraer Datos")
        self.btn_extract.clicked.connect(self._extraer_datos)
        self.btn_extract.setEnabled(False)
        file_layout.addWidget(self.btn_extract)
        
        self.btn_limpiar = QPushButton("Limpiar Lista")
        self.btn_limpiar.clicked.connect(self._limpiar_lista)
        self.btn_limpiar.setEnabled(False)
        file_layout.addWidget(self.btn_limpiar)
        
        main_layout.addLayout(file_layout)
        
        # Lista de facturas cargadas
        facturas_layout = QVBoxLayout()
        facturas_label = QLabel("Facturas cargadas en memoria:")
        facturas_label.setFont(QFont("Arial", 10, QFont.Bold))
        facturas_layout.addWidget(facturas_label)
        
        self.facturas_list = QTableWidget()
        self.facturas_list.setColumnCount(3)
        self.facturas_list.setHorizontalHeaderLabels(["#", "Archivo", "N° Factura"])
        self.facturas_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.facturas_list.setSelectionMode(QTableWidget.SingleSelection)
        self.facturas_list.itemSelectionChanged.connect(self._seleccionar_factura)
        self.facturas_list.setMaximumHeight(150)
        facturas_layout.addWidget(self.facturas_list)
        
        main_layout.addLayout(facturas_layout)
        
        # Notebook para pestañas de previsualización
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Pestaña de texto OCR crudo
        ocr_widget = QWidget()
        ocr_layout = QVBoxLayout(ocr_widget)
        ocr_layout.setContentsMargins(5, 5, 5, 5)
        
        ocr_label = QLabel("Texto extraído por OCR (para depuración):")
        ocr_label.setFont(QFont("Arial", 10, QFont.Bold))
        ocr_layout.addWidget(ocr_label)
        
        self.ocr_text = QTextEdit()
        self.ocr_text.setReadOnly(True)
        self.ocr_text.setFont(QFont("Consolas", 8))
        ocr_layout.addWidget(self.ocr_text)
        
        self.tabs.addTab(ocr_widget, "Texto OCR")
        
        # Pestaña de cabecera
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        self.header_text = QTextEdit()
        self.header_text.setReadOnly(True)
        self.header_text.setFont(QFont("Consolas", 9))
        header_layout.addWidget(self.header_text)
        
        self.tabs.addTab(header_widget, "Cabecera")
        
        # Pestaña de detalle
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(5, 5, 5, 5)
        
        self.detail_table = QTableWidget()
        columns = ["Código", "Descripción", "Cantidad", "Unidad", "Precio Unit.", "Subtotal", "Total"]
        self.detail_table.setColumnCount(len(columns))
        self.detail_table.setHorizontalHeaderLabels(columns)
        self.detail_table.setAlternatingRowColors(True)
        self.detail_table.setSelectionBehavior(QTableWidget.SelectRows)
        detail_layout.addWidget(self.detail_table)
        
        self.tabs.addTab(detail_widget, "Detalle")
        
        # Frame de botones
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.btn_generate = QPushButton("Generar Excel")
        self.btn_generate.clicked.connect(self._generar_excel)
        self.btn_generate.setEnabled(False)
        button_layout.addWidget(self.btn_generate)
        
        main_layout.addLayout(button_layout)
        
        # Barra de estado
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo")
        
        # Label permanente para mostrar estadísticas de tokens
        self.tokens_label = QLabel("Tokens: 0")
        self.tokens_label.setStyleSheet("color: #0066cc; font-weight: bold; padding: 0 10px;")
        self.status_bar.addPermanentWidget(self.tokens_label)
        
        # Botón para ver estadísticas detalladas
        self.btn_stats = QPushButton("Ver Estadísticas")
        self.btn_stats.clicked.connect(self._mostrar_estadisticas)
        self.btn_stats.setMaximumWidth(120)
        self.status_bar.addPermanentWidget(self.btn_stats)
    
    def _seleccionar_archivos(self):
        """Abre el diálogo para seleccionar uno o varios archivos PDF"""
        archivos, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleccionar Factura(s) PDF",
            "",
            "Archivos PDF (*.pdf);;Todos los archivos (*.*)"
        )
        
        if archivos:
            # Agregar archivos a la lista (evitar duplicados)
            for archivo in archivos:
                if archivo not in [info['path'] for info in self.facturas_info]:
                    self.facturas_info.append({
                        'path': archivo,
                        'nombre': Path(archivo).name
                    })
            
            # Actualizar interfaz
            self._actualizar_lista_facturas()
            self.btn_extract.setEnabled(True)
            self.btn_limpiar.setEnabled(len(self.facturas_info) > 0)
            
            if len(archivos) == 1:
                self.file_path_edit.setText(Path(archivos[0]).name)
                self.status_bar.showMessage(f"Archivo seleccionado: {Path(archivos[0]).name}")
            else:
                self.file_path_edit.setText(f"{len(archivos)} archivos seleccionados")
                self.status_bar.showMessage(f"{len(archivos)} archivos seleccionados")
    
    def _limpiar_lista(self):
        """Limpia la lista de facturas cargadas"""
        respuesta = QMessageBox.question(
            self,
            "Confirmar",
            "¿Desea limpiar todas las facturas cargadas?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if respuesta == QMessageBox.Yes:
            self.facturas_cargadas.clear()
            self.facturas_info.clear()
            self.factura_actual = None
            self.pdf_path = None
            self._actualizar_lista_facturas()
            self._limpiar_vista()
            self.btn_extract.setEnabled(False)
            self.btn_limpiar.setEnabled(False)
            self.btn_generate.setEnabled(False)
            self.file_path_edit.clear()
            # Resetear estadísticas de tokens
            if self.extractor:
                self.extractor.resetear_estadisticas_tokens()
                self._actualizar_estadisticas_tokens()
            self.status_bar.showMessage("Lista limpiada")
    
    def _actualizar_lista_facturas(self):
        """Actualiza la tabla de facturas cargadas"""
        self.facturas_list.setRowCount(len(self.facturas_cargadas))
        
        for idx, factura in enumerate(self.facturas_cargadas):
            # Número de fila
            item_num = QTableWidgetItem(str(idx + 1))
            item_num.setFlags(item_num.flags() & ~Qt.ItemIsEditable)
            self.facturas_list.setItem(idx, 0, item_num)
            
            # Nombre del archivo
            nombre_archivo = self.facturas_info[idx]['nombre'] if idx < len(self.facturas_info) else "N/A"
            item_nombre = QTableWidgetItem(nombre_archivo)
            item_nombre.setFlags(item_nombre.flags() & ~Qt.ItemIsEditable)
            self.facturas_list.setItem(idx, 1, item_nombre)
            
            # Número de factura
            num_factura = factura.cabecera.numero_factura or "N/A"
            item_factura = QTableWidgetItem(str(num_factura))
            item_factura.setFlags(item_factura.flags() & ~Qt.ItemIsEditable)
            self.facturas_list.setItem(idx, 2, item_factura)
        
        # Ajustar columnas
        self.facturas_list.resizeColumnsToContents()
    
    def _seleccionar_factura(self):
        """Selecciona una factura de la lista para visualizarla"""
        fila_seleccionada = self.facturas_list.currentRow()
        if fila_seleccionada >= 0 and fila_seleccionada < len(self.facturas_cargadas):
            self.factura_actual = self.facturas_cargadas[fila_seleccionada]
            self._mostrar_cabecera()
            self._mostrar_detalle()
    
    def _actualizar_estadisticas_tokens(self):
        """Actualiza el label de tokens en la barra de estado"""
        if self.extractor:
            stats = self.extractor.obtener_estadisticas_tokens()
            if stats['llamadas'] > 0:
                self.tokens_label.setText(
                    f"Tokens: {stats['tokens_total']:,} total "
                    f"({stats['tokens_prompt']:,} entrada + {stats['tokens_completion']:,} salida) | "
                    f"Llamadas: {stats['llamadas']}"
                )
            else:
                self.tokens_label.setText("Tokens: 0")
    
    def _obtener_precios_modelo(self, modelo: str) -> tuple:
        """Obtiene los precios por 1K tokens según el modelo"""
        # Precios aproximados por 1M tokens (divididos por 1000 para obtener por 1K)
        # Estos son precios estándar de Azure OpenAI, pueden variar según tu plan
        precios = {
            'gpt-4o-mini': (0.00015, 0.0006),  # $0.15 entrada, $0.60 salida por 1M tokens
            'gpt-4o': (0.0025, 0.01),          # $2.50 entrada, $10.00 salida por 1M tokens
            'gpt-4': (0.03, 0.06),             # $30 entrada, $60 salida por 1M tokens
            'gpt-4-turbo': (0.01, 0.03),       # $10 entrada, $30 salida por 1M tokens
            'gpt-35-turbo': (0.0005, 0.0015),  # $0.50 entrada, $1.50 salida por 1M tokens
        }
        
        # Normalizar nombre del modelo (puede venir como "gpt-4o" o "gpt-4o-2024-08-06")
        modelo_base = modelo.lower().split('-')[0:2]  # Tomar "gpt" y "4o" o "4"
        if len(modelo_base) >= 2:
            if modelo_base[1].startswith('4o'):
                modelo_key = 'gpt-4o'
            elif modelo_base[1].startswith('4'):
                if 'turbo' in modelo.lower():
                    modelo_key = 'gpt-4-turbo'
                else:
                    modelo_key = 'gpt-4'
            elif modelo_base[1].startswith('35'):
                modelo_key = 'gpt-35-turbo'
            else:
                modelo_key = 'gpt-4o-mini'  # Default
        else:
            modelo_key = 'gpt-4o-mini'  # Default
        
        # Obtener precios, usar gpt-4o-mini como fallback
        return precios.get(modelo_key, precios['gpt-4o-mini'])
    
    def _mostrar_estadisticas(self):
        """Muestra un diálogo con estadísticas detalladas de tokens"""
        if not self.extractor:
            QMessageBox.information(self, "Estadísticas", "No hay estadísticas disponibles.")
            return
        
        stats = self.extractor.obtener_estadisticas_tokens()
        
        if stats['llamadas'] == 0:
            QMessageBox.information(
                self,
                "Estadísticas de Tokens",
                "No se han realizado llamadas a Azure OpenAI aún.\n\n"
                "Las estadísticas se mostrarán después de procesar facturas."
            )
            return
        
        # Obtener el modelo configurado
        modelo = self.extractor.modelo_azure if hasattr(self.extractor, 'modelo_azure') else 'gpt-4o-mini'
        
        # Obtener precios según el modelo
        costo_entrada_por_1k, costo_salida_por_1k = self._obtener_precios_modelo(modelo)
        
        # Calcular costos
        costo_entrada = (stats['tokens_prompt'] / 1000) * costo_entrada_por_1k
        costo_salida = (stats['tokens_completion'] / 1000) * costo_salida_por_1k
        costo_total = costo_entrada + costo_salida
        
        mensaje = f"""
ESTADÍSTICAS DE USO DE AZURE OPENAI

Modelo: {modelo}
Llamadas realizadas: {stats['llamadas']}

TOKENS:
  • Entrada (Prompt): {stats['tokens_prompt']:,} tokens
  • Salida (Completion): {stats['tokens_completion']:,} tokens
  • Total: {stats['tokens_total']:,} tokens

PROMEDIO POR LLAMADA:
  • {stats['promedio_por_llamada']:.0f} tokens/llamada

COSTO ESTIMADO ({modelo}):
  • Entrada: ${costo_entrada:.4f}
  • Salida: ${costo_salida:.4f}
  • Total estimado: ${costo_total:.4f}

Nota: Los costos son estimados y pueden variar según tu plan de Azure.
        """
        
        QMessageBox.information(self, "Estadísticas de Tokens", mensaje.strip())
    
    def _limpiar_vista(self):
        """Limpia las vistas de cabecera y detalle"""
        self.header_text.clear()
        self.detail_table.setRowCount(0)
        self.ocr_text.clear()
    
    def _extraer_datos(self):
        """Extrae los datos de todos los PDFs seleccionados"""
        if not self.facturas_info or not self.extractor:
            return
        
        facturas_exitosas = 0
        facturas_fallidas = []
        
        try:
            # Procesar cada archivo
            for idx, info in enumerate(self.facturas_info):
                archivo = info['path']
                nombre = info['nombre']
                
                self.status_bar.showMessage(f"Procesando {idx + 1}/{len(self.facturas_info)}: {nombre}...")
                QApplication.processEvents()
                
                try:
                    # Extraer factura
                    factura = self.extractor.extraer_factura(archivo)
                    
                    # Agregar a la lista de facturas cargadas
                    if idx < len(self.facturas_cargadas):
                        self.facturas_cargadas[idx] = factura
                    else:
                        self.facturas_cargadas.append(factura)
                    
                    facturas_exitosas += 1
                    
                except Exception as e:
                    facturas_fallidas.append(f"{nombre}: {str(e)}")
                    # Agregar factura vacía para mantener el índice
                    if idx >= len(self.facturas_cargadas):
                        from models import Factura
                        self.facturas_cargadas.append(Factura())
            
            # Actualizar lista de facturas
            self._actualizar_lista_facturas()
            
            # Mostrar la primera factura si hay alguna
            if self.facturas_cargadas:
                self.factura_actual = self.facturas_cargadas[0]
                self.facturas_list.selectRow(0)
                self._mostrar_texto_ocr()
                self._mostrar_cabecera()
                self._mostrar_detalle()
            
            # Habilitar botón de generar Excel si hay facturas exitosas
            self.btn_generate.setEnabled(facturas_exitosas > 0)
            
            # Mostrar mensaje de resultado
            mensaje = f"Procesadas {facturas_exitosas} factura(s) correctamente."
            if facturas_fallidas:
                mensaje += f"\n\n{len(facturas_fallidas)} factura(s) fallaron:\n" + "\n".join(facturas_fallidas[:5])
                if len(facturas_fallidas) > 5:
                    mensaje += f"\n... y {len(facturas_fallidas) - 5} más"
            
            self.status_bar.showMessage(f"Procesadas {facturas_exitosas} factura(s)")
            self._actualizar_estadisticas_tokens()
            
            if facturas_fallidas:
                QMessageBox.warning(self, "Proceso completado con errores", mensaje)
            else:
                QMessageBox.information(self, "Éxito", mensaje)
        
        except Exception as e:
            self.status_bar.showMessage("Error al extraer datos")
            QMessageBox.critical(
                self,
                "Error",
                f"Error al extraer datos:\n{str(e)}"
            )
    
    def _mostrar_texto_ocr(self):
        """Muestra el texto crudo extraído por OCR"""
        if not self.extractor:
            return
        
        texto_ocr = self.extractor.obtener_texto_extraido()
        if texto_ocr:
            self.ocr_text.setPlainText(texto_ocr)
        else:
            self.ocr_text.setPlainText("No hay texto OCR disponible")
    
    def _mostrar_cabecera(self):
        """Muestra los datos de la cabecera en el área de texto"""
        if not self.factura_actual:
            return
        
        cabecera = self.factura_actual.cabecera
        datos = cabecera.to_dict()
        
        texto = "INFORMACIÓN DE LA FACTURA\n"
        texto += "=" * 60 + "\n\n"
        
        for campo, valor in datos.items():
            if valor:  # Solo mostrar campos con valor
                texto += f"{campo:.<30} {valor}\n"
        
        self.header_text.setPlainText(texto)
    
    def _mostrar_detalle(self):
        """Muestra los items del detalle en la tabla"""
        if not self.factura_actual:
            return
        
        # Limpiar tabla
        self.detail_table.setRowCount(0)
        
        # Agregar items
        for item in self.factura_actual.detalle:
            row = self.detail_table.rowCount()
            self.detail_table.insertRow(row)
            
            valores = [
                item.codigo or "",
                item.descripcion or "",
                str(item.cantidad) if item.cantidad else "",
                item.unidad_medida or "",
                f"${item.precio_unitario:,.2f}" if item.precio_unitario else "",
                f"${item.subtotal:,.2f}" if item.subtotal else "",
                f"${item.total_item:,.2f}" if item.total_item else ""
            ]
            
            for col, valor in enumerate(valores):
                table_item = QTableWidgetItem(str(valor))
                table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                self.detail_table.setItem(row, col, table_item)
        
        # Ajustar columnas
        self.detail_table.resizeColumnsToContents()
    
    def _generar_excel(self):
        """Genera el archivo Excel con todas las facturas cargadas"""
        if not self.facturas_cargadas or not self.generador:
            return
        
        # Filtrar facturas vacías
        facturas_validas = [f for f in self.facturas_cargadas if f.cabecera.numero_factura]
        
        if not facturas_validas:
            QMessageBox.warning(
                self,
                "Advertencia",
                "No hay facturas válidas para generar el Excel."
            )
            return
        
        # Solicitar ubicación para guardar
        archivo_salida, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Excel",
            "",
            "Archivos Excel (*.xlsx);;Todos los archivos (*.*)"
        )
        
        if not archivo_salida:
            return
        
        # Asegurar extensión .xlsx
        if not archivo_salida.endswith('.xlsx'):
            archivo_salida += '.xlsx'
        
        try:
            self.status_bar.showMessage("Generando archivo Excel...")
            QApplication.processEvents()
            
            # Generar Excel con todas las facturas
            self.generador.generar_excel_multiple(facturas_validas, archivo_salida)
            
            self.status_bar.showMessage(f"Excel generado: {Path(archivo_salida).name}")
            QMessageBox.information(
                self,
                "Éxito",
                f"El archivo Excel se ha generado correctamente con {len(facturas_validas)} factura(s):\n{archivo_salida}"
            )
        
        except Exception as e:
            self.status_bar.showMessage("Error al generar Excel")
            QMessageBox.critical(
                self,
                "Error",
                f"Error al generar el archivo Excel:\n{str(e)}"
            )
