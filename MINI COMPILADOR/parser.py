# Analizador sintáctico: recibe la lista de tokens producida por lexer.l y valida su estructura.

from dataclasses import dataclass, field

@dataclass
class Token:
    tipo: str
    lexema: str
    linea: int

@dataclass
class Programa:
    sentencias: list = field(default_factory=list)
    linea: int = 1

@dataclass
class Bloque:
    sentencias: list = field(default_factory=list)
    linea: int = 0

@dataclass
class Declaracion:
    tipo_dato: str = ""
    nombre: str = ""
    valor: object = None
    linea: int = 0
    constante: bool = False

@dataclass
class Asignacion:
    nombre: str = ""
    valor: object = None  # None cuando el operador es ++ o --
    linea: int = 0
    operador: str = "="  # "=", "+=", "-=", "*=", "/=", "%=", "++" o "--"

@dataclass
class Parametro:
    tipo: str = ""
    nombre: str = ""
    linea: int = 0

@dataclass
class Funcion:
    tipo_retorno: str = ""
    nombre: str = ""
    parametros: list = field(default_factory=list)
    cuerpo: object = None
    linea: int = 0

@dataclass
class Llamada:
    nombre: str = ""
    argumentos: list = field(default_factory=list)
    linea: int = 0

@dataclass
class CicloDoWhile:
    cuerpo: object = None
    condicion: object = None
    linea: int = 0

@dataclass
class Romper:
    linea: int = 0

@dataclass
class Continuar:
    linea: int = 0

@dataclass
class Caso:
    valor: object = None  # None = default
    sentencias: list = field(default_factory=list)
    linea: int = 0

@dataclass
class Switch:
    expresion: object = None
    casos: list = field(default_factory=list)
    linea: int = 0

@dataclass
class Impresion:
    argumentos: list = field(default_factory=list)
    linea: int = 0

@dataclass
class Retorno:
    valor: object = None
    linea: int = 0

@dataclass
class Condicional:
    condicion: object = None
    cuerpo: object = None
    sino: object = None  # Bloque, otro Condicional (else if) o None
    linea: int = 0

@dataclass
class CicloWhile:
    condicion: object = None
    cuerpo: object = None
    linea: int = 0

@dataclass
class CicloFor:
    inicio: object = None
    condicion: object = None
    paso: object = None
    cuerpo: object = None
    linea: int = 0

@dataclass
class BinOp:
    operador: str = ""
    izquierda: object = None
    derecha: object = None
    linea: int = 0

@dataclass
class Unario:
    operador: str = ""
    operando: object = None
    linea: int = 0

@dataclass
class Literal:
    tipo: str = ""  # "int", "float", "cadena" o "bool"
    valor: str = ""
    linea: int = 0

@dataclass
class Variable:
    nombre: str = ""
    linea: int = 0

# Tipos de dato del lenguaje (palabras reservadas que inician una declaración).
TIPOS_DATO = ("int", "float", "string", "bool", "void")

class ErrorSintactico(Exception):
    pass

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.profundidad = 0  # > 0 cuando se está dentro de un bloque { }

    def actual(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        linea = self.tokens[-1].linea if self.tokens else 1
        return Token("EOF", "fin de archivo", linea)

    def avanzar(self):
        tok = self.actual()
        if self.pos < len(self.tokens):
            self.pos += 1
        return tok

    def coincide(self, *, tipo=None, lexema=None):
        tok = self.actual()
        if tipo is not None and tok.tipo != tipo:
            return False
        if lexema is not None and tok.lexema != lexema:
            return False
        return True

    def aceptar(self, *, tipo=None, lexema=None):
        if self.coincide(tipo=tipo, lexema=lexema):
            return self.avanzar()
        return None

    def esperar(self, *, tipo=None, lexema=None, mensaje=None):
        tok = self.actual()
        if self.coincide(tipo=tipo, lexema=lexema):
            return self.avanzar()
        esperado = mensaje or lexema or tipo or "token válido"
        raise ErrorSintactico(
            f"Línea {tok.linea}: se esperaba {esperado}, pero se encontró '{tok.lexema}'."
        )

    def analizar(self):
        sentencias = []
        while not self.coincide(tipo="EOF"):
            sentencias.append(self.sentencia())
        return Programa(sentencias)

    def sentencia(self):
        tok = self.actual()

        if tok.tipo == "PALABRA_RESERVADA":
            if tok.lexema == "const":
                return self.declaracion()
            if tok.lexema in TIPOS_DATO:
                if self.es_funcion():
                    return self.funcion()
                return self.declaracion()
            if tok.lexema == "if":
                return self.condicional()
            if tok.lexema == "while":
                return self.ciclo_while()
            if tok.lexema == "do":
                return self.ciclo_do_while()
            if tok.lexema == "for":
                return self.ciclo_for()
            if tok.lexema == "switch":
                return self.sentencia_switch()
            if tok.lexema == "print":
                return self.impresion()
            if tok.lexema == "return":
                return self.retorno()
            if tok.lexema == "break":
                self.avanzar()
                self.esperar(tipo="PUNTO_COMA", mensaje="';' después de break")
                return Romper(tok.linea)
            if tok.lexema == "continue":
                self.avanzar()
                self.esperar(tipo="PUNTO_COMA", mensaje="';' después de continue")
                return Continuar(tok.linea)
        elif tok.tipo == "IDENTIFICADOR":
            if self.siguiente().tipo == "PAR_IZQ":
                llamada = self.llamada()
                self.esperar(tipo="PUNTO_COMA", mensaje="';' después de la llamada a la función")
                return llamada
            return self.asignacion()
        elif tok.tipo == "OP_INCREMENTO":
            return self.asignacion()
        elif tok.tipo == "LLAVE_IZQ":
            return self.bloque()

        raise ErrorSintactico(
            f"Línea {tok.linea}: inicio de sentencia no válido: '{tok.lexema}'."
        )

    def siguiente(self, desplazamiento=1):
        i = self.pos + desplazamiento
        if i < len(self.tokens):
            return self.tokens[i]
        return Token("EOF", "fin de archivo", self.tokens[-1].linea if self.tokens else 1)

    def es_funcion(self):
        """tipo IDENTIFICADOR '(' ... => definición de función."""
        return self.siguiente(1).tipo == "IDENTIFICADOR" and self.siguiente(2).tipo == "PAR_IZQ"

    def tipo_dato(self, mensaje):
        tok = self.esperar(tipo="PALABRA_RESERVADA", mensaje=mensaje)
        if tok.lexema not in TIPOS_DATO:
            raise ErrorSintactico(f"Línea {tok.linea}: se esperaba {mensaje}, pero se encontró '{tok.lexema}'.")
        return tok

    def declaracion(self, exigir_punto_coma=True):
        constante = self.aceptar(lexema="const") is not None
        tipo = self.tipo_dato("un tipo de dato (int, float, string, bool o void)")
        nombre = self.esperar(tipo="IDENTIFICADOR", mensaje="un identificador después del tipo")
        valor = None
        if self.aceptar(tipo="OP_ASIGNACION"):
            valor = self.expresion()
        if exigir_punto_coma:
            self.esperar(tipo="PUNTO_COMA", mensaje="';' al final de la declaración")
        return Declaracion(tipo.lexema, nombre.lexema, valor, nombre.linea, constante)

    def asignacion(self, exigir_punto_coma=True):
        # Forma prefija: ++x  /  --x
        if self.coincide(tipo="OP_INCREMENTO"):
            op = self.avanzar()
            nombre = self.esperar(tipo="IDENTIFICADOR", mensaje="una variable después de " + op.lexema)
            nodo = Asignacion(nombre.lexema, None, nombre.linea, op.lexema)
        else:
            nombre = self.esperar(tipo="IDENTIFICADOR")
            tok = self.actual()
            if tok.tipo == "OP_INCREMENTO":
                self.avanzar()
                nodo = Asignacion(nombre.lexema, None, nombre.linea, tok.lexema)
            elif tok.tipo == "OP_ASIG_COMPUESTA":
                self.avanzar()
                nodo = Asignacion(nombre.lexema, self.expresion(), nombre.linea, tok.lexema)
            else:
                self.esperar(tipo="OP_ASIGNACION", mensaje="'=' en la asignación")
                nodo = Asignacion(nombre.lexema, self.expresion(), nombre.linea, "=")
        if exigir_punto_coma:
            self.esperar(tipo="PUNTO_COMA", mensaje="';' al final de la asignación")
        return nodo

    def funcion(self):
        tipo = self.avanzar()
        nombre = self.esperar(tipo="IDENTIFICADOR")
        if self.profundidad > 0:
            raise ErrorSintactico(
                f"Línea {nombre.linea}: la función '{nombre.lexema}' debe definirse en el nivel global, no dentro de un bloque."
            )
        self.esperar(tipo="PAR_IZQ", mensaje="'(' después del nombre de la función")
        parametros = []
        if not self.coincide(tipo="PAR_DER"):
            while True:
                ptipo = self.tipo_dato("el tipo de dato del parámetro")
                pnombre = self.esperar(tipo="IDENTIFICADOR", mensaje="el nombre del parámetro")
                parametros.append(Parametro(ptipo.lexema, pnombre.lexema, pnombre.linea))
                if not self.aceptar(tipo="COMA"):
                    break
        self.esperar(tipo="PAR_DER", mensaje="')' para cerrar los parámetros")
        cuerpo = self.bloque()
        return Funcion(tipo.lexema, nombre.lexema, parametros, cuerpo, nombre.linea)

    def llamada(self):
        nombre = self.esperar(tipo="IDENTIFICADOR")
        self.esperar(tipo="PAR_IZQ", mensaje="'(' en la llamada a la función")
        argumentos = []
        if not self.coincide(tipo="PAR_DER"):
            argumentos.append(self.expresion())
            while self.aceptar(tipo="COMA"):
                argumentos.append(self.expresion())
        self.esperar(tipo="PAR_DER", mensaje="')' para cerrar la llamada a la función")
        return Llamada(nombre.lexema, argumentos, nombre.linea)

    def impresion(self):
        tok = self.esperar(lexema="print")
        self.esperar(tipo="PAR_IZQ", mensaje="'(' después de print")
        argumentos = []
        if not self.coincide(tipo="PAR_DER"):
            argumentos.append(self.expresion())
            while self.aceptar(tipo="COMA"):
                argumentos.append(self.expresion())
        self.esperar(tipo="PAR_DER", mensaje="')' para cerrar print")
        self.esperar(tipo="PUNTO_COMA", mensaje="';' después de print")
        return Impresion(argumentos, tok.linea)

    def retorno(self):
        tok = self.esperar(lexema="return")
        valor = None
        if not self.coincide(tipo="PUNTO_COMA"):
            valor = self.expresion()
        self.esperar(tipo="PUNTO_COMA", mensaje="';' después de return")
        return Retorno(valor, tok.linea)

    def condicional(self):
        tok = self.esperar(lexema="if")
        self.esperar(tipo="PAR_IZQ", mensaje="'(' después de if")
        condicion = self.expresion()
        self.esperar(tipo="PAR_DER", mensaje="')' al cerrar la condición")
        cuerpo = self.bloque()
        sino = None
        if self.aceptar(lexema="else"):
            if self.coincide(lexema="if"):
                sino = self.condicional()
            else:
                sino = self.bloque()
        return Condicional(condicion, cuerpo, sino, tok.linea)

    def ciclo_while(self):
        tok = self.esperar(lexema="while")
        self.esperar(tipo="PAR_IZQ", mensaje="'(' después de while")
        condicion = self.expresion()
        self.esperar(tipo="PAR_DER", mensaje="')' al cerrar la condición del while")
        cuerpo = self.bloque()
        return CicloWhile(condicion, cuerpo, tok.linea)

    def ciclo_do_while(self):
        tok = self.esperar(lexema="do")
        cuerpo = self.bloque()
        self.esperar(lexema="while", mensaje="'while' después del cuerpo del do")
        self.esperar(tipo="PAR_IZQ", mensaje="'(' después de while")
        condicion = self.expresion()
        self.esperar(tipo="PAR_DER", mensaje="')' al cerrar la condición del do-while")
        self.esperar(tipo="PUNTO_COMA", mensaje="';' al final del do-while")
        return CicloDoWhile(cuerpo, condicion, tok.linea)

    def sentencia_switch(self):
        tok = self.esperar(lexema="switch")
        self.esperar(tipo="PAR_IZQ", mensaje="'(' después de switch")
        expresion = self.expresion()
        self.esperar(tipo="PAR_DER", mensaje="')' al cerrar la expresión del switch")
        self.esperar(tipo="LLAVE_IZQ", mensaje="'{' para iniciar el switch")
        self.profundidad += 1
        casos = []
        while not self.coincide(tipo="LLAVE_DER"):
            actual = self.actual()
            if actual.tipo == "EOF":
                raise ErrorSintactico(f"Línea {actual.linea}: se esperaba '}}' para cerrar el switch.")
            if self.aceptar(lexema="case"):
                valor = self.unario()
            elif self.aceptar(lexema="default"):
                valor = None
            else:
                raise ErrorSintactico(
                    f"Línea {actual.linea}: se esperaba 'case' o 'default' dentro del switch, pero se encontró '{actual.lexema}'."
                )
            self.esperar(tipo="DOS_PUNTOS", mensaje="':' después de la etiqueta del case")
            sentencias = []
            while not (
                self.coincide(lexema="case") or self.coincide(lexema="default")
                or self.coincide(tipo="LLAVE_DER") or self.coincide(tipo="EOF")
            ):
                sentencias.append(self.sentencia())
            casos.append(Caso(valor, sentencias, actual.linea))
        self.esperar(tipo="LLAVE_DER")
        self.profundidad -= 1
        return Switch(expresion, casos, tok.linea)

    def ciclo_for(self):
        tok = self.esperar(lexema="for")
        self.esperar(tipo="PAR_IZQ", mensaje="'(' después de for")

        inicio = None
        if not self.coincide(tipo="PUNTO_COMA"):
            if self.actual().tipo == "PALABRA_RESERVADA" and self.actual().lexema in TIPOS_DATO + ("const",):
                inicio = self.declaracion(exigir_punto_coma=False)
            else:
                inicio = self.asignacion(exigir_punto_coma=False)
        self.esperar(tipo="PUNTO_COMA", mensaje="';' después de la inicialización del for")

        condicion = None
        if not self.coincide(tipo="PUNTO_COMA"):
            condicion = self.expresion()
        self.esperar(tipo="PUNTO_COMA", mensaje="';' después de la condición del for")

        paso = None
        if not self.coincide(tipo="PAR_DER"):
            paso = self.asignacion(exigir_punto_coma=False)
        self.esperar(tipo="PAR_DER", mensaje="')' al cerrar el for")
        cuerpo = self.bloque()
        return CicloFor(inicio, condicion, paso, cuerpo, tok.linea)

    def bloque(self):
        llave = self.esperar(tipo="LLAVE_IZQ", mensaje="'{' para iniciar el bloque")
        self.profundidad += 1
        sentencias = []
        while not self.coincide(tipo="LLAVE_DER"):
            if self.coincide(tipo="EOF"):
                raise ErrorSintactico(
                    f"Línea {self.actual().linea}: se esperaba '}}' para cerrar el bloque."
                )
            sentencias.append(self.sentencia())
        self.esperar(tipo="LLAVE_DER")
        self.profundidad -= 1
        return Bloque(sentencias, llave.linea)

    # Precedencia (de menor a mayor): ||  &&  == !=  < > <= >=  + -  * / %  ! - +(unarios)
    def expresion(self):
        return self.o_logico()

    def _binaria(self, siguiente, tipo_op, operadores):
        nodo = siguiente()
        while self.coincide(tipo=tipo_op) and self.actual().lexema in operadores:
            op = self.avanzar()
            derecha = siguiente()
            nodo = BinOp(op.lexema, nodo, derecha, op.linea)
        return nodo

    def o_logico(self):
        return self._binaria(self.y_logico, "OP_LOGICO", ("||",))

    def y_logico(self):
        return self._binaria(self.igualdad, "OP_LOGICO", ("&&",))

    def igualdad(self):
        return self._binaria(self.comparacion, "OP_RELACIONAL", ("==", "!="))

    def comparacion(self):
        return self._binaria(self.suma, "OP_RELACIONAL", ("<", ">", "<=", ">="))

    def suma(self):
        return self._binaria(self.termino, "OP_ARITMETICO", ("+", "-"))

    def termino(self):
        return self._binaria(self.unario, "OP_ARITMETICO", ("*", "/", "%"))

    def unario(self):
        tok = self.actual()
        if (tok.tipo == "OP_ARITMETICO" and tok.lexema in ("+", "-")) or (
            tok.tipo == "OP_LOGICO" and tok.lexema == "!"
        ):
            self.avanzar()
            return Unario(tok.lexema, self.unario(), tok.linea)
        return self.factor()

    def factor(self):
        tok = self.actual()
        if tok.tipo == "NUMERO_ENTERO":
            self.avanzar()
            return Literal("int", tok.lexema, tok.linea)
        if tok.tipo == "NUMERO_DECIMAL":
            self.avanzar()
            return Literal("float", tok.lexema, tok.linea)
        if tok.tipo == "CADENA":
            self.avanzar()
            return Literal("cadena", tok.lexema, tok.linea)
        if tok.tipo == "BOOLEANO":
            self.avanzar()
            return Literal("bool", tok.lexema, tok.linea)
        if tok.tipo == "IDENTIFICADOR":
            if self.siguiente().tipo == "PAR_IZQ":
                return self.llamada()
            self.avanzar()
            return Variable(tok.lexema, tok.linea)
        if self.aceptar(tipo="PAR_IZQ"):
            nodo = self.expresion()
            self.esperar(tipo="PAR_DER", mensaje="')' para cerrar la expresión")
            return nodo
        raise ErrorSintactico(
            f"Línea {tok.linea}: se esperaba un valor, identificador o expresión, pero se encontró '{tok.lexema}'."
        )


def analizar_tokens(tokens_crudos):
    tokens = []
    for tipo, lexema, linea in tokens_crudos:
        tokens.append(Token(tipo, lexema, int(linea)))
    parser = Parser(tokens)
    try:
        arbol = parser.analizar()
        return (
            True,
            "Análisis sintáctico exitoso.\nEl código cumple con la gramática definida para el lenguaje.",
            arbol,
        )
    except ErrorSintactico as error:
        return False, f"Error sintáctico.\n{error}", None
