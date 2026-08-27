#!/usr/bin/python -u
# vim: fileencoding=utf-8:nomodified:nowrap:textwidth=0:foldmethod=marker:foldcolumn=4:ruler:showcmd:lcs=tab\:|- list:tabstop=8:noexpandtab:nosmarttab:softtabstop=0:shiftwidth=0
# -*- coding: utf-8 -*-

import re
import sys

def parse_order(order_line):
    """Rozloží ORDER na čisté položky (bez vykřičníků a formátování)."""
    clean = re.sub(r'"[^"]*"', '', order_line)  # Odstraní textové popisky
    clean = re.sub(r'%[0-9]+', '', clean)       # Odstraní formátování %3, %1
    clean = clean.replace('ORDER:', '').replace(';', '')
    # Striktně odstraníme vykřičníky z názvů v ORDER
    tokens = [t.strip().lstrip('!') for t in clean.split(',') if t.strip()]
    return tokens

def get_field_width(pin_name, field_sizes):
    return field_sizes.get(pin_name, 1)

def clean_pin_name(name):
    """Odstraní případný vykřičník z názvu pinu pro unifikaci v paměti."""
    return name.strip().lstrip('!')

def format_value_for_width(val, width):
    val = val.strip().strip("'").strip('"')
    if val == '.':
        return '.' * width
    if val == '*':
        return '"' + ('*' * width) + '"'
    if val in ['Z', 'X', 'L', 'H']:
        return val * width
        
    try:
        hex_digits = (width + 3) // 4
        num_val = int(val, 16) if any(c in val.lower() for c in 'abcdef') or val.startswith('0x') else int(val, 10)
        return f"'{num_val:0{hex_digits}X}'"
    except ValueError:
        return val

def parse_manual_vector(vector_line, order_pins, field_sizes):
    """Analyzuje ruční vektorový řádek a vytáhne z něj aktuální stavy pinů."""
    # Odstraníme komentáře
    clean = re.sub(r'/\*.*?\*/', '', vector_line).strip().rstrip(';')
    # Najdeme řetězce v apostrofech/uvozovkách nebo samostatná slova/znaky
    tokens = re.findall(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|\S+", clean)
    
    states = {}
    pin_idx = 0
    
    for token in tokens:
        if pin_idx >= len(order_pins):
            break
        pin = order_pins[pin_idx]
        states[pin] = token
        pin_idx += 1
        
    return states

def eval_expr(expr, context):
    for k, v in context.items():
        expr = re.sub(r'\b' + re.escape(k) + r'\b', str(v), expr)
    
    def evaluate_match(match):
        inner = match.group(1)
        hex_literals = re.findall(r"['\"]([0-9a-fA-F]+)['\"]", inner)
        for lit in hex_literals:
            inner = inner.replace(f"'{lit}'", str(int(lit, 16))).replace(f'"{lit}"', str(int(lit, 16)))
        try:
            result = eval(inner, {"__builtins__": None})
            if isinstance(result, int):
                return f"{result:X}"
            return str(result)
        except:
            return inner
            
    return re.sub(r'\{\s*(.*?)\s*\}', evaluate_match, expr)

def preprocess(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    order_pins = []
    field_sizes = {}
    macros = {}
    global_states = {} 
    
    in_macro = False
    current_macro_name = None
    current_macro_args = []
    current_macro_body = []
    output_lines = []

    for line_num, line in enumerate(lines, 1):
        clean_line = line.strip()

        if clean_line.startswith('#field_size'):
            parts = clean_line.replace('#field_size', '').split()
            for part in parts:
                if '=' in part:
                    f_name, f_size = part.split('=')
                    field_sizes[clean_pin_name(f_name)] = int(f_size.strip())
            continue

        if 'ORDER:' in line:
            order_pins = parse_order(line)
            output_lines.append(line)
            continue

        # Detekce ručních vektorů před makry pro synchronizaci stavu
        if order_pins and clean_line and not clean_line.startswith(('$', '#', '/', 'VECTORS:', '/*')):
            # Pokud řádek vypadá jako vektor (začíná signálem např. Z, 0, 1, C)
            if clean_line[0] in ['0','1','C','K','Z','X','L','H']:
                man_states = parse_manual_vector(clean_line, order_pins, field_sizes)
                global_states.update(man_states)

        # Definice makra
        macro_def_match = re.match(r'^#def_macro\s+(\w+)\s*\((.*?)\)', clean_line)
        if macro_def_match:
            in_macro = True
            current_macro_name = macro_def_match.group(1)
            current_macro_args = [a.strip() for a in macro_def_match.group(2).split(',') if a.strip()]
            current_macro_body = []
            continue

        if clean_line.startswith('#end_macro'):
            in_macro = False
            macros[current_macro_name] = {'args': current_macro_args, 'body': current_macro_body}
            continue

        if in_macro:
            current_macro_body.append(line)
            continue

        # Volání makra
        macro_call_match = re.match(r'^#call\s+(\w+)\s*\((.*?)\)', clean_line)
        if macro_call_match:
            cname = macro_call_match.group(1)
            cargs = [p.strip().strip("'").strip('"') for p in re.findall(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|[^,]+", macro_call_match.group(2))]
            
            macro = macros[cname]
            context = dict(zip(macro['args'], cargs))
            
            output_lines.append(f"/* --- Expanze {cname} --- */\n")
            
            for body_line in macro['body']:
                b_clean = body_line.strip()
                
                # Podpora pro #set uvnitř makra
                set_match = re.match(r'^#set\s+([\w!]+)\s*=\s*(.*)', b_clean)
                if set_match:
                    pin_name = clean_pin_name(set_match.group(1))
                    pin_val = eval_expr(set_match.group(2).strip().strip(';'), context)
                    global_states[pin_name] = pin_val
                    continue
                
                # Generování inteligentního vektoru
                if b_clean.startswith('#gen_vector'):
                    assignments = b_clean.replace('#gen_vector', '').split()
                    local_states = global_states.copy()
                    
                    for ass in assignments:
                        if '=' in ass:
                            p_name, p_val = ass.split('=')
                            p_name = clean_pin_name(p_name)
                            p_val = eval_expr(p_val.strip(), context)
                            local_states[p_name] = p_val
                    
                    vector_parts = []
                    for pin in order_pins:
                        width = get_field_width(pin, field_sizes)
                        val = local_states.get(pin, None)
                        
                        if val is None:
                            # Výchozí nouzové X, pokud pin nikde neexistoval
                            if width > 1:
                                formatted_part = '"' + ('X' * width) + '"'
                            else:
                                formatted_part = 'X'
                        else:
                            formatted_part = format_value_for_width(val, width)
                            
                        vector_parts.append(formatted_part)
                            
                    vector_line = " ".join(vector_parts) + " ;\n"
                    output_lines.append(vector_line)
                    continue
                
                output_lines.append(eval_expr(body_line, context))
                
            output_lines.append(f"/* --- Konec expanze {cname} --- */\n")
            continue

        # Podpora pro #set v hlavní sekci
        set_main_match = re.match(r'^#set\s+([\w!]+)\s*=\s*(.*)', clean_line)
        if set_main_match:
            pin_name = clean_pin_name(set_main_match.group(1))
            pin_val = set_main_match.group(2).strip().strip(';')
            global_states[pin_name] = pin_val
            continue

        output_lines.append(line)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)
    print(f"Úspěšně vygenerováno: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Použití: python SI_preprocess.py <vstup.psi> <vystup.si>")
    else:
        preprocess(sys.argv[1], sys.argv[2])
