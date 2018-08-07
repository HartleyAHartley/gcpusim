import sys

regAMatch = {"SUM_BA":(lambda x,y: x + y),
             "AND_BA":(lambda x,y: x & y),
             "OR_BA" :(lambda x,y: x | y),
             "COMA"  :(lambda x,y:~x),
             "SHFA_L":(lambda x,y: x << 1),
             "SHFA_R":(lambda x,y: x >> 1)}
regBMatch = {"SUM_AB":(lambda x,y: x + y),
             "AND_AB":(lambda x,y: x & y),
             "OR_AB" :(lambda x,y: x | y),
             "COMB"  :(lambda x,y:~y),
             "SHFA_L":(lambda x,y: y << 1),
             "SHFB_R":(lambda x,y: y >> 1)}

branchMatch = {"BEQ":(lambda x: x==0),"BNE":(lambda x: x!=0),
               "BN" :(lambda x: x<0), "BP" :(lambda x: x>=0)}
dataMatch = {"LDAA" :(lambda x: x.setReg("regA",x.parseOperand())),
             "LDAB" :(lambda x: x.setReg("regB",x.parseOperand())),
             "LDX"  :(lambda x: x.setReg("regX",x.parseOperand())),
             "LDY"  :(lambda x: x.setReg("regY",x.parseOperand())),
             "STAA" :(lambda x:  x.write("regA",x.parseOperand())),
             "STAB" :(lambda x:  x.write("regB",x.parseOperand()))}
class Gcpu:
    def __init__(self):
        self.regA = 0
        self.regB = 0
        self.regX = 0
        self.regY = 0
        self.rom = {}
        self.ram = {}
        self.instructions = {}
        self.parsedInstructions = {}
        self.labels = {}
        self.line = 0
        self.halt = False
        self.breakpoint = False
        self.incStep = True
        self.bp = {"regA":"","regB":"","regX":"","regY":"","ram":"","rom":""}
        self.bpline = []
        self.continues = False

    def check_status(func):
        def _check_status(self, *args, **kwargs):
            if self.halt:
                print("Gcpu has encountered an error and has halted")
                self.dump()
                return False
            else:
                return func(self, *args, **kwargs)
        return _check_status
    def check_regBP(func):
        def _check_regBP(self, *args, **kwargs):
            if "w" in self.bp[args[0]] and not self.continues:
                self.breakpoint = True
                print(f"Break on {args[0]} write: \n"+\
                                "{self.CurrentInstruction()}")
                return False
            else:
                return func(self, *args, **kwargs)
        return _check_regBP
    def check_ramBP(func):
        def _check_ramBP(self, *args, **kwargs):
            if "w" in self.bp["ram"] and not self.continues:
                self.breakpoint = True
                print(f"Break on ram write: \n"+\
                               f"{self.CurrentInstruction()}")
                data = 0
                if args[0] == "regA":
                    data = self.regA
                else:
                    data = self.regB
                print(f"0x{data:0{2}X} ==> Address 0x{args[1]:0{4}X}")
                return False
            else:
                return func(self, *args, **kwargs)
        return _check_ramBP
    def check_romBP(func):
        def _check_romBP(self, *args, **kwargs):
            if "r" in self.bp["rom"] and not self.continues:
                self.breakpoint = True
                print(f"Break on rom read: \n"+\
                               f"{self.CurrentInstruction()}")
                return False
            else:
                return func(self, *args, **kwargs)
        return _check_romBP   
    def check_lineBP(func):
        def _check_lineBP(self, *args, **kwargs):
            if self.line in self.bpline and not self.continues:
                self.breakpoint = True
                print(f"Break on 0x{self.line:0{3}X}: \n"+\
                               f"{self.CurrentInstruction()}")
                return False
            else:
                return func(self, *args, **kwargs)
        return _check_lineBP
    def setBP(self,location,operation):
        if location in self.bp:
            self.bp[location] = operation
        elif location == "line" and not (operation in self.bpline):
                self.bpline.append(operation)
        elif location == "rmline":
                self.bpline.remove(operation)

    def CurrentInstruction(self):
        return f"0x{self.line:0{3}X}: {self.instructions[self.line][0]} "+\
                 " ".join(self.instructions[self.line][1])
    def strInstructions(self):
        buffer = ""
        for instr in self.instructions:
            buffer += f"0x{instr:0{3}X}: {self.instructions[instr][0]} "+\
                       " ".join(self.instructions[instr][1])+"\n"
        return buffer
    def strLabels(self):
        buffer = ""
        for i in self.labels:
                buffer += f"{i[2:]}: 0x{self.labels[i]:0{2}X}\n"
        return buffer
    def strRom(self):
        buffer = ""
        for i in self.rom:
            buffer += f"0x{i:0{3}X}: 0x{self.rom[i]:0{2}X}\n"
        return buffer
    def strRam(self):
        buffer = ""
        for i in sorted(self.ram):
            buffer += f"0x{i:0{3}X}: 0x{self.ram[i]:0{2}X}\n"
        return buffer
    def strRegs(self):
        buffer =f"REGA: 0x{self.regA:0{2}X}\n"+\
                f"REGB: 0x{self.regB:0{2}X}\n"+\
                f"REGX: 0x{self.regX:0{4}X}\n"+\
                f"REGY: 0x{self.regY:0{4}X}\n"
        return buffer
    
    def __str__(self):
        buffer  = "\n ------GCPU_DUMP------- \n\n"+\
                 f"Instructions:\n{self.strInstructions()}"+\
                 f"\nLabel Locations\n{self.strLabels()}"+\
                 f"\nRom:\n{self.strRom()}"+\
                 f"\nRam:\n{self.strRam()}"+\
                 f"\nRegisters:\n{self.strRegs()}"+\
                 f"\n\nCurrent Line: 0x{self.line:0{3}X}"+\
                  "\n\n ------END_DUMP-------- \n\n"
        return buffer
    def dump(self):
        print(self)
        
    def load(self,filename):
        asm = open(filename,"r")
        origin = ""
        lineNum = 0
        for line in asm:
            line = line.strip()
            line = line.split(" ")
            if(line[0] == ''):
                continue
            if("::" in line[0]):
                self.labels[line[0]] = lineNum
                continue
            if("org" in line[0]):
                lineNum = int(line[1],0)
                continue
            if("db" in line[0]):
                self.rom[lineNum] = int(line[1],0)
                lineNum += 1
                continue
            args = []
            for arg in line[1:]:
                if ('%' in arg) or ("//" in arg):
                    break
                args.append(arg)
            self.instructions[lineNum]=(line[0],args)
            lineNum += 1
    @check_status
    @check_ramBP
    def write(self,reg,addr):
        if(addr > 0x0FFF and addr < 0x2000):
            if reg == "regA":
                self.ram[addr] = self.regA
            elif reg == "regB":
                self.ram[addr] = self.regB
        else:
            print("Invalid write operation at line: "+str(self.line))
            self.halt = True
    @check_status
    @check_romBP        
    def read(self,addr):
        if (addr < 0x1000 and addr >= 0x0000):
            return self.rom[addr]
        elif (addr > 0x0FFF and addr < 0x2000):
            return self.ram[addr]
        else:
            print("Invalid addr for reading; Gcpu has halted")
            self.halt = True
    @check_status
    def parse(self, instruction):
        inst = instruction[0]
        operands = instruction[1]
        if inst in branchMatch:
            if branchMatch[inst](self.regA):
                if self.line == self.labels[operands[0]]:
                    print("Execution has reached an infinite loop"+\
                                                   " and has halted")
                    self.halt = True
                self.line = self.labels[operands[0]]
                return False
        elif inst in regAMatch:
            self.setReg("regA",regAMatch[inst](self.regA,self.regB))
        elif inst in regBMatch:
            self.setReg("regB",regBMatch[inst](self.regA,self.regB))
        elif inst in ["INX","INY"]:
            if inst == "INX":
                self.setReg("regX",self.regX+1)
            elif inst == "INY":
                self.setReg("regY",self.regY+1)
        elif inst in dataMatch:
            dataMatch[inst](self)
        return True
    @check_status
    def parseOperand(self):
        instr = self.instructions[self.line][0]
        operand = " ".join(self.instructions[self.line][1])
        if "#" in operand and instr in ["LDAA","LDAB","LDX","LDY"]:
            return int(operand.strip()[1:],0)
        elif "," in operand and instr in ["LDAA","LDAB","STAA","STAB"]:
            commaEnd = operand.find(',')
            addr = 0
            if "Y" in operand:
                addr = self.regY + int(operand[:commaEnd])
            elif "X" in operand:
                addr = self.regX + int(operand[:commaEnd])
            if instr in ["LDAA","LDAB"]:
                return self.read(addr)
            else:
                return addr
        else:
            addr = int(operand,0)
            if instr in ["LDAA","LDAB"]:
                return self.read(addr)
            elif instr in ["STAA","STAB"]:
                return addr
            else:
                data = self.read(addr+1)
                data = data << 8
                data += self.read(addr)
                return data
    @check_status
    @check_regBP
    def setReg(self, reg, data):
        if reg == "regA":
            self.regA = data & 0xFF
        elif reg == "regB":
            self.regB = data & 0xFF
        elif reg == "regX":
            self.regX = data & 0xFFFF
        elif reg == "regY":
            self.regY = data & 0xFFFF
    @check_status
    @check_lineBP
    def step(self,debug=False):
        try:
            self.incStep = self.parse(self.instructions[self.line])
        except KeyError as e:
            print("Execution has reached an undefined "+\
                  "instruction at address: " + hex(self.line))
            self.halt = True
        if debug and not self.breakpoint:
            print(self.CurrentInstruction())
        if not self.breakpoint and self.incStep:
            self.line += 1
        self.continues = False
        
    @check_status
    def run(self,debug=False):
        self.continues = True
        while not self.halt:
            self.step(debug)
            if self.breakpoint:
                self.breakpoint = False
                break
            
