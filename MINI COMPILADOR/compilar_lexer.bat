@echo off
rem Regenera el analizador lexico a partir de lexer.l (requiere Flex y GCC en el PATH)
flex lexer.l
gcc lex.yy.c -o analizador.exe
echo Listo: analizador.exe generado.
pause
