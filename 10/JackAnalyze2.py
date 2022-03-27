T_KEYWARD = 0
T_SYMBOL = 1
T_IDENTIFIER = 2
T_CONST = 3
T_STRING_CONST = 4
T_EOF = 5

_kwd_else = (
    "Array",
    "class",
    "field",
    "static",
    "var",
    "int",
    "char",
    "boolean",
    "void",
    "true",
    "false",
    "null",
    "this",
)

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

_keyword = _kwd_else + _kwd_subroutines + _kwd_stmts

_symbol = {
    "{",
    "}",
    "(",
    ")",
    "[",
    "]",
    ".",
    ",",
    ";",
    "+",
    "-",
    "*",
    "/",
    "&",
    "|",
    "<",
    ">",
    "=",
    "~",
}


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
        raise Exception
    # print(tk_type, tk)


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


def process(expected: str, tk: str, tk_type: int, w):
    if expected == tk:
        write_token(tk_type, tk, w)
    else:
        raise Exception(tk, tk_type, expected)


def compile_kwd(kwd, tk_type, f, w):
    if kwd == "class":
        compile_class(kwd, tk_type, f, w)
    elif kwd in _kwd_subroutines:
        compile_subroutine(kwd, tk_type, f, w)
    elif kwd == "var":
        w.write("<varDec>\n")
        process("var", kwd, tk_type, w)
        tk_type, sym = compile_until(T_SYMBOL, ';', f, w)
        process(";", sym, tk_type, w)
        w.write("</varDec>\n")
    elif kwd in _kwd_stmts:
        compile_stmts(kwd, tk_type, f, w)
    # else:
    #     raise Exception(kwd)


def compile_stmts(kwd, tk_type, f, w):
    if kwd == "let":
        compile_let_stmt(kwd, tk_type, f, w)
    elif kwd == "do":
        compile_do_stmt(kwd, tk_type, f, w)
    elif kwd == "while":
        compile_while_stmt(kwd, tk_type, f, w)
    elif kwd == "return":
        compile_return_stmt(kwd, tk_type, f, w)


def get_exps(ut_type, until, f):
    tk_type, content = advance(f)
    exps = []
    while content != until or tk_type != ut_type:
        exps.append((tk_type, content))
        tk_type, content = advance(f)
    return tk_type, content, exps


def compile_exps(exps, f, w):
    w.write("<expression>\n")
    w.write(str(exps) + '\n')
    w.write("</expression>\n")


def compile_let_stmt(kwd, tk_type, f, w):
    w.write("<letStatement>\n")
    process("let", kwd, tk_type, w)
    advance_process(f, w)  # varname
    tk_type, sym, exps = get_exps(T_SYMBOL, "=", f)
    if exps:
        compile_exps(exps, f, w)
    process("=", sym, tk_type, w)
    tk_type, sym, exps = get_exps(T_SYMBOL, ";", f)
    compile_exps(exps, f, w)
    process(";", sym, tk_type, w)
    w.write("</letStatement>\n")


def compile_do_stmt(kwd, tk_type, f, w):
    w.write("<doStatement>\n")
    process("do", kwd, tk_type, w)
    tk_type, sym = compile_until(T_SYMBOL, "(", f, w)
    process("(", sym, tk_type, w)
    w.write("<expressionList>\n")

    tk_type, sym, exps = get_exps(T_SYMBOL, ")", f)
    compile_exps(exps, f, w)

    w.write("</expressionList>\n")
    process(")", sym, tk_type, w)
    advance_process(f, w, ';')
    w.write("</doStatement>\n")


def compile_return_stmt(kwd, tk_type, f, w):
    w.write("<returnStatement>\n")
    process("return", kwd, tk_type, w)
    tk_type, sym, exps = get_exps(T_SYMBOL, ";", f)
    if exps:
        compile_exps(exps, f, w)
    process(";", sym, tk_type, w)
    w.write("</returnStatement>\n")


def compile_while_stmt(kwd, tk_type, f, w):
    w.write("<whileStatement>\n")
    tk_type, sym = compile_until(T_SYMBOL, "{", f, w)
    process("{", sym, tk_type, w)
    tk_type, sym = compile_until(T_SYMBOL, "}", f, w)
    process("}", sym, tk_type, w)
    w.write("</whileStatement>\n")


def advance_process(f, w, expected=None):
    tk_type, content = advance(f)
    if expected is None:
        process(content, content, tk_type, w)
    else:
        process(expected, content, tk_type, w)


def compile_subroutine(kwd, tk_type, f, w):
    w.write("<subroutineDec>\n")
    process(kwd, kwd, tk_type, w)  # function
    advance_process(f, w)  # void
    advance_process(f, w)  # main
    advance_process(f, w, "(")

    w.write("<parameterList>\n")
    tk_type, sym = compile_until(T_SYMBOL, ")", f, w)
    w.write("</parameterList>\n")
    process(")", sym, tk_type, w)

    w.write("<subroutineBody>\n")
    advance_process(f, w, "{")
    tk_type, kwd = compile_until(T_KEYWARD, _kwd_stmts, f, w)
    w.write("<statements>\n")
    compile_stmts(kwd, tk_type, f, w)
    tk_type, sym = compile_until(T_SYMBOL, "}", f, w)
    w.write("</statements>\n")
    process("}", sym, tk_type, w)
    w.write("</subroutineBody>\n")
    w.write("</subroutineDec>\n")


def compile_class(kwd, tk_type, f, w):
    w.write("<class>\n")
    process("class", kwd, tk_type, w)  # class
    advance_process(f, w)  # main
    advance_process(f, w, "{")
    tk_type, sym = compile_until(T_SYMBOL, "}", f, w)
    process("}", sym, tk_type, w)
    w.write("</class>\n")


def compile_until(ut_type, until, f, w):
    tk_type, content = advance(f)
    if not isinstance(until, tuple):
        until = (until,)
    while content not in until or ut_type != tk_type:
        _compile(content, tk_type, f, w)
        tk_type, content = advance(f)
    return tk_type, content


def _compile(content, tk_type, f, w):
    if tk_type == TAG_EOF:
        return
    elif tk_type == T_KEYWARD:
        compile_kwd(content, tk_type, f, w)
    else:
        write_token(tk_type, content, w)


def parse(open_file, write_file):
    f = open(open_file, "r")
    g = open(write_file, "w")
    tk_type, content = advance(f)
    _compile(content, tk_type, f, g)

    f.close()
    g.close()


if __name__ == "__main__":
    tokenizer = JackTokenizer("ArrayTest/Main.jack", write_file="ArrayTest_MainT.xml")
    tokenizer.tokenize()

    parse("ArrayTest_MainT.xml", write_file="ArrayTest_Main.xml")
    # tokenizer = JackTokenizer("Square/Main.jack", write_file="Square_MainT.xml")
    # tokenizer.tokenize()
    # tokenizer = JackTokenizer("Square/Square.jack", write_file="Square_SquareT.xml")
    # tokenizer.tokenize()
    # tokenizer = JackTokenizer("Square/SquareGame.jack", write_file="Square_SquareGameT.xml")
    # tokenizer.tokenize()
    #
    # tokenizer = JackTokenizer("ExpressionLessSquare/Main.jack", write_file="ExpressionLessSquare_MainT.xml")
    # tokenizer.tokenize()
    # tokenizer = JackTokenizer("ExpressionLessSquare/Square.jack", write_file="ExpressionLessSquare_SquareT.xml")
    # tokenizer.tokenize()
    # tokenizer = JackTokenizer("ExpressionLessSquare/SquareGame.jack", write_file="ExpressionLessSquare_SquareGameT.xml")
    # tokenizer.tokenize()
