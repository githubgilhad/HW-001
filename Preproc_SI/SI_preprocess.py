#!/usr/bin/python -u
# vim: fileencoding=utf-8:nomodified:nowrap:textwidth=0:foldmethod=marker:foldcolumn=4:ruler:showcmd:lcs=tab\:|- list:tabstop=8:noexpandtab:nosmarttab:softtabstop=0:shiftwidth=0


import re
import sys

def parse_hex_or_int(val_str):
    """Převádí textový parametr na číslo (detekuje hex i dec)."""
    val_str = val_str.strip().strip("'").strip('"')
    if not val_str:
        return 0
    # Pokud obsahuje hex znaky nebo je to typický hex
    try:
        return int(val_str, 16)
    except ValueError:
        try:
            return int(val_str, 10)
        except ValueError:
            return val_str # Vrátí jako text, pokud nelze převést

def eval_expr(expr, context):
    """Vyhodnotí matematický výraz uvnitř složených závorek s podporou HEX."""
    # Nahrazení parametrů z kontextu makra
    for k, v in context.items():
        # Pokud je v parametru hex řetězec bez prefixu, zkusíme ho ošetřit
        expr = re.sub(r'\b' + re.escape(k) + r'\b', f"'{v}'", expr)

    # Interní funkce pro vyhodnocení matematiky v závorkách { 'A000' + reg }
    def evaluate_match(match):
        inner = match.group(1)
        # Najde hex řetězce v apostrofech 'A000' a převede je na int
        hex_literals = re.findall(r"['\"]([0-9a-fA-F]+)['\"]", inner)
        for lit in hex_literals:
            inner = inner.replace(f"'{lit}'", str(int(lit, 16))).replace(f'"{lit}"', str(int(lit, 16)))
        
        # Dosadí čistá čísla, pokud zbyla
        for k, v in context.items():
            inner = inner.replace(k, str(parse_hex_or_int(v)))

        try:
            # Bezpečné vyhodnocení základní matematiky (+, -, *, /)
            result = eval(inner, {"__builtins__": None})
            if isinstance(result, int):
                # Vrátí jako velká hexadecimální písmena (čtyřmístně nebo dvoumístně podle potřeby)
                # Pro adresy chceme často 4 znaky, pro data 2. Zde formátujeme dynamicky na min. 2 znaky.
                return f"{result:02X}"
            return str(result)
        except Exception as e:
            return f"ERROR_EVAL({inner}): {str(e)}"

    # Nejprve vyhodnotí složitější výrazy v závorkách uvnitř řetězce
    expr = re.sub(r'\{\s*(.*?)\s*\}', evaluate_match, expr)
    return expr

def preprocess(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    macros = {}
    current_macro_name = None
    current_macro_args = []
    current_macro_body = []
    
    in_macro_definition = False
    output_lines = []

    for line_num, line in enumerate(lines, 1):
        clean_line = line.strip()

        # 1. Definice makra: #def_macro NAZEV(arg1, arg2)
        macro_def_match = re.match(r'^#def_macro\s+(\w+)\s*\((.*?)\)', clean_line)
        if macro_def_match:
            in_macro_definition = True
            current_macro_name = macro_def_match.group(1)
            current_macro_args = [a.strip() for a in macro_def_match.group(2).split(',') if a.strip()]
            current_macro_body = []
            continue

        # 2. Konec makra: #end_macro
        if clean_line.startswith('#end_macro'):
            in_macro_definition = False
            macros[current_macro_name] = {
                'args': current_macro_args,
                'body': current_macro_body
            }
            continue

        # Pokud jsme uvnitř makra, ukládáme řádky do těla
        if in_macro_definition:
            current_macro_body.append(line) # zachováme původní řádek kvůli odsazení
            continue

        # 3. Volání makra: #call NAZEV(param1, param2)
        macro_call_match = re.match(r'^#call\s+(\w+)\s*\((.*?)\)', clean_line)
        if macro_call_match:
            cname = macro_call_match.group(1)
            # Extrakce parametrů (podpora pro řetězce v uvozovkách/apostrofech)
            cargs = [p.strip().strip("'").strip('"') for p in re.findall(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|[^,]+", macro_call_match.group(2))]
            
            if cname not in macros:
                print(f"Chyba na řádku {line_num}: Makro '{cname}' neexistuje.")
                sys.exit(1)
                
            macro = macros[cname]
            if len(cargs) != len(macro['args']):
                print(f"Chyba na řádku {line_num}: Makro '{cname}' očekává {len(macro['args'])} parametrů, předáno {len(cargs)}.")
                sys.exit(1)

            # Vytvoření kontextu (mapování argument -> hodnota)
            context = dict(zip(macro['args'], cargs))
            
            # Expandování těla makra
            # output_lines.append(f"/* --- Začátek expanze makra {cname} --- */\n")
            for body_line in macro['body']:
                expanded_line = eval_expr(body_line, context)
                output_lines.append(expanded_line)
            # output_lines.append(f"/* --- Konec expanze makra {cname} --- */\n")
            continue

        # Běžné simulační řádky projdou beze změny
        output_lines.append(line)

    # Zápis hotového .si souboru
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)
    print(f"Úspěšně vygenerováno: {output_file}")

if __name__ == "__main__":
    # Spuštění: python preprocess_si.py simulace.psi barrel22.si
    if len(sys.argv) < 3:
        print("Použití: python preprocess_si.py <vstupní_soubor.psi> <výstupní_soubor.si>")
    else:
        preprocess(sys.argv[1], sys.argv[2])
