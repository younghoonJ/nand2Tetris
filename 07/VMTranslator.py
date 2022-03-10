import argparse
import enum
from pathlib import Path

stack_base_addr = 256
temp_base_addr = 5

# RAM[0] = stack_base_addr
# RAM[1] = local_base_addr
# RAM[2] = argment_base_addr
# RAM[3] = this_base_addr
# RAM[4] = that_base_addr


stack_init = """
@{base_addr}
D=A
@SP
M=D
""".strip()

# set value (segment + index) to D
addr_seg_index = """
@{segment}
D=M
@{index}
D=D+A
""".strip()

addr_seg_index_temp = """
@5
D=A
@{index}
D=D+A
""".strip()

# retrieve value from segment+index and set this value to D
retrieve_val = """
@{segment}
D={AorM}
@{index}
A=D+A
D=M
""".strip()

# push value stored in D
stack_push = """
@SP
A=M
M=D
@SP
M=M+1
""".strip()

# pop and set value to D
stack_pop = f"""
@SP
AM=M-1
D=M
""".strip()

# (neg, not) and set value to D
stack_neg = """
@SP
AM=M-1
MD={op}M
@SP
M=M+1
""".strip()

# (add, sub, and, or) and set value to D
stack_add = """
@SP
AM=M-1
D=M
A=A-1
MD=M{op}D
""".strip()

# (eq, gt, lt).
stack_jeq = """
@R15
M=-1
@SP
AM=M-1
D=M
@SP
AM=M-1
D=M-D
@STK_NOT_F{i}
D;{op}
@R15
M=0
(STK_NOT_F{i})
@R15
D=M
@SP
A=M
M=D
@SP
M=M+1
""".strip()

map_seg = {
    "local": "LCL",
    "argument": "ARG",
    "this": "THIS",
    "that": "THAT",
}

map_op = {
    "neg": "-",
    "not": "!",
    "add": "+",
    "sub": "-",
    "and": "&",
    "or": "|",
}

map_cmp = {
    "eq": "JEQ",
    "gt": "JGT",
    "lt": "JLT",
}


class CodeWriter:
    def __init__(self, write_file, static_name) -> None:
        self.static_name = static_name
        self.g = open(write_file, "w")
        self._retcnt = 0

    def close_write(self):
        self.g.close()

    def write_push(self, segment, index):
        if segment == "static":
            s = [f"@{self.static_name}.{index}", "D=M"]
        elif segment == "pointer":
            if index == 0:
                s = ["@THIS", "D=M"]
            elif index == 1:
                s = ["@THAT", "D=M"]
            else:
                raise Exception
        elif segment == "constant":
            s = [f"@{index}", "D=A"]
        elif segment == "temp":
            s = [retrieve_val.format(segment=5, AorM="A", index=index)]
        else:
            s = [retrieve_val.format(segment=map_seg[segment], AorM="M", index=index)]
        s.append(stack_push)
        self.g.write("\n".join(s) + "\n")

    def write_pop(self, segment, index):
        if segment == "static":
            s = [f"@{self.static_name}.{index}", "D=A"]
        elif segment == "pointer":
            if index == 0:
                s = ["@THIS", "D=A"]
            elif index == 1:
                s = ["@THAT", "D=A"]
            else:
                raise Exception
        elif segment == "temp":
            s = [addr_seg_index_temp.format(index=index)]
        else:
            s = [addr_seg_index.format(segment=map_seg[segment], index=index)]
        s += ["@R15",
              "M=D",
              stack_pop,
              "@R15",
              "A=M",
              "M=D", ]
        self.g.write("\n".join(s) + "\n")

    def write_arithmetic(self, command):
        if command in map_op:
            if command in ("neg", "not"):
                self.g.write(stack_neg.format(op=map_op[command]) + "\n")
            else:
                self.g.write(stack_add.format(op=map_op[command]) + "\n")
        elif command in map_cmp:
            self.g.write(stack_jeq.format(i=self._retcnt, op=map_cmp[command]) + "\n")
            self._retcnt += 1


class CommandTypes(enum.Enum):
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
    def __init__(self) -> None:
        self.line = None
        self.command_type = None
        self._arg1 = None
        self._arg2 = None

    def parse(self, line):
        line = line.strip().split()
        if line[0] == "push":
            self.command_type = CommandTypes.C_PUSH
            self._arg1 = line[1]
            self._arg2 = int(line[2])
        elif line[0] == "pop":
            self.command_type = CommandTypes.C_POP
            self._arg1 = line[1]
            self._arg2 = int(line[2])
        elif line[0] in ("sub", "add", "and", "or", "neg", "not", "eq", "gt", "lt"):
            self.command_type = CommandTypes.C_ARITHMETIC
            self._arg1 = line[0]
        else:
            raise Exception

    @property
    def arg1(self):
        if self.command_type == CommandTypes.C_RETURN:
            raise Exception
        return self._arg1

    @property
    def arg2(self):
        if self.command_type not in (
                CommandTypes.C_PUSH,
                CommandTypes.C_POP,
                CommandTypes.C_FUNCTION,
                CommandTypes.C_CALL,
        ):
            raise Exception
        return self._arg2


def main():
    parser = argparse.ArgumentParser()
    # parser.add_argument("-f", "--file", type=str)
    parser.add_argument("file")
    args = parser.parse_args()

    fname = Path(args.file)
    static_name = fname.parts[-1].split(".")[0]
    vm_parser = VMParser()
    write_fname = fname.parts[-1]
    write_fname = "/".join(fname.parts[0:-1] + (write_fname.split(".")[0] + ".asm",))
    code_writer = CodeWriter(write_fname, static_name)

    with open(fname, "r") as f:
        for line in f.readlines():
            comment_idx = line.find("//")
            vm_line = line[:comment_idx].strip()
            if vm_line == "":
                continue
            vm_parser.parse(vm_line)
            if vm_parser.command_type == CommandTypes.C_PUSH:
                code_writer.write_push(vm_parser.arg1, vm_parser.arg2)
            elif vm_parser.command_type == CommandTypes.C_POP:
                code_writer.write_pop(vm_parser.arg1, vm_parser.arg2)
            elif vm_parser.command_type == CommandTypes.C_ARITHMETIC:
                code_writer.write_arithmetic(vm_parser.arg1)


if __name__ == "__main__":
    main()