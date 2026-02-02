import cv2
import pandas as pd
import os
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from pyzbar import pyzbar
from fpdf import FPDF
from datetime import datetime

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDRectangleFlatIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.toast import toast
from plyer import filechooser

# --- CONFIGURACIÓN DE RUTA ---
DIRECTORIO_APP = os.path.dirname(os.path.abspath(__file__))
RUTA_DB = os.path.join(DIRECTORIO_APP, 'inventario.xlsx')

KV = '''
MDScreenManager:
    VentanaVenta:
    VentanaInventario:
    VentanaListaProductos:

<VentanaVenta>:
    name: 'venta'
    MDBoxLayout:
        orientation: 'vertical'
        MDTopAppBar:
            title: "Punto de Venta"
            right_action_items: [["view-list", lambda x: root.ir_a_lista()], ["package-variant", lambda x: root.ir_a_inventario()], ["keyboard", lambda x: root.dialogo_venta_manual()]]
        
        MDBoxLayout:
            orientation: 'vertical'
            padding: dp(5)
            spacing: dp(5)
            
            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: 0.35
                MDCard:
                    elevation: 1
                    Image:
                        id: camera_preview
                MDLabel:
                    id: status_label
                    text: "Escaneando..."
                    halign: "center"
                    size_hint_y: None
                    height: dp(25)

            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: 0.65
                MDLabel:
                    text: "CARRITO (Toca para editar)"
                    font_style: "Caption"
                    size_hint_y: None
                    height: dp(20)
                    halign: "center"
                MDBoxLayout:
                    id: table_container
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(70)
                    spacing: dp(10)
                    padding: [dp(10), dp(5)]
                    MDLabel:
                        id: total_label
                        text: "TOTAL: $0.00"
                        font_style: "H6"
                    MDRaisedButton:
                        text: "VACIAR"
                        md_bg_color: 0.7, 0.1, 0.1, 1
                        on_release: root.confirmar_vaciar()
                    MDRaisedButton:
                        text: "COBRAR"
                        md_bg_color: 0, 0.5, 0.2, 1
                        on_release: root.confirmar_finalizar()

<VentanaInventario>:
    name: 'inventario'
    MDBoxLayout:
        orientation: 'vertical'
        MDTopAppBar:
            title: "Registrar Producto"
            left_action_items: [["arrow-left", lambda x: root.ir_a_venta()]]
        
        MDBoxLayout:
            orientation: 'vertical'
            padding: dp(20)
            spacing: dp(10)
            MDTextField:
                id: inv_codigo
                hint_text: "Código de Barras"
            MDTextField:
                id: inv_nombre
                hint_text: "Nombre"
            MDBoxLayout:
                spacing: dp(10)
                MDTextField:
                    id: inv_precio
                    hint_text: "Precio"
                    input_filter: "float"
                MDTextField:
                    id: inv_stock
                    hint_text: "Stock"
                    input_filter: "int"
            MDRaisedButton:
                text: "GUARDAR"
                pos_hint: {"center_x": .5}
                on_release: root.guardar_producto()
            MDSeparator:
            MDRectangleFlatIconButton:
                icon: "file-excel"
                text: "IMPORTAR EXCEL"
                pos_hint: {"center_x": .5}
                on_release: root.importar_desde_excel()
            Widget:

<VentanaListaProductos>:
    name: 'lista'
    MDBoxLayout:
        orientation: 'vertical'
        MDTopAppBar:
            title: "Inventario Total"
            left_action_items: [["arrow-left", lambda x: root.ir_a_venta()]]
        MDLabel:
            text: "Toca un producto para eliminarlo"
            halign: "center"
            theme_text_color: "Hint"
            size_hint_y: None
            height: dp(30)
        MDBoxLayout:
            id: container_lista
            padding: dp(5)
'''

class VentanaVenta(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.carrito = {}
        self.dialogo = None
        self.capture = cv2.VideoCapture(0)
        Clock.schedule_interval(self.update_video, 1.0/30.0)
        Clock.schedule_once(self.init_table)

    def init_table(self, *args):
        self.table = MDDataTable(
            use_pagination=True,
            rows_num=5,
            column_data=[("Cod", dp(20)), ("Prod", dp(30)), ("$", dp(15)), ("Cant", dp(12))]
        )
        self.table.bind(on_row_press=self.abrir_dialogo_edicion)
        self.ids.table_container.add_widget(self.table)

    def update_video(self, dt):
        ret, frame = self.capture.read()
        if ret:
            barcodes = pyzbar.decode(frame)
            for barcode in barcodes:
                self.procesar_codigo(barcode.data.decode('utf-8'))
            buf = cv2.flip(frame, 0).tobytes()
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.ids.camera_preview.texture = texture

    def procesar_codigo(self, codigo):
        app = MDApp.get_running_app()
        if codigo in app.inventario:
            prod = app.inventario[codigo]
            if codigo in self.carrito: self.carrito[codigo][2] += 1
            else: self.carrito[codigo] = [prod['nombre'], prod['precio'], 1]
            self.actualizar_tabla()
        else:
            self.ids.status_label.text = f"Desconocido: {codigo}"

    def actualizar_tabla(self):
        filas = []
        total = 0
        for cod, d in self.carrito.items():
            filas.append((str(cod), str(d[0][:15]), str(d[1]), str(d[2])))
            total += float(d[1]) * d[2]
        self.table.row_data = filas
        self.ids.total_label.text = f"TOTAL: ${total:.2f}"

    def abrir_dialogo_edicion(self, instance_table, instance_row):
        try:
            row_index = int(instance_row.index / len(instance_table.column_data))
            self.codigo_actual_editando = instance_table.row_data[row_index][0]
            nombre_prod = self.carrito[self.codigo_actual_editando][0]
            
            layout = MDBoxLayout(orientation="horizontal", spacing=dp(10), adaptive_size=True, pos_hint={"center_x": .5})
            btn_menos = MDRaisedButton(text="-", on_release=self.restar_uno)
            self.label_cant_dialogo = MDLabel(text=str(self.carrito[self.codigo_actual_editando][2]), halign="center", width=dp(40))
            btn_mas = MDRaisedButton(text="+", on_release=self.sumar_uno)
            layout.add_widget(btn_menos); layout.add_widget(self.label_cant_dialogo); layout.add_widget(btn_mas)

            self.dialogo = MDDialog(
                title=f"Editar {nombre_prod}",
                type="custom",
                content_cls=MDBoxLayout(layout, height=dp(50), orientation="vertical", size_hint_y=None),
                buttons=[
                    MDFlatButton(text="QUITAR", text_color=(1,0,0,1), on_release=self.eliminar_item_carrito),
                    MDRaisedButton(text="CERRAR", on_release=lambda x: self.dialogo.dismiss())
                ]
            )
            self.dialogo.open()
        except: pass

    def sumar_uno(self, *args):
        self.carrito[self.codigo_actual_editando][2] += 1
        self.label_cant_dialogo.text = str(self.carrito[self.codigo_actual_editando][2])
        self.actualizar_tabla()

    def restar_uno(self, *args):
        if self.carrito[self.codigo_actual_editando][2] > 1:
            self.carrito[self.codigo_actual_editando][2] -= 1
            self.label_cant_dialogo.text = str(self.carrito[self.codigo_actual_editando][2])
            self.actualizar_tabla()

    def eliminar_item_carrito(self, *args):
        if self.codigo_actual_editando in self.carrito: del self.carrito[self.codigo_actual_editando]
        self.actualizar_tabla(); self.dialogo.dismiss()

    def confirmar_vaciar(self):
        self.carrito = {}; self.actualizar_tabla()
        toast("Carrito vacío")

    def confirmar_finalizar(self):
        if not self.carrito: return
        self.dialogo = MDDialog(
            title="Finalizar Venta",
            text="¿Desea generar un ticket PDF?",
            buttons=[
                MDFlatButton(text="SOLO COBRAR", on_release=lambda x: self.finalizar_venta(False)),
                MDRaisedButton(text="TICKET Y COBRAR", on_release=lambda x: self.finalizar_venta(True))
            ]
        )
        self.dialogo.open()

    def finalizar_venta(self, generar_ticket=False):
        app = MDApp.get_running_app()
        total_v = 0
        lineas_ticket = []
        
        for cod, d in self.carrito.items():
            subtotal = float(d[1]) * d[2]
            total_v += subtotal
            lineas_ticket.append(f"{d[0]} x{d[2]} - ${subtotal:.2f}")
            if cod in app.inventario:
                app.inventario[cod]['stock'] -= d[2]
        
        if generar_ticket:
            self.crear_pdf(lineas_ticket, total_v)
            
        app.guardar_db_a_excel()
        self.carrito = {}
        self.actualizar_tabla()
        if self.dialogo: self.dialogo.dismiss()
        toast("Venta finalizada con éxito")

    def crear_pdf(self, lineas, total):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, "TICKET DE VENTA", ln=True, align='C')
            pdf.set_font("Arial", size=12)
            pdf.ln(10)
            for l in lineas:
                pdf.cell(200, 10, l, ln=True)
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, f"TOTAL: ${total:.2f}", ln=True)
            pdf.output(f"ticket_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            toast("Ticket PDF generado")
        except Exception as e:
            toast(f"Error al crear PDF: {e}")

    def ir_a_inventario(self): self.manager.current = 'inventario'
    def ir_a_lista(self): self.manager.current = 'lista'
    def dialogo_venta_manual(self):
        self.campo_m = MDTextField(hint_text="Código")
        self.dialogo = MDDialog(title="Venta Manual", type="custom", 
            content_cls=MDBoxLayout(self.campo_m, height=dp(60), orientation="vertical", size_hint_y=None),
            buttons=[MDRaisedButton(text="AÑADIR", on_release=lambda x: [self.procesar_codigo(self.campo_m.text), self.dialogo.dismiss()])])
        self.dialogo.open()

class VentanaInventario(MDScreen):
    def guardar_producto(self):
        app = MDApp.get_running_app()
        cod = self.ids.inv_codigo.text.strip()
        if cod:
            app.inventario[cod] = {'nombre': self.ids.inv_nombre.text, 'precio': float(self.ids.inv_precio.text or 0), 'stock': int(self.ids.inv_stock.text or 0)}
            app.guardar_db_a_excel()
            toast("Guardado")
        self.ir_a_venta()

    def importar_desde_excel(self):
        filechooser.open_file(on_selection=self._procesar_excel)

    def _procesar_excel(self, seleccion):
        if not seleccion: return
        app = MDApp.get_running_app()
        try:
            df = pd.read_excel(seleccion[0], dtype={'codigo': str})
            app.inventario.update(df.set_index('codigo').to_dict('index'))
            app.guardar_db_a_excel()
            toast("Excel importado")
        except: toast("Error en archivo")

    def ir_a_venta(self): 
        self.manager.current = 'venta'

class VentanaListaProductos(MDScreen):
    def on_enter(self): self.cargar_tabla()

    def cargar_tabla(self):
        self.ids.container_lista.clear_widgets()
        app = MDApp.get_running_app()
        filas = [(str(k), str(v['nombre'])[:15], str(v['precio']), str(v['stock'])) for k, v in app.inventario.items()]
        self.table = MDDataTable(
            use_pagination=True, 
            rows_num=10, 
            check=False,
            column_data=[("Cod", dp(20)), ("Nombre", dp(35)), ("Precio", dp(15)), ("Stk", dp(12))],
            row_data=filas
        )
        self.table.bind(on_row_press=self.confirmar_eliminacion_toque)
        self.ids.container_lista.add_widget(self.table)

    def confirmar_eliminacion_toque(self, instance_table, instance_row):
        try:
            row_index = int(instance_row.index / len(instance_table.column_data))
            self.cod_a_borrar = instance_table.row_data[row_index][0]
            nombre = instance_table.row_data[row_index][1]
            
            self.dialogo_borrar = MDDialog(
                title="¿Eliminar producto?",
                text=f"¿Borrar {nombre}?",
                buttons=[
                    MDFlatButton(text="CANCELAR", on_release=lambda x: self.dialogo_borrar.dismiss()),
                    MDRaisedButton(text="BORRAR", md_bg_color=(1,0,0,1), on_release=self.ejecutar_borrado)
                ]
            )
            self.dialogo_borrar.open()
        except: pass

    def ejecutar_borrado(self, *args):
        app = MDApp.get_running_app()
        if self.cod_a_borrar in app.inventario:
            del app.inventario[self.cod_a_borrar]
            app.guardar_db_a_excel()
            self.cargar_tabla()
            toast("Eliminado")
        self.dialogo_borrar.dismiss()

    def ir_a_venta(self): 
        self.manager.current = 'venta'

class POSApp(MDApp):
    inventario = {}
    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.cargar_excel()
        return Builder.load_string(KV)

    def cargar_excel(self):
        if os.path.exists(RUTA_DB):
            try:
                df = pd.read_excel(RUTA_DB, dtype={'codigo': str})
                self.inventario = df.set_index('codigo').to_dict('index')
            except: self.inventario = {}

    def guardar_db_a_excel(self):
        if self.inventario:
            df = pd.DataFrame.from_dict(self.inventario, orient='index')
            df.index.name = 'codigo'
            df.reset_index(inplace=True)
            df.to_excel(RUTA_DB, index=False)

if __name__ == '__main__':
    POSApp().run()
