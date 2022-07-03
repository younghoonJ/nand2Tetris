import argparse
import enum
import os
import pathlib
from typing import TextIO


class CONST(enum.Enum):
    EOF = 0


class Ctypes(enum.Enum):
    C_ARITHMETIC = enum.auto()
    C_PUSH = enum.auto()
    C_POP = enum.auto()
    C_LABEL = enum.auto()
    C_GOTO = enum.auto()
    C_IF = enum.auto()
    C_FUNCTION = enum.auto()
    C_RETURN = enum.auto()
    C_CALL = enum.auto()


map_ctypes = {
    "push": Ctypes.C_PUSH,
    "pop": Ctypes.C_POP,
    "function": Ctypes.C_FUNCTION,
    "call": Ctypes.C_CALL,
    "label": Ctypes.C_LABEL,
    "if-goto": Ctypes.C_IF,
    "goto": Ctypes.C_GOTO,
    "return": Ctypes.C_RETURN
}


class VMParser:
    def __init__(self, f: TextIO):
        self.f = f
        self.vm_comm = next(self.f, CONST.EOF)
        self._next_line = None
        self._comm_type = None
        self._arg1 = None
        self._arg2 = None

    def has_more_lines(self):
        self._next_line = next(self.f, CONST.EOF)
        return self._next_line != CONST.EOF

    def advance(self):
        self.vm_comm = self._next_line

    def strip_comment(self):
        self.vm_comm = self.vm_comm[:self.vm_comm.find("//")].strip()

    def parse(self):
        lst = self.vm_comm.strip().split()
        _c_type = lst[0].strip()
        self._arg1 = None
        self._arg2 = None
        if _c_type in ("sub", "add", "and", "or", "neg", "not", "eq", "gt", "lt"):
            self._comm_type = Ctypes.C_ARITHMETIC
            self._arg1 = _c_type
        elif _c_type in ("label", "goto", "if-goto"):
            self._comm_type = get_or_raise(_c_type, map_ctypes)
            self._arg1 = lst[1].strip()
        elif _c_type == "return":
            self._comm_type = get_or_raise(_c_type, map_ctypes)
        else:
            self._comm_type = get_or_raise(_c_type, map_ctypes)
            self._arg1 = lst[1].strip()
            self._arg2 = int(lst[2].strip())

    @property
    def command_type(self) -> Ctypes:
        return self._comm_type

    @property
    def arg1(self):
        if self._comm_type == Ctypes.C_RETURN:
            raise Exception("should not be called if current command is C_RETURN.")
        return self._arg1

    @property
    def arg2(self):
        if self._comm_type not in (Ctypes.C_PUSH, Ctypes.C_POP, Ctypes.C_FUNCTION, Ctypes.C_CALL):
            raise Exception("should be called only if current command is C_PUSH, C_POP, C_FUNCTION or C_CALL.")
        return self._arg2

    def print_command(self):
        if self._arg2 is None:
            print(self.command_type, self.arg1)
        else:
            print(self.command_type, self.arg1, self.arg2)


map_bi_op = {
    "add": "+",
    "sub": "-",
    "and": "&",
    "or": "|"
}

map_si_op = {
    "neg": "-",
    "not": "!"
}

map_cmp_op = {
    "eq": "JEQ",
    "gt": "JGT",
    "lt": "JLT"
}

map_mem_seg = {
    "local": "LCL",
    "argument": "ARG",
    "this": "THIS",
    "that": "THAT"
}

STACK_BASE_ADDR = 256
ASM_STACK_PUSH = ["@SP",
                  "AM=M+1",
                  "A=A-1",
                  "M=D"]

ASM_STACK_POP_D = ["@R15",
                   "M=D",
                   "@SP",
                   "AM=M-1",
                   "D=M",
                   "@R15",
                   "A=M",
                   "M=D"]

ASM_STACK_POP = ["@SP",
                 "AM=M-1",
                 "D=M"]


def get_or_raise(key, map):
    v = map.get(key, None)
    if v is None:
        raise NotImplementedError(f"not implemented operator: {key}")
    return v


def write_asm(f, lst):
    f.write("\n".join(lst) + "\n")


class CodeWriter:
    def __init__(self, f):
        self.f = f
        self._jmp_cnt = 0
        self.file_name = None
        self.func_name = "SYSTEM"

    def set_filename(self, file_name):
        self.file_name = file_name

    def bootstrap(self):
        s = [f"@{STACK_BASE_ADDR}",
             "D=A",
             "@SP",
             "M=D"]
        write_asm(self.f, s)
        self.write_call("Sys.init", 0)

    def write_call(self, func_name, n_args):
        return_addr = f"{func_name}$ret.{self._jmp_cnt}"
        s = [f"@{return_addr}", "D=A"] + ASM_STACK_PUSH  # push returnAddress
        s += ["@LCL", "D=M"] + ASM_STACK_PUSH  # push LCL
        s += ["@ARG", "D=M"] + ASM_STACK_PUSH  # push ARG
        s += ["@THIS", "D=M"] + ASM_STACK_PUSH  # push THIS
        s += ["@THAT", "D=M"] + ASM_STACK_PUSH  # push THAT
        s += ["@SP", "D=M", "@LCL", "M=D"]  # LCL = SP
        s += ["@5", "D=D-A", f"@{n_args}", "D=D-A", "@ARG", "M=D"]  # ARG = SP - 5 - nArgs
        s += [f"@{func_name}", "0;JMP"]  # goto f
        s += [f"({return_addr})"]  # (returnAddress)
        write_asm(self.f, s)
        self._jmp_cnt += 1

    def write_function(self, func_name, n_vars):
        self.func_name = func_name
        s = [f"({func_name})"]
        if n_vars > 0:
            s += [f"@{n_vars}",
                  "D=A",
                  f"({func_name}_rep)",
                  "@SP",
                  "AM=M+1",
                  "A=A-1",
                  "M=0",
                  f"@{func_name}_rep",
                  "D=D-1;JGT"]
        write_asm(self.f, s)

    def write_return(self):
        # frame = "R13", ret_addr = "R14"
        s = ["@LCL", "D=M", "@R13", "M=D",  # frame = LCL
             "@5", "A=D-A", "D=M", "@R14", "M=D",  # retAddr = *(frame - 5)
             "@SP", "AM=M-1", "D=M", "@ARG", "A=M", "M=D",  # *ARG = pop()
             "@ARG", "D=M", "@SP", "M=D+1",  # SP = ARG + 1
             "@R13", "AM=M-1", "D=M", "@THAT", "M=D",  # THAT = *(frame - 1)
             "@R13", "AM=M-1", "D=M", "@THIS", "M=D",  # THIS = *(frame - 2)
             "@R13", "AM=M-1", "D=M", "@ARG", "M=D",  # ARG = *(frame - 3)
             "@R13", "AM=M-1", "D=M", "@LCL", "M=D",  # LCL = *(frame - 4)
             "@R14", "A=M", "0;JMP"]
        write_asm(self.f, s)

    def write_arithmetic(self, comm: str):
        if comm in map_bi_op:
            op = get_or_raise(comm, map_bi_op)
            s = ["@SP",
                 "AM=M-1",
                 "D=M",
                 "A=A-1",
                 f"MD=M{op}D"]
        elif comm in map_si_op:
            op = get_or_raise(comm, map_si_op)
            s = ["@SP",
                 "AM=M-1",
                 f"MD={op}M",
                 "@SP",
                 "M=M+1"]
        elif comm in map_cmp_op:
            op = get_or_raise(comm, map_cmp_op)
            s = ["@R15",
                 "M=-1",
                 "@SP",
                 "AM=M-1",
                 "D=M",
                 "@SP",
                 "AM=M-1",
                 "D=M-D",
                 f"@JMP_FALSE{self._jmp_cnt}",
                 f"D;{op}",
                 "@R15",
                 "M=0",
                 f"(JMP_FALSE{self._jmp_cnt})",
                 "@R15",
                 "D=M",
                 "@SP",
                 "A=M",
                 "M=D",
                 "@SP",
                 "M=M+1"]
            self._jmp_cnt += 1
        else:
            raise NotImplementedError(comm)
        write_asm(self.f, s)

    def write_push(self, seg: str, idx: int):
        if seg == "constant":
            s = [f"@{idx}", "D=A"]
        elif seg == "pointer":
            if idx == 0:
                s = ["@THIS", "D=M"]
            elif idx == 1:
                s = ["@THAT", "D=M"]
            else:
                raise NotImplementedError(f"{seg} {idx}")
        elif seg == "temp":
            s = ["@5", "D=A", f"@{idx}", "A=D+A", "D=M"]
        elif seg == "static":
            s = [f"@{self.file_name}.{idx}", "D=M"]
        else:
            mem_seg = get_or_raise(seg, map_mem_seg)
            s = [f"@{mem_seg}",
                 "D=M",
                 f"@{idx}",
                 "A=D+A",
                 "D=M"]
        s += ASM_STACK_PUSH
        write_asm(self.f, s)

    def write_pop(self, seg: str, idx: int):
        if seg == "pointer":
            if idx == 0:
                s = ["@THIS", "D=A"]
            elif idx == 1:
                s = ["@THAT", "D=A"]
            else:
                raise NotImplementedError(f"{seg} {idx}")
        elif seg == "temp":
            s = ["@5", "D=A", f"@{idx}", "D=D+A"]
        elif seg == "static":
            s = [f"@{self.file_name}.{idx}", "D=A"]
        else:
            mem_seg = get_or_raise(seg, map_mem_seg)
            s = [f"@{mem_seg}",
                 "D=M",
                 f"@{idx}",
                 "D=D+A"]
        s += ASM_STACK_POP_D
        write_asm(self.f, s)

    def write_label(self, label: str):
        s = [f"({self.func_name}${label})"]
        write_asm(self.f, s)

    def write_goto(self, label: str):
        s = [f"@{self.func_name}${label}", "0;JMP"]
        write_asm(self.f, s)

    def write_if_goto(self, label: str):
        s = ASM_STACK_POP + [f"@{self.func_name}${label}", "D;JNE"]
        write_asm(self.f, s)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file_dir')
    args = parser.parse_args()
    file_dir = pathlib.Path(args.file_dir)

    lst_vm = []
    if pathlib.Path.is_dir(file_dir):
        for p in file_dir.glob("*.vm"):
            if p.parts[-1] == "Sys.vm":
                lst_vm = [p] + lst_vm
            else:
                lst_vm.append(p)
        asm_out_name = file_dir.parts[-1] + ".asm"
        asm_out_path = "/".join(file_dir.parts + (asm_out_name,))
        do_bootstrap = True
    elif os.path.isfile(file_dir) and file_dir.parts[-1].endswith(".vm"):
        lst_vm.append(file_dir)
        asm_out_name = file_dir.parts[-1][:-2] + "asm"
        asm_out_path = "/".join(file_dir.parts[:-1] + (asm_out_name,))
        do_bootstrap = False
    else:
        raise NotImplementedError

    print("vm files ", lst_vm)
    print("output: ", asm_out_path, asm_out_name)

    with open(asm_out_path, 'w') as g:
        code_writer = CodeWriter(g)

        if do_bootstrap:
            code_writer.bootstrap()

        for fname in lst_vm:
            with open(fname, 'r')as f:
                vm_parser = VMParser(f)
                code_writer.set_filename(fname.parts[-1].split(".")[0])

                while vm_parser.has_more_lines():
                    vm_parser.advance()
                    vm_parser.strip_comment()
                    if vm_parser.vm_comm:
                        vm_parser.parse()
                        # vm_parser.print_command()
                        if vm_parser.command_type == Ctypes.C_PUSH:
                            code_writer.write_push(vm_parser.arg1, vm_parser.arg2)
                        elif vm_parser.command_type == Ctypes.C_POP:
                            code_writer.write_pop(vm_parser.arg1, vm_parser.arg2)
                        elif vm_parser.command_type == Ctypes.C_ARITHMETIC:
                            code_writer.write_arithmetic(vm_parser.arg1)
                        elif vm_parser.command_type == Ctypes.C_RETURN:
                            code_writer.write_return()
                        elif vm_parser.command_type == Ctypes.C_CALL:
                            code_writer.write_call(vm_parser.arg1, vm_parser.arg2)
                        elif vm_parser.command_type == Ctypes.C_FUNCTION:
                            code_writer.write_function(vm_parser.arg1, vm_parser.arg2)
                        elif vm_parser.command_type == Ctypes.C_GOTO:
                            code_writer.write_goto(vm_parser.arg1)
                        elif vm_parser.command_type == Ctypes.C_IF:
                            code_writer.write_if_goto(vm_parser.arg1)
                        elif vm_parser.command_type == Ctypes.C_LABEL:
                            code_writer.write_label(vm_parser.arg1)
                        else:
                            raise NotImplementedError


if __name__ == "__main__":
    main()
