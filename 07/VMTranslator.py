import argparse
import enum
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
        if _c_type == "push":
            self._comm_type = Ctypes.C_PUSH
            self._arg1 = lst[1].strip()
            self._arg2 = int(lst[2].strip())
        elif _c_type == "pop":
            self._comm_type = Ctypes.C_POP
            self._arg1 = lst[1].strip()
            self._arg2 = int(lst[2].strip())
        elif _c_type in ("sub", "add", "and", "or", "neg", "not", "eq", "gt", "lt"):
            self._comm_type = Ctypes.C_ARITHMETIC
            self._arg1 = _c_type
            self._arg2 = None
        else:
            raise Exception(f"unimplemented vm commmand type: {_c_type}.")

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


def get_or_raise(key, map):
    v = map.get(key, None)
    if v is None:
        raise NotImplementedError(f"not implemented operator: {key}")
    return v


def write_asm(f, lst):
    f.write("\n".join(lst) + "\n")


class CodeWriter:
    def __init__(self, f, static_name):
        self.f = f
        self._jmp_cnt = 0
        self._static_name = static_name

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
                 "A=A-1",
                 "D=M-D",
                 f"@JMP_FALSE{self._jmp_cnt}",
                 f"D;{op}",
                 "@R15",
                 "M=0",
                 f"(JMP_FALSE{self._jmp_cnt})",
                 "@R15",
                 "D=M",
                 "@SP",
                 "A=M-1",
                 "M=D"]
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
            s = [f"@{self._static_name}.{idx}", "D=M"]
        else:
            mem_seg = get_or_raise(seg, map_mem_seg)
            s = [f"@{mem_seg}",
                 "D=M",
                 f"@{idx}",
                 "A=D+A",
                 "D=M"]
        s += ["@SP",
              "A=M",
              "M=D",
              "@SP",
              "M=M+1"]
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
            s = [f"@{self._static_name}.{idx}", "D=A"]
        else:
            mem_seg = get_or_raise(seg, map_mem_seg)
            s = [f"@{mem_seg}",
                 "D=M",
                 f"@{idx}",
                 "D=D+A"]
        s += ["@R15",
              "M=D",
              "@SP",
              "AM=M-1",
              "D=M",
              "@R15",
              "A=M",
              "M=D"]
        write_asm(self.f, s)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    args = parser.parse_args()
    file_name = pathlib.Path(args.file)
    static_name = file_name.parts[-1].split(".")[0]
    write_fname = pathlib.Path(*file_name.parts[0:-1]).joinpath(static_name + ".asm")
    # print(static_name, write_fname)

    with open(file_name, 'r') as f:
        with open(write_fname, 'w') as g:
            vm_parser = VMParser(f)
            code_writer = CodeWriter(g, static_name)

            while vm_parser.has_more_lines():
                vm_parser.advance()
                vm_parser.strip_comment()
                if vm_parser.vm_comm != "":
                    vm_parser.parse()
                    # vm_parser.print_command()
                    if vm_parser.command_type == Ctypes.C_PUSH:
                        code_writer.write_push(vm_parser.arg1, vm_parser.arg2)
                    elif vm_parser.command_type == Ctypes.C_POP:
                        code_writer.write_pop(vm_parser.arg1, vm_parser.arg2)
                    elif vm_parser.command_type == Ctypes.C_ARITHMETIC:
                        code_writer.write_arithmetic(vm_parser.arg1)
                    else:
                        raise NotImplementedError


if __name__ == "__main__":
    main()
