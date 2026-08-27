.. vim: ft=rst showbreak=--»\  noexpandtab fileencoding=utf-8 nomodified   wrap textwidth=0 foldmethod=marker foldmarker={{{,}}} foldcolumn=4 ruler showcmd lcs=tab\:|- list tabstop=8 noexpandtab nosmarttab softtabstop=0 shiftwidth=0 linebreak  

############################
:date: 2026.08.26 03:30:16
:_modified: 1970.01.01 00:00:00
:tags: SW
:authors: Gilhad
:summary: PSI2SI
:title: PSI2SI
:nice_title: |logo| %title% |logo|

%HEADER%



PSI2SI - Preprocesor pro WinCUPL
################################

**PSI2SI** (Preprocessor Simulation Input to Simulation Input) je nástroj v jazyce Python, který řeší chyby a omezení starších verzí simulatoru WinCUPL/Winsim (konkrétně verze 5.30.4 a starší).

Motivace
########

Starší verze WinCUPL obsahují chybu, kdy použití vlastních maker přímo v souborech ``.SI`` způsobí pád aplikace („unhandled exception“). Navíc chybí podpora znaku tečky ``.`` pro opakování poslední hodnoty ve vektoru. 

Tento preprocesor obchází tyto problémy tak, že vezme vlastní rozšířený soubor ``.PSI``, vyhodnotí všechna makra, provede potřebnou aritmetiku a vygeneruje čistý, zastupitelný soubor ``.SI``, který už WinCUPL bez problémů pochytí.

Instalace a použití
###################

Skript nevyžaduje žádné externí závislosti nad rámec standardní knihovny Pythonu 3.

**Základní volání:**

.. code-block:: bash

    python PSI2SI.py vstup.PSI vystup.SI

Pokud při zpracování dojde k chybě (např. chybná syntaxe makra), skript vypíše detaily na standardní chybový výstup (``stderr``) a pokračuje ve zpracování.

Syntaxe souboru .PSI
####################

Soubor ``.PSI`` je směsicí standardního kódu pro WinCUPL a speciálních direktiv preprocesoru. Direktivy začínají znakem ``#`` bez mezery.

Komentáře
=========

Staré komentáře
---------------
Standardní blokové komentáře WinCUPL jsou podporovány a jsou před zpracováním z textu odstraněny. Preprocesor respektuje uvozovky (znaky ``"`` a ``'`` uvnitř komentáře neukončí komentář předčasně).

.. code-block:: 

    /* Toto je komentář a bude smazán */
    MSG "Toto není komentář /* protoze je to v retezci */";

Nové komentáře (direktivy preprocesoru)
----------------------------------------
Preprocesor přidává vlastní systém komentářů, který podporuje vnořování a hlavně **expanzi proměnných z maker**.

* ``#comment Text s {promennou}`` – Vytvoří jednořádkový komentář. Vygeneruje: ``/* Text s hodnotou */``
* ``#comm_start Text`` a ``#comm_end`` – Vytvoří víceřádkový blok. Vše mezi těmito direktivy se zkopíruje a expandují se v něm proměnné.
* ``#//`` nebo ``#none`` – Jednořádkový "tichý" komentář. Používá se uvnitř maker. Řádek se úplně ignoruje a nic nevygeneruje.

.. code-block:: 

    #comm_start Začátek testu registru {reg_name}
    Toto je taky součástí komentáře.
    #comm_end

Definice maker
==============

Makra se definují pomocí ``#def_macro`` (nebo ``#macro``) a končí pomocí ``#end_macro``. Definice maker se nesmí vnořovat, ale uvnitř makra lze volat jiné makro.

.. code-block:: 

    #def_macro NAZEV_MAKRA(param1, param2)
        $MSG "Volani makra: {param1}, {param2}";
    #end_macro

**Předávání parametrů:**

* *Hexa symboly:* Pokud se parametr přečte jako platné hexadecimální číslo (např. ``FF``, ``10``, ``1A``), převede se interně na integer.
* *Řetězce:* Pokud je parametr uzavřen v uvozovkách nebo apostrofech (např. ``"text"`` nebo ``'A0'``), zpracuje se jako textový řetězec (s podporou escape sekvencí jako ``\"``).

Matematické výrazy (Expanze ``{...}``)
========================================

Kdekoli v textu (v ``$MSG``, v komentářích i v příkazech ``#set``) lze použít složené závorky ``{...}``. Obsah se vyhodnotí jako matematický výraz.

* Pokud je výsledkem celé číslo, formátuje se jako **velká hexadecimální hodnota** (např. ``255`` -> ``FF``).
* Lze používat standardní operátory (``+``, ``-``, ``*``, ``/``).
* Hexadecimální literály se píší bez prefixu (např. ``A000``). Kalkulačka je inteligentní – pokud slovo neodpovídá názvu parametru makra a obsahuje jen hexa znaky, převede ho na číslo.

**Příklad sčítání adres:**
Pokud voláte makro s parametrem ``reg_num = 8``, zápis ``{'A000'+reg_num}`` se vyhodnotí jako ``0xA000 + 8`` a výsledkem bude řetězec ``A008``.

Pokud výraz obalíte do uvozovek/apostrofů, např. ``'{A000'+reg_num}'``, preprocesor tyto obalovací znaky zachová a výsledkem bude ``'A008'``.

Generování vektorů (Stavový automat)
====================================

Preprocesor "sleduje" aktuální stav vektorů. Když WinCUPL vidí řádek s vektorem, preprocesor si zapamatuje hodnoty jednotlivých pinů. To umožňuje generovat nové vektory pomocí ``#SET`` a ``#GEN_VECTOR`` bez nutnosti opisovat celý řádek.

Konfigurace sběrnic (``#FIELD_SIZE``)
-------------------------------------
Definuje šířku sběrnic v bitech. Všechny piny nezmíněné v tomto seznamu mají automaticky šířku 1 bit.

.. code-block:: 

    #field_size DATA=8 ADDR=16 COUNT=13

Příkaz ORDER
------------
Preprocesor analyzuje standardní příkaz ``ORDER``. 
Důležité chování:

* Formátovací texty obalené do uvozovek (např. ``" CNT:"``) se **přenesou do výstupu, ale při generování vektorů se zcela ignorují** (nezabírají místo v datovém řádku).
* Znak ``!`` (active low) se respektuje, ale pro logiku preprocesoru se ignoruje.

Příkazy ``#SET`` a ``#GEN_VECTOR``
----------------------------------
Slouží k měnění stavu a tvorbě vektorových řádků uvnitř maker.

* ``#SET SIGNAL = HODNOTA`` – Připraví změnu pro další generovaný vektor.
* ``#GEN_VECTOR`` – Vygeneruje vektorový řádek. Vezme aktuální paměťovaný stav, přepíše pouze ty sloupce, které byly nastaveny přes ``#SET``, výsledek zapíše do výstupu a paměť aktualizuje. Seznam připravených změn se poté vymaže.

**Pravidla pro formátování hodnot v ``#SET``:**
Chování preprocesoru ohledně uvozovek a apostrofů přesně odpovídá potřebám WinCUPL:

* **Vstupní hodnoty (pro simulátor):** Chceme je obalit do *apostrofů* (např. ``'80'``).
* **Výstupní hodnoty (jen pro logování):** Chceme je obalit do *uvozovek* (např. ``"*"``).
* Pokud v ``#SET`` hodnotu **neobalíte** ničím, preprocesor ji automaticky vygeneruje v apostrofech (např. ``#SET DATA = {value}`` s hodnotou ``80`` vygeneruje ``'80'``).
* Pokud hodnotu v ``#SET`` **obalíte**, preprocesor respektuje vámi zvolený obal (např. ``#SET COUNT = "*""`` vygeneruje přesně ``"*"``).

Kompletní příklad
#################

.. code-block:: 

    MSG "### Start simulace ###";
    
    /* Definice šířek sběrnic */
    #field_size DATA=8 ADDR=16 
    
    #def_macro WRITE_REG(reg_num, value)
    #// Tento řádek se nepřeloží a nevygeneruje
    #comm_start Zapisuji data {value} na adresu {'A000'+reg_num}
    (Toto je taky součástí komentáře)
    #comm_end
    
    $MSG "### WRITE_REG({reg_num}, {value}) ###";
    
    #set ADDR = {'A000'+reg_num}
    #set Rw   = 0
    #set DATA = {value}
    
    #set E = 0; 
    #set Q = 1;
    #gen_vector
    
    #set E = 1;
    #gen_vector
    
    #set Q = 0;
    #gen_vector
    
    #set E = 0;
    #gen_vector
    #end_macro

    ORDER: !Dev_FIRQ, %1, !Reset, BA, %1, E, Q, Rw, %1, ADDR, %1, DATA, %1, " CNT:", COUNT ;
    
    VECTORS:
    
    $MSG "## Počáteční stav";
    Z 00 C01 'A008' "*" *****
    
    #call WRITE_REG(8, 80)

Výsledný soubor .SI
###################

.. code-block:: 

    MSG "### Start simulace ###";
    
    MSG "### WRITE_REG(8, 80) ###";
    
    /* Zapisuji data 80 na adresu A008
    (Toto je taky součástí komentáře)
    */
    Z 10 010 'A008' '80' *****
    Z 10 110 'A008' '80' *****
    Z 10 100 'A008' '80' *****
    Z 10 000 'A008' '80' *****
    
    ORDER: !Dev_FIRQ, %1, !Reset, BA, %1, E, Q, Rw, %1, ADDR, %1, DATA, %1, " CNT:", COUNT ;
    
    VECTORS:
    
    $MSG "## Počáteční stav";
    Z 00 C01 'A008' "*" *****

Licence
#######

Tento skript byl vytvořen pro usnadnění vývoje hardwaru na starších platformách. Můžete jej volně používat a upravovat podle svých potřeb.
