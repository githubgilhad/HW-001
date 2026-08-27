.. vim: ft=rst showbreak=--»\  noexpandtab fileencoding=utf-8 nomodified   wrap textwidth=0 foldmethod=marker foldmarker={{{,}}} foldcolumn=4 ruler showcmd lcs=tab\:|- list tabstop=8 noexpandtab nosmarttab softtabstop=0 shiftwidth=0 linebreak  


:date: 2026.08.25 21:54:59
:_modified: 1970.01.01 00:00:00
:tags: SW
:authors: Gilhad
:summary: PSI2PS - zadani pro umelaka
:title: %summary%
:nice_title: |logo| %title% |logo|

%HEADER%

zadani
--------------------------------------------------------------------------------



Ahoj. Potrebuju napsat program na zpracovani maker (preprocessor)vytvareni name.SI souboru pro stary winsim/wincupl verze 5.30.4, pro simulaci navrhovaneho obvodu.

MOTIVACE
================================================================================

Novejsi simulator se mi nepodarilo sehnat (a nejspis ani neexistuje) a tato verze ma chybu, ze pri definici makra vzdycky spadne na "unhandled exeption". Taky neumi pouzit znak tecka pro opakovani posledni zadane hodnoty na danem miste, takze jako nejschudnejsi cesta se mi jevi prevzit cele generovani radku do vlastnich rukou a podle toho si vytvorit vlastni syntaxi.

Konkretne to chci pouzit pro chip ATF1508, a chci to pouzit ciste pro simulaci v PC, aniz bych ten chip mel vubec fyzicky v ruce. Ten chip bude slouzit jako GLUE_LOGIC pro 8bitovy pocitac s HD6309 procesorem a radou periferii a dvema EMS okny pro vyuziti vice vetsich pametovych chipu, nez CPU dokaze adresovat.  Mam pro nej pomerne komplexni navrh rovnic a potrebuju vyzkouset, jestli tam nekde nejsou logicke chyby, preklepy a tak podobne. Navrh pouziva vsech 80 dostupnych pinu (mimo JTAG rezervovavny pro programovani) a asi 120 ze 128 dostupnych MacroCells. Takze vyuziju moznosti mit v jednom souboru vic ruznych "ORDER" a "VECTORS" prikazu a testovat zvlast napriklad generovani interruptu z poctu hodinovych pulzu a zvlast cteni a zapis ruznych pripojenych chipu (nektere jsou na pridavnych MHF kartach a jejich ovladani je trochu slozitejsi, protoze jsou zaroven sdilene s jinymi systemy na tech kartach). A potrebuju ta makra napsat jednou na zacatku a pak je pouzivat v ruznych sekcich (ORDER+VECTORS), kde data budou jinak dlouha a jinak organizovana.

Vysledek se pouzije jako vstup.SI (Simulation Input) pro wincupl, ktery z nej vytvori vystup.SO (Simulation Output), pricemz kontroluje zda jsou vsechny testovane hodnoty shodne s predpokladanymi. Ja si potom prohlidnu vystup a sam zhodnotim, jak to vypada s hodnotama, pro ktere nejsou predpokladane hodnoty zname (znacene * hvezdicka v kodu, takze simulator je vypocte, zapise do vysledku, ale neporovnava s nicim).

ZADANI
================================================================================

Program PSI2SI (preprocessor from PSI to SI) cte soubor.PSI (Preproces Simulation Input) a vytvari soubor.SI (Simulation Input) pro wincupl/winsim ve formatu `cuplsim`.

* soubor.PSI obsahuje prikazy a komentare pro simulator (a tedy kopiruji do vysledneho soubor.SI)  a makra, ktera se interpretuji a expanduji (a ve vyslednem souboru bude jen jejich vystup)
* simulator je citlivy na syntaxi, negeneruj zbytecne poznamky do vysledneho souboru
* preprocessor bude pouzivan pri intenzivnim vyvoji, takze je potreba pocitat s tim, ze se ve vstupu budou vyskytovat ruzne zakomentovane kusy kodu, ktere je potreba ignorovat (protoze jinak by neplatny kod mohl rozhodit vysledky) - a udelame alternativni system komentaru, ktery bude umoznovat vnoreni
* * stavajici/stary system komentaru povazuje za komentar blok zacinajici `/*` a koncici `*/`, kde ty znacky nesmi byt soucasti retezce (tedy mezi uvozovkami)
* * pri zpracovani vstupniho souboru se zahodi vse od `/*` (lomitko hvezdicka) do nejblizsiho `*/` (hvezdicka lomitko) (nekolik `/*` za sebou `/*` se ignoruji, porad je to jeden komentar, koncici prvnim `*/` ) (s ohledem na uvozovky), napr. `/* MSG "cosi" */` je stary komentar a bude zahozen, zatimco `MSG " tady bylo /* jen tak"` neni zacatkem komentare.
* preprocesor bude pouzivat jako syntaxi znak mriz (hash, `#`) nasledovany bez mezery klicovym slovem (kdekoli na radku), od toho mista do konce radku jde o nas specialni kod, ktery se ve vystupu neobjevi. Pozor, samotny znak mriz ma v soubor.SI svuj vyznam, takze pokud neni nasledovany nasim klicovym slovem, tak se musi chovat jako obycejny znak.
* * nase klicova slova se porovnavaji bez ohledu na velikost znaku (case insensitive), takze `#macro` je totez co `#MACRO` nebo `#Macro` nebo jina variace
* * co je za nasim klicovym slovem do konce radku je nas kod a ve vystupnim souboru se neobjevi
* * `#comm_start` je zacatek komentare, ve vystupnim souboru bude nahrazen znakem pro zacatek komentare `/*` nasledovanym mezerou a zbytkem vstupniho radku. Nasledujici radky se kopiruji (a neinterpretuji) az do radku s klicovym slovem `#comm_end` kterym komentar konci. Toto klicove slovo se nahradi koncem komentare `*/` a zbytek radku se ignoruje
* * `#comment` je jednoradkovy komentar, ktery se do vystupu ulozi jako otevreni komentare `/*` zbytek radku a konec komentare `*/`
* * `#hide` a `#unhide` slouzi zavorky cokoli mezi nima se ignoruje (az na vnorene `#hide` a `#unhide`), neprovadi a ve vystupnim souboru se neobjevi
* jako symbol budu oznacovat sled znaku (a-z, A-Z, 0-9, _) bez ohledu na velikost ( `My_Macro` je totez co `MY_macro`)
* `#MACRO` definuje makro, nasleduje symbol pro jmeno makra, volitelne nasleduje seznam parametru oddeleny carkami a uzavreny v jednoduchych zavorkach, zbytek radky se ignoruje. Priklad: `#MACRO WRITE_REG (reg, value)`
* * Pri volani je aktualni hodnota parametru bud symbol, nebo retezec uzavreny v uvozovkach, resp. apostrofech. Uvozovky, resp. apostrofy a backsleshe uvnitr retezce musi byt escapovane backsleshem. Symboly se interpretuji jako hexadecimalni cisla, pokud se konverze nezdari, tak jako retezec. Priklady: `FF`, `1`, `10` jsou cisla (256,1,16), `"Hello here"`, `"Hi 'world'"`, `"say \"backslash is \\ \""`, `'uvozovky \'"\' v apostrofech'` jsou platne retezce, `reg`, `value` se berou jako retezce.
* * nasledujici radky az do `#END_MACRO` jsou telo makra (do vysledku se nekopiruji, az v miste volani makra se expanduji). Definice maker nelze vnorovat, ale uvnitr definice muze byt volani dalsiho makra.
* * `#CALL` nasledovane jmenem makra (a pripadne seznamem parametru v zavorkach) je volanim makra. Makro se v tom miste expanduje. Pocet parametru musi odpovidat definici, jinak preprocesor vypise chybu na stderr.
* * v nasledujicich radcich se obsah slozenych zavorek `{` a `}` nahradi vypoctenou hodnotu. To plati i pro vnitrek retezcu. Priklad: `$MSG "In macro WRITE_REG({reg}, {value})";` necha pri expanzi `#call WRITE_REG(7, "'80'")` ve vystupu `$MSG "In macro WRITE_REG(7, '80')";`
* * Vypoctena hodnota se uvadi jako hexadecimalni cislo s vekymi pismeny (tedy napr. `12DEAD34`, nikoli `12dead34`)
* * `#SET` je nasledovano jmenem signalu, nebo sbernice, rovnitkem a hodnotou, ktera ma byt prirazena, napr. `#SET DATA='*'`, nebo `#SET OE={active}`, nebo `#SET OE=1`. Toto se strada v nejake pomocne promenne, az do nasledujiciho `#GEN_VECTOR`. U vice prirazeni plati posledni. 
* * `#GEN_VECTOR` vygeneruje do vystupu spravne zformatovany vektor, kde jsou jako zaklad pouzity hodnoty posledniho znameho ci vygenerovaneho vektoru a nasledne jsou nahrazeny jen ty sloupce, ktere maji neco v `#SET`, viz nize.
* Preprocesor si musi hlidat prikazy `ORDER` nasledovany seznamem parametru oddelenych carkou `,` a ukonceny strednikem `;`. Seznam muze byt na vice radcich a muze obsahovat komentare. 
* * Parametr `procento+cislo`, napr. `%3` znamena pocet mezer mezi sloupci (zde napr. 3 mezery). 
* * Parametr `retezec v uvozovkach`, napr. `" COUNT:"` se tyka vystupu simulatoru, kopiruje se do vystupu, ale mezi parametry ho nezapocitame.
* * Jinak parametr je jmeno signalu, nebo sbernice, napr. `D5`, `DATA`, pripadne pred nim muze byt vykricnik pro signaly typu active low, napr. `!OE`. Pro nase ucely vykricnik sice preneseme do vystupu, ale jinak ignorujeme. Zde na velikosti pismen zalezi (nazvy jsou case sensitive).
* * * `#FIELD_SIZE` definuje sirky sbernic v bitech, napr. `#FIELD_SIZE DATA=8 CA=16 COUNT=12` definuje tri sbernice o ruznych sirkach. Pokud neni parametr v `ORDER` sbernice, tak ma sirku presne jeden bit.
* Preprocesor (mimo makro) kopiruje radky zacinajici znakem dollar `$` tak jak jsou a jinak je ignoruje (obsahuji syntaxi pro .SI)
* Neprazdne radky mezi `VECTORS` a nasledujicim `ORDER` (nebo koncem souboru) obsahuji takzvane vektory, cili sled znaku rikajici, co ma simulator simulovat/testovat. Musi presne odpovidat predchozimu `ORDER`.
* * sloupci `%3` odpovidaji tri mezery, sloupci `%1` jedna mezera atd.
* * sloupci se jmenem sbernice (napr. `DATA`) odpovida bud pocet znaku rovny sirce sbernice (napr. `11110000`, nebo `****ZZZZ`), nebo znak mezi uvozovkami, nebo mezi apostrofy (napr. `"*"`, nebo `'1'`) kde se ten znak roztahne na sirku sbernice (apostrofy plati pro vstup, uvozovky pro vystup, je mezi tim rozdil), nebo hexadecimalni cislo mezi apostrofy (napr. `'A008'`), ktere se rozvine na sirku sbernice jako bitovy vzor.
* * sloupci se jmenem signalu (cokoli neni sbernice, nebo procento, nebo retezec v uvozovkach) odpovida jeden znak (bit).
* * znaky muzou byt `01CKLHZXNP*`
* * Za defaultni hodnotu sloupce lze povazovat znak hvezdicka `*` znamenajici `simulator nejak urci`.
* * Prikaz `ORDER` definuje bitovou sirku pro `VECTORS` a tvar vypisu. Pri prikazu `ORDER` je potreba zalozit nejakou promennou/objekt/strukturu pro jeho uchovani (a zahodit starou) a hodnoty naplnit hvezdickama.
* * Po prikazu `VECTORS` je potreba sledovat platne radky a prebirat z nich aktualni hodnoty

Priklad vstupu:


.. code::

	
	MSG "### PSI macros, use SI_preprocessor.py Aa.psi Aa.si ###";
	
	/* Definujeme sirky sbernic z PLD (ostatni neuvedene piny maji automaticky sirku 1) */
	#field_size DATA=8 CA=16 COUNT=13
	
	
	#def_macro READ_REG(reg_num)
	$MSG "### READ_REG({reg_num}) ###";
	#set CA   = '{'A000'+reg_num}'
	#set Rw   = 1
	#set DATA = "*"
	
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
	
	#def_macro WRITE_REG(reg_num, value)
	$MSG "### WRITE_REG({reg_num}, {value}) ###";
	#set CA   = '{'A000'+reg_num}'
	#set Rw   = 0
	
	#set E = 0; 
	#set Q = 1;
	#set DATA="{value}"
	#gen_vector
	
	#set E = 1;
	#set DATA="{value}"
	#gen_vector
	
	#set Q = 0;
	#set DATA="{value}"
	#gen_vector
	
	#set E = 0;
	#set DATA="{value}"
	#gen_vector
	#end_macro
	
	
	MSG "## Test FIRQ (with [CNT11..6].AP = Reset; /* .AR */ ";
	ORDER: !Dev_FIRQ, %1, !Reset, BA, %1, E, Q, Rw, %1, CA, %1, DATA, %1, " CNT:", COUNT, %1, TIMER_EN, " CNT_R:", CNT_R11, CNT_R10, CNT_R9, CNT_R8 ;
	
	VECTORS:
	
	$MSG "## Reset all";
	Z 00 C01 'A008' "*" "*" *****
	
	$MSG "## write TIMER_EN true";
	Z 10 110 'A008' '80' "*" *****
	Z 10 100 'A008' '80' "*" *****
	
	$MSG "## read TIMER_EN by hands";
	Z 10 001 'A008' "*" "*" *****
	Z 10 011 'A008' "*" "*" *****
	Z 10 111 'A008' "*" "*" *****
	Z 10 101 'A008' "*" "*" *****
	#call WRITE_REG(8,80)
	#call READ_REG(0)
	#call READ_REG(1)


By melo vygenerovat neco jako  (az na spoustu prazdnych radku)


.. code::

	
	MSG "### PSI macros, use SI_preprocessor.py Aa.psi Aa.si ###";
	
	MSG "## Test FIRQ (with [CNT11..6].AP = Reset; /* .AR */ ";
	ORDER: !Dev_FIRQ, %1, !Reset, BA, %1, E, Q, Rw, %1, CA, %1, DATA, %1, " CNT:", COUNT, %1, TIMER_EN, " CNT_R:", CNT_R11, CNT_R10, CNT_R9, CNT_R8 ;
	
	VECTORS:
	
	$MSG "## Reset all";
	Z 00 C01 'A008' "*" "*" *****
	
	$MSG "## write TIMER_EN true";
	Z 10 110 'A008' '80' "*" *****
	Z 10 100 'A008' '80' "*" *****
	
	$MSG "## read TIMER_EN by hands";
	Z 10 001 'A008' "*" "*" *****
	Z 10 011 'A008' "*" "*" *****
	Z 10 111 'A008' "*" "*" *****
	Z 10 101 'A008' "*" "*" *****

	$MSG "### WRITE_REG(8, 80) ###";
	
	Z 10 010' 'A008' '80' "*" *****
	Z 10 110' 'A008' '80' "*" *****
	Z 10 100' 'A008' '80' "*" *****
	Z 10 000' 'A008' '80' "*" *****
	
	$MSG "### READ_REG(0) ###";
	
	Z 10 011' 'A000' "*" "*" *****
	Z 10 111' 'A000' "*" "*" *****
	Z 10 101' 'A000' "*" "*" *****
	Z 10 001' 'A000' "*" "*" *****
	
	$MSG "### READ_REG(1) ###";
	
	Z 10 011' 'A001' "*" "*" *****
	Z 10 111' 'A001' "*" "*" *****
	Z 10 101' 'A001' "*" "*" *****
	Z 10 001' 'A001' "*" "*" *****

Pokud potrebujes jeste neco upresnit, klidne se zeptej.

