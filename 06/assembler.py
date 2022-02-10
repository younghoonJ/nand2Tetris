import argparse


class Parsed:
    def __init__(self, content=None):
        self.content = content

    def set_value(self, content):
        self.content = content


class SIGFINISH(Parsed):
    ...


class C(Parsed):
    def __init__(self, content):
        super().__init__(self.parse(content))

    def parse(self, content):
        eq = content.find("=")
        if eq == -1:
            dest = "null"
        else:
            dest = content[:eq]
        sc = content.find(";")
        if sc == -1:
            comp = content[eq + 1:]
            jump = "null"
        else:
            comp = content[eq + 1: sc]
            jump = content[sc + 1:]
        return dest, comp, jump

    def to_bin(self):
        dest, comp, jump = self.content
        return "111" + self.comp(comp) + self.dest(dest) + self.jump(jump)

    def comp(self, arg):
        if arg in code_prefix:
            return "1" + map_comp[code_prefix[arg]]
        else:
            return "0" + map_comp[arg]

    def jump(self, arg):
        return map_jump[arg]

    def dest(self, arg):
        if "A" in arg:
            ret = "1"
        else:
            ret = "0"
        if "D" in arg:
            ret += "1"
        else:
            ret += "0"
        if "M" in arg:
            ret += "1"
        else:
            ret += "0"
        return ret


class A(Parsed):
    def __init__(self, content):
        super().__init__(content[1:])

    @property
    def is_symbol(self):
        return not self.content.isdigit()

    def to_bin(self):
        return bin(int(self.content))[2:].zfill(16)


class L(Parsed):
    def __init__(self, content):
        super().__init__(content[1:-1])

    def to_bin(self):
        return self.content


class Parser:
    def __init__(self, input_file):
        self.f = open(input_file, "r")
        self.inst_str = None

    def has_moreline(self):
        self.inst_str = self.f.readline()
        return bool(self.inst_str)

    def advance(self):
        if self.has_moreline():
            self.remove_comment(self.inst_str)
            if self.inst_str == "":
                self.advance()
            return self.parse(self.inst_str)
        else:
            self.f.close()
            return SIGFINISH()

    def remove_comment(self, line):
        s = line.find("//")
        if s > -1:
            line = line[:s]
        self.inst_str = line.strip()

    def parse(self, inst_str):
        if inst_str.startswith("@"):
            return A(inst_str)
        elif inst_str.startswith("(") and inst_str.endswith(")"):
            return L(inst_str)
        elif "=" in inst_str or ";" in inst_str:
            return C(inst_str)
        else:
            raise NotImplementedError()


map_jump = {
    "null": "000",
    "JGT": "001",
    "JEQ": "010",
    "JGE": "011",
    "JLT": "100",
    "JNE": "101",
    "JLE": "110",
    "JMP": "111",
}
map_comp = {
    "0": "101010",
    "1": "111111",
    "-1": "111010",
    "D": "001100",
    "A": "110000",
    "!D": "001101",
    "!A": "110001",
    "-D": "001111",
    "-A": "110011",
    "D+1": "011111",
    "A+1": "110111",
    "D-1": "001110",
    "A-1": "110010",
    "D+A": "000010",
    "D-A": "010011",
    "A-D": "000111",
    "D&A": "000000",
    "D|A": "010101",
}
code_prefix = {
    "M": "A",
    "!M": "!A",
    "-M": "-A",
    "M+1": "A+1",
    "M-1": "A-1",
    "D+M": "D+A",
    "D-M": "D-A",
    "M-D": "A-D",
    "D&M": "D&A",
    "D|M": "D|A",
}

predefined_syms = {
    "R0": 0,
    "R1": 1,
    "R2": 2,
    "R3": 3,
    "R4": 4,
    "R5": 5,
    "R6": 6,
    "R7": 7,
    "R8": 8,
    "R9": 9,
    "R10": 10,
    "R11": 11,
    "R12": 12,
    "R13": 13,
    "R14": 14,
    "R15": 15,
    "SP": 0,
    "LCL": 1,
    "ARG": 2,
    "THIS": 3,
    "THAT": 4,
    "SCREEN": 16384,
    "KBD": 24576

}


class SymbolTable:
    def __init__(self):
        self._table = {}
        self._table.update(predefined_syms)

    def add_entry(self, symbol, address):
        self._table[symbol] = address

    def contains(self, symbol):
        return symbol in self._table

    def get_address(self, symbol):
        return self._table[symbol]


class Assembler:
    def __init__(self, input_file):
        self.parser = Parser(input_file)
        self.inst = []
        self.sym_table = SymbolTable()
        self.line_no = 0
        self.var_addr = 16

    def generate(self):
        lst = []
        while True:
            s = self.parser.advance()
            if isinstance(s, SIGFINISH):
                break
            if isinstance(s, L):
                self.sym_table.add_entry(s.content, self.line_no)
            else:
                lst.append(s)
                self.line_no += 1

        for parsed in lst:
            if isinstance(parsed, L):
                raise Exception
            elif isinstance(parsed, A):
                if parsed.is_symbol:
                    if not self.sym_table.contains(parsed.content):
                        self.sym_table.add_entry(parsed.content, self.var_addr)
                        self.var_addr += 1
                    parsed.set_value(self.sym_table.get_address(parsed.content))
                self.inst.append(parsed.to_bin())
            elif isinstance(parsed, C):
                self.inst.append(parsed.to_bin())
            else:
                raise Exception()

    def save(self, write_path):
        with open(write_path + "", "w") as g:
            for i in self.inst:
                g.write(i + "\n")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Process some integers.")
    arg_parser.add_argument("asm", help=".asm file")
    args = arg_parser.parse_args()
    read_path = args.asm
    # read_path = "./rect/Rect.asm"
    write_path = read_path.replace(".asm", ".hack")

    assembler = Assembler(read_path)
    assembler.generate()
    assembler.save(write_path)
