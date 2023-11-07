import argparse
import os
import pathlib
# from typing import Union, List
from collections import namedtuple

CHAR_NEWLINE = '\n'
_SYMBOLS = ("{", "}", "(", ")", "[", "]", ".", ",", ";",)
_OPERATORS = ("+",
              "-",
              "*",
              "/",
              "&",
              "|",
              "<",
              ">",
              "=",
              "&lt;",
              "&gt;",
              "&amp;",
              )
_UNARY_OPERATORS = ("-", "~",)
_SYMBOLS = _SYMBOLS + _OPERATORS + _UNARY_OPERATORS

_KWD_CLASS = ("class",)
_KWD_VARDEC = ("var",)
_KWD_VOID = ("void",)
_KWD_CLASSVAR = ("static", "field",)
_KWD_CONSTANT = ("true", "false", "null", "this",)
_KWD_SUBRT = ("constructor", "function", "method",)
_KWD_STMT = ("let", "do", "if", "else", "while", "return",)
_KWD_TYPE = ("int", "char", "boolean",)
_KEYWORDS = _KWD_CLASS + _KWD_VARDEC + _KWD_VOID + \
            _KWD_CLASSVAR + _KWD_CONSTANT + _KWD_SUBRT + \
            _KWD_STMT + _KWD_TYPE

_RESERVED_IDENTIFIERS = ("Array", "Keyboard", "Output",)

T_KEYWORD = 0
T_SYMBOL = 1
T_IDENTIFIER = 2
T_CONST = 3
T_STRING_CONST = 4
T_EOF = 5

POST_KWD_SEP = (' ',) + _SYMBOLS
POST_IDF_SEP = (' ',) + _SYMBOLS

OS_CLASS = ("Keyboard", "Output", "Memory", "Screen", "Sys", "Array", "Math")

Token = namedtuple("Token", "type content")


def get_tk_header(tk_type):
    if tk_type == T_CONST:
        return "integerConstant"
    elif tk_type == T_IDENTIFIER:
        return "identifier"
    elif tk_type == T_KEYWORD:
        return "keyword"
    elif tk_type == T_SYMBOL:
        return "symbol"
    elif tk_type == T_STRING_CONST:
        return "stringConstant"
    else:
        raise Exception(tk_type)


def make_token_str(tk: Token):
    header = get_tk_header(tk.type)
    return f"<{header}> {tk.content} </{header}>\n"


class JackTokenizer:

    def __init__(self, input_file, output_path):
        self.input_path = input_file
        self.output_path = output_path

        self.buff = ''
        # self.tokens: List[Token] = []
        self.tokens = []
        self.reading_string_const = False
        self.reading_integral_const = False

    def tokenize(self):
        with open(self.input_path, 'r') as f:
            is_block_comment = False

            for line in f.readlines():
                is_inline_comment = False
                i = 0
                if len(line) == 1:
                    line += ' '
                while i < len(line) - 1:
                    char_now, char_next = line[i], line[i + 1]
                    if is_block_comment:
                        if char_now == '*' and char_next == '/':
                            is_block_comment = False
                            break
                    if char_now == '/' and char_next == '*':
                        is_block_comment = True
                    if char_now == '/' and char_next == '/':
                        is_inline_comment = True
                        break
                    if not is_block_comment:
                        self.buff += char_now
                        if i == len(line) - 1:
                            self.buff += char_next
                        if self.analyze_buff(self.buff + char_next):
                            self.buff = ''
                            if self.tokens[-1][0] == T_STRING_CONST \
                                    and char_next == '\"':
                                i += 1
                    i += 1
                if is_inline_comment:
                    continue

        with open(self.output_path, 'w') as f:
            f.write("<tokens>\n")
            for token in self.tokens:
                f.write(make_token_str(token))
                # f.write(f"<{tk_header}> {token[1]} </{tk_header}>\n")
            f.write("</tokens>\n")

    def add_token(self, tk_type, tk_content):
        self.tokens.append(Token(tk_type, tk_content))

    def is_keyword(self, rext_buff):
        for kwd in _KEYWORDS:
            if rext_buff.startswith(kwd):
                if rext_buff[-1] in POST_KWD_SEP and rext_buff[:-1] == kwd:
                    self.add_token(T_KEYWORD, kwd)
                    # self.buff = self.buff[len(kwd) + 1:]
                    return True
        return False

    def is_integral_constant(self, rext_buff):
        if rext_buff[0] in "0123456789":
            idx_ = 1
            self.reading_integral_const = True
            while idx_ < len(rext_buff) and rext_buff[idx_] in "0123456789":
                idx_ += 1
            if idx_ < len(rext_buff) and rext_buff[idx_] not in "0123456789":
                self.add_token(T_CONST, rext_buff[:idx_])
                self.reading_integral_const = False
                return True
        return False

    def is_string_constant(self, rext_buff):
        if rext_buff[0] == "\"":
            self.reading_string_const = True
            last_idx = rext_buff[1:].rfind("\"")
            if last_idx > -1:
                self.reading_string_const = False
                self.add_token(T_STRING_CONST, rext_buff[1:last_idx + 1])
                return True
        return False

    def is_symbol(self, rext_buff):
        for symbol in _SYMBOLS:
            if rext_buff.startswith(symbol):
                if symbol == "<":
                    symbol = "&lt;"
                elif symbol == ">":
                    symbol = "&gt;"
                elif symbol == "&":
                    symbol = "&amp;"
                self.add_token(T_SYMBOL, symbol)
                return True
        return False

    def is_identifier(self, rext_buff):
        if rext_buff and (rext_buff[-1] in POST_IDF_SEP):
            self.add_token(T_IDENTIFIER, rext_buff[:-1])
            return True
        return False

    def analyze_buff(self, rext_buff):
        rext_buff = rext_buff.lstrip()
        if len(rext_buff) < 2:
            return False
        ret = self.is_string_constant(rext_buff)
        if ret:
            return True
        ret = self.is_integral_constant(rext_buff)
        if ret:
            return True

        if not (self.reading_string_const or self.reading_integral_const):
            return (self.is_string_constant(rext_buff) or
                    self.is_integral_constant(rext_buff) or
                    self.is_keyword(rext_buff) or
                    self.is_symbol(rext_buff) or
                    self.is_identifier(rext_buff))
        return False


LAST_TOKEN = Token(T_EOF, "T_EOF")


def is_comma_sep(tk: Token):
    return tk.type == T_SYMBOL and tk.content == ","


Row = namedtuple("Row", "name type kind index")


class SymbolTable:
    def __init__(self):
        self.table = {}
        self._idx_table = {}
        self.fn_name = None
        self.fn_kind = None
        self.fn_return_type = None
        self.num_args = None

    def isin(self, var_name: str):
        return var_name in self.table

    def reset(self):
        self.table.clear()
        self._idx_table.clear()

    def get_index(self, kind):
        if kind in self._idx_table:
            self._idx_table[kind] += 1
            return self._idx_table[kind]
        self._idx_table[kind] = 0
        return 0

    def get_row(self, name: str):
        return self.table[name]

    def define(self, name: str, type_: str, kind: str):
        self.table[name] = Row(name, type_, kind, self.get_index(kind))

    def var_count(self, kind: str):
        return sum(1 for v in self.table.values() if v.kind == kind)

    def kind_of(self, name: str):
        return self.table[name].kind

    def type_of(self, name: str):
        return self.table[name].type

    def index_of(self, name: str):
        return self.table[name].index


class ClassInfo:
    def __init__(self, sym_table_cls, sym_table_subrts):
        self.sym_table_cls = sym_table_cls
        self.sym_table_subrts = sym_table_subrts


class VMWriter:
    def __init__(self, path_to_output):
        self.vm_code = []
        self.path_to_output = path_to_output

    def clear(self):
        self.vm_code.clear()

    def close(self):
        with open(self.path_to_output, 'w') as f:
            for line in self.vm_code:
                f.write(line + '\n')

    def _write(self, code: str):
        if (len(self.vm_code) == 100):
            p = 100
        self.vm_code.append(code)

    def write_push(self, segment: str, index: int):
        self._write(f"push {segment} {index}")

    def write_pop(self, segment: str, index: int):
        self._write(f"pop {segment} {index}")

    def write_arithmetic(self, command: str):
        self._write(f"{command}")

    def write_label(self, label: str):
        self._write(f"label {label}")

    def write_goto(self, label: str):
        self._write(f"goto {label}")

    def write_if_goto(self, label: str):
        self._write(f"if-goto {label}")

    def write_call(self, name: str, nArgs: int):
        self._write(f"call {name} {nArgs}")

    def write_function(self, name: str, nVars: int):
        self._write(f"function {name} {nVars}")

    def write_return(self):
        self._write(f"return")


class JackCompiler:
    def __init__(self):
        self.input_path = None
        self.vm_writer = None
        self.tokens = []
        self.curr_idx = 0
        self.types = _KWD_TYPE

        self.class_name: str = ""
        self.sym_table_cls: SymbolTable = None
        self.sym_table_subrts = None

        self.curr_subrt_name = ""
        self.curr_subrt_type = ""

        self.while_cnt = 0
        self.if_cnt = 0

        self.write_code = False
        self.do_exps = False

        self.class_infos = {}

    def cache_class_info(self):
        self.class_infos[self.class_name] = ClassInfo(self.sym_table_cls,
                                                      self.sym_table_subrts)

    def set_paths(self, input_file, output_path):
        self.input_path = input_file
        self.vm_writer = VMWriter(output_path)

    def get_subrt_sym_table(self, subrt_name) -> SymbolTable:
        return self.sym_table_subrts[subrt_name]

    def make_token(self, line: str):
        _types = [
            ("<integerConstant>", "</integerConstant>", T_CONST),
            ("<identifier>", "</identifier>", T_IDENTIFIER),
            ("<keyword>", "</keyword>", T_KEYWORD),
            ("<symbol>", "</symbol>", T_SYMBOL),
            ("<stringConstant>", "</stringConstant>", T_STRING_CONST),
        ]

        line = line.strip()
        if line == "":
            return

        for tk_header, tk_closer, tk_type in _types:
            if line.startswith(tk_header):
                idx_start = len(tk_header) + 1
                idx_last = line.find(tk_closer) - 1
                self.tokens.append(Token(tk_type, line[idx_start:idx_last]))

    def process(self, expected, tk: Token) -> Token:
        if isinstance(expected, str):
            expected = (expected,)
        if tk.content in expected:
            return self.advance()
        raise Exception(f"expected({expected}) != {tk}")

    def load_tokens(self):

        with open(self.input_path, 'r') as f:
            for line in f.readlines():
                self.make_token(line)

    def clear_all(self):
        self.curr_idx = 0
        self.tokens.clear()
        self.vm_writer.clear()
        self.if_cnt = 0
        self.while_cnt = 0

    def compile(self, read_class_info: bool):
        self.clear_all()
        self.load_tokens()
        self.write_code = not read_class_info

        tk = self.tokens[self.curr_idx]
        tk = self.compile_class(tk)
        if tk == LAST_TOKEN and self.write_code:
            self.vm_writer.close()
        return tk

    def advance(self) -> Token:
        if self.curr_idx == len(self.tokens) - 1:
            return LAST_TOKEN
        self.curr_idx += 1
        return self.tokens[self.curr_idx]

    def compile_keyword(self, tk):
        if tk[1] in _KWD_CLASS:
            return self.compile_class(tk)
        elif tk[1] in _KWD_SUBRT:
            return self.compile_subroutine(tk)
        else:
            raise Exception

    def compile_class(self, tk: Token) -> Token:
        # self.buff_write("<class>\n")
        if not self.write_code:
            self.sym_table_cls = SymbolTable()
            self.sym_table_subrts = {}

        tk = self.process(_KWD_CLASS, tk)  # class
        self.types = self.types + (tk.content,)
        self.class_name = tk.content

        if self.write_code:
            self.sym_table_cls = self.class_infos[self.class_name].sym_table_cls
            self.sym_table_subrts = self.class_infos[
                self.class_name].sym_table_subrts

        tk = self.process(tk.content, tk)  # class name
        tk = self.process("{", tk)  # {

        while tk.type == T_KEYWORD and tk.content in _KWD_CLASSVAR:
            tk = self.compile_class_var(tk)

        while tk.type == T_KEYWORD and tk.content in _KWD_SUBRT:
            tk = self.compile_subroutine(tk)

        tk = self.process("}", tk)  # }
        # self.buff_write("</class>\n")
        return tk

    def compile_class_var(self, tk: Token) -> Token:
        # self.buff_write("<classVarDec>\n")
        kind_ = tk.content
        tk = self.process(_KWD_CLASSVAR, tk)
        if not self.is_var_type(tk):
            raise Exception
        type_ = tk.content
        tk = self.process(self.types, tk)
        name_ = tk.content
        tk = self.process(tk.content, tk)
        if not self.write_code:
            self.sym_table_cls.define(name_, type_, kind_)

        while is_comma_sep(tk):
            tk = self.process(",", tk)
            name_ = tk.content
            tk = self.process(tk.content, tk)
            if not self.write_code:
                self.sym_table_cls.define(name_, type_, kind_)

        tk = self.process(";", tk)
        # self.buff_write("</classVarDec>\n")
        return tk

    def is_kwd_void(self, tk: Token):
        return tk.type == T_KEYWORD and tk.content in _KWD_VOID

    def compile_subroutine(self, tk: Token):
        self.if_cnt = 0
        self.while_cnt = 0
        if not self.write_code:
            subrt_table = SymbolTable()
            subrt_table.fn_kind = tk.content
            if tk.content == "method":
                subrt_table.define("this", self.class_name, "arg")
        self.curr_subrt_type = tk.content

        tk = self.process(_KWD_SUBRT, tk)
        if not self.is_var_type(tk) and not self.is_kwd_void(tk):
            raise Exception

        if not self.write_code:
            subrt_table.fn_return_type = tk.content

        tk = self.process(_KWD_VOID + self.types, tk)

        self.curr_subrt_name = tk.content
        if not self.write_code:
            subrt_table.fn_name = self.curr_subrt_name
            self.sym_table_subrts[self.curr_subrt_name] = subrt_table

        tk = self.process(tk.content, tk)  # subroutineName

        tk = self.process("(", tk)
        tk = self.compile_parameter_list(tk)
        tk = self.process(")", tk)

        tk = self.process("{", tk)
        while tk.type == T_KEYWORD and tk.content in _KWD_VARDEC:
            tk = self.compile_var_dec(tk)

        if self.write_code:
            subrt_table = self.get_subrt_sym_table(self.curr_subrt_name)
            self.vm_writer.write_function(
                f"{self.class_name}.{self.curr_subrt_name}",
                subrt_table.var_count("var"))

            if self.curr_subrt_type == "constructor":
                self.vm_writer.write_push("constant",
                                          self.sym_table_cls.var_count("field"))
                self.vm_writer.write_call("Memory.alloc", 1)
                self.vm_writer.write_pop("pointer", 0)
            elif self.curr_subrt_type == "method":
                self.vm_writer.write_push("argument", 0)
                self.vm_writer.write_pop("pointer", 0)

        tk = self.compile_statements(tk)
        tk = self.process("}", tk)
        return tk

    def compile_statements(self, tk: Token):
        while tk.type == T_KEYWORD and tk.content in _KWD_STMT:
            tk = self.compile_statement(tk)
        return tk

    def get_seg_index(self, var_name, subrt_name: str):
        subrt_table = self.get_subrt_sym_table(subrt_name)
        if not subrt_table.isin(var_name):
            if self.sym_table_cls.isin(var_name):
                kind_ = self.sym_table_cls.kind_of(var_name)
                if kind_ == "field":
                    return "this", self.sym_table_cls.index_of(var_name)
                elif kind_ == "static":
                    return "static", self.sym_table_cls.index_of(var_name)
                else:
                    raise NotImplementedError
            else:
                raise NotImplementedError

        row = subrt_table.get_row(var_name)
        if row.kind == "var":
            return "local", row.index
        elif row.kind == "arg":
            if self.curr_subrt_type in ("function", "method", "constructor"):
                return "argument", row.index

        raise NotImplementedError

    def compile_statement(self, tk: Token):
        if tk.content == "let":
            tk = self.process("let", tk)
            var_name = tk.content
            tk = self.process(tk.content, tk)
            lhs_is_array = False
            if tk.type == T_SYMBOL and tk.content == "[":
                lhs_is_array = True
                tk = self.process("[", tk)
                tk = self.compile_expression(tk)
                tk = self.process("]", tk)
                if self.write_code:
                    seg, index = self.get_seg_index(var_name,
                                                    self.curr_subrt_name)
                    self.vm_writer.write_push(seg, index)
                    self.vm_writer.write_arithmetic("add")
            tk = self.process("=", tk)
            tk = self.compile_expression(tk)
            tk = self.process(";", tk)

            if self.write_code:
                if lhs_is_array:
                    self.vm_writer.write_pop("temp", 0)
                    self.vm_writer.write_pop("pointer", 1)
                    self.vm_writer.write_push("temp", 0)
                    self.vm_writer.write_pop("that", 0)
                else:
                    seg, index = self.get_seg_index(var_name,
                                                    self.curr_subrt_name)
                    self.vm_writer.write_pop(seg, index)
        elif tk.content == "if":
            label_TRUE = f"IF_TRUE{self.if_cnt}"
            label_FALSE = f"IF_FALSE{self.if_cnt}"
            label_END = f"IF_END{self.if_cnt}"
            self.if_cnt += 1

            tk = self.process("if", tk)
            tk = self.process("(", tk)
            tk = self.compile_expression(tk)

            # self.vm_writer.write_arithmetic("not")
            # self.vm_writer.write_if_goto(label1)
            if self.write_code:
                self.vm_writer.write_if_goto(label_TRUE)
                self.vm_writer.write_goto(label_FALSE)
                self.vm_writer.write_label(label_TRUE)

            tk = self.process(")", tk)
            tk = self.process("{", tk)
            tk = self.compile_statements(tk)
            tk = self.process("}", tk)

            # self.vm_writer.write_goto(label2)
            # self.vm_writer.write_label(label1)

            if tk.type == T_KEYWORD and tk.content == "else":
                if self.write_code:
                    self.vm_writer.write_goto(label_END)
                    self.vm_writer.write_label(label_FALSE)
                tk = self.process("else", tk)
                tk = self.process("{", tk)
                tk = self.compile_statements(tk)
                tk = self.process("}", tk)
                if self.write_code:
                    self.vm_writer.write_label(label_END)
            else:
                self.vm_writer.write_label(label_FALSE)
        elif tk.content == "while":
            label_TRUE = f"WHILE_EXP{self.while_cnt}"
            label_FALSE = f"WHILE_END{self.while_cnt}"
            self.while_cnt += 1

            if self.write_code:
                self.vm_writer.write_label(label_TRUE)

            tk = self.process("while", tk)
            tk = self.process("(", tk)
            tk = self.compile_expression(tk)

            if self.write_code:
                self.vm_writer.write_arithmetic("not")
                self.vm_writer.write_if_goto(label_FALSE)

            tk = self.process(")", tk)
            tk = self.process("{", tk)
            tk = self.compile_statements(tk)
            tk = self.process("}", tk)

            if self.write_code:
                self.vm_writer.write_goto(label_TRUE)
                self.vm_writer.write_label(label_FALSE)
        elif tk.content == "do":
            self.do_exps = True
            tk = self.process("do", tk)
            tk = self.compile_subroutine_call(tk)
            tk = self.process(";", tk)

            if self.write_code:
                self.vm_writer.write_pop("temp", 0)
            self.do_exps = False
        elif tk.content == "return":
            tk = self.process("return", tk)
            is_void_return = True
            if not (tk.type == T_SYMBOL and tk.content == ";"):
                is_void_return = False
                tk = self.compile_expression(tk)
            tk = self.process(";", tk)
            if is_void_return:
                if self.write_code:
                    self.vm_writer.write_push("constant", 0)
            if self.write_code:
                self.vm_writer.write_return()
        return tk

    def compile_expression(self, tk: Token):
        tk = self.compile_term(tk)
        if tk.type == T_SYMBOL and tk.content in _OPERATORS:
            operator_ = tk.content
            tk = self.process(_OPERATORS, tk)
            tk = self.compile_term(tk)
            if self.write_code:
                if operator_ == "*":
                    self.vm_writer.write_call("Math.multiply", 2)
                elif operator_ == "/":
                    self.vm_writer.write_call("Math.divide", 2)
                elif operator_ == "+":
                    self.vm_writer.write_arithmetic("add")
                elif operator_ == "|":
                    self.vm_writer.write_arithmetic("or")
                elif operator_ == "&gt;":
                    self.vm_writer.write_arithmetic("gt")
                elif operator_ == "&lt;":
                    self.vm_writer.write_arithmetic("lt")
                elif operator_ == "&amp;":
                    self.vm_writer.write_arithmetic("and")
                elif operator_ == "=":
                    self.vm_writer.write_arithmetic("eq")
                elif operator_ == "-":
                    self.vm_writer.write_arithmetic("sub")
                else:
                    raise NotImplementedError

        return tk

    def compile_term(self, tk: Token):
        # self.buff_write("<term>\n")
        if tk.type == T_CONST:
            num_const = tk.content
            tk = self.process(tk.content, tk)
            if self.write_code:
                self.vm_writer.write_push("constant", num_const)
        elif tk.type == T_STRING_CONST:
            if self.write_code:
                self.vm_writer.write_push("constant", len(tk.content))
                self.vm_writer.write_call("String.new", 1)
            str_const = tk.content
            if self.write_code:
                for c in str_const:
                    self.vm_writer.write_push("constant", ord(c))
                    self.vm_writer.write_call("String.appendChar", 2)
            tk = self.process(tk.content, tk)
        elif tk.type == T_KEYWORD and tk.content in _KWD_CONSTANT:
            kwd_const = tk.content
            tk = self.process(_KWD_CONSTANT, tk)
            if self.write_code:
                if kwd_const in ("null", "false"):
                    self.vm_writer.write_push("constant", 0)
                elif kwd_const == "true":
                    self.vm_writer.write_push("constant", 0)
                    self.vm_writer.write_arithmetic("not")
                elif kwd_const == "this":
                    self.vm_writer.write_push("pointer", 0)
                else:
                    raise NotImplementedError
        elif tk.type == T_IDENTIFIER:
            tk_next: Token = self.tokens[self.curr_idx + 1]
            if tk_next.type == T_SYMBOL and tk_next.content == "[":
                #  Array
                var_name = tk.content
                tk = self.process(tk.content, tk)  # [
                tk = self.process("[", tk)
                tk = self.compile_expression(tk)
                tk = self.process("]", tk)
                if self.write_code:
                    seg, index = self.get_seg_index(var_name,
                                                    self.curr_subrt_name)
                    self.vm_writer.write_push(seg, index)
                    self.vm_writer.write_arithmetic("add")
                    self.vm_writer.write_pop("pointer", 1)
                    self.vm_writer.write_push("that", 0)
            elif tk_next.type == T_SYMBOL and tk_next.content in ("(", "."):
                tk = self.compile_subroutine_call(tk)
            else:
                if self.write_code:
                    seg, index = self.get_seg_index(tk.content,
                                                    self.curr_subrt_name)
                    self.vm_writer.write_push(seg, index)
                tk = self.process(tk.content, tk)
        elif tk.type == T_SYMBOL and tk.content == "(":
            tk = self.process("(", tk)
            tk = self.compile_expression(tk)
            tk = self.process(")", tk)
        elif tk.type == T_SYMBOL and tk.content in _UNARY_OPERATORS:
            unary_op = tk.content
            tk = self.process(_UNARY_OPERATORS, tk)
            tk = self.compile_term(tk)
            if self.write_code:
                if unary_op == "-":
                    self.vm_writer.write_arithmetic("neg")
                elif unary_op == "~":
                    self.vm_writer.write_arithmetic("not")
                else:
                    raise NotImplementedError
        else:
            raise NotImplementedError(f"compilte_term: {tk}")
        return tk

    def compile_expression_list(self, tk: Token) -> (Token, int):
        num_exps_call = 0
        if not (tk.type == T_SYMBOL and tk.content == ")"):
            tk = self.compile_expression(tk)
            num_exps_call += 1
            while is_comma_sep(tk):
                tk = self.process(",", tk)
                tk = self.compile_expression(tk)
                num_exps_call += 1
        return tk, num_exps_call

    def is_argument_less(self, obj_name, method_name):
        if obj_name in OS_CLASS:
            return True
        if method_name == "new":
            return True
        for fn_name, fn_sym_table in self.sym_table_subrts.items():
            if fn_name == method_name:
                if fn_sym_table.fn_kind == "function":
                    return True

        if obj_name in self.class_infos:
            info_ = self.class_infos[obj_name]
            for fn_name, fn_sym_table in info_.sym_table_subrts.items():
                if fn_name == method_name and fn_sym_table.fn_kind == "function":
                    return True

        return False

    def get_fn_kind(self, class_name, subrt_name):
        if class_name in OS_CLASS:
            return "function"
        return self.class_infos[class_name].sym_table_subrts[subrt_name].fn_kind

    def compile_subroutine_call(self, tk: Token):
        obj_name = ""
        class_name = ""
        method_name = tk.content
        tk = self.process(tk.content, tk)
        this_class_method_call = False
        if tk.type == T_SYMBOL and tk.content == ".":
            tk = self.process(".", tk)
            class_name = method_name
            obj_name = method_name
            if obj_name == "this":
                this_class_method_call = True
            method_name = tk.content
            tk = self.process(tk.content, tk)
        else:
            this_class_method_call = True

        fn_kind = "method"
        if self.write_code:
            if this_class_method_call:
                class_name = self.class_name
            else:
                if method_name != "new":
                    table_: SymbolTable = self.sym_table_subrts[
                        self.curr_subrt_name]
                    if table_.isin(obj_name):
                        class_name = table_.get_row(obj_name).type
                    else:
                        cls_table_ = self.sym_table_cls
                        if cls_table_.isin(obj_name):
                            row_ = cls_table_.get_row(obj_name)
                            if row_.kind == "field":
                                class_name = row_.type
                        # else:
                        #     if class_name != self.class_name and obj_name not in OS_CLASS:
                        #         class_name ==
                        #     else:
                        #         raise NotImplementedError
            fn_kind = self.get_fn_kind(class_name, method_name)

            if fn_kind == "method":
                if this_class_method_call:
                    _, index = self.get_seg_index("this", method_name)
                    self.vm_writer.write_push("pointer", index)
                else:
                    if self.sym_table_cls.isin(obj_name):
                        row_ = self.sym_table_cls.get_row(obj_name)
                        if row_.kind == "field":
                            self.vm_writer.write_push("this", row_.index)
                        else:
                            raise NotImplementedError
                    else:
                        table_ = self.sym_table_subrts[self.curr_subrt_name]
                        row_ = table_.get_row(obj_name)
                        if row_.kind == "var":
                            self.vm_writer.write_push("local", row_.index)
                        else:
                            raise NotImplementedError

        tk = self.process("(", tk)
        tk, num_exps = self.compile_expression_list(tk)
        tk = self.process(")", tk)

        if self.write_code:
            if not self.is_argument_less(class_name, method_name):
                num_exps += 1
                # if this_class_method_call:
                #     if not self.do_exps:
                #         _, index = self.get_seg_index("this", method_name)
                #         self.vm_writer.write_push("pointer", index)
                # else:
                #     if self.sym_table_cls.isin(obj_name):
                #         row_ = self.sym_table_cls.get_row(obj_name)
                #         if row_.kind == "field":
                #             self.vm_writer.write_push("this", row_.index)
                #         else:
                #             raise NotImplementedError
                #     else:
                #         table_ = self.sym_table_subrts[self.curr_subrt_name]
                #         row_ = table_.get_row(obj_name)
                #         if row_.kind == "var":
                #             self.vm_writer.write_push("local", row_.index)
                #         else:
                #             raise NotImplementedError
            self.vm_writer.write_call(f"{class_name}.{method_name}", num_exps)
        return tk

    def compile_var_dec(self, tk):
        sym_table = self.sym_table_subrts[self.curr_subrt_name]

        # self.buff_write("<varDec>\n")
        tk = self.process(_KWD_VARDEC, tk)
        if not self.is_var_type(tk):
            raise Exception

        type_ = tk.content
        tk = self.process(_KWD_VOID + self.types, tk)
        name_ = tk.content
        tk = self.process(tk.content, tk)
        if not self.write_code:
            sym_table.define(name_, type_, "var")

        while is_comma_sep(tk):
            tk = self.process(",", tk)
            name_ = tk.content
            tk = self.process(tk.content, tk)
            if not self.write_code:
                sym_table.define(name_, type_, "var")
        tk = self.process(";", tk)
        # self.buff_write("</varDec>\n")
        return tk

    def is_var_type(self, tk: Token):
        if tk.type == T_SYMBOL:
            return False
        if tk.type == T_KEYWORD and tk.content in _KWD_TYPE:
            return True
        if tk.type == T_IDENTIFIER:
            if tk.content not in self.types:
                self.types = self.types + (tk.content,)
            return True
        return False

    def compile_parameter_list(self, tk: Token):
        if self.is_var_type(tk):
            sym_table: SymbolTable = self.sym_table_subrts[self.curr_subrt_name]
            type_ = tk.content
            tk = self.process(_KWD_VOID + self.types, tk)
            name_ = tk.content
            tk = self.process(tk.content, tk)
            if not self.write_code:
                sym_table.define(name_, type_, "arg")

            while is_comma_sep(tk):
                tk = self.process(",", tk)
                if not self.is_var_type(tk):
                    raise Exception
                type_ = tk.content
                tk = self.process(_KWD_VOID + self.types, tk)
                name_ = tk.content
                tk = self.process(tk.content, tk)
                if not self.write_code:
                    sym_table.define(name_, type_, "arg")
        else:
            if not (tk.type == T_SYMBOL and tk.content == ")"):
                raise Exception
        return tk


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_dir")
    args = parser.parse_args()
    file_dir = pathlib.Path(args.file_dir)
    print("file_dir:", file_dir)

    # append_ = "_dev"
    append_ = ""

    jack_files = []
    if pathlib.Path.is_dir(file_dir):
        for p in file_dir.glob("*.jack"):
            fname = p.parts[-1].split(".")[0]
            if not fname:
                continue
            jack_files.append(
                (p, pathlib.Path(file_dir, fname + f"T{append_}.xml"),
                 pathlib.Path(file_dir, fname + f"{append_}.xml"),
                 pathlib.Path(file_dir, fname + f"{append_}.vm")))
    elif os.path.isfile(file_dir) and file_dir.parts[-1].endswith(
            ".jack"):
        fname = file_dir.parts[-1].split(".")[0]
        pre = pathlib.Path(*file_dir.parts[:-1])
        jack_files.append(
            (file_dir, pathlib.Path(pre, fname + f"T{append_}.xml"),
             pathlib.Path(pre, fname + f"{append_}.xml"),
             pathlib.Path(file_dir, fname + f"{append_}.vm")))
    else:
        raise NotImplementedError

    compiler = JackCompiler()

    for jack in jack_files:
        tokenizer = JackTokenizer(input_file=jack[0],
                                  output_path=jack[1])
        tokenizer.tokenize()

        compiler.set_paths(input_file=jack[1], output_path=jack[3])
        compiler.compile(read_class_info=True)
        compiler.cache_class_info()

    for jack in jack_files:
        compiler.set_paths(input_file=jack[1], output_path=jack[3])
        compiler.compile(read_class_info=False)


if __name__ == "__main__":
    main()
