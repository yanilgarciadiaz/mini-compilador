%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int num_linea = 1;

void emitir(const char *tipo, const char *lexema) {
    printf("%s|%s|%d\n", tipo, lexema, num_linea);
}
%}

DIGITO      [0-9]
LETRA       [a-zA-Z_]
ENTERO      {DIGITO}+
DECIMAL     {DIGITO}+"."{DIGITO}+
ID          {LETRA}({LETRA}|{DIGITO})*

%%

 /* ---- Palabras reservadas ---- */
"if"|"else"|"while"|"do"|"for"|"switch"|"case"|"default"|"break"|"continue"|"return"|"print"|"const"|"int"|"float"|"string"|"bool"|"void" {
    emitir("PALABRA_RESERVADA", yytext);
}

"true"|"false" { emitir("BOOLEANO", yytext); }

 /* ---- Numeros, identificadores y cadenas ---- */
{DECIMAL} { emitir("NUMERO_DECIMAL", yytext); }
{ENTERO}  { emitir("NUMERO_ENTERO", yytext);  }
{ID}      { emitir("IDENTIFICADOR", yytext);  }

\"([^\"\\\n]|\\.)*\" { emitir("CADENA", yytext); }
\"([^\"\\\n]|\\.)*   { emitir("ERROR_LEXICO", yytext); }

 /* ---- Operadores ---- */
"=="|"!="|"<="|">=" { emitir("OP_RELACIONAL", yytext); }
"<"|">"             { emitir("OP_RELACIONAL", yytext); }
"&&"|"||"|"!"       { emitir("OP_LOGICO", yytext); }
"++"|"--"           { emitir("OP_INCREMENTO", yytext); }
"+="|"-="|"*="|"/="|"%=" { emitir("OP_ASIG_COMPUESTA", yytext); }
"="                 { emitir("OP_ASIGNACION", yytext); }
"+"|"-"|"*"|"/"|"%" { emitir("OP_ARITMETICO", yytext); }

 /* ---- Simbolos ---- */
";" { emitir("PUNTO_COMA", yytext); }
"," { emitir("COMA", yytext); }
":" { emitir("DOS_PUNTOS", yytext); }
"(" { emitir("PAR_IZQ", yytext); }
")" { emitir("PAR_DER", yytext); }
"{" { emitir("LLAVE_IZQ", yytext); }
"}" { emitir("LLAVE_DER", yytext); }

 /* ---- Comentarios y espacios ---- */
"//".*                { /* comentario de linea: se ignora */ }
"/*"([^*]|\*+[^*/])*\*+"/" {
    /* comentario de bloque: contamos saltos de linea internos */
    for (int i = 0; yytext[i]; i++) if (yytext[i] == '\n') num_linea++;
}

\n { num_linea++; }
[ \t\r]+ { /* espacios en blanco: se ignoran */ }

 /* Caracter especial de varios bytes (tildes, simbolos Unicode, etc.)
    Se agrupa como UN SOLO error, en vez de reportar cada byte por separado. */
[\xC0-\xFF][\x80-\xBF]* { emitir("ERROR_LEXICO", yytext); }

. { emitir("ERROR_LEXICO", yytext); }

%%

int yywrap(void) { return 1; }

int main(int argc, char **argv) {
    if (argc > 1) {
        FILE *f = fopen(argv[1], "r");
        if (!f) { fprintf(stderr, "No se pudo abrir %s\n", argv[1]); return 1; }
        yyin = f;
    }
    yylex();
    return 0;
}
