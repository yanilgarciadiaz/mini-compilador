# Analizador semántico
# Recibe el árbol sintáctico (AST) que construye parser.py y comprueba las
# reglas de significado del lenguaje: declaración de variables y funciones,
# ámbitos, compatibilidad de tipos y uso correcto de las expresiones.

from dataclasses import dataclass, field

from parser import (
    Programa,
    Bloque,
    Declaracion,
    Asignacion,
    Impresion,
    Retorno,
    Condicional,
    CicloWhile,
    CicloDoWhile,
    CicloFor,
    Switch,
    Romper,
    Continuar,
    Funcion,
    Llamada,
    BinOp,
    Unario,
    Literal,
    Variable,
)

ERROR = "error"  
SEV_ERROR = "ERROR"
SEV_ADVERTENCIA = "ADVERTENCIA"

OPS_ARITMETICOS = ("+", "-", "*", "/", "%")
OPS_LOGICOS = ("&&", "||")


@dataclass
class Simbolo:
    nombre: str
    tipo: str
    ambito: str
    nivel: int
    linea: int
    inicializada: bool
    usada: bool = False
    avisado_sin_inicializar: bool = False
    clase: str = "variable"  # variable, constante, parámetro o función
    constante: bool = False


@dataclass
class Diagnostico:
    severidad: str
    linea: int
    mensaje: str


@dataclass
class ResultadoSemantico:
    simbolos: list = field(default_factory=list)
    diagnosticos: list = field(default_factory=list)

    @property
    def errores(self):
        return sum(1 for d in self.diagnosticos if d.severidad == SEV_ERROR)

    @property
    def advertencias(self):
        return sum(1 for d in self.diagnosticos if d.severidad == SEV_ADVERTENCIA)

    @property
    def correcto(self):
        return self.errores == 0


def tipo_de_expresion(tipo_declarado):
    """Tipo declarado (string) -> tipo que manejan las expresiones (cadena)."""
    return "cadena" if tipo_declarado == "string" else tipo_declarado


class AnalizadorSemantico:
    def __init__(self):
        self.pila = [] 
        self.simbolos = []
        self.diagnosticos = []
        self.funciones = {}  # nombre -> nodo Funcion
        self.funcion_actual = None
        self.en_ciclo = 0
        self.en_switch = 0

    # Utilidades
    def error(self, linea, mensaje):
        self.diagnosticos.append(Diagnostico(SEV_ERROR, linea, mensaje))

    def advertencia(self, linea, mensaje):
        self.diagnosticos.append(Diagnostico(SEV_ADVERTENCIA, linea, mensaje))

    def abrir_ambito(self, nombre):
        self.pila.append((nombre, {}))

    def cerrar_ambito(self):
        _, tabla = self.pila.pop()
        for sim in tabla.values():
            if not sim.usada and sim.tipo != "void" and sim.clase in ("variable", "constante"):
                self.advertencia(
                    sim.linea,
                    f"La {sim.clase} '{sim.nombre}' fue declarada pero nunca se usa.",
                )

    def buscar(self, nombre):
        for _, tabla in reversed(self.pila):
            if nombre in tabla:
                return tabla[nombre]
        return None

    def registrar(self, nombre, tipo, linea, inicializada, clase="variable", constante=False, usada=False):
        """Agrega un símbolo al ámbito actual. Devuelve False si ya existía."""
        ambito, tabla = self.pila[-1]
        if nombre in tabla:
            previa = tabla[nombre]
            articulo = "El" if previa.clase == "parámetro" else "La"
            participio = "declarado" if previa.clase == "parámetro" else "declarada"
            self.error(
                linea,
                f"{articulo} {previa.clase} '{nombre}' ya fue {participio} en este ámbito (línea {previa.linea}).",
            )
            return False
        if nombre in self.funciones and clase != "función":
            self.error(
                linea,
                f"El nombre '{nombre}' ya pertenece a una función (línea {self.funciones[nombre].linea}).",
            )
        simbolo = Simbolo(
            nombre=nombre,
            tipo=tipo,
            ambito=ambito,
            nivel=len(self.pila) - 1,
            linea=linea,
            inicializada=inicializada,
            usada=usada,
            clase=clase,
            constante=constante,
        )
        tabla[nombre] = simbolo
        self.simbolos.append(simbolo)
        return True

    # Punto de entrada
    def analizar(self, arbol):
        self.abrir_ambito("global")
        for sentencia in arbol.sentencias:
            if isinstance(sentencia, Funcion):
                if sentencia.nombre in self.funciones:
                    previa = self.funciones[sentencia.nombre]
                    self.error(
                        sentencia.linea,
                        f"La función '{sentencia.nombre}' ya fue definida (línea {previa.linea}).",
                    )
                else:
                    self.funciones[sentencia.nombre] = sentencia
        for sentencia in arbol.sentencias:
            self.visitar(sentencia)
        self.cerrar_ambito()

        orden = {SEV_ERROR: 0, SEV_ADVERTENCIA: 1}
        self.diagnosticos.sort(key=lambda d: (d.linea, orden[d.severidad]))
        return ResultadoSemantico(self.simbolos, self.diagnosticos)

    # Sentencias
    def visitar(self, nodo):
        if isinstance(nodo, Declaracion):
            self.v_declaracion(nodo)
        elif isinstance(nodo, Asignacion):
            self.v_asignacion(nodo)
        elif isinstance(nodo, Impresion):
            for argumento in nodo.argumentos:
                self.expresion(argumento)
        elif isinstance(nodo, Retorno):
            self.v_retorno(nodo)
        elif isinstance(nodo, Condicional):
            self.v_condicional(nodo)
        elif isinstance(nodo, CicloWhile):
            self.v_while(nodo)
        elif isinstance(nodo, CicloDoWhile):
            self.v_do_while(nodo)
        elif isinstance(nodo, CicloFor):
            self.v_for(nodo)
        elif isinstance(nodo, Switch):
            self.v_switch(nodo)
        elif isinstance(nodo, Romper):
            if self.en_ciclo == 0 and self.en_switch == 0:
                self.error(nodo.linea, "'break' solo puede usarse dentro de un ciclo o de un switch.")
        elif isinstance(nodo, Continuar):
            if self.en_ciclo == 0:
                self.error(nodo.linea, "'continue' solo puede usarse dentro de un ciclo.")
        elif isinstance(nodo, Funcion):
            self.v_funcion(nodo)
        elif isinstance(nodo, Llamada):
            self.e_llamada(nodo, como_sentencia=True)
        elif isinstance(nodo, Bloque):
            self.v_bloque(nodo, f"bloque (L{nodo.linea})")

    def v_bloque(self, nodo, etiqueta):
        self.abrir_ambito(etiqueta)
        for sentencia in nodo.sentencias:
            self.visitar(sentencia)
        self.cerrar_ambito()

    def v_declaracion(self, nodo):
        tipo_valor = None
        # La expresión inicial se evalúa antes de registrar la variable.
        if nodo.valor is not None:
            tipo_valor = self.expresion(nodo.valor)

        if nodo.tipo_dato == "void":
            self.error(
                nodo.linea,
                f"No se puede declarar la variable '{nodo.nombre}' de tipo void.",
            )
        if nodo.constante and nodo.valor is None:
            self.error(
                nodo.linea,
                f"La constante '{nodo.nombre}' debe inicializarse al declararla.",
            )

        self.registrar(
            nodo.nombre,
            nodo.tipo_dato,
            nodo.linea,
            inicializada=nodo.valor is not None,
            clase="constante" if nodo.constante else "variable",
            constante=nodo.constante,
        )

        if nodo.valor is not None:
            self.compatibilidad(nodo.tipo_dato, tipo_valor, nodo.linea, f"'{nodo.nombre}'")

    def v_asignacion(self, nodo):
        op = nodo.operador
        if op == "=":
            tipo_valor = self.expresion(nodo.valor)
            simbolo = self.buscar(nodo.nombre)
            if simbolo is None:
                self.error(nodo.linea, f"La variable '{nodo.nombre}' no ha sido declarada.")
                return
            if simbolo.constante:
                self.error(nodo.linea, f"No se puede modificar la constante '{nodo.nombre}'.")
                return
            self.compatibilidad(simbolo.tipo, tipo_valor, nodo.linea, f"'{nodo.nombre}'")
            simbolo.inicializada = True
            return

        tipo_valor = self.expresion(nodo.valor) if nodo.valor is not None else None
        simbolo = self.buscar(nodo.nombre)
        if simbolo is None:
            self.error(nodo.linea, f"La variable '{nodo.nombre}' no ha sido declarada.")
            return
        tipo_var = self.e_variable(Variable(nodo.nombre, nodo.linea))
        if simbolo.constante:
            self.error(nodo.linea, f"No se puede modificar la constante '{nodo.nombre}'.")
            return
        if tipo_var not in ("int", "float", ERROR):
            self.error(
                nodo.linea,
                f"El operador '{op}' solo se puede usar con variables numéricas ('{nodo.nombre}' es {simbolo.tipo}).",
            )
            return
        if tipo_valor is None or tipo_var == ERROR:
            return
        if tipo_valor == "cadena":
            self.error(nodo.linea, f"La operación '{op}' no es válida con cadenas.")
            return
        if op in ("/=", "%=") and self.es_cero(nodo.valor):
            self.error(nodo.linea, "División entre cero.")
        if tipo_var == "int" and tipo_valor == "float":
            self.advertencia(
                nodo.linea,
                f"Pérdida de precisión: se asigna un valor float a '{nodo.nombre}' de tipo int.",
            )

    def v_retorno(self, nodo):
        tipo_valor = self.expresion(nodo.valor) if nodo.valor is not None else None
        funcion = self.funcion_actual
        if funcion is None:
            self.advertencia(
                nodo.linea,
                "Uso de 'return' fuera de una función: el programa terminará en este punto.",
            )
            return
        if funcion.tipo_retorno == "void":
            if nodo.valor is not None:
                self.error(
                    nodo.linea,
                    f"La función '{funcion.nombre}' es void y no puede devolver un valor.",
                )
        elif nodo.valor is None:
            self.error(
                nodo.linea,
                f"La función '{funcion.nombre}' debe devolver un valor de tipo {funcion.tipo_retorno}.",
            )
        else:
            self.compatibilidad(
                funcion.tipo_retorno, tipo_valor, nodo.linea, f"al retorno de '{funcion.nombre}'"
            )

    def v_condicional(self, nodo):
        self.condicion(nodo.condicion, "if")
        self.v_bloque(nodo.cuerpo, f"if (L{nodo.linea})")
        if nodo.sino is not None:
            if isinstance(nodo.sino, Condicional):
                self.v_condicional(nodo.sino)
            else:
                self.v_bloque(nodo.sino, f"else (L{nodo.sino.linea})")

    def v_while(self, nodo):
        self.condicion(nodo.condicion, "while")
        self.en_ciclo += 1
        self.v_bloque(nodo.cuerpo, f"while (L{nodo.linea})")
        self.en_ciclo -= 1

    def v_do_while(self, nodo):
        self.en_ciclo += 1
        self.v_bloque(nodo.cuerpo, f"do-while (L{nodo.linea})")
        self.en_ciclo -= 1
        self.condicion(nodo.condicion, "do-while")

    def v_for(self, nodo):
        self.abrir_ambito(f"for (L{nodo.linea})")
        if nodo.inicio is not None:
            self.visitar(nodo.inicio)
        if nodo.condicion is not None:
            self.condicion(nodo.condicion, "for")
        if nodo.paso is not None:
            self.visitar(nodo.paso)
        self.en_ciclo += 1
        self.v_bloque(nodo.cuerpo, f"cuerpo de for (L{nodo.linea})")
        self.en_ciclo -= 1
        self.cerrar_ambito()

    def v_switch(self, nodo):
        tipo = self.expresion(nodo.expresion)
        clase_switch = self.clase_valor(tipo)
        vistos = {}
        hay_default = False

        self.abrir_ambito(f"switch (L{nodo.linea})")
        self.en_switch += 1
        for caso in nodo.casos:
            if caso.valor is None:
                if hay_default:
                    self.error(caso.linea, "El switch tiene más de un 'default'.")
                hay_default = True
            else:
                clave, tipo_caso = self.valor_constante(caso.valor)
                if clave is None:
                    self.error(caso.linea, "El valor de un 'case' debe ser un literal (número, cadena o booleano).")
                else:
                    if clase_switch is not None and self.clase_valor(tipo_caso) != clase_switch:
                        self.error(
                            caso.linea,
                            "El valor del 'case' no es del mismo tipo que la expresión del switch.",
                        )
                    if clave in vistos:
                        self.error(
                            caso.linea,
                            f"El valor del 'case' está repetido (ya aparece en la línea {vistos[clave]}).",
                        )
                    else:
                        vistos[clave] = caso.linea
            for sentencia in caso.sentencias:
                self.visitar(sentencia)
        self.en_switch -= 1
        self.cerrar_ambito()

    @staticmethod
    def clase_valor(tipo):
        if tipo in ("int", "float"):
            return "numero"
        if tipo in ("cadena", "bool"):
            return tipo
        return None  

    @staticmethod
    def valor_constante(nodo):
        """Si el nodo es un literal (con signo opcional) devuelve (clave, tipo)."""
        if isinstance(nodo, Literal):
            if nodo.tipo in ("int", "float"):
                return float(nodo.valor), nodo.tipo
            return nodo.valor, nodo.tipo
        if (
            isinstance(nodo, Unario)
            and nodo.operador in ("+", "-")
            and isinstance(nodo.operando, Literal)
            and nodo.operando.tipo in ("int", "float")
        ):
            valor = float(nodo.operando.valor)
            return (-valor if nodo.operador == "-" else valor), nodo.operando.tipo
        return None, None

    def v_funcion(self, nodo):
        simbolo_funcion = Simbolo(
            nombre=nodo.nombre,
            tipo=nodo.tipo_retorno,
            ambito="global",
            nivel=0,
            linea=nodo.linea,
            inicializada=True,
            usada=True,
            clase="función",
        )
        self.simbolos.append(simbolo_funcion)

        self.abrir_ambito(f"función {nodo.nombre} (L{nodo.linea})")
        anterior = self.funcion_actual
        self.funcion_actual = nodo
        for p in nodo.parametros:
            if p.tipo == "void":
                self.error(p.linea, f"El parámetro '{p.nombre}' no puede ser de tipo void.")
            self.registrar(p.nombre, p.tipo, p.linea, inicializada=True, clase="parámetro", usada=True)
        for sentencia in nodo.cuerpo.sentencias:
            self.visitar(sentencia)
        if nodo.tipo_retorno != "void" and not self.siempre_retorna(nodo.cuerpo.sentencias):
            self.advertencia(
                nodo.linea,
                f"La función '{nodo.nombre}' puede terminar sin devolver un valor en alguno de sus caminos.",
            )
        self.funcion_actual = anterior
        self.cerrar_ambito()

    def siempre_retorna(self, sentencias):
        for s in sentencias:
            if isinstance(s, Retorno):
                return True
            if isinstance(s, Bloque) and self.siempre_retorna(s.sentencias):
                return True
            if isinstance(s, Condicional) and self.condicional_retorna(s):
                return True
        return False

    def condicional_retorna(self, nodo):
        if nodo.sino is None or not self.siempre_retorna(nodo.cuerpo.sentencias):
            return False
        if isinstance(nodo.sino, Condicional):
            return self.condicional_retorna(nodo.sino)
        return self.siempre_retorna(nodo.sino.sentencias)

    def condicion(self, nodo, estructura):
        tipo = self.expresion(nodo)
        if tipo == "cadena":
            self.error(
                self.linea_de(nodo),
                f"La condición del {estructura} no puede ser una cadena.",
            )

    @staticmethod
    def linea_de(nodo):
        return getattr(nodo, "linea", 0)

    # Tipos
    @staticmethod
    def receptor(objetivo, destino):
        """"'x'" -> "a 'x' de tipo int";  "al retorno de 'f'" -> "al retorno de 'f' (tipo int)"."""
        if objetivo.startswith("'"):
            return f"a {objetivo} de tipo {destino}"
        return f"{objetivo} (tipo {destino})"

    def compatibilidad(self, destino, origen, linea, objetivo):
        """`objetivo`: nombre entre comillas (p. ej. "'total'") o frase con preposición
        (p. ej. "al parámetro 'n' de 'f'")."""
        if destino == "void" or ERROR in (destino, origen):
            return
        a = self.receptor(objetivo, destino)
        if destino == "string":
            if origen != "cadena":
                clase = "booleano" if origen == "bool" else "numérico"
                self.error(
                    linea,
                    f"Tipos incompatibles: no se puede asignar un valor {clase} {a}.",
                )
            return
        if destino == "bool":
            if origen == "cadena":
                self.error(
                    linea,
                    f"Tipos incompatibles: no se puede asignar una cadena {a}.",
                )
            elif origen in ("int", "float"):
                self.error(
                    linea,
                    f"Tipos incompatibles: no se puede asignar un valor numérico {a}.",
                )
            return
        if origen == "cadena":
            self.error(
                linea,
                f"Tipos incompatibles: no se puede asignar una cadena {a}.",
            )
        elif destino == "int" and origen == "float":
            self.advertencia(
                linea,
                f"Pérdida de precisión: se asigna un valor float {a}.",
            )

    # Expresiones: devuelven el tipo resultante
    def expresion(self, nodo):
        if isinstance(nodo, Literal):
            return nodo.tipo
        if isinstance(nodo, Variable):
            return self.e_variable(nodo)
        if isinstance(nodo, Unario):
            return self.e_unario(nodo)
        if isinstance(nodo, BinOp):
            return self.e_binaria(nodo)
        if isinstance(nodo, Llamada):
            return self.e_llamada(nodo)
        return ERROR

    def e_variable(self, nodo):
        simbolo = self.buscar(nodo.nombre)
        if simbolo is None:
            self.error(nodo.linea, f"La variable '{nodo.nombre}' no ha sido declarada.")
            return ERROR
        simbolo.usada = True
        if not simbolo.inicializada and not simbolo.avisado_sin_inicializar:
            simbolo.avisado_sin_inicializar = True
            self.advertencia(
                nodo.linea,
                f"La variable '{nodo.nombre}' se usa antes de ser inicializada.",
            )
        if simbolo.tipo == "void":
            return ERROR
        return tipo_de_expresion(simbolo.tipo)

    def e_llamada(self, nodo, como_sentencia=False):
        # Los argumentos se evalúan siempre para detectar errores dentro de ellos.
        tipos_arg = [self.expresion(a) for a in nodo.argumentos]
        funcion = self.funciones.get(nodo.nombre)
        if funcion is None:
            self.error(nodo.linea, f"La función '{nodo.nombre}' no ha sido definida.")
            return ERROR
        esperados = len(funcion.parametros)
        if len(nodo.argumentos) != esperados:
            self.error(
                nodo.linea,
                f"La función '{nodo.nombre}' espera {esperados} argumento(s), pero recibió {len(nodo.argumentos)}.",
            )
        else:
            for parametro, tipo_arg in zip(funcion.parametros, tipos_arg):
                self.compatibilidad(
                    parametro.tipo, tipo_arg, nodo.linea,
                    f"al parámetro '{parametro.nombre}' de '{nodo.nombre}'",
                )
        if funcion.tipo_retorno == "void":
            if not como_sentencia:
                self.error(
                    nodo.linea,
                    f"La función '{nodo.nombre}' es void: no devuelve ningún valor que se pueda usar en una expresión.",
                )
                return ERROR
            return "void"
        return tipo_de_expresion(funcion.tipo_retorno)

    def e_unario(self, nodo):
        tipo = self.expresion(nodo.operando)
        if tipo == "cadena":
            self.error(
                nodo.linea,
                f"El operador unario '{nodo.operador}' no es válido con cadenas.",
            )
            return ERROR
        if nodo.operador == "!":
            return "bool"
        return "int" if tipo == "bool" else tipo

    def e_binaria(self, nodo):
        izq = self.expresion(nodo.izquierda)
        der = self.expresion(nodo.derecha)
        op = nodo.operador

        if op in OPS_ARITMETICOS:
            if "cadena" in (izq, der):
                self.error(
                    nodo.linea,
                    f"La operación '{op}' no es válida con cadenas.",
                )
                return ERROR
            if op in ("/", "%") and self.es_cero(nodo.derecha):
                self.error(nodo.linea, "División entre cero.")
            if ERROR in (izq, der):
                return ERROR
            return "float" if "float" in (izq, der) else "int"

        if op in OPS_LOGICOS:
            if "cadena" in (izq, der):
                self.error(
                    nodo.linea,
                    f"El operador '{op}' no es válido con cadenas.",
                )
            return "bool"

        # Operadores relacionales
        if ERROR not in (izq, der) and "cadena" in (izq, der):
            if izq != der:
                self.error(
                    nodo.linea,
                    f"No se puede comparar una cadena con un valor numérico ('{op}').",
                )
            elif op not in ("==", "!="):
                self.error(
                    nodo.linea,
                    f"El operador '{op}' no es válido para comparar cadenas.",
                )
        return "bool"

    @staticmethod
    def es_cero(nodo):
        if isinstance(nodo, Literal) and nodo.tipo in ("int", "float"):
            try:
                return float(nodo.valor) == 0.0
            except ValueError:
                return False
        return False


def analizar_semantico(arbol):
    """Analiza el árbol sintáctico y devuelve un ResultadoSemantico."""
    return AnalizadorSemantico().analizar(arbol)
