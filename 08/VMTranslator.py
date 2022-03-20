import argparse
import os
from pathlib import Path

stack_base_addr = 256

# local_base_addr = 1017
# argment_base_addr = 2
# this_base_addr = 3
# that_base_addr = 4
temp_base_addr = 5

# RAM = [0] * 512
# RAM[0] = stack_base_addr
# RAM[1] = local_base_addr
# RAM[2] = argment_base_addr
# RAM[3] = this_base_addr
# RAM[4] = that_base_addr


init_stack = """
@{stack_base_addr}
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
AM=M+1
A=A-1
M=D
""".strip()

# pop and set value to D
stack_pop = f"""
@SP
AM=M-1
D=M
""".strip()

# pop value and set to *D
pop_tail = f"""
@R15
M=D
@SP
AM=M-1
D=M
@R15
A=M
M=D
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

call_fn = """
@{return_address}
D=A
{stack_push}
@LCL
D=M
{stack_push}
@ARG
D=M
{stack_push}
@THIS
D=M
{stack_push}
@THAT
D=M
{stack_push}
@SP
D=M
@LCL
M=D
@5
D=D-A
@{n_vars}
D=D-A
@ARG
M=D
@{function_name}
0;JMP
({return_address})
""".strip()

func_str = """
({function_name})
@{n_vars}
D=A
({function_name}_init)
@SP
AM=M+1
A=A-1
M=0
@{function_name}_init
D=D-1;JGT
""".strip()

return_str = """
@LCL
D=M
@{frame}
M=D
@5
A=D-A
D=M
@{ret_addr}
M=D
@SP
AM=M-1
D=M
@ARG
A=M
M=D
@ARG
D=M
@SP
M=D+1
@{frame}
AM=M-1
D=M
@THAT
M=D
@{frame}
AM=M-1
D=M
@THIS
M=D
@{frame}
AM=M-1
D=M
@ARG
M=D
@{frame}
AM=M-1
D=M
@LCL
M=D
@{ret_addr}
A=M
0;JMP
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
    def __init__(self, write_path) -> None:
        self.static_name = None
        self.write_path = write_path
        self.g = None
        self._retcnt = 0
        self.function_name = "SYSTEM"

    def bootstrap(self):
        self.g.write(init_stack.format(stack_base_addr=stack_base_addr) + "\n")
        self.write_call("Sys.init", 0)

    def close_g(self):
        self.g.close()

    def open_g(self):
        self.g = open(self.write_path, "w")

    def write_function(self, function_name, n_vars):
        self.function_name = function_name
        if n_vars == 0:
            self.g.write(f"({function_name})\n")
        else:
            self.g.write(
                func_str.format(function_name=function_name, n_vars=n_vars) + "\n"
            )

    def write_call(self, function_name, n_vars):
        return_address = f"{function_name}$ret.{self._retcnt}"
        self._retcnt += 1
        self.g.write(
            call_fn.format(
                return_address=return_address,
                stack_push=stack_push,
                n_vars=n_vars,
                function_name=function_name,
            )
            + "\n"
        )

    def write_return(self):
        self.g.write(return_str.format(frame="R13", ret_addr="R14") + "\n")

    def write_label(self, label):
        self.g.write(f"({self.function_name}${label})\n")

    def write_goto(self, label):
        self.g.write(f"@{self.function_name}${label}\n0;JMP\n")

    def write_if_goto(self, label):
        self.g.write(stack_pop + "\n")
        self.g.write(f"@{self.function_name}${label}\nD;JNE\n")

    def write_push(self, segment, index):
        if segment == "static":
            push_head = f"@{self.static_name}.{index}\nD=M\n"
        elif segment == "pointer":
            if index == 0:
                push_head = "@THIS\nD=M\n"
            elif index == 1:
                push_head = "@THAT\nD=M\n"
            else:
                raise Exception
        elif segment == "constant":
            push_head = f"@{index}\nD=A\n"
        elif segment == "temp":
            push_head = retrieve_val.format(segment=5, AorM="A", index=index) + "\n"
        else:
            push_head = retrieve_val.format(segment=map_seg[segment], AorM="M", index=index) + "\n"
        self.g.write(push_head + stack_push + "\n")

    def write_pop(self, segment, index):
        if segment == "static":
            pop_head = f"@{self.static_name}.{index}\nD=A\n"
        elif segment == "pointer":
            if index == 0:
                pop_head = "@THIS\nD=A\n"
            elif index == 1:
                pop_head = "@THAT\nD=A\n"
            else:
                raise Exception
        elif segment == "temp":
            if index > 0:
                pop_head = addr_seg_index_temp.format(index=index) + "\n"
            else:
                pop_head = f"@5\nD=A\n"
        else:
            if index > 0:
                pop_head = addr_seg_index.format(segment=map_seg[segment], index=index) + "\n"
            else:
                pop_head = f"@{map_seg[segment]}\nD=M\n"
        self.g.write(pop_head + pop_tail + "\n")

    def write_arithmetic(self, command):
        if command in map_op:
            if command in ("neg", "not"):
                self.g.write(stack_neg.format(op=map_op[command]) + "\n")
            else:
                self.g.write(stack_add.format(op=map_op[command]) + "\n")
        elif command in map_cmp:
            self.g.write(stack_jeq.format(i=self._retcnt, op=map_cmp[command]) + "\n")
            self._retcnt += 1
        else:
            raise NotImplementedError


C_LABEL = 0
C_GOTO = 1
C_IF = 2
C_FUNCTION = 3
C_RETURN = 4
C_CALL = 5
C_PUSH = 6
C_POP = 7
C_ARITHMETIC = 8

command_types = {
    "label": C_LABEL,
    "goto": C_GOTO,
    "if-goto": C_IF,
    "function": C_FUNCTION,
    "call": C_CALL,
    "return": C_RETURN,
    "push": C_PUSH,
    "pop": C_POP,
    "sub": C_ARITHMETIC,
    "add": C_ARITHMETIC,
    "and": C_ARITHMETIC,
    "or": C_ARITHMETIC,
    "neg": C_ARITHMETIC,
    "not": C_ARITHMETIC,
    "eq": C_ARITHMETIC,
    "gt": C_ARITHMETIC,
    "lt": C_ARITHMETIC,
}


class VMParser:
    def __init__(self) -> None:
        self.line = None
        self.command_type = None
        self._arg1 = None
        self._arg2 = None

    def parse(self, line):
        line = line.strip().split()
        self.command_type = command_types.get(line[0].strip(), None)
        if self.command_type is None:
            raise NotImplementedError(f"{line[0]}")
        if self.command_type == C_ARITHMETIC:
            self._arg1 = line[0].strip()
        if len(line) > 1:
            self._arg1 = line[1].strip()
        if len(line) > 2:
            self._arg2 = int(line[2].strip())

    @property
    def arg1(self):
        if self.command_type == C_RETURN:
            raise Exception
        return self._arg1

    @property
    def arg2(self):
        if self.command_type not in (C_PUSH, C_POP, C_FUNCTION, C_CALL):
            raise Exception
        return self._arg2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_dir")
    args = parser.parse_args()
    file_dir = Path(args.file_dir)

    lst_vm = []
    if Path.is_dir(file_dir):
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
    print("output: " + asm_out_path)

    vm_parser = VMParser()
    code_writer = CodeWriter(asm_out_path)
    code_writer.open_g()
    if do_bootstrap:
        code_writer.bootstrap()

    for fname in lst_vm:
        print(f"translating: {fname}")
        static_name = fname.parts[-1].split(".")[0]
        code_writer.static_name = static_name
        with open(fname, "r") as f:
            for line in f.readlines():
                comment_idx = line.find("//")
                vm_line = line[:comment_idx].strip()
                if vm_line == "":
                    continue
                vm_parser.parse(vm_line)
                if vm_parser.command_type == C_PUSH:
                    code_writer.write_push(vm_parser.arg1, vm_parser.arg2)
                elif vm_parser.command_type == C_POP:
                    code_writer.write_pop(vm_parser.arg1, vm_parser.arg2)
                elif vm_parser.command_type == C_ARITHMETIC:
                    code_writer.write_arithmetic(vm_parser.arg1)
                elif vm_parser.command_type == C_LABEL:
                    code_writer.write_label(vm_parser.arg1)
                elif vm_parser.command_type == C_GOTO:
                    code_writer.write_goto(vm_parser.arg1)
                elif vm_parser.command_type == C_IF:
                    code_writer.write_if_goto(vm_parser.arg1)
                elif vm_parser.command_type == C_FUNCTION:
                    code_writer.write_function(vm_parser.arg1, vm_parser.arg2)
                elif vm_parser.command_type == C_CALL:
                    code_writer.write_call(vm_parser.arg1, vm_parser.arg2)
                elif vm_parser.command_type == C_RETURN:
                    code_writer.write_return()
                else:
                    raise Exception

    code_writer.close_g()


if __name__ == "__main__":
    main()
