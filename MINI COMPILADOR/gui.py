import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import re
import sys
import tempfile
import shutil
import webbrowser

from parser import analizar_tokens
from semantic import analizar_semantico
from traductor import traducir_a_javascript, generar_codigo_intermedio

# Ruta del analizador léxico generado con Flex
if getattr(sys, "frozen", False):
    _carpeta = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    _carpeta = os.path.dirname(os.path.abspath(__file__))
_nombre = "analizador.exe" if os.name == "nt" else "analizador"
RUTA_EJECUTABLE = os.path.join(_carpeta, _nombre)

# Paleta general
COLOR_FONDO = "#f4f6f9"
COLOR_TITULO = "#0d2e4e"
COLOR_ACENTO = "#2791ae"
COLOR_ACENTO_CLARO = "#d6eaf1"
COLOR_TAB = "#e3e9f0"
COLOR_TAB_TEXTO = "#4a5b70"

COLORES_TOKEN = {
    "PALABRA_RESERVADA": "#8e44ad",
    "BOOLEANO": "#c0392b",
    "IDENTIFICADOR": "#2980b9",
    "NUMERO_ENTERO": "#16a085",
    "NUMERO_DECIMAL": "#16a085",
    "CADENA": "#032ea3",
    "OP_RELACIONAL": "#55c02b",
    "OP_LOGICO": "#d35400",
    "OP_ASIGNACION": "#a50c9d",
    "OP_ASIG_COMPUESTA": "#a50c9d",
    "OP_INCREMENTO": "#a50c9d",
    "OP_ARITMETICO": "#5da005",
    "ERROR_LEXICO": "#da3321",
    "PAR_IZQ": "#ddab4d",
    "PAR_DER": "#ddab4d",
    "LLAVE_IZQ": "#ddab4d",
    "LLAVE_DER": "#ddab4d",
    "PUNTO_COMA": "#dd3bac",
    "COMA": "#dd3bac",
    "DOS_PUNTOS": "#dd3bac",
}

COLOR_ERROR = "#c0392b"
COLOR_ADVERTENCIA = "#b9770e"
COLOR_OK = "#1e8449"

# Tema oscuro del visor de JavaScript
JS_FONDO = "#1e2430"
JS_FONDO_CABECERA = "#161b26"
JS_FONDO_NUMEROS = "#181d28"
JS_TEXTO = "#d7dde8"
JS_NUMEROS = "#5c6b82"
JS_COLORES = {
    "js_kw": "#c792ea",       # palabras clave
    "js_bool": "#ff9cac",     # true / false
    "js_builtin": "#82aaff",  # console, Math
    "js_func": "#ffcb6b",     # nombres de función
    "js_cadena": "#c3e88d",
    "js_numero": "#f78c6c",
    "js_comentario": "#6b7a90",
}
JS_KEYWORDS = {
    "function", "let", "const", "if", "else", "for", "while", "do", "switch",
    "case", "default", "break", "continue", "return",
}
_PATRON_JS = re.compile(
    r"(?P<js_comentario>//[^\n]*)"
    r'|(?P<js_cadena>"(?:[^"\\\n]|\\.)*")'
    r"|(?P<js_numero>\b\d+(?:\.\d+)?\b)"
    r"|(?P<palabra>[A-Za-z_]\w*)"
)

CODIGO_EJEMPLO = """// Escriba aquí su programa (o use "Subir Archivo")
const int LIMITE = 5;
int suma = 0;

int cuadrado(int n) {
    return n * n;
}

for (int i = 1; i <= LIMITE; i++) {
    suma += cuadrado(i);
}

if (suma > 50 && suma < 100) {
    print("Suma de cuadrados:", suma);
} else {
    print("Fuera de rango");
}
"""


class AnalizadorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mini Compilador")
        self.root.geometry("980x880")
        self.root.minsize(760, 640)
        self.root.configure(bg=COLOR_FONDO)
        self.codigo_js = ""
        self.aplicar_estilos()
        self.crear_interfaz()

    # Estilos de ttk
    def aplicar_estilos(self):
        estilo = ttk.Style(self.root)
        estilo.configure("Treeview", rowheight=24, font=("Segoe UI", 9))

    # Analizador léxico
    def _ejecutar_flex(self, codigo):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(codigo)
            ruta_tmp = tmp.name
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            resultado = subprocess.run(
                [RUTA_EJECUTABLE, ruta_tmp],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                creationflags=flags,
            )
        finally:
            try:
                os.remove(ruta_tmp)
            except OSError:
                pass

        tokens = []
        for linea in resultado.stdout.splitlines():
            if not linea:
                continue
            # Formato: TIPO|lexema|linea
            tipo, resto = linea.split("|", 1)
            lexema, num_linea = resto.rsplit("|", 1)
            tokens.append((tipo, lexema, int(num_linea)))
        return tokens

    def obtener_tokens(self, codigo):
        if not os.path.exists(RUTA_EJECUTABLE):
            raise FileNotFoundError(
                f"No se encontró {os.path.basename(RUTA_EJECUTABLE)} en la carpeta del programa.\n"
                "Genérelo con: flex lexer.l  y  gcc lex.yy.c -o analizador.exe"
            )
        return self._ejecutar_flex(codigo)

    # Interfaz
    def crear_interfaz(self):
        frame_titulo = tk.Frame(self.root, bg=COLOR_FONDO)
        frame_titulo.pack(fill="x", padx=15, pady=(14, 2))

        tk.Label(
            frame_titulo,
            text="COMPILADOR",
            font=("Segoe UI", 15, "bold"),
            bg=COLOR_FONDO,
            fg=COLOR_TITULO,
        ).pack(anchor="w")
        tk.Frame(self.root, bg=COLOR_ACENTO, height=3).pack(fill="x", padx=15, pady=(4, 10))

        self.frame_error = tk.Frame(
            self.root,
            bg="#fadbd8",
            highlightbackground="#e74c3c",
            highlightthickness=1,
        )
        self.lbl_error_texto = tk.Label(
            self.frame_error,
            text="",
            font=("Segoe UI", 10, "bold"),
            bg="#fadbd8",
            fg="#c0392b",
            anchor="w",
            justify="left",
        )
        self.lbl_error_texto.pack(fill="x", padx=10, pady=8)

        frame_botones = tk.Frame(self.root, bg=COLOR_FONDO)
        frame_botones.pack(fill="x", padx=15, pady=5)

        tk.Button(
            frame_botones,
            text="Subir Archivo",
            command=self.abrir_archivo,
            bg="#e3e9f0",
            fg="#2c3e50",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            frame_botones,
            text="▶  Analizar Código",
            command=self.analizar,
            bg=COLOR_ACENTO,
            fg="white",
            activebackground="#1f7a93",
            activeforeground="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
        ).pack(side="left", padx=8)

        tk.Button(
            frame_botones,
            text="Limpiar",
            command=self.limpiar,
            bg="#eef1f4",
            fg="#7f8c8d",
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
        ).pack(side="left", padx=8)

        self.lbl_estado = tk.Label(
            frame_botones,
            text="Listo para analizar",
            bg=COLOR_FONDO,
            fg="#7f8c8d",
            font=("Segoe UI", 9, "italic"),
        )
        self.lbl_estado.pack(side="right", padx=5)

        self.lbl_editor = tk.Label(
            self.root,
            text="Código Fuente de Entrada",
            bg=COLOR_FONDO,
            font=("Segoe UI", 10, "bold"),
            fg="#34495e",
            anchor="w",
        )
        self.lbl_editor.pack(fill="x", padx=15, pady=(10, 2))

        frame_editor = tk.Frame(self.root, bg="white", bd=1, relief="solid")
        frame_editor.pack(fill="both", expand=True, padx=15, pady=5)

        self.editor = tk.Text(
            frame_editor,
            height=8,
            font=("Consolas", 10),
            wrap="none",
            bd=0,
            padx=5,
            pady=5,
        )
        self.editor.pack(side="left", fill="both", expand=True)
        scroll_editor = ttk.Scrollbar(frame_editor, orient="vertical", command=self.editor.yview)
        scroll_editor.pack(side="right", fill="y")
        self.editor.config(yscrollcommand=scroll_editor.set)
        self.editor.insert("1.0", CODIGO_EJEMPLO)

        tk.Label(
            self.root,
            text="Resultados del Análisis",
            bg=COLOR_FONDO,
            font=("Segoe UI", 10, "bold"),
            fg="#34495e",
            anchor="w",
        ).pack(fill="x", padx=15, pady=(10, 0))

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=(0, 8))

        frame_tokens = tk.Frame(self.notebook, bg="white")
        frame_sintactico = tk.Frame(self.notebook, bg="white")
        frame_semantico = tk.Frame(self.notebook, bg="white")
        frame_intermedio = tk.Frame(self.notebook, bg="white")
        frame_traductor = tk.Frame(self.notebook, bg=JS_FONDO)
        self.notebook.add(frame_tokens, text="Tokens")
        self.notebook.add(frame_sintactico, text="Sintáctico")
        self.notebook.add(frame_semantico, text="Semántico")
        self.notebook.add(frame_intermedio, text="Código Intermedio")
        self.notebook.add(frame_traductor, text="Traductor")

        columnas = ("tipo", "lexema", "linea")
        self.tabla = ttk.Treeview(frame_tokens, columns=columnas, show="headings", height=8)
        self.tabla.heading("tipo", text="Tipo de Token")
        self.tabla.heading("lexema", text="Lexema")
        self.tabla.heading("linea", text="Línea")
        self.tabla.column("tipo", width=260, anchor="w")
        self.tabla.column("lexema", width=260, anchor="w")
        self.tabla.column("linea", width=80, anchor="center")
        self.tabla.pack(side="left", fill="both", expand=True)

        scroll_tabla = ttk.Scrollbar(frame_tokens, orient="vertical", command=self.tabla.yview)
        self.tabla.config(yscrollcommand=scroll_tabla.set)
        scroll_tabla.pack(side="right", fill="y")

        for tipo, color in COLORES_TOKEN.items():
            self.tabla.tag_configure(tipo, foreground=color, font=("Consolas", 10, "bold"))

        self.txt_sintactico = tk.Text(
            frame_sintactico,
            font=("Consolas", 11),
            wrap="word",
            bd=0,
            padx=14,
            pady=14,
            state="disabled",
        )
        self.txt_sintactico.pack(fill="both", expand=True)
        self.txt_sintactico.tag_configure("ok", foreground=COLOR_OK, font=("Consolas", 11, "bold"))
        self.txt_sintactico.tag_configure("error", foreground=COLOR_ERROR, font=("Consolas", 11, "bold"))
        self.mostrar_sintactico("Aún no se ha realizado el análisis sintáctico.", "normal")

        self.crear_tab_semantico(frame_semantico)
        self.crear_tab_intermedio(frame_intermedio)
        self.crear_tab_traductor(frame_traductor)
        self.crear_barra_acciones()

        self.editor.tag_configure("linea_sel", background="#fdebd0")

    def crear_tab_semantico(self, frame):
        # Texto para mensajes (estado inicial o fase previa no superada)
        self.txt_semantico = tk.Text(
            frame,
            font=("Consolas", 11),
            wrap="word",
            bd=0,
            padx=14,
            pady=14,
            state="disabled",
        )
        self.txt_semantico.tag_configure("ok", foreground=COLOR_OK, font=("Consolas", 11, "bold"))
        self.txt_semantico.tag_configure("error", foreground=COLOR_ERROR, font=("Consolas", 11, "bold"))

        # Panel de resultados: resumen + tabla de símbolos + diagnósticos
        self.panel_semantico = tk.Frame(frame, bg="white")

        self.lbl_resumen = tk.Label(
            self.panel_semantico,
            text="",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            padx=12,
            pady=8,
        )
        self.lbl_resumen.pack(fill="x")

        paned = ttk.PanedWindow(self.panel_semantico, orient="vertical")
        paned.pack(fill="both", expand=True, pady=(6, 0))

        # Tabla de símbolos
        frame_simbolos = tk.Frame(paned, bg="white")
        tk.Label(
            frame_simbolos,
            text="Tabla de símbolos",
            font=("Segoe UI", 9, "bold"),
            bg="white",
            fg="#34495e",
            anchor="w",
        ).pack(fill="x", padx=4)
        cols_sim = ("nombre", "clase", "tipo", "ambito", "linea", "inicializada", "usada")
        self.tabla_simbolos = ttk.Treeview(
            frame_simbolos, columns=cols_sim, show="headings", height=5
        )
        encabezados = {
            "nombre": ("Nombre", 140, "w"),
            "clase": ("Clase", 90, "center"),
            "tipo": ("Tipo", 60, "center"),
            "ambito": ("Ámbito", 170, "w"),
            "linea": ("Línea", 55, "center"),
            "inicializada": ("Inicializada", 85, "center"),
            "usada": ("Usada", 60, "center"),
        }
        for col, (texto, ancho, ancla) in encabezados.items():
            self.tabla_simbolos.heading(col, text=texto)
            self.tabla_simbolos.column(col, width=ancho, anchor=ancla)
        sc1 = ttk.Scrollbar(frame_simbolos, orient="vertical", command=self.tabla_simbolos.yview)
        self.tabla_simbolos.config(yscrollcommand=sc1.set)
        self.tabla_simbolos.pack(side="left", fill="both", expand=True)
        sc1.pack(side="right", fill="y")
        self.tabla_simbolos.tag_configure("sin_uso", foreground=COLOR_ADVERTENCIA)
        paned.add(frame_simbolos, weight=1)

        # Diagnósticos
        frame_diag = tk.Frame(paned, bg="white")
        tk.Label(
            frame_diag,
            text="Errores y advertencias (clic para ubicar la línea en el editor)",
            font=("Segoe UI", 9, "bold"),
            bg="white",
            fg="#34495e",
            anchor="w",
        ).pack(fill="x", padx=4)
        cols_diag = ("severidad", "linea", "mensaje")
        self.tabla_diag = ttk.Treeview(
            frame_diag, columns=cols_diag, show="headings", height=5
        )
        self.tabla_diag.heading("severidad", text="Severidad")
        self.tabla_diag.heading("linea", text="Línea")
        self.tabla_diag.heading("mensaje", text="Descripción")
        self.tabla_diag.column("severidad", width=110, anchor="w")
        self.tabla_diag.column("linea", width=60, anchor="center")
        self.tabla_diag.column("mensaje", width=560, anchor="w")
        sc2 = ttk.Scrollbar(frame_diag, orient="vertical", command=self.tabla_diag.yview)
        self.tabla_diag.config(yscrollcommand=sc2.set)
        self.tabla_diag.pack(side="left", fill="both", expand=True)
        sc2.pack(side="right", fill="y")
        self.tabla_diag.tag_configure("ERROR", foreground=COLOR_ERROR, font=("Consolas", 10, "bold"))
        self.tabla_diag.tag_configure("ADVERTENCIA", foreground=COLOR_ADVERTENCIA, font=("Consolas", 10))
        self.tabla_diag.bind("<<TreeviewSelect>>", self.ubicar_linea)
        paned.add(frame_diag, weight=1)

        self.mostrar_semantico_mensaje("Aún no se ha realizado el análisis semántico.", "normal")

    def mostrar_semantico_mensaje(self, texto, tag):
        self.panel_semantico.pack_forget()
        self.txt_semantico.pack(fill="both", expand=True)
        self.txt_semantico.config(state="normal")
        self.txt_semantico.delete("1.0", "end")
        self.txt_semantico.insert("1.0", texto, tag)
        self.txt_semantico.config(state="disabled")

    def mostrar_semantico_resultado(self, resultado):
        self.txt_semantico.pack_forget()
        self.panel_semantico.pack(fill="both", expand=True)

        errores = resultado.errores
        advertencias = resultado.advertencias
        txt_err = f"{errores} error" if errores == 1 else f"{errores} errores"
        txt_adv = (
            f"{advertencias} advertencia" if advertencias == 1 else f"{advertencias} advertencias"
        )
        if resultado.correcto:
            self.lbl_resumen.config(
                text=f"Análisis semántico correcto: {txt_err}, {txt_adv}.",
                bg="#d5f5e3",
                fg=COLOR_OK,
            )
        else:
            self.lbl_resumen.config(
                text=f"Análisis semántico con errores: {txt_err}, {txt_adv}.",
                bg="#fadbd8",
                fg=COLOR_ERROR,
            )

        for fila in self.tabla_simbolos.get_children():
            self.tabla_simbolos.delete(fila)
        for s in resultado.simbolos:
            self.tabla_simbolos.insert(
                "",
                "end",
                values=(
                    "    " * s.nivel + s.nombre,
                    s.clase,
                    s.tipo,
                    s.ambito,
                    s.linea,
                    "Sí" if s.inicializada else "No",
                    "Sí" if s.usada else "No",
                ),
                tags=(("" if s.usada else "sin_uso"),),
            )

        for fila in self.tabla_diag.get_children():
            self.tabla_diag.delete(fila)
        for d in resultado.diagnosticos:
            self.tabla_diag.insert(
                "",
                "end",
                values=(d.severidad.capitalize(), d.linea, d.mensaje),
                tags=(d.severidad,),
            )

    def crear_tab_intermedio(self, frame):
        self.txt_intermedio_msg = tk.Text(
            frame,
            font=("Consolas", 11),
            wrap="word",
            bd=0,
            padx=14,
            pady=14,
            state="disabled",
        )
        self.txt_intermedio_msg.tag_configure("ok", foreground=COLOR_OK, font=("Consolas", 11, "bold"))
        self.txt_intermedio_msg.tag_configure("error", foreground=COLOR_ERROR, font=("Consolas", 11, "bold"))

        self.panel_intermedio = tk.Frame(frame, bg="white")

        tk.Label(
            self.panel_intermedio,
            text="Código de tres direcciones (cuádruplos)",
            font=("Segoe UI", 9, "bold"),
            bg="white",
            fg="#34495e",
            anchor="w",
        ).pack(fill="x", padx=8, pady=(8, 4))

        cols = ("n", "op", "arg1", "arg2", "res", "inst")
        self.tabla_ci = ttk.Treeview(self.panel_intermedio, columns=cols, show="headings")
        encabezados_ci = {
            "n": ("#", 45, "center"),
            "op": ("Operador", 110, "center"),
            "arg1": ("Arg 1", 140, "w"),
            "arg2": ("Arg 2", 140, "w"),
            "res": ("Resultado", 140, "w"),
            "inst": ("Instrucción", 360, "w"),
        }
        for col, (texto, ancho, ancla) in encabezados_ci.items():
            self.tabla_ci.heading(col, text=texto)
            self.tabla_ci.column(col, width=ancho, anchor=ancla)
        sc_ci = ttk.Scrollbar(self.panel_intermedio, orient="vertical", command=self.tabla_ci.yview)
        self.tabla_ci.config(yscrollcommand=sc_ci.set)
        self.tabla_ci.pack(side="left", fill="both", expand=True)
        sc_ci.pack(side="right", fill="y")

        self.mostrar_intermedio_mensaje("Aún no se ha generado el código intermedio.", "normal")

    def mostrar_intermedio_mensaje(self, texto, tag):
        self.panel_intermedio.pack_forget()
        self.txt_intermedio_msg.pack(fill="both", expand=True)
        self.txt_intermedio_msg.config(state="normal")
        self.txt_intermedio_msg.delete("1.0", "end")
        self.txt_intermedio_msg.insert("1.0", texto, tag)
        self.txt_intermedio_msg.config(state="disabled")

    def mostrar_intermedio_resultado(self, arbol):
        try:
            cuadruplos = generar_codigo_intermedio(arbol)
        except Exception as e:
            messagebox.showerror("Error del generador", str(e))
            self.mostrar_intermedio_mensaje(f"Error interno del generador:\n{e}", "error")
            return
        self.txt_intermedio_msg.pack_forget()
        self.panel_intermedio.pack(fill="both", expand=True)
        for fila in self.tabla_ci.get_children():
            self.tabla_ci.delete(fila)
        for i, c in enumerate(cuadruplos, start=1):
            self.tabla_ci.insert(
                "",
                "end",
                values=(i, c.op, c.arg1, c.arg2, c.resultado, c.texto()),
            )

    def crear_tab_traductor(self, frame):
        # Texto para mensajes (estado inicial o fase previa no superada)
        self.txt_traductor_msg = tk.Text(
            frame,
            font=("Consolas", 11),
            wrap="word",
            bd=0,
            padx=14,
            pady=14,
            state="disabled",
            bg="white",
        )
        self.txt_traductor_msg.tag_configure("ok", foreground=COLOR_OK, font=("Consolas", 11, "bold"))
        self.txt_traductor_msg.tag_configure("error", foreground=COLOR_ERROR, font=("Consolas", 11, "bold"))

        # Panel del código traducido
        self.panel_traductor = tk.Frame(frame, bg=JS_FONDO)

        # Cabecera
        cabecera = tk.Frame(self.panel_traductor, bg=JS_FONDO_CABECERA)
        cabecera.pack(fill="x")
        tk.Label(
            cabecera,
            text=" JS ",
            font=("Consolas", 11, "bold"),
            bg="#f7df1e",
            fg="#1b1b1b",
        ).pack(side="left", padx=(12, 8), pady=10)
        tk.Label(
            cabecera,
            text="JavaScript",
            font=("Segoe UI", 11, "bold"),
            bg=JS_FONDO_CABECERA,
            fg="white",
        ).pack(side="left")
        self.lbl_trad_resumen = tk.Label(
            cabecera,
            text="",
            font=("Segoe UI", 9),
            bg=JS_FONDO_CABECERA,
            fg="#8fa3bd",
        )
        self.lbl_trad_resumen.pack(side="left", padx=14)

        # Barra horizontal
        self.sb_horizontal = ttk.Scrollbar(self.panel_traductor, orient="horizontal")
        self.sb_horizontal.pack(side="bottom", fill="x")

        # Cuerpo: numeración de líneas + código
        cuerpo = tk.Frame(self.panel_traductor, bg=JS_FONDO)
        cuerpo.pack(fill="both", expand=True)

        fuente = ("Consolas", 11)
        self.gutter = tk.Text(
            cuerpo,
            width=4,
            font=fuente,
            bd=0,
            padx=8,
            pady=10,
            wrap="none",
            bg=JS_FONDO_NUMEROS,
            fg=JS_NUMEROS,
            state="disabled",
            cursor="arrow",
            takefocus=0,
            highlightthickness=0,
        )
        self.gutter.tag_configure("derecha", justify="right")
        self.gutter.pack(side="left", fill="y")
        for evento in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.gutter.bind(evento, lambda e: "break")

        self.txt_traduccion = tk.Text(
            cuerpo,
            font=fuente,
            wrap="none",
            bd=0,
            padx=12,
            pady=10,
            state="disabled",
            bg=JS_FONDO,
            fg=JS_TEXTO,
            insertbackground="white",
            selectbackground="#3b4a63",
            selectforeground="white",
            highlightthickness=0,
        )
        for tag, color in JS_COLORES.items():
            self.txt_traduccion.tag_configure(tag, foreground=color)
        self.txt_traduccion.tag_configure("js_comentario", foreground=JS_COLORES["js_comentario"], font=("Consolas", 11, "italic"))

        self.sb_vertical = ttk.Scrollbar(cuerpo, orient="vertical", command=self._desplazar_codigo)
        self.sb_horizontal.config(command=self.txt_traduccion.xview)
        self.txt_traduccion.config(
            yscrollcommand=self._al_desplazar_codigo,
            xscrollcommand=self.sb_horizontal.set,
        )
        self.sb_vertical.pack(side="right", fill="y")
        self.txt_traduccion.pack(side="left", fill="both", expand=True)

        self.mostrar_traductor_mensaje("Aún no se ha ejecutado el traductor.", "normal")

    def crear_barra_acciones(self):
        barra = tk.Frame(self.root, bg=COLOR_FONDO)
        barra.pack(fill="x", padx=15, pady=(0, 15))

        self.btn_copiar = tk.Button(
            barra,
            text="Copiar",
            command=self.copiar_traduccion,
            bg=COLOR_ACENTO,
            fg="white",
            activebackground="#1f7a93",
            activeforeground="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
        )
        self.btn_copiar.pack(side="left", padx=(0, 8))

        self.btn_guardar = tk.Button(
            barra,
            text="Guardar",
            command=self.guardar_traduccion,
            bg="#e3e9f0",
            fg="#2c3e50",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
        )
        self.btn_guardar.pack(side="left", padx=8)

        self.btn_ejecutar = tk.Button(
            barra,
            text="Ejecutar",
            command=self.ejecutar_javascript,
            bg="#e3e9f0",
            fg="#2c3e50",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
        )
        self.btn_ejecutar.pack(side="left", padx=8)

        self.btn_html = tk.Button(
            barra,
            text="Abrir HTML",
            command=self.abrir_html,
            bg="#e3e9f0",
            fg="#2c3e50",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
        )
        self.btn_html.pack(side="left", padx=8)

        self._activar_acciones(False)

    def _activar_acciones(self, activo):
        if not hasattr(self, "btn_copiar"):
            return
        estado = "normal" if activo else "disabled"
        for btn in (self.btn_copiar, self.btn_guardar, self.btn_ejecutar, self.btn_html):
            btn.config(state=estado)

    def _desplazar_codigo(self, *args):
        self.txt_traduccion.yview(*args)
        self.gutter.yview(*args)

    def _al_desplazar_codigo(self, primero, ultimo):
        self.sb_vertical.set(primero, ultimo)
        self.gutter.yview_moveto(primero)

    def mostrar_traductor_mensaje(self, texto, tag):
        self.codigo_js = ""
        self._activar_acciones(False)
        self.panel_traductor.pack_forget()
        self.txt_traductor_msg.pack(fill="both", expand=True)
        self.txt_traductor_msg.config(state="normal")
        self.txt_traductor_msg.delete("1.0", "end")
        self.txt_traductor_msg.insert("1.0", texto, tag)
        self.txt_traductor_msg.config(state="disabled")

    def mostrar_traductor_resultado(self, arbol, advertencias):
        try:
            codigo = traducir_a_javascript(arbol)
        except Exception as e:  # no debería ocurrir
            messagebox.showerror("Error del traductor", str(e))
            self.mostrar_traductor_mensaje(f"Error interno del traductor:\n{e}", "error")
            return
        self.codigo_js = codigo
        self._activar_acciones(True)

        self.txt_traductor_msg.pack_forget()
        self.panel_traductor.pack(fill="both", expand=True)

        # Código
        self.txt_traduccion.config(state="normal")
        self.txt_traduccion.delete("1.0", "end")
        self.txt_traduccion.insert("1.0", codigo.rstrip("\n"))
        self.resaltar_js(codigo.rstrip("\n"))
        self.txt_traduccion.config(state="disabled")

        # Numeración de líneas
        n = codigo.rstrip("\n").count("\n") + 1
        self.gutter.config(state="normal")
        self.gutter.delete("1.0", "end")
        self.gutter.insert("1.0", "\n".join(str(i) for i in range(1, n + 1)), "derecha")
        self.gutter.config(state="disabled")
        self.txt_traduccion.yview_moveto(0)
        self.gutter.yview_moveto(0)

        nota = ""
        if advertencias:
            nota = f"  ·  {advertencias} advertencia(s) semántica(s)"
        self.lbl_trad_resumen.config(text=f"Traducción generada: {n} líneas{nota}")

    def resaltar_js(self, codigo):
        for tag in JS_COLORES:
            self.txt_traduccion.tag_remove(tag, "1.0", "end")
        for numero, linea in enumerate(codigo.split("\n"), start=1):
            for m in _PATRON_JS.finditer(linea):
                tag = m.lastgroup
                if tag == "palabra":
                    palabra = m.group()
                    if palabra in JS_KEYWORDS:
                        tag = "js_kw"
                    elif palabra in ("true", "false"):
                        tag = "js_bool"
                    elif palabra in ("console", "Math"):
                        tag = "js_builtin"
                    elif linea[: m.start()].rstrip().endswith("function") or linea[m.end(): m.end() + 1] == "(":
                        tag = "js_func"
                    else:
                        continue
                self.txt_traduccion.tag_add(tag, f"{numero}.{m.start()}", f"{numero}.{m.end()}")

    def copiar_traduccion(self):
        if not self.codigo_js:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.codigo_js)
        self.lbl_estado.config(text="Código JavaScript copiado al portapapeles.", fg="#27ae60")

    def guardar_traduccion(self):
        if not self.codigo_js:
            messagebox.showinfo("Traductor", "Primero debe analizar un programa sin errores.")
            return
        ruta = filedialog.asksaveasfilename(
            defaultextension=".js",
            initialfile="programa.js",
            filetypes=[("JavaScript", "*.js"), ("Todos los archivos", "*.*")],
        )
        if ruta:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(self.codigo_js)
            self.lbl_estado.config(text=f"Guardado: {os.path.basename(ruta)}", fg="#27ae60")

    def ejecutar_javascript(self):
        if not self.codigo_js:
            messagebox.showinfo("Ejecutar", "Primero debe analizar un programa sin errores.")
            return
        node = shutil.which("node")
        if not node:
            messagebox.showerror(
                "Ejecutar",
                "No se encontró Node.js. Instálelo y compruebe que 'node' esté en el PATH.",
            )
            return
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(self.codigo_js)
            ruta = tmp.name
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            resultado = subprocess.run(
                [node, ruta],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
                creationflags=flags,
            )
        except subprocess.TimeoutExpired:
            messagebox.showerror("Ejecutar", "El programa tardó demasiado y se detuvo.")
            return
        finally:
            try:
                os.remove(ruta)
            except OSError:
                pass
        salida = (resultado.stdout or "") + (resultado.stderr or "")
        if not salida.strip():
            salida = "(sin salida)"
        ventana = tk.Toplevel(self.root)
        ventana.title("Salida de Node.js")
        ventana.geometry("640x360")
        ventana.configure(bg="white")
        txt = tk.Text(ventana, font=("Consolas", 11), wrap="word", bd=0, padx=12, pady=12)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", salida)
        txt.config(state="disabled")
        self.lbl_estado.config(text="Programa ejecutado con Node.js.", fg="#27ae60")

    def abrir_html(self):
        if not self.codigo_js:
            messagebox.showinfo("Abrir HTML", "Primero debe analizar un programa sin errores.")
            return
        html = (
            "<!DOCTYPE html>\n<html>\n<head>\n"
            '<meta charset="utf-8">\n<title>Mini Compilador</title>\n'
            "<style>body{font-family:Consolas,monospace;background:#1e2430;color:#d7dde8;"
            "padding:24px} pre{white-space:pre-wrap}</style>\n</head>\n<body>\n"
            '<pre id="salida"></pre>\n<script>\n'
            "const _s = document.getElementById('salida');\n"
            "console.log = function() {\n"
            "  _s.textContent += Array.from(arguments).join(' ') + '\\n';\n"
            "};\n"
            + self.codigo_js
            + "\n</script>\n</body>\n</html>\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(html)
            ruta = tmp.name
        if os.name == "nt":
            os.startfile(ruta)
        else:
            webbrowser.open("file://" + ruta)
        self.lbl_estado.config(text="Código abierto en el navegador.", fg="#27ae60")

    def ubicar_linea(self, _evento=None):
        seleccion = self.tabla_diag.selection()
        if not seleccion:
            return
        linea = int(self.tabla_diag.item(seleccion[0], "values")[1])
        self.editor.tag_remove("linea_sel", "1.0", "end")
        self.editor.tag_add("linea_sel", f"{linea}.0", f"{linea}.end+1c")
        self.editor.see(f"{linea}.0")

    def mostrar_sintactico(self, texto, tag):
        self.txt_sintactico.config(state="normal")
        self.txt_sintactico.delete("1.0", "end")
        self.txt_sintactico.insert("1.0", texto, tag)
        self.txt_sintactico.config(state="disabled")

    def abrir_archivo(self):
        ruta = filedialog.askopenfilename(
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if ruta:
            with open(ruta, "r", encoding="utf-8") as f:
                self.editor.delete("1.0", "end")
                self.editor.insert("1.0", f.read())
            self.lbl_estado.config(text=f"Cargado: {os.path.basename(ruta)}", fg="#27ae60")

    def limpiar(self):
        self.editor.delete("1.0", "end")
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)
        self.frame_error.pack_forget()
        self.mostrar_sintactico("Aún no se ha realizado el análisis sintáctico.", "normal")
        self.mostrar_semantico_mensaje("Aún no se ha realizado el análisis semántico.", "normal")
        self.mostrar_intermedio_mensaje("Aún no se ha generado el código intermedio.", "normal")
        self.mostrar_traductor_mensaje("Aún no se ha ejecutado el traductor.", "normal")
        self.editor.tag_remove("linea_sel", "1.0", "end")
        self.lbl_estado.config(text="Listo para analizar", fg="#7f8c8d")

    def analizar(self):
        codigo = self.editor.get("1.0", "end")

        try:
            tokens_crudos = self.obtener_tokens(codigo)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        for fila in self.tabla.get_children():
            self.tabla.delete(fila)

        tokens = []
        total_tokens = 0
        total_errores = 0
        detalle_errores = []

        for tipo, lexema, num_linea in tokens_crudos:
            tag_usado = tipo if tipo in COLORES_TOKEN else ""
            self.tabla.insert("", "end", values=(tipo, lexema, num_linea), tags=(tag_usado,))
            total_tokens += 1

            if tipo == "ERROR_LEXICO":
                total_errores += 1
                if lexema.startswith('"'):
                    detalle_errores.append(f"Línea {num_linea}: cadena sin cerrar {lexema}")
                else:
                    detalle_errores.append(f"Línea {num_linea}: carácter no reconocido '{lexema}'")
            else:
                tokens.append((tipo, lexema, num_linea))

        self.frame_error.pack_forget()
        self.editor.tag_remove("linea_sel", "1.0", "end")

        if total_errores > 0:
            texto_alerta = (
                f"Se encontraron {total_errores} error(es) léxico(s):\n"
                + "\n".join(detalle_errores)
            )
            self.lbl_error_texto.config(text=texto_alerta)
            self.frame_error.pack(fill="x", padx=15, pady=(0, 8), before=self.lbl_editor)
            self.lbl_estado.config(
                text=f"Análisis detenido: {total_errores} error(es) léxico(s).",
                fg="#e74c3c",
            )
            self.mostrar_sintactico(
                "No se ejecutó el análisis sintáctico porque primero deben corregirse los errores léxicos.",
                "error",
            )
            self.mostrar_semantico_mensaje(
                "No se puede realizar el análisis semántico: primero deben corregirse los errores léxicos.",
                "error",
            )
            self.mostrar_intermedio_mensaje(
                "No se puede generar el código intermedio: primero deben corregirse los errores léxicos.",
                "error",
            )
            self.mostrar_traductor_mensaje(
                "No se puede traducir a JavaScript, primero deben corregirse los errores léxicos.",
                "error",
            )
            self.notebook.select(0)
            return

        correcto, mensaje, arbol = analizar_tokens(tokens)
        if not correcto:
            self.mostrar_sintactico(mensaje, "error")
            self.mostrar_semantico_mensaje(
                "No se puede realizar el análisis semántico, el análisis sintáctico no fue exitoso.\n"
                "Corrija el error indicado en la pestaña Sintáctico.",
                "error",
            )
            self.mostrar_intermedio_mensaje(
                "No se puede generar el código intermedio, el análisis sintáctico no fue exitoso.",
                "error",
            )
            self.mostrar_traductor_mensaje(
                "No se puede traducir a JavaScript, el análisis sintáctico no fue exitoso.",
                "error",
            )
            self.lbl_estado.config(text="Se detectó un error sintáctico.", fg="#e67e22")
            self.notebook.select(1)
            return

        self.mostrar_sintactico(mensaje, "ok")

        # El árbol generado por el parser se entrega al analizador semántico.
        resultado_sem = analizar_semantico(arbol)
        self.mostrar_semantico_resultado(resultado_sem)

        if resultado_sem.correcto:
            self.mostrar_intermedio_resultado(arbol)
            self.mostrar_traductor_resultado(arbol, resultado_sem.advertencias)
            self.lbl_estado.config(
                text=f"Análisis completo: {total_tokens} tokens, sintaxis y semántica correctas.",
                fg="#27ae60",
            )
            self.notebook.select(3)
        else:
            self.mostrar_intermedio_mensaje(
                "No se puede generar el código intermedio, el análisis semántico encontró errores.\n"
                "Corrija los errores indicados en la pestaña Semántico.",
                "error",
            )
            self.mostrar_traductor_mensaje(
                "No se puede traducir a JavaScript, el análisis semántico encontró errores.\n"
                "Corrija los errores indicados en la pestaña Semántico.",
                "error",
            )
            self.lbl_estado.config(
                text=f"Se detectaron {resultado_sem.errores} error(es) semántico(s).",
                fg="#e67e22",
            )
            self.notebook.select(2)


if __name__ == "__main__":
    root = tk.Tk()
    app = AnalizadorApp(root)
    root.mainloop()
