#!/usr/bin/python -u
# vim: fileencoding=utf-8:nomodified:nowrap:textwidth=0:foldmethod=marker:foldcolumn=4:ruler:showcmd:lcs=tab\:|- list:tabstop=8:noexpandtab:nosmarttab:softtabstop=0:shiftwidth=0
"""
PSI2SI Preprocessor
Převádí .PSI (Preprocessor Simulation Input) na .SI (Simulation Input) pro WinCUPL/Winsim.
Řeší chyby starsejších verzí WinCUPL ohledně maker a teček.
"""

import sys
import re

class Preprocessor:
    def __init__(self):
        self.output = []
        self.macros = {}
        self.bus_widths = {}
        self.order_struct = []
        self.current_state = {}
        self.pending_sets = {}
        
        self.in_vectors = False
        self.in_order = False
        self.order_buffer = ""
        self.hide_depth = 0
        self.in_new_comment = False

    def run(self, text):
        # 1. Odstranění starých komentářů /* ... */, ale respektuje uvozovky
        text = self.remove_old_comments(text)
        lines = text.split('\n')
        self.process_lines(lines, {})
        return "\n".join(self.output)

    def remove_old_comments(self, text):
        def replacer(match):
            if match.group(0).startswith('/*'):
                return ""
            return match.group(0)
        # Naleze retezce v uvozovkach/apostrofech NEBO stary komentar
        return re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|/\*.*?\*/', replacer, text, flags=re.DOTALL)

    def process_lines(self, lines, local_vars):
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            idx += 1
            stripped = line.strip()

            if self.hide_depth > 0:
                if stripped.lower().startswith('#hide'): self.hide_depth += 1
                elif stripped.lower().startswith('#unhide'): self.hide_depth -= 1
                continue

            if self.in_new_comment:
                if stripped.lower().startswith('#comm_end'):
                    self.output.append('*/')
                    self.in_new_comment = False
                else:
                    self.output.append(line)
                continue

            if stripped.startswith('#'):
                match = re.match(r'#([a-zA-Z_][a-zA-Z0-9_]*)', stripped)
                if match:
                    kw = match.group(1).lower()
                    rest_of_line = stripped[match.end():].strip()

                    if kw == 'hide':
                        self.hide_depth += 1
                        continue
                    elif kw == 'unhide':
                        self.hide_depth -= 1
                        continue
                    elif kw == 'comm_start':
                        self.output.append('/* ' + rest_of_line)
                        self.in_new_comment = True
                        continue
                    elif kw == 'comment':
                        self.output.append('/* ' + rest_of_line + ' */')
                        continue
                    elif kw in ('macro', 'def_macro'):
                        name_match = re.match(r'([a-zA-Z_][A-Za-z0-9_]*)\s*(?:\((.*?)\))?', rest_of_line, re.DOTALL)
                        if name_match:
                            m_name = name_match.group(1).lower()
                            m_params_str = name_match.group(2)
                            m_params = [p.strip() for p in m_params_str.split(',')] if m_params_str else []
                            body = []
                            while idx < len(lines):
                                m_line = lines[idx]
                                idx += 1
                                if m_line.strip().lower().startswith('#end_macro'):
                                    break
                                body.append(m_line)
                            self.macros[m_name] = {'params': m_params, 'body': body}
                        continue
                    elif kw == 'end_macro':
                        continue
                    elif kw == 'call':
                        self.handle_call(rest_of_line, local_vars)
                        continue
                    elif kw == 'field_size':
                        self.parse_field_size(rest_of_line)
                        continue
                    elif kw == 'set':
                        self.handle_set(rest_of_line, local_vars)
                        continue
                    elif kw == 'gen_vector':
                        self.handle_gen_vector()
                        continue

            if local_vars:
                line = self.expand_exprs(line, local_vars)

            if self.in_order:
                self.order_buffer += line
                if ';' in line:
                    self.in_order = False
                    self.parse_order(self.order_buffer)
                    self.output.append(self.order_buffer)
                continue

            if stripped.upper().startswith('ORDER'):
                self.in_order = True
                self.order_buffer = line
                if ';' in line:
                    self.in_order = False
                    self.parse_order(self.order_buffer)
                    self.output.append(self.order_buffer)
                continue

            if stripped.upper().startswith('VECTORS'):
                self.in_vectors = True
                self.output.append(line)
                continue

            if self.in_vectors and stripped and not stripped.startswith('$'):
                self.parse_vector_line(stripped)
                self.output.append(line)
                continue

            if stripped.startswith('$'):
                self.output.append(line)
                continue

            self.output.append(line)

    def parse_field_size(self, text):
        for match in re.finditer(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\d+)', text):
            self.bus_widths[match.group(1)] = int(match.group(2))

    def handle_set(self, text, local_vars):
        text = self.expand_exprs(text, local_vars)
        match = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', text)
        if match:
            name = match.group(1)
            value = match.group(2).strip().rstrip(';').strip()
            self.pending_sets[name] = value
        else:
            print(f"Chyba: Špatná syntaxe #set: {text}", file=sys.stderr)

    def handle_gen_vector(self):
        for name, val_str in self.pending_sets.items():
            width = self.bus_widths.get(name, 1)
            self.current_state[name] = self.expand_bus_value(val_str, width)

        out_line = ""
        for item in self.order_struct:
            if item[0] == 'space':
                out_line += " " * item[1]
            elif item[0] == 'str':
                # FORMÁTOVACÍ TEXT SE DO VÝSLEDNÉHO VEKTORU NEZAPISUJE
                pass
            elif item[0] == 'signal':
                out_line += self.current_state.get(item[1], '*')
            elif item[0] == 'bus':
                name, width = item[1], item[2]
                bits = self.current_state.get(name, '*' * width)
                is_uniform = all(c == bits[0] for c in bits)
                if is_uniform:
                    out_line += f"'{bits[0]}'"
                else:
                    try:
                        hex_val = format(int(bits, 2), 'X')
                        if len(hex_val) % 2 != 0: hex_val = '0' + hex_val
                        out_line += f"'{hex_val}'"
                    except:
                        out_line += bits

        self.output.append(out_line)
        self.pending_sets.clear()

    def expand_bus_value(self, val_str, width):
        val_str = val_str.strip()
        if val_str.startswith('"') and val_str.endswith('"'):
            val_str = val_str[1:-1].strip()
        elif val_str.startswith("'") and val_str.endswith("'"):
            val_str = val_str[1:-1].strip()

        if len(val_str) == 1:
            return val_str * width
        elif len(val_str) == width:
            return val_str
        else:
            try:
                num = int(val_str, 16)
                return format(num, f'0{width}b')
            except:
                return '*' * width

    def parse_vector_line(self, line):
        idx = 0
        for item in self.order_struct:
            if item[0] == 'space':
                idx += item[1]
            elif item[0] == 'str':
                # FORMÁTOVACÍ TEXT SE VE VEKTORU NEVYSKYTUJE, INDEX SE NESMÍ POSOUVAT
                pass
            elif item[0] == 'signal':
                if idx < len(line):
                    self.current_state[item[1]] = line[idx]
                idx += 1
            elif item[0] == 'bus':
                name, width = item[1], item[2]
                while idx < len(line) and line[idx] == ' ': idx += 1
                if idx < len(line) and line[idx] in "'\"":
                    quote = line[idx]
                    end_q = line.find(quote, idx + 1)
                    if end_q != -1:
                        val_str = line[idx+1:end_q]
                        self.current_state[name] = self.expand_bus_value(val_str, width)
                        idx = end_q + 1
                    else:
                        idx += 1
                else:
                    bits = line[idx:idx+width]
                    if len(bits) == width:
                        self.current_state[name] = bits
                    idx += width

    def parse_order(self, order_str):
        match = re.search(r'ORDER\s*:(.*);', order_str, re.IGNORECASE | re.DOTALL)
        if not match: return
        content = match.group(1)
        
        tokens = []
        current = ""
        in_quote = None
        for c in content:
            if in_quote:
                current += c
                if c == in_quote: in_quote = None
            else:
                if c in "'\"": in_quote = c; current += c
                elif c == ',': tokens.append(current.strip()); current = ""
                else: current += c
        if current.strip(): tokens.append(current.strip())

        self.order_struct = []
        self.current_state = {}

        for t in tokens:
            if not t: continue
            if t.startswith('"') and t.endswith('"'):
                self.order_struct.append(('str', t))
            elif t.startswith('%'):
                try: self.order_struct.append(('space', int(t[1:])))
                except: pass
            else:
                name = t.lstrip('!')
                width = self.bus_widths.get(name, 1)
                if width > 1:
                    self.order_struct.append(('bus', name, width))
                else:
                    self.order_struct.append(('signal', name))
                self.current_state[name] = '*' * width

    def expand_exprs(self, line, local_vars):
        def replacer(match):
            expr = match.group(1)
            try:
                return self.eval_expr(expr, local_vars)
            except:
                return match.group(0)
        return re.sub(r'\{([^{}]+)\}', replacer, line)

    def eval_expr(self, expr, local_vars):
        original_expr = expr
            
        # Extrakce obalujících uvozovek (např. '{A000'+reg_num}' -> zůstane {A000'+reg_num} a víme, že obalovat máme)
        has_outer_quotes = False
        quote_char = "'"
        if len(expr) >= 2 and expr[0] in "'\"" and expr[-1] == expr[0]:
            has_outer_quotes = True
            quote_char = expr[0]
            expr = expr[1:-1]
            
        # Odstranění vnitřních uvozovek a složených závorek (není to uživatelský text, ale hexa zápis)
        expr = expr.replace('{', '').replace('}', '').replace("'", "").replace('"', '')
        
        # Převod čistě hexa slov (obsahující A-F) na pythoní 0x... syntax
        def hex_to_int(m):
            s = m.group(0)
            if re.search(r'[A-Fa-f]', s): 
                return "0x" + s
            return s
        expr = re.sub(r'[0-9A-Fa-f]+', hex_to_int, expr)
        
        # Vyhodnocení matematického výrazu. Proměnné z makra se předají jako skutečné hodnoty.
        try:
            val = eval(expr, {"__builtins__": {}}, local_vars)
        except:
            return original_expr # Fallback
            
        # Formátování výsledku: čísla vždy jako HEXA velkými písmeny
        if isinstance(val, int):
            res = format(val, 'X')
        else:
            res = str(val)
            
        if has_outer_quotes:
            res = quote_char + res + quote_char
        return res

    def parse_args(self, s):
        args = []
        current = ""
        in_quote = None
        i = 0
        while i < len(s):
            c = s[i]
            if in_quote:
                current += c
                if c == '\\':
                    if i + 1 < len(s): current += s[i+1]; i += 2; continue
                elif c == in_quote: in_quote = None
            else:
                if c in ('"', "'"): in_quote = c; current += c
                elif c == ',': args.append(current.strip()); current = ""
                else: current += c
            i += 1
        if current.strip(): args.append(current.strip())
        return args

    def handle_call(self, text, parent_vars):
        match = re.match(r'([a-zA-Z_][A-Za-z0-9_]*)\s*\((.*)?\)\s*$', text, re.DOTALL)
        if not match:
            print(f"Chyba: Špatná syntaxe #call: {text}", file=sys.stderr)
            return
        name = match.group(1).lower()
        args_str = match.group(2) or ""
        
        if name not in self.macros:
            print(f"Chyba: Volání nedefinovaného makra {name}", file=sys.stderr)
            return
            
        macro = self.macros[name]
        params = macro['params']
        args = self.parse_args(args_str)
        
        if len(params) != len(args):
            print(f"Chyba: Makro {name} očekává {len(params)} parametrů, dostalo {len(args)}", file=sys.stderr)
            return
        
        new_vars = {}
        for p, a in zip(params, args):
            a = a.strip()
            if (a.startswith('"') and a.endswith('"')) or (a.startswith("'") and a.endswith("'")):
                new_vars[p] = a[1:-1].replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
            else:
                try: new_vars[p] = int(a, 16) # Zde se parsuje vstup jako hexa
                except: new_vars[p] = a
        
        merged_vars = {**parent_vars, **new_vars}
        self.process_lines(macro['body'], merged_vars)


def main():
    if len(sys.argv) != 3:
        print("Použití: python PSI2SI.py vstup.PSI vystup.SI", file=sys.stderr)
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Chyba: Vstupní soubor '{input_file}' nenalezen.", file=sys.stderr)
        sys.exit(1)
        
    preprocessor = Preprocessor()
    result = preprocessor.run(text)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result)

if __name__ == '__main__':
    main()

