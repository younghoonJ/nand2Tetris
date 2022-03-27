import argparse
import os
from pathlib import Path

T_KEYWARD = 0
T_SYMBOL = 1
T_IDENTIFIER = 2
T_CONST = 3
T_STRING_CONST = 4
T_EOF = 5

_kwd_else = (
    "class",
    "var",
    "int",
    "char",
    "boolean",
    "void",
)

_kwd_classvar = ("static", "field")

_kwd_constant = ("true", "false", "null", "this")

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

_keyword = _kwd_else + _kwd_classvar + _kwd_constant + _kwd_subroutines + _kwd_stmts

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
        w.write(f"<stringConstant> {tk} </stringConstant>\n")
    else:
        raise Exception(tk_type, tk)


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
            elif s in "0123456789":
                self.tokens.append((T_CONST, int(s)))
            else:
                self.tokens.append((T_IDENTIFIER, s))

    def is_keyword(self, line):
        for k in _keyword:
            if line.startswith(k, self.idx):
                if self.idx == self.tk_start or line[self.idx - 1] == " ":
                    self.make_token(line[self.tk_start: self.idx])
                    self.tokens.append((T_KEYWARD, line[self.idx: self.idx + len(k)]))
                    self.idx += len(k)
                    self.tk_start = self.idx
                    return True
        return False

    def is_symbol(self, line):
        for k in _symbol:
            if line.startswith(k, self.idx):
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
                return True
        return False

    def tokenize_line(self, line):
        self.idx = 0
        self.tk_start = 0
        self.tokens = []
        idx = line.find("//")
        if idx > -1:
            line = line[:idx]
        while self.idx < len(line):
            if self.is_keyword(line):
                pass
            elif self.is_symbol(line):
                pass
            else:
                self.idx += 1


TAG_TOKENS = "<tokens>"
TAG_KWD = "<keyword>"
TAG_IDENTIFIER = "<identifier>"
TAG_STRCONST = "<stringConstant>"
TAG_INTCONST = "<integerConstant>"
TAG_SYMBOL = "<symbol>"
TAG_EOF = "</tokens>"

str2type = {
    TAG_KWD: T_KEYWARD,
    TAG_IDENTIFIER: T_IDENTIFIER,
    TAG_STRCONST: T_STRING_CONST,
    TAG_INTCONST: T_CONST,
    TAG_SYMBOL: T_SYMBOL,
    TAG_EOF: T_EOF,
}


def advance(f):
    s = f.readline().strip()
    if s == TAG_TOKENS:
        return advance(f)
    elif s == TAG_EOF:
        return T_EOF, ""
    elif s == "":
        return advance(f)
    else:
        idx0 = s.find(">")
        idx1 = s.find("</")
        tag = s[: idx0 + 1].strip()
        content = s[idx0 + 1: idx1].strip()
        return str2type[tag], content


def process(expected: str, tk: str, tk_type: int, f, w):
    if expected == tk:
        write_token(tk_type, tk, w)
        return advance(f)
    else:
        raise Exception(expected, tk, tk_type)


def compile_kwd(tk, tk_type, f, w):
    if tk == "class":
        return compile_class(tk, tk_type, f, w)
    elif tk in _kwd_subroutines:
        return compile_subroutine(tk, tk_type, f, w)
    elif tk == "var":
        w.write("<varDec>\n")
        tk_type, tk = process("var", tk, tk_type, f, w)
        tk_type, tk = compile_until(tk, tk_type, T_SYMBOL, ';', f, w)
        tk_type, tk = process(";", tk, tk_type, f, w)
        w.write("</varDec>\n")
        return tk_type, tk
    elif tk in _kwd_classvar:
        w.write("<classVarDec>\n")
        tk_type, tk = process(tk, tk, tk_type, f, w)
        tk_type, tk = compile_until(tk, tk_type, T_SYMBOL, ';', f, w)
        tk_type, tk = process(";", tk, tk_type, f, w)
        w.write("</classVarDec>\n")
        return tk_type, tk
    elif tk in _kwd_stmts:
        return compile_stmts(tk, tk_type, f, w)
    else:
        return process(tk, tk, tk_type, f, w)


def compile_stmts(tk, tk_type, f, w):
    if tk == "let":
        return compile_let_stmt(tk, tk_type, f, w)
    elif tk == "do":
        return compile_do_stmt(tk, tk_type, f, w)
    elif tk == "while":
        return compile_while_stmt(tk, tk_type, f, w)
    elif tk == "return":
        return compile_return_stmt(tk, tk_type, f, w)
    elif tk == "if":
        return compile_if_stmt(tk, tk_type, f, w)


def compile_let_stmt(tk, tk_type, f, w):
    w.write("<letStatement>\n")
    tk_type, tk = process("let", tk, tk_type, f, w)
    tk_type, tk = process(tk, tk, tk_type, f, w)  # varname
    if tk == "[" and tk_type == T_SYMBOL:
        tk_type, tk = process("[", tk, tk_type, f, w)
        tk_type, tk = compile_exps(tk, tk_type, f, w)
        tk_type, tk = process("]", tk, tk_type, f, w)
    tk_type, tk = process("=", tk, tk_type, f, w)
    tk_type, tk = compile_exps(tk, tk_type, f, w)
    tk_type, tk = process(";", tk, tk_type, f, w)
    w.write("</letStatement>\n")
    return tk_type, tk


def compile_do_stmt(tk, tk_type, f, w):
    w.write("<doStatement>\n")
    tk_type, tk = process("do", tk, tk_type, f, w)
    tk_type, tk = process(tk, tk, tk_type, f, w)
    tk_type, tk = compile_subrt_call(tk, tk_type, f, w)
    tk_type, tk = process(";", tk, tk_type, f, w)
    w.write("</doStatement>\n")
    return tk_type, tk


def compile_return_stmt(tk, tk_type, f, w):
    w.write("<returnStatement>\n")
    tk_type, tk = process("return", tk, tk_type, f, w)
    if tk != ";":
        tk_type, tk = compile_exps(tk, tk_type, f, w)
    tk_type, tk = process(";", tk, tk_type, f, w)
    w.write("</returnStatement>\n")
    return tk_type, tk


def compile_while_stmt(tk, tk_type, f, w):
    w.write("<whileStatement>\n")
    tk_type, tk = process("while", tk, tk_type, f, w)
    tk_type, tk = process("(", tk, tk_type, f, w)
    tk_type, tk = compile_exps(tk, tk_type, f, w)
    tk_type, tk = process(")", tk, tk_type, f, w)
    tk_type, tk = process("{", tk, tk_type, f, w)
    w.write("<statements>\n")
    tk_type, tk = compile_until(tk, tk_type, T_SYMBOL, "}", f, w)
    w.write("</statements>\n")
    tk_type, tk = process("}", tk, tk_type, f, w)
    w.write("</whileStatement>\n")
    return tk_type, tk


def compile_exps(tk, tk_type, f, w):
    w.write("<expression>\n")
    tk_type, tk = compile_term(tk, tk_type, f, w)
    while tk in _op and tk_type == T_SYMBOL:
        tk_type, tk = process(tk, tk, tk_type, f, w)
        tk_type, tk = compile_term(tk, tk_type, f, w)
    w.write("</expression>\n")
    return tk_type, tk


def compile_subrt_call(tk, tk_type, f, w):
    if tk == "(" and tk_type == T_SYMBOL:
        tk_type, tk = process("(", tk, tk_type, f, w)
        tk_type, tk = compile_exps_list(tk, tk_type, f, w)
        tk_type, tk = process(")", tk, tk_type, f, w)
        return tk_type, tk
    elif tk_type == T_SYMBOL and tk == ".":
        tk_type, tk = process(".", tk, tk_type, f, w)
        tk_type, tk = process(tk, tk, tk_type, f, w)
        return compile_subrt_call(tk, tk_type, f, w)
    else:
        return tk_type, tk


def compile_term(tk, tk_type, f, w):
    w.write("<term>\n")
    if tk_type in (T_CONST, T_STRING_CONST) or tk in _kwd_constant:
        tk_type, tk = process(tk, tk, tk_type, f, w)
    elif tk_type == T_IDENTIFIER:
        tk_type, tk = process(tk, tk, tk_type, f, w)
        if tk_type == T_SYMBOL and tk == "[":
            tk_type, tk = process("[", tk, tk_type, f, w)
            tk_type, tk = compile_exps(tk, tk_type, f, w)
            tk_type, tk = process("]", tk, tk_type, f, w)
        else:
            tk_type, tk = compile_subrt_call(tk, tk_type, f, w)
    elif tk == "(" and tk_type == T_SYMBOL:
        tk_type, tk = process("(", tk, tk_type, f, w)
        tk_type, tk = compile_exps(tk, tk_type, f, w)
        tk_type, tk = process(")", tk, tk_type, f, w)
    elif tk in ("-", "~"):
        tk_type, tk = process(tk, tk, tk_type, f, w)
        tk_type, tk = compile_term(tk, tk_type, f, w)
    w.write("</term>\n")
    return tk_type, tk


def compile_exps_list(tk, tk_type, f, w):
    w.write("<expressionList>\n")
    while True:
        if tk == ")" and tk_type == T_SYMBOL:
            break
        tk_type, tk = compile_exps(tk, tk_type, f, w)
        if tk == "," and tk_type == T_SYMBOL:
            tk_type, tk = process(",", tk, tk_type, f, w)
    w.write("</expressionList>\n")
    return tk_type, tk


def compile_subroutine(tk, tk_type, f, w):
    w.write("<subroutineDec>\n")
    tk_type, tk = process(tk, tk, tk_type, f, w)  # function
    tk_type, tk = process(tk, tk, tk_type, f, w)  # void
    tk_type, tk = process(tk, tk, tk_type, f, w)  # main
    tk_type, tk = process("(", tk, tk_type, f, w)
    w.write("<parameterList>\n")
    tk_type, tk = compile_until(tk, tk_type, T_SYMBOL, ")", f, w)
    w.write("</parameterList>\n")
    tk_type, tk = process(")", tk, tk_type, f, w)
    w.write("<subroutineBody>\n")
    tk_type, tk = process("{", tk, tk_type, f, w)
    tk_type, tk = compile_until(tk, tk_type, T_KEYWARD, _kwd_stmts, f, w)
    w.write("<statements>\n")
    tk_type, tk = compile_until(tk, tk_type, T_SYMBOL, "}", f, w)
    w.write("</statements>\n")
    tk_type, tk = process("}", tk, tk_type, f, w)
    w.write("</subroutineBody>\n")
    w.write("</subroutineDec>\n")
    return tk_type, tk


def compile_class(tk, tk_type, f, w):
    w.write("<class>\n")
    tk_type, tk = process("class", tk, tk_type, f, w)  # class
    tk_type, tk = process(tk, tk, tk_type, f, w)  # main
    tk_type, tk = process("{", tk, tk_type, f, w)  # {
    tk_type, tk = compile_until(tk, tk_type, T_SYMBOL, "}", f, w)
    # tk_type, tk = compile_token(tk, tk_type, f, w)
    tk_type, tk = process("}", tk, tk_type, f, w)
    w.write("</class>\n")
    return tk_type, tk


def compile_if_stmt(tk, tk_type, f, w):
    w.write("<ifStatement>\n")
    tk_type, tk = process("if", tk, tk_type, f, w)
    tk_type, tk = process("(", tk, tk_type, f, w)
    tk_type, tk = compile_exps(tk, tk_type, f, w)
    tk_type, tk = process(")", tk, tk_type, f, w)
    tk_type, tk = process("{", tk, tk_type, f, w)
    w.write("<statements>\n")
    tk_type, tk = compile_until(tk, tk_type, T_SYMBOL, "}", f, w)
    w.write("</statements>\n")
    tk_type, tk = process("}", tk, tk_type, f, w)
    if tk == "else" and tk_type == T_KEYWARD:
        tk_type, tk = process("else", tk, tk_type, f, w)
        tk_type, tk = process("{", tk, tk_type, f, w)
        w.write("<statements>\n")
        tk_type, tk = compile_until(tk, tk_type, T_SYMBOL, "}", f, w)
        w.write("</statements>\n")
        tk_type, tk = process("}", tk, tk_type, f, w)
    w.write("</ifStatement>\n")
    return tk_type, tk


def compile_until(tk, tk_type, ut_type, until, f, w):
    if isinstance(until, str):
        until = (until,)
    while tk not in until or ut_type != tk_type:
        tk_type, tk = compile_token(tk, tk_type, f, w)
    return tk_type, tk


def compile_token(tk, tk_type, f, w):
    if tk_type == TAG_EOF:
        return None, None
    elif tk_type == T_KEYWARD:
        return compile_kwd(tk, tk_type, f, w)
    else:
        write_token(tk_type, tk, w)
        return advance(f)


def parse(open_file, write_file):
    f = open(open_file, "r")
    g = open(write_file, "w")
    tk_type, tk = advance(f)
    compile_token(tk, tk_type, f, g)

    f.close()
    g.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_dir")
    args = parser.parse_args()
    file_dir = Path(args.file_dir)

    lst_jack = []
    if Path.is_dir(file_dir):
        for p in file_dir.glob("*.jack"):
            fname = p.parts[-1].split(".")[0]
            lst_jack.append((p, Path(file_dir, fname + "T.xml"), Path(file_dir, fname + ".xml")))
    elif os.path.isfile(file_dir) and file_dir.parts[-1].endswith(".jack"):
        fname = file_dir.parts[-1].split(".")[0]
        pre = Path(*file_dir.parts[:-1])
        lst_jack.append((file_dir, Path(pre, fname + "T.xml"), Path(pre, fname + ".xml")))
    else:
        raise NotImplementedError

    for jack in lst_jack:
        tokenizer = JackTokenizer(input_file=jack[0], write_file=jack[1])
        tokenizer.tokenize()
        parse(jack[1], jack[2])


if __name__ == "__main__":
    main()
