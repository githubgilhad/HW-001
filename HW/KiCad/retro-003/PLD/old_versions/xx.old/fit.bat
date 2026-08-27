@echo ###########################################################
@echo ###             FIT                                      ##
@echo ###########################################################


set "NAZEV=%~1"

C:
cd \Wincupl\WinCupl\Fitters\
@echo on

fit1508 Z:\%NAZEV%.tt2 -CUPL -dev P1508T100 -JTAG ON

@cd C:\Documents and Settings\Name
@z:
