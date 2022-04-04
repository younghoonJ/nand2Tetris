import argparse
import os
from pathlib import Path

from JackTokenizer import JackTokenizer, _op

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

str2type = {
    TAG_KWD: T_KEYWARD,
    TAG_IDENTIFIER: T_IDENTIFIER,
    TAG_STRCONST: T_STRING_CONST,
    TAG_INTCONST: T_CONST,
    TAG_SYMBOL: T_SYMBOL,
    TAG_EOF: T_EOF,
}


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
        self.sym_table: SymbolTable = None
        self.vmwriter = VMWriter(vm_write_file)

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
            self.compile_subroutine()
        elif self.tk == "var":
            self.w.write("<varDec>\n")
            self.compile_declaration()
            self.w.write("</varDec>\n")
            return self.tk_type, self.tk
        elif self.tk in _kwd_classvar:
            self.w.write("<classVarDec>\n")
            self.compile_declaration()
            self.w.write("</classVarDec>\n")
        elif self.tk in _kwd_stmts:
            self.compile_stmts()
        else:
            self.process(self.tk)

    def compile_declaration(self):
        kind_ = self.tk
        self.process(self.tk)
        type_ = self.tk
        names = []
        while True:
            self.process(self.tk)
            if self.tk_type == T_IDENTIFIER:
                names.append(self.tk)
            if self.tk == ";" and self.tk_type == T_SYMBOL:
                break
        for n in names:
            self.sym_table.define(n, type_, kind_)
        self.process(";")
        return names

    def compile_subroutine(self):
        self.w.write("<subroutineDec>\n")
        self.process(self.tk)  # function
        self.process(self.tk)  # void
        self.process(self.tk)  # main
        self.process("(")
        self.w.write("<parameterList>\n")
        self.compile_until(T_SYMBOL, ")")
        self.w.write("</parameterList>\n")
        self.process(")")
        self.w.write("<subroutineBody>\n")
        self.process("{")
        self.compile_until(T_KEYWARD, _kwd_stmts)
        self.w.write("<statements>\n")
        self.compile_until(T_SYMBOL, "}")
        self.w.write("</statements>\n")
        self.process("}")
        self.w.write("</subroutineBody>\n")
        self.w.write("</subroutineDec>\n")

    def compile_class(self):
        self.cls_sym_table.reset()
        self.sym_table = self.cls_sym_table
        self.w.write("<class>\n")
        self.process("class")  # class
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
        self.process(self.tk)  # varname
        if self.tk == "[" and self.tk_type == T_SYMBOL:
            self.process("[")
            self.compile_exps()
            self.process("]")
        self.process("=")
        self.compile_exps()
        self.process(";")
        self.w.write("</letStatement>\n")

    def compile_do_stmt(self):
        self.w.write("<doStatement>\n")
        self.process("do")
        self.process(self.tk)
        self.compile_subrt_call()
        self.process(";")
        self.w.write("</doStatement>\n")

    def compile_return_stmt(self):
        self.w.write("<returnStatement>\n")
        self.process("return")
        if self.tk != ";":
            self.compile_exps()
        self.process(";")
        self.w.write("</returnStatement>\n")

    def compile_while_stmt(self):
        self.w.write("<whileStatement>\n")
        self.process("while")
        self.process("(")
        self.compile_exps()
        self.process(")")
        self.process("{")
        self.w.write("<statements>\n")
        self.compile_until(T_SYMBOL, "}")
        self.w.write("</statements>\n")
        self.process("}")
        self.w.write("</whileStatement>\n")

    def compile_exps(self):
        self.w.write("<expression>\n")
        self.compile_term()
        while self.tk in _op and self.tk_type == T_SYMBOL:
            self.process(self.tk)
            self.compile_term()
        self.w.write("</expression>\n")

    def compile_subrt_call(self):
        if self.tk == "(" and self.tk_type == T_SYMBOL:
            self.process("(")
            self.compile_exps_list()
            self.process(")")
        elif self.tk_type == T_SYMBOL and self.tk == ".":
            self.process(".")
            self.process(self.tk)
            self.compile_subrt_call()

    def compile_exps_list(self):
        self.w.write("<expressionList>\n")
        while True:
            if self.tk == ")" and self.tk_type == T_SYMBOL:
                break
            self.compile_exps()
            if self.tk == "," and self.tk_type == T_SYMBOL:
                self.process(",")
        self.w.write("</expressionList>\n")

    def compile_term(self):
        self.w.write("<term>\n")
        if self.tk_type == T_CONST:
            self.vmwriter.write_push(SEG_CONST, self.tk)
            self.process(self.tk)
        elif self.tk_type == T_STRING_CONST:
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
            # seg = kind2seg_map[self.sym_table.kindof(self.tk)]
            # self.vmwriter.write_push(seg, self.tk)
            self.process(self.tk)
            if self.tk_type == T_SYMBOL and self.tk == "[":
                self.process("[")
                self.compile_exps()
                self.process("]")
            else:
                self.compile_subrt_call()
        elif self.tk == "(" and self.tk_type == T_SYMBOL:
            self.process("(")
            self.compile_exps()
            self.process(")")
        elif self.tk in ("-", "~"):
            self.process(self.tk)
            self.compile_term()
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


SEG_CONST = "constant"
SEG_ARG = "argument"
SEG_LCL = "local"
SEG_STATIC = "static"
SEG_THIS = "this"
SEG_THAG = "that"
SEG_PTR = "pointer"
SEG_EMP = "temp"

ARI_NOT = "not"

kind2seg_map = {
    'arg': SEG_ARG,
    'static': SEG_STATIC,
    'var': SEG_LCL,
    'field': SEG_THIS
}


class VMWriter:
    def __init__(self, write_file):
        self.write_file = write_file
        self.w = None

    def open(self):
        self.w = open(self.write_file, 'w')

    def close(self):
        self.w.close()

    def write_push(self, seg, idx):
        self.w.write(f"push {seg} {idx}\n")

    def write_pop(self, seg, idx):
        self.w.write(f"pop {seg} {idx}\n")

    def write_arithmetic(self, command):
        self.w.write(command)

    def write_label(self, label):
        self.w.write(f"label {label}\n")

    def write_goto(self, label):
        self.w.write(f"goto {label}\n")

    def write_if(self, label):
        self.w.write(f"if-goto {label}\n")

    def write_call(self, name, n_args):
        self.w.write(f"call {name} {n_args}\n")

    def write_function(self, name, n_vars):
        self.w.write(f"function {name} {n_vars}\n")


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


if __name__ == "__main__":
    main()
