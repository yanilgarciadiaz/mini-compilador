# Traductor de Código - Versión 2

Compilador por fases: léxico, sintáctico, semántico y **traductor a JavaScript**.
En esta versión se amplió el lenguaje y la pestaña Traductor muestra únicamente el JavaScript generado (con opciones de **Copiar** y **Guardar**).

## Ejecución
cmd
python gui.py

(o `py gui.py`). Mantener todos los archivos en la misma carpeta.

## Análisis léxico (Flex)
`lexer.l` fue ampliado. Los archivos `lex.yy.c` y `analizador.exe` de la versión anterior se retiraron porque quedaron desactualizados. Para generarlos de nuevo ejecute `compilar_lexer.bat` (equivale a `flex lexer.l` y `gcc lex.yy.c -o analizador.exe`).
Mientras no exista un `analizador.exe` actualizado, la aplicación usa automáticamente `lexer_python.py`, que aplica las mismas reglas. El texto bajo el título indica cuál se está usando.

## Lenguaje
**Tipos:** `int`, `float`, `string`, `bool`, `void`. **Literales:** enteros, decimales, cadenas (con `\"`), `true`, `false`.

**Palabras reservadas:** `if else while do for switch case default break continue return print const int float string bool void true false`.

**Operadores:** aritméticos `+ - * / %`; relacionales `== != < > <= >=`; lógicos `&& || !`; asignación `=`; compuestos `+= -= *= /= %=`; incremento `++ --`.

**Sentencias**
- Declaración (`int x = 1;`) y constantes (`const int N = 5;`).
- `if / else if / else`, `while`, `do { } while (...);`, `for`, `switch / case / default`, `break`, `continue`.
- Funciones globales con parámetros tipados y retorno: `int suma(int a, int b) { return a + b; }`. Se pueden llamar antes de definirlas y ser recursivas.
- `print(a, b, ...)` se traduce a `console.log`.
- Comentarios `//` y `/* */`.

## Reglas semánticas
Errores:
- Variable o función no declarada; identificador redeclarado en el mismo ámbito; nombre de variable igual al de una función.
- Variable `void`; modificar una `const`; `const` sin valor inicial.
- Tipos incompatibles (cadena↔número, número→`bool`, `bool`→`string`).
- Operaciones aritméticas o lógicas con cadenas; comparaciones inválidas con cadenas.
- División o módulo entre el literal cero.
- Condición de `if`, `while`, `do-while` o `for` que sea una cadena.
- `break` fuera de ciclo/switch; `continue` fuera de ciclo.
- `switch`: `case` repetido, de otro tipo, que no sea literal, o más de un `default`.
- Funciones: número de argumentos incorrecto, tipos incompatibles en argumentos o retorno, `return` con valor en `void`, `return` sin valor en función no `void`, función `void` usada como valor, función no definida o duplicada.
- `++`, `--` y compuestos sobre variables no numéricas.

Advertencias: pérdida de precisión float→int, variable usada sin inicializar, variable/constante nunca usada, `return` fuera de función, función que puede terminar sin devolver valor.

## Pestaña Traductor
Si no hay errores léxicos, sintácticos ni semánticos, se muestra directamente el código JavaScript (con numeración de líneas y colores). Detalles de la traducción:
- Todo se envuelve en `main()`; las funciones se definen dentro de `main`.
- `==`/`!=` pasan a `===`/`!==`; la división entre enteros usa `Math.trunc`.
- Asignar un float a un `int` trunca el valor.
- Nombres que son palabras reservadas de JavaScript reciben un `_` al final.

`traductor.py` conserva además el generador de cuádruplos (`generar_codigo_intermedio`), que ya no se muestra y queda listo para la fase de optimización.

## Archivos de ejemplo
- `exampLenguaje.txt`: usa todo lo nuevo del lenguaje.
- `exampTraductor.txt`, `exampCorrecto.txt`: programas correctos.
- `examp.txt`: errores léxicos. `exampSintactico.txt`: error sintáctico. `exampSemantico.txt`: errores semánticos.
