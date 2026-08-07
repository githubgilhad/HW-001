@echo off
echo ###########################################################
echo ###             CPLD                                     ##
echo ###########################################################

:: Kontrola, zda byl zadán parametr
if "%~1"=="" (
    echo Chyba: Musite zadat nazev souboru bez pripony!
    echo Priklad: pld.bat JmenoSouboru
    pause
    exit /b
)

:: Uložení parametru do proměnné
set "NAZEV=%~1"

C:
CD \wincupl\shared

cupl -bxf -m1 -u c:\Wincupl\Shared\cupl.dl  z:\%NAZEV%.PLD

copy Z:\%NAZEV%.tt2 Z:\%NAZEV%.tt2.bck
echo "backup + fixing nodes"
set "SOUBOR=Z:\%NAZEV%.tt2"
set "VBS_SKRIPT=%TEMP%\replace.vbs"

:: Vytvoreni pomocneho VBScriptu
echo Set fso = CreateObject("Scripting.FileSystemObject") > "%VBS_SKRIPT%"
echo Set f = fso.OpenTextFile("%SOUBOR%", 1) >> "%VBS_SKRIPT%"
echo text = f.ReadAll >> "%VBS_SKRIPT%"
echo f.Close >> "%VBS_SKRIPT%"
echo Set regEx = New RegExp >> "%VBS_SKRIPT%"
echo regEx.Pattern = ":1(0[1-9]|[1-9][0-9])" >> "%VBS_SKRIPT%"
echo regEx.Global = True >> "%VBS_SKRIPT%"
echo text = regEx.Replace(text, "") >> "%VBS_SKRIPT%"
echo Set f = fso.OpenTextFile("%SOUBOR%", 2) >> "%VBS_SKRIPT%"
echo f.Write text >> "%VBS_SKRIPT%"
echo f.Close >> "%VBS_SKRIPT%"

:: Spusteni VBScriptu

%SystemRoot%\System32\cscript.exe //nologo "%VBS_SKRIPT%"

:: Smazani pomocneho VBScriptu
del "%VBS_SKRIPT%"


C:
cd \Wincupl\WinCupl\Fitters\
@echo on

fit1508 Z:\%NAZEV%.tt2 -CUPL -dev P1508T100 -JTAG ON -preassign keep

@cd C:\Documents and Settings\Name
@z:
