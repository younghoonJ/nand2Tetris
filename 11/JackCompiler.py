import argparse
import os
from pathlib import Path

TAG_TOKENS = "<tokens>"
TAG_KWD = "<keyword>"
TAG_IDENTIFIER = "<identifier>"
TAG_STRCONST = "<stringConstant>"
TAG_INTCONST = "<integerConstant>"
TAG_SYMBOL = "<symbol>"
TAG_EOF = "</tokens>"

T_KEYWARD = 0
T_SYMBOL = 1
T_IDENTIFIER = 2
T_CONST = 3
T_STRING_CONST = 4
T_EOF = 5

_identifier_declration = ("static", "field", "var")

_kwd_else = (
    "class",
    "var",
    "int",
    "char",
    "boolean",
    "void",
)

_kwd_classvar = ("static", "field")
_kwd_constant = ("true", "false", "null")
_kwd_constant_this = ("this",)
_kwd_subroutines = ("constructor",
                    "function",
                    "method",)

_kwd_stmts = (
    "let",
    "do",
    "if",
    "else",
    "while",
    "return",
)

_keyword = _kwd_else + _kwd_classvar + _kwd_constant + _kwd_constant_this + _kwd_subroutines + _kwd_stmts
_keyword_aspace = _kwd_else + _kwd_classvar + _kwd_subroutines + _kwd_stmts

str2type = {
    TAG_KWD: T_KEYWARD,
    TAG_IDENTIFIER: T_IDENTIFIER,
    TAG_STRCONST: T_STRING_CONST,
    TAG_INTCONST: T_CONST,
    TAG_SYMBOL: T_SYMBOL,
    TAG_EOF: T_EOF,
}

SEG_CONST = "constant"
SEG_ARG = "argument"
SEG_LCL = "local"
SEG_STATIC = "static"
SEG_THIS = "this"
SEG_THAT = "that"
SEG_PTR = "pointer"
SEG_TEMP = "temp"

kind2seg_map = {
    'arg': SEG_ARG,
    'static': SEG_STATIC,
    'var': SEG_LCL,
    'field': SEG_THIS
}

ARI_NEG = "neg"
ARI_NOT = "not"
ARI_ADD = "add"
ARI_SUB = "sub"
ARI_AND = "and"
ARI_OR = "or"
ARI_LT = "lt"
ARI_GT = "gt"
ARI_EQ = "eq"

_ARI_MAP = {
    "+": ARI_ADD,
    "-": ARI_SUB,
    "&": ARI_AND,
    "|": ARI_OR,
    "<": ARI_LT,
    ">": ARI_GT,
    "=": ARI_EQ,
    "&lt;": ARI_LT,
    "&gt;": ARI_GT,
    "&amp;": ARI_AND,
}
_MATH_MAP = {
    "*": "Math.multiply",
    "/": "Math.divide",
}

_symbol = (
    "{",
    "}",
    "(",
    ")",
    "[",
    "]",
    ".",
    ",",
    ";",)

_op = ("+",
       "-",
       "*",
       "/",
       "&",
       "|",
       "<",
       ">",
       "=",
       "~",
       "&lt;",
       "&gt;",
       "&amp;",
       )
_symbol = _symbol + _op


def write_token(tk_type, tk, w):
    if tk_type == T_CONST:
        w.write(f"<integerConstant> {tk} </integerConstant>\n")
    elif tk_type == T_IDENTIFIER:
        w.write(f"<identifier> {tk} </identifier>\n")
    elif tk_type == T_KEYWARD:
        w.write(f"<keyword> {tk} </keyword>\n")
    elif tk_type == T_SYMBOL:
        w.write(f"<symbol> {tk} </symbol>\n")
    elif tk_type == T_STRING_CONST:
        w.write(f"<stringConstant> \"{tk}\" </stringConstant>\n")
    else:
        raise Exception(tk_type, tk)


class SymbolTable:
    def __init__(self):
        self.table = None
        self.cnt = None
        self.reset()

    def reset(self):
        self.table = {}
        self.cnt = {
            "static": 0,
            "field": 0,
            "arg": 0,
            "var": 0
        }

    def __getitem__(self, item):
        return self.table[item]

    def __contains__(self, item):
        return item in self.table

    def define(self, name: str, type_: str, kind: str):
        self.table[name] = (type_, kind, self.cnt[kind])
        self.cnt[kind] += 1

    def var_count(self, kind):
        return self.cnt[kind]

    def kindof(self, name):
        v = self.table.get(name, None)
        if v is not None:
            return v[0]
        else:
            return v

    def typeof(self, name):
        return self.table.get(name)[1]

    def indexof(self, name):
        return self.table.get(name)[2]


class CompileEngine:
    def __init__(self, open_file, write_file, vm_write_file):
        self.open_file = open_file
        self.write_file = write_file
        self.f = None
        self.w = None
        self.tk_type = -1
        self.tk = ""
        self.prev_kwd = ""
        self.type = ""
        self.cls_sym_table = SymbolTable()
        self.subrt_sym_table = SymbolTable()
        self.vmwriter = VMWriter(vm_write_file)
        self.cls_name = None
        self.label_cnt = 0
        self.dec_names = []

    def get_and_increament(self):
        i = self.label_cnt
        self.label_cnt += 1
        return i

    def get_sym(self, item):
        if item in self.subrt_sym_table:
            return self.subrt_sym_table[item]
        elif item in self.cls_sym_table:
            return self.cls_sym_table[item]
        else:
            return None, None, None

    def advance(self):
        s = self.f.readline().strip()
        if s == TAG_TOKENS:
            self.advance()
        elif s == TAG_EOF:
            self.tk_type = T_EOF
            self.tk = ""
        elif s == "":
            self.advance()
        else:
            idx0 = s.find(">")
            idx1 = s.find("</")
            tag = s[: idx0 + 1].strip()
            content = s[idx0 + 1: idx1].strip()
            self.tk_type = str2type[tag]
            self.tk = content

    def write_token(self):
        if self.tk_type == T_CONST:
            self.w.write(f"<integerConstant> {self.tk} </integerConstant>\n")
        elif self.tk_type == T_IDENTIFIER:
            self.w.write(f"<identifier> {self.tk} </identifier>\n")
        elif self.tk_type == T_KEYWARD:
            self.w.write(f"<keyword> {self.tk} </keyword>\n")
        elif self.tk_type == T_SYMBOL:
            self.w.write(f"<symbol> {self.tk} </symbol>\n")
        elif self.tk_type == T_STRING_CONST:
            self.w.write(f"<stringConstant> {self.tk} </stringConstant>\n")
        else:
            raise Exception(self.tk_type, self.tk)

    def process(self, expected: str):
        print(expected, self.tk)
        if expected == self.tk:
            self.write_token()
            self.advance()
        else:
            raise Exception(expected, self.tk, self.tk_type)

    def compile(self):
        self.f = open(self.open_file, "r")
        self.w = open(self.write_file, "w")
        self.vmwriter.open()
        self.advance()
        self.compile_token()
        self.f.close()
        self.w.close()
        self.vmwriter.close()

    def compile_until(self, ut_type, until):
        if isinstance(until, str):
            until = (until,)
        while self.tk not in until or ut_type != self.tk_type:
            self.compile_token()

    def compile_token(self):
        if self.tk_type == TAG_EOF:
            self.tk_type = None
            self.tk = None
        elif self.tk_type == T_KEYWARD:
            self.prev_kwd = self.tk
            self.compile_kwd()
        else:
            self.write_token()
            self.advance()

    def compile_kwd(self):
        if self.tk == "class":
            self.compile_class()
        elif self.tk in _kwd_subroutines:
            self.compile_subroutine(self.tk)
        elif self.tk == "var":
            self.w.write("<varDec>\n")
            self.compile_declaration(self.subrt_sym_table)
            self.w.write("</varDec>\n")
        elif self.tk in _kwd_classvar:
            self.w.write("<classVarDec>\n")
            self.compile_declaration(self.cls_sym_table)
            self.w.write("</classVarDec>\n")
        elif self.tk in _kwd_stmts:
            self.compile_stmts()
        else:
            self.process(self.tk)

    def compile_declaration(self, sym_table):
        kind_ = self.tk
        self.process(self.tk)
        type_ = self.tk
        self.dec_names.clear()
        while True:
            self.process(self.tk)
            if self.tk_type == T_IDENTIFIER:
                self.dec_names.append(self.tk)
            if self.tk == ";" and self.tk_type == T_SYMBOL:
                break
        for n in self.dec_names:
            sym_table.define(n, type_, kind_)
        self.process(";")

    def compile_subroutine(self, fn_type):
        self.subrt_sym_table.reset()
        if fn_type == "method":
            self.subrt_sym_table.define("this", self.cls_name, "arg")
        self.w.write("<subroutineDec>\n")
        self.process(self.tk)  # function
        self.process(self.tk)  # void
        fn_name = self.tk
        self.process(self.tk)  # main
        self.process("(")
        self.w.write("<parameterList>\n")
        while self.tk != ")":
            type_ = self.tk
            self.process(type_)  # int
            var_ = self.tk
            self.process(var_)  # a
            self.subrt_sym_table.define(var_, type_, "arg")
            if self.tk == ",":
                self.process(",")
        self.w.write("</parameterList>\n")
        self.process(")")
        self.w.write("<subroutineBody>\n")
        self.process("{")
        self.compile_until(T_KEYWARD, _kwd_stmts)
        self.vmwriter.write_function(f"{self.cls_name}.{fn_name}", self.subrt_sym_table.var_count("var"))
        self.w.write("<statements>\n")
        self.compile_until(T_SYMBOL, "}")
        self.w.write("</statements>\n")
        self.process("}")
        self.w.write("</subroutineBody>\n")
        self.w.write("</subroutineDec>\n")

    def compile_class(self):
        self.cls_sym_table.reset()
        self.w.write("<class>\n")
        self.process("class")  # class
        self.cls_name = self.tk
        self.process(self.tk)  # main
        self.process("{")  # {
        self.compile_until(T_SYMBOL, "}")
        # compile_token(tk, tk_type, f, w)
        self.process("}")
        self.w.write("</class>\n")

    def compile_stmts(self):
        if self.tk == "let":
            self.compile_let_stmt()
        elif self.tk == "do":
            self.compile_do_stmt()
        elif self.tk == "while":
            self.compile_while_stmt()
        elif self.tk == "return":
            self.compile_return_stmt()
        elif self.tk == "if":
            self.compile_if_stmt()

    def compile_let_stmt(self):
        self.w.write("<letStatement>\n")
        self.process("let")
        maybe_arr_name = self.tk
        type_, kind_, idx = self.get_sym(maybe_arr_name)
        if kind_ is None:
            raise Exception
        self.process(self.tk)  # varname
        if self.tk == "[" and self.tk_type == T_SYMBOL:
            self.process("[")
            self.compile_exps()
            self.process("]")
            self.vmwriter.write_push(kind2seg_map[kind_], idx)
            self.vmwriter.write_arithmetic(ARI_ADD)
            self.vmwriter.write_pop(SEG_TEMP, 0)
            self.process("=")
            self.compile_exps()
            self.vmwriter.write_push(SEG_TEMP, 0)
            self.vmwriter.write_pop(SEG_PTR, 1)
            self.vmwriter.write_pop(SEG_THAT, 0)
        else:
            self.process("=")
            self.compile_exps()
            self.vmwriter.write_pop(kind2seg_map[kind_], idx)
        self.process(";")
        self.w.write("</letStatement>\n")

    def compile_do_stmt(self):
        self.w.write("<doStatement>\n")
        self.process("do")
        identifier = self.tk
        self.process(self.tk)
        self.compile_subrt_call(identifier)
        self.process(";")
        self.w.write("</doStatement>\n")
        self.vmwriter.write_pop(SEG_TEMP, 0)

    def compile_return_stmt(self):
        self.w.write("<returnStatement>\n")
        self.process("return")
        if self.tk != ";":
            self.compile_exps()
        else:  # if no val to return
            self.vmwriter.write_push(SEG_CONST, 0)
        self.vmwriter.write_return()
        self.process(";")
        self.w.write("</returnStatement>\n")

    def compile_while_stmt(self):
        self.w.write("<whileStatement>\n")
        self.process("while")
        self.process("(")
        label1 = f"L{self.get_and_increament()}"
        self.vmwriter.write_label(label1)
        self.compile_exps()
        self.vmwriter.write_arithmetic(ARI_NOT)
        label2 = f"L{self.get_and_increament()}"
        self.vmwriter.write_if_goto(label2)
        self.process(")")
        self.process("{")
        self.w.write("<statements>\n")
        self.compile_until(T_SYMBOL, "}")
        self.vmwriter.write_goto(label1)
        self.vmwriter.write_label(label2)
        self.w.write("</statements>\n")
        self.process("}")
        self.w.write("</whileStatement>\n")

    def compile_exps(self):
        self.w.write("<expression>\n")
        self.compile_term()
        while self.tk in _op and self.tk_type == T_SYMBOL:
            op = self.tk
            self.process(self.tk)
            self.compile_term()
            if op in _MATH_MAP:
                self.vmwriter.write_call(_MATH_MAP[op], 2)
            elif op in _ARI_MAP:
                self.vmwriter.write_arithmetic(_ARI_MAP[op])
            else:
                raise NotImplementedError(op)
        self.w.write("</expression>\n")

    def compile_subrt_call(self, cls_or_inst, n_args=0):
        if self.tk == "(" and self.tk_type == T_SYMBOL:
            self.process("(")
            n_args += self.compile_exps_list()
            self.process(")")
            self.vmwriter.write_call(cls_or_inst, n_args)
        elif self.tk_type == T_SYMBOL and self.tk == ".":
            self.process(".")
            fn_name = self.tk
            if fn_name in self.subrt_sym_table:  # subroutine
                cls_or_inst = f"{self.cls_name}.{fn_name}"
                n_args += 1
            else:
                cls_or_inst = f"{cls_or_inst}.{fn_name}"
            self.process(self.tk)
            self.compile_subrt_call(cls_or_inst, n_args)

    def compile_exps_list(self):
        n_nargs = 0
        self.w.write("<expressionList>\n")
        while True:
            if self.tk == ")" and self.tk_type == T_SYMBOL:
                break
            self.compile_exps()
            n_nargs += 1
            if self.tk == "," and self.tk_type == T_SYMBOL:
                self.process(",")
        self.w.write("</expressionList>\n")
        return n_nargs

    def compile_term(self):
        self.w.write("<term>\n")
        if self.tk_type == T_CONST:
            self.vmwriter.write_push(SEG_CONST, self.tk)
            self.process(self.tk)
        elif self.tk_type == T_STRING_CONST:
            self.tk = self.tk[1:-1]
            self.vmwriter.write_push(SEG_CONST, len(self.tk))
            self.vmwriter.write_call("String.new", 1)
            for c in self.tk:
                self.vmwriter.write_push(SEG_CONST, ord(c))
                self.vmwriter.write_call("String.appendChar", 2)
            self.process(self.tk)
        elif self.tk in _kwd_constant:
            self.vmwriter.write_push(SEG_CONST, 0)
            if self.tk == "true":
                self.vmwriter.write_arithmetic(ARI_NOT)
            self.process(self.tk)
        elif self.tk in _kwd_constant_this:
            self.vmwriter.write_push(SEG_PTR, 0)
            self.process(self.tk)
        elif self.tk_type == T_IDENTIFIER:
            maybe_arr_name = self.tk
            self.process(self.tk)
            if self.tk_type == T_SYMBOL and self.tk == "[":
                self.process("[")
                self.compile_exps()
                self.process("]")
                type_, kind_, idx = self.get_sym(maybe_arr_name)
                if kind_ is None:
                    raise Exception
                self.vmwriter.write_push(kind2seg_map[kind_], idx)
                self.vmwriter.write_arithmetic(ARI_ADD)
                self.vmwriter.write_pop(SEG_PTR, 1)
                self.vmwriter.write_push(SEG_THAT, 0)
            elif self.tk_type == T_SYMBOL and self.tk in (".", "("):
                self.compile_subrt_call(maybe_arr_name)
            else:
                type_, kind_, idx = self.get_sym(maybe_arr_name)
                if kind_ is None:
                    raise Exception
                self.vmwriter.write_push(kind2seg_map[kind_], idx)
        elif self.tk == "(" and self.tk_type == T_SYMBOL:
            self.process("(")
            self.compile_exps()
            self.process(")")
        elif self.tk in ("-", "~"):
            op = self.tk
            self.process(self.tk)
            self.compile_term()
            if op == "-":
                self.vmwriter.write_arithmetic(ARI_NEG)
            elif op == "":
                self.vmwriter.write_arithmetic(ARI_NOT)
        self.w.write("</term>\n")

    def compile_if_stmt(self):
        self.w.write("<ifStatement>\n")
        self.process("if")
        self.process("(")
        self.compile_exps()
        self.process(")")
        self.process("{")
        self.w.write("<statements>\n")
        self.compile_until(T_SYMBOL, "}")
        self.w.write("</statements>\n")
        self.process("}")
        if self.tk == "else" and self.tk_type == T_KEYWARD:
            self.process("else")
            self.process("{")
            self.w.write("<statements>\n")
            self.compile_until(T_SYMBOL, "}")
            self.w.write("</statements>\n")
            self.process("}")
        self.w.write("</ifStatement>\n")


class VMWriter:
    def __init__(self, write_file):
        self.write_file = write_file
        self.ww = None
        self.lst = []

    def w_write(self, s):
        self.lst.append(s)
        self.ww.write(s)

    def open(self):
        self.ww = open(self.write_file, 'w')

    def close(self):
        self.ww.close()

    def write_push(self, seg, idx):
        self.w_write(f"push {seg} {idx}\n")

    def write_pop(self, seg, idx):
        self.w_write(f"pop {seg} {idx}\n")

    def write_arithmetic(self, command):
        self.w_write(command + "\n")

    def write_label(self, label):
        self.w_write(f"label {label}\n")

    def write_goto(self, label):
        self.w_write(f"goto {label}\n")

    def write_if_goto(self, label):
        self.w_write(f"if-goto {label}\n")

    def write_call(self, name, n_args):
        self.w_write(f"call {name} {n_args}\n")

    def write_function(self, name, n_vars):
        self.w_write(f"function {name} {n_vars}\n")

    def write_return(self):
        self.w_write("return\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_dir")
    args = parser.parse_args()
    file_dir = Path(args.file_dir)

    lst_jack = []
    if Path.is_dir(file_dir):
        for p in file_dir.glob("*.jack"):
            fname = p.parts[-1].split(".")[0]
            lst_jack.append(
                (p, Path(file_dir, fname + "T.xml"), Path(file_dir, fname + ".xml"), Path(file_dir, fname + ".vm")))
    elif os.path.isfile(file_dir) and file_dir.parts[-1].endswith(".jack"):
        fname = file_dir.parts[-1].split(".")[0]
        pre = Path(*file_dir.parts[:-1])
        lst_jack.append((file_dir, Path(pre, fname + "T.xml"), Path(pre, fname + ".vm")))
    else:
        raise NotImplementedError

    for jack in lst_jack:
        tokenizer = JackTokenizer(input_file=jack[0], write_file=jack[1])
        tokenizer.tokenize()
        engine = CompileEngine(jack[1], jack[2], jack[3])
        engine.compile()



class JackTokenizer:
    def __init__(self, input_file, write_file) -> None:
        self.input_file = input_file
        self.write_file = write_file
        self.idx = 0
        self.tk_start = 0
        self.tokens = []

    def tokenize(self):
        f = open(self.input_file, "r")
        g = open(self.write_file, "w")
        g.write("<tokens>\n")
        is_comment = False
        for line in f.readlines():
            line = line.strip()
            if line == "":
                continue
            if line.startswith("//"):
                continue

            if is_comment:
                if line == "*/":
                    is_comment = False
                continue

            if line.startswith("/*"):
                if not line.endswith("*/"):
                    is_comment = True
                continue

            self.tokenize_line(line)
            for tk_type, tk in self.tokens:
                write_token(tk_type, tk, g)
        g.write("</tokens>")
        g.close()
        f.close()

    def make_token(self, s):
        s = s.strip()
        if s == "":
            return
        elif s.startswith('"') and s.endswith('"'):
            self.tokens.append((T_STRING_CONST, s[1:-1]))
        else:
            if " " in s:
                for i in s.split(" "):
                    self.make_token(i)
            elif s[0] in "0123456789":
                self.tokens.append((T_CONST, int(s)))
            else:
                self.tokens.append((T_IDENTIFIER, s))

    def is_keyword(self, line):
        for k in _keyword:
            if line.startswith(k, self.idx):
                if self.idx == self.tk_start or line[self.idx - 1] == " ":
                    if k in _keyword_aspace and line[self.idx + len(k)] != " ":
                        continue
                    self.make_token(line[self.tk_start: self.idx])
                    self.tokens.append((T_KEYWARD, line[self.idx: self.idx + len(k)].strip()))
                    self.idx += len(k)
                    self.tk_start = self.idx
                    return True
        return False

    def is_symbol(self, line):
        for k in _symbol:
            if line.startswith(k, self.idx):
                if k == ";" and self.idx != len(line) - 1:  # string
                    continue
                self.make_token(line[self.tk_start: self.idx])
                if k == "<":
                    sym = "&lt;"
                elif k == ">":
                    sym = "&gt;"
                elif k == "&":
                    sym = "&amp;"
                else:
                    sym = line[self.idx: self.idx + len(k)]
                self.tokens.append((T_SYMBOL, sym))
                self.idx += len(k)
                self.tk_start = self.idx
                if k == "+":
                    print("!")
                return True
        return False

    def tokenize_line(self, line):
        self.idx = 0
        self.tk_start = 0
        self.tokens = []
        idx = line.find("//")
        if idx > -1:
            line = line[:idx].strip()
        while self.idx < len(line):
            if self.is_keyword(line):
                pass
            elif self.is_symbol(line):
                pass
            else:
                self.idx += 1

if __name__ == "__main__":
    main()
