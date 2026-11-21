# Generación de código intermedio y traducción a JavaScript
#
#   1. GeneradorCI   -> código de tres direcciones almacenado como CUÁDRUPLOS
#                       (operador, argumento 1, argumento 2, resultado), con
#                       temporales t1, t2... y etiquetas L1, L2...
#   2. TraductorJS   -> recorre el árbol sintáctico y produce el código fuente
#                       equivalente en JavaScript

from dataclasses import dataclass

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

# PARTE 1: CÓDIGO DE TRES DIRECCIONES (CUÁDRUPLOS)
@dataclass
class Cuadruplo:
    op: str
    arg1: str = ""
    arg2: str = ""
    resultado: str = ""

    def texto(self):
        op, a1, a2, res = self.op, self.arg1, self.arg2, self.resultado
        if op == "=":
            return f"{res} = {a1}"
        if op == "minus":
            return f"{res} = minus {a1}"
        if op == "!":
            return f"{res} = ! {a1}"
        if op == "label":
            return f"{res}:"
        if op == "goto":
            return f"    goto {res}"
        if op == "ifFalse":
            return f"    ifFalse {a1} goto {res}"
        if op == "ifTrue":
            return f"    ifTrue {a1} goto {res}"
        if op == "param":
            return f"    param {a1}"
        if op == "call":
            if res:
                return f"    {res} = call {a1}, {a2}"
            return f"    call {a1}, {a2}"
        if op == "return":
            return f"    return {a1}".rstrip()
        if op == "function":
            return f"function {a1}({a2}):"
        if op == "endfunction":
            return f"end function {a1}"
        return f"{res} = {a1} {op} {a2}"


class GeneradorCI:
    def __init__(self):
        self.cuadruplos = []
        self._n_temp = 0
        self._n_etiq = 0
        self._ciclos = []  # pila de (etiqueta_break, etiqueta_continue)
        self._funciones = []  # funciones pendientes: se generan al final

    # -- utilidades
    def temporal(self):
        self._n_temp += 1
        return f"t{self._n_temp}"

    def etiqueta(self):
        self._n_etiq += 1
        return f"L{self._n_etiq}"

    def emitir(self, op, arg1="", arg2="", resultado=""):
        self.cuadruplos.append(Cuadruplo(op, str(arg1), str(arg2), str(resultado)))

    # -- sentencias 
    def generar(self, arbol):
        for sentencia in arbol.sentencias:
            self.sentencia(sentencia)
        # Las funciones se colocan después del flujo principal.
        for funcion in self._funciones:
            self.funcion(funcion)
        return self.cuadruplos

    def sentencia(self, nodo):
        if isinstance(nodo, Declaracion):
            if nodo.valor is not None:
                self.asignar(nodo.nombre, nodo.valor)
        elif isinstance(nodo, Asignacion):
            self.asignacion(nodo)
        elif isinstance(nodo, Impresion):
            direcciones = [self.expresion(a) for a in nodo.argumentos]
            for d in direcciones:
                self.emitir("param", d)
            self.emitir("call", "print", len(direcciones))
        elif isinstance(nodo, Retorno):
            if nodo.valor is not None:
                self.emitir("return", self.expresion(nodo.valor))
            else:
                self.emitir("return")
        elif isinstance(nodo, Condicional):
            self.condicional(nodo)
        elif isinstance(nodo, CicloWhile):
            self.ciclo_while(nodo)
        elif isinstance(nodo, CicloDoWhile):
            self.ciclo_do_while(nodo)
        elif isinstance(nodo, CicloFor):
            self.ciclo_for(nodo)
        elif isinstance(nodo, Switch):
            self.sentencia_switch(nodo)
        elif isinstance(nodo, Romper):
            self.emitir("goto", "", "", self._ciclos[-1][0])
        elif isinstance(nodo, Continuar):
            destino = next(c for _, c in reversed(self._ciclos) if c is not None)
            self.emitir("goto", "", "", destino)
        elif isinstance(nodo, Funcion):
            self._funciones.append(nodo)
        elif isinstance(nodo, Llamada):
            self.llamada(nodo)
        elif isinstance(nodo, Bloque):
            for s in nodo.sentencias:
                self.sentencia(s)

    def asignar(self, nombre, valor):
        resultado = self.expresion(valor, destino=nombre)
        if resultado != nombre:
            self.emitir("=", resultado, "", nombre)

    def asignacion(self, nodo):
        op = nodo.operador
        if op == "=":
            self.asignar(nodo.nombre, nodo.valor)
        elif op in ("++", "--"):
            self.emitir(op[0], nodo.nombre, "1", nodo.nombre)
        else:
            y = self.expresion(nodo.valor)
            self.emitir(op[0], nodo.nombre, y, nodo.nombre)

    def funcion(self, nodo):
        nombres = ", ".join(p.nombre for p in nodo.parametros)
        self.emitir("function", nodo.nombre, nombres)
        for s in nodo.cuerpo.sentencias:
            self.sentencia(s)
        self.emitir("endfunction", nodo.nombre)

    def llamada(self, nodo, con_resultado=False):
        direcciones = [self.expresion(a) for a in nodo.argumentos]
        for d in direcciones:
            self.emitir("param", d)
        t = self.temporal() if con_resultado else ""
        self.emitir("call", nodo.nombre, len(direcciones), t)
        return t

    def condicional(self, nodo):
        cond = self.expresion(nodo.condicion)
        if nodo.sino is None:
            l_fin = self.etiqueta()
            self.emitir("ifFalse", cond, "", l_fin)
            self.sentencia(nodo.cuerpo)
            self.emitir("label", "", "", l_fin)
        else:
            l_else = self.etiqueta()
            l_fin = self.etiqueta()
            self.emitir("ifFalse", cond, "", l_else)
            self.sentencia(nodo.cuerpo)
            self.emitir("goto", "", "", l_fin)
            self.emitir("label", "", "", l_else)
            self.sentencia(nodo.sino)  # Bloque o Condicional (else if)
            self.emitir("label", "", "", l_fin)

    def ciclo_while(self, nodo):
        l_inicio = self.etiqueta()
        l_fin = self.etiqueta()
        self.emitir("label", "", "", l_inicio)
        cond = self.expresion(nodo.condicion)
        self.emitir("ifFalse", cond, "", l_fin)
        self._ciclos.append((l_fin, l_inicio))
        self.sentencia(nodo.cuerpo)
        self._ciclos.pop()
        self.emitir("goto", "", "", l_inicio)
        self.emitir("label", "", "", l_fin)

    def ciclo_do_while(self, nodo):
        l_inicio = self.etiqueta()
        l_cond = self.etiqueta()
        l_fin = self.etiqueta()
        self.emitir("label", "", "", l_inicio)
        self._ciclos.append((l_fin, l_cond))
        self.sentencia(nodo.cuerpo)
        self._ciclos.pop()
        self.emitir("label", "", "", l_cond)
        cond = self.expresion(nodo.condicion)
        self.emitir("ifTrue", cond, "", l_inicio)
        self.emitir("label", "", "", l_fin)

    def ciclo_for(self, nodo):
        if nodo.inicio is not None:
            self.sentencia(nodo.inicio)
        l_inicio = self.etiqueta()
        l_paso = self.etiqueta()
        l_fin = self.etiqueta()
        self.emitir("label", "", "", l_inicio)
        if nodo.condicion is not None:
            cond = self.expresion(nodo.condicion)
            self.emitir("ifFalse", cond, "", l_fin)
        self._ciclos.append((l_fin, l_paso))
        self.sentencia(nodo.cuerpo)
        self._ciclos.pop()
        self.emitir("label", "", "", l_paso)
        if nodo.paso is not None:
            self.sentencia(nodo.paso)
        self.emitir("goto", "", "", l_inicio)
        self.emitir("label", "", "", l_fin)

    def sentencia_switch(self, nodo):
        valor = self.expresion(nodo.expresion)
        l_fin = self.etiqueta()
        etiquetas = [self.etiqueta() for _ in nodo.casos]
        # 1) Comparaciones: saltan al cuerpo del case que coincida.
        l_default = None
        for caso, etiqueta in zip(nodo.casos, etiquetas):
            if caso.valor is None:
                l_default = etiqueta
                continue
            t = self.temporal()
            self.emitir("==", valor, self.expresion(caso.valor), t)
            self.emitir("ifTrue", t, "", etiqueta)
        self.emitir("goto", "", "", l_default or l_fin)
        # 2) Cuerpos (caen de uno al siguiente, como en C/JavaScript).
        continuar = next((c for _, c in reversed(self._ciclos) if c is not None), None)
        self._ciclos.append((l_fin, continuar))
        for caso, etiqueta in zip(nodo.casos, etiquetas):
            self.emitir("label", "", "", etiqueta)
            for s in caso.sentencias:
                self.sentencia(s)
        self._ciclos.pop()
        self.emitir("label", "", "", l_fin)

    # -- expresiones: devuelven la "dirección" donde queda el valor 
    def expresion(self, nodo, destino=None):
        if isinstance(nodo, Literal):
            return nodo.valor
        if isinstance(nodo, Variable):
            return nodo.nombre
        if isinstance(nodo, Llamada):
            return self.llamada(nodo, con_resultado=True)
        if isinstance(nodo, Unario):
            if nodo.operador == "+":
                return self.expresion(nodo.operando, destino)
            y = self.expresion(nodo.operando)
            t = destino or self.temporal()
            self.emitir("minus" if nodo.operador == "-" else "!", y, "", t)
            return t
        if isinstance(nodo, BinOp):
            y = self.expresion(nodo.izquierda)
            z = self.expresion(nodo.derecha)
            t = destino or self.temporal()
            self.emitir(nodo.operador, y, z, t)
            return t
        return "?"


def generar_codigo_intermedio(arbol):
    """Devuelve la lista de Cuadruplo del programa."""
    return GeneradorCI().generar(arbol)


def cuadruplos_a_texto(cuadruplos):
    """Código de tres direcciones como texto (una instrucción por línea)."""
    return "\n".join(c.texto() for c in cuadruplos)


# PARTE 2: TRADUCTOR A JAVASCRIPT
P_OR, P_AND, P_IGUAL, P_REL, P_ADD, P_MUL, P_UNA, P_ATOM = 1, 2, 3, 4, 5, 6, 7, 8
PREC_OP = {
    "||": P_OR,
    "&&": P_AND,
    "==": P_IGUAL, "!=": P_IGUAL,
    "<": P_REL, ">": P_REL, "<=": P_REL, ">=": P_REL,
    "+": P_ADD, "-": P_ADD,
    "*": P_MUL, "/": P_MUL, "%": P_MUL,
}
ARITMETICOS = ("+", "-", "*", "/", "%")
ORDEN = ("<", ">", "<=", ">=")
LOGICOS = ("&&", "||")

# Palabras que JavaScript no permite como nombre de variable/función (o que el
# código generado necesita): si el programa las usa, se les añade un "_" al final.
_RESERVADAS_JS = {
    "break", "case", "catch", "class", "const", "continue", "debugger", "default",
    "delete", "do", "enum", "export", "extends", "false", "finally", "function",
    "import", "in", "instanceof", "new", "null", "super", "switch", "this", "throw",
    "true", "try", "typeof", "var", "with", "yield", "let", "static", "await",
    "async", "of", "undefined", "NaN", "Infinity", "Math", "console", "main",
    "arguments", "eval", "implements", "interface", "package", "private",
    "protected", "public",
}


def _envolver(texto, prec, minimo):
    return f"({texto})" if prec < minimo else texto


class TraductorJS:
    def __init__(self):
        self.lineas = []
        self.nivel = 0
        self.ambitos = []  # pila de {nombre_fuente: (nombre_emitido, tipo)}
        self.funciones = {}  # nombre_fuente -> (nombre_emitido, tipo_retorno, [tipos de parámetros])
        self.retorno_actual = None  # tipo de retorno de la función que se está traduciendo

    # -- salida 
    def linea(self, texto=""):
        self.lineas.append(("    " * self.nivel + texto) if texto else "")

    def linea_en_blanco(self):
        if self.lineas and self.lineas[-1] != "":
            self.lineas.append("")

    # -- ámbitos 
    def nombre_emitido(self, nombre):
        return nombre + "_" if nombre in _RESERVADAS_JS else nombre

    def declarar(self, nombre, tipo):
        emitido = self.nombre_emitido(nombre)
        self.ambitos[-1][nombre] = (emitido, tipo)
        return emitido

    def buscar(self, nombre):
        for ambito in reversed(self.ambitos):
            if nombre in ambito:
                return ambito[nombre]
        return (self.nombre_emitido(nombre), "int")

    # -- programa 
    def traducir(self, arbol):
        for s in arbol.sentencias:
            if isinstance(s, Funcion):
                self.funciones[s.nombre] = (
                    self.nombre_emitido(s.nombre),
                    s.tipo_retorno,
                    [p.tipo for p in s.parametros],
                )
        self.linea("// Código generado automáticamente por el traductor del compilador.")
        self.linea("function main() {")
        self.nivel += 1
        self.ambitos.append({})
        for s in arbol.sentencias:
            self.sentencia(s)
        self.ambitos.pop()
        self.nivel -= 1
        self.linea("}")
        self.linea()
        self.linea("main();")
        return "\n".join(self.lineas) + "\n"

    # -- sentencias 
    def sentencia(self, nodo):
        if isinstance(nodo, Declaracion):
            self.linea(self.texto_declaracion(nodo) + ";")
        elif isinstance(nodo, Asignacion):
            self.linea(self.texto_asignacion(nodo) + ";")
        elif isinstance(nodo, Impresion):
            argumentos = ", ".join(self.expresion(a)[0] for a in nodo.argumentos)
            self.linea(f"console.log({argumentos});")
        elif isinstance(nodo, Retorno):
            self.retornar(nodo)
        elif isinstance(nodo, Condicional):
            self.condicional(nodo)
        elif isinstance(nodo, CicloWhile):
            self.linea(f"while ({self.condicion(nodo.condicion)}) {{")
            self.cuerpo(nodo.cuerpo)
            self.linea("}")
        elif isinstance(nodo, CicloDoWhile):
            self.linea("do {")
            self.cuerpo(nodo.cuerpo)
            self.linea(f"}} while ({self.condicion(nodo.condicion)});")
        elif isinstance(nodo, CicloFor):
            self.ciclo_for(nodo)
        elif isinstance(nodo, Switch):
            self.sentencia_switch(nodo)
        elif isinstance(nodo, Romper):
            self.linea("break;")
        elif isinstance(nodo, Continuar):
            self.linea("continue;")
        elif isinstance(nodo, Funcion):
            self.funcion(nodo)
        elif isinstance(nodo, Llamada):
            self.linea(self.expresion(nodo)[0] + ";")
        elif isinstance(nodo, Bloque):
            self.linea("{")
            self.cuerpo(nodo)
            self.linea("}")

    def cuerpo(self, bloque):
        self.ambitos.append({})
        self.nivel += 1
        for s in bloque.sentencias:
            self.sentencia(s)
        self.nivel -= 1
        self.ambitos.pop()

    def funcion(self, nodo):
        emitido = self.funciones[nodo.nombre][0]
        self.ambitos.append({})  # los parámetros y el cuerpo comparten ámbito
        parametros = [self.declarar(p.nombre, p.tipo) for p in nodo.parametros]
        anterior = self.retorno_actual
        self.retorno_actual = nodo.tipo_retorno
        self.linea_en_blanco()
        self.linea(f"function {emitido}({', '.join(parametros)}) {{")
        self.nivel += 1
        for s in nodo.cuerpo.sentencias:
            self.sentencia(s)
        self.nivel -= 1
        self.linea("}")
        self.linea()
        self.retorno_actual = anterior
        self.ambitos.pop()

    def retornar(self, nodo):
        if nodo.valor is None:
            self.linea("return;")
            return
        triple = self.expresion(nodo.valor)
        texto = self.convertir(triple, self.retorno_actual) if self.retorno_actual else triple[0]
        self.linea(f"return {texto};")

    def condicional(self, nodo):
        encabezado = "if"
        actual = nodo
        while True:
            self.linea(f"{encabezado} ({self.condicion(actual.condicion)}) {{")
            self.cuerpo(actual.cuerpo)
            sino = actual.sino
            if sino is None:
                self.linea("}")
                return
            if isinstance(sino, Condicional):
                encabezado = "} else if"
                actual = sino
                continue
            self.linea("} else {")
            self.cuerpo(sino)
            self.linea("}")
            return

    def ciclo_for(self, nodo):
        self.ambitos.append({})  # la variable del for vive solo dentro del for
        if nodo.inicio is None:
            inicio = ""
        elif isinstance(nodo.inicio, Declaracion):
            inicio = self.texto_declaracion(nodo.inicio)
        else:
            inicio = self.texto_asignacion(nodo.inicio)
        cond = self.condicion(nodo.condicion) if nodo.condicion is not None else ""
        paso = self.texto_asignacion(nodo.paso) if nodo.paso is not None else ""
        self.linea(f"for ({inicio}; {cond}; {paso}) {{")
        self.cuerpo(nodo.cuerpo)
        self.linea("}")
        self.ambitos.pop()

    def sentencia_switch(self, nodo):
        self.linea(f"switch ({self.expresion(nodo.expresion)[0]}) {{")
        self.nivel += 1
        self.ambitos.append({})  # todos los case comparten un único ámbito
        for caso in nodo.casos:
            if caso.valor is None:
                self.linea("default:")
            else:
                self.linea(f"case {self.expresion(caso.valor)[0]}:")
            self.nivel += 1
            for s in caso.sentencias:
                self.sentencia(s)
            self.nivel -= 1
        self.ambitos.pop()
        self.nivel -= 1
        self.linea("}")

    def texto_declaracion(self, nodo):
        triple = self.expresion(nodo.valor) if nodo.valor is not None else None
        emitido = self.declarar(nodo.nombre, nodo.tipo_dato)  # después de evaluar el valor
        valor = self.convertir(triple, nodo.tipo_dato) if triple else self.valor_defecto(nodo.tipo_dato)
        palabra = "const" if nodo.constante else "let"
        return f"{palabra} {emitido} = {valor}"

    def texto_asignacion(self, nodo):
        emitido, tipo = self.buscar(nodo.nombre)
        op = nodo.operador
        if op in ("++", "--"):
            return f"{emitido}{op}"
        triple = self.expresion(nodo.valor)
        if op == "=":
            return f"{emitido} = {self.convertir(triple, tipo)}"

        # Asignación compuesta (+=, -=, *=, /=, %=)
        base = op[0]
        txt, prec, t = self.numerico(triple)
        if tipo == "int" and (t == "float" or base == "/"):
            # En una variable entera el resultado se trunca (la división entera trunca).
            derecha = _envolver(txt, prec, PREC_OP[base] + 1)
            return f"{emitido} = Math.trunc({emitido} {base} {derecha})"
        return f"{emitido} {op} {txt}"

    def valor_defecto(self, tipo):
        return {"int": "0", "float": "0.0", "string": '""', "bool": "false"}.get(tipo, "0")

    # -- expresiones: devuelven (texto, precedencia, tipo) 
    def expresion(self, nodo):
        if isinstance(nodo, Literal):
            tipo = "string" if nodo.tipo == "cadena" else nodo.tipo
            return (nodo.valor, P_ATOM, tipo)
        if isinstance(nodo, Variable):
            emitido, tipo = self.buscar(nodo.nombre)
            return (emitido, P_ATOM, tipo)
        if isinstance(nodo, Llamada):
            return self.llamada(nodo)
        if isinstance(nodo, Unario):
            return self.unario(nodo)
        if isinstance(nodo, BinOp):
            return self.binaria(nodo)
        return ("/* ? */", P_ATOM, "int")

    def llamada(self, nodo):
        emitido, retorno, tipos = self.funciones.get(
            nodo.nombre, (self.nombre_emitido(nodo.nombre), "int", [])
        )
        argumentos = []
        for i, arg in enumerate(nodo.argumentos):
            triple = self.expresion(arg)
            argumentos.append(self.convertir(triple, tipos[i]) if i < len(tipos) else triple[0])
        return (f"{emitido}({', '.join(argumentos)})", P_ATOM, retorno)

    def unario(self, nodo):
        if nodo.operador == "!":
            txt, p, _ = self.expresion(nodo.operando)
            return ("!" + _envolver(txt, p, P_UNA), P_UNA, "bool")
        txt, p, t = self.numerico(self.expresion(nodo.operando))
        txt = _envolver(txt, p, P_UNA)
        if txt.startswith(nodo.operador): 
            txt = f"({txt})"
        return (nodo.operador + txt, P_UNA, t)

    def binaria(self, nodo):
        op = nodo.operador
        pop = PREC_OP[op]
        izq = self.expresion(nodo.izquierda)
        der = self.expresion(nodo.derecha)

        if op in LOGICOS:
            izq, der = self.booleano(izq), self.booleano(der)
        elif op in ARITMETICOS or op in ORDEN:
            izq, der = self.numerico(izq), self.numerico(der)
        elif (izq[2] == "bool") != (der[2] == "bool"):
            izq, der = self.numerico(izq), self.numerico(der)

        l = _envolver(izq[0], izq[1], pop)
        r = _envolver(der[0], der[1], pop + 1) 

        if op in LOGICOS:
            return (f"{l} {op} {r}", pop, "bool")
        if op in ARITMETICOS:
            tipo = "float" if "float" in (izq[2], der[2]) else "int"
            if op == "/" and izq[2] == "int" and der[2] == "int":
                return (f"Math.trunc({l} / {r})", P_ATOM, "int")  # división entera
            return (f"{l} {op} {r}", pop, tipo)
        return (f"{l} {self.operador_relacional(op)} {r}", pop, "bool")

    @staticmethod
    def operador_relacional(op):
        return {"==": "===", "!=": "!=="}.get(op, op)

    @staticmethod
    def numerico(triple):
        txt, p, t = triple
        if t == "bool":
            return (f"({txt} ? 1 : 0)", P_ATOM, "int")
        return triple

    @staticmethod
    def booleano(triple):
        """Los operandos de && y || se convierten a bool."""
        txt, p, t = triple
        if t in ("int", "float"):
            return (f"{_envolver(txt, p, P_REL)} !== 0", P_IGUAL, "bool")
        return triple

    def convertir(self, triple, destino):
        """Ajusta una expresión al tipo de la variable que la recibe."""
        txt, p, t = triple
        if destino in ("int", "float") and t == "bool":
            return self.numerico(triple)[0]
        if destino == "int" and t == "float":
            return f"Math.trunc({txt})"
        return txt

    def condicion(self, nodo):
        return self.expresion(nodo)[0]


def traducir_a_javascript(arbol):
    """Traduce el árbol sintáctico a código JavaScript (texto)."""
    return TraductorJS().traducir(arbol)
