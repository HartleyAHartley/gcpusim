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
               "BN":(lambda x: x<0),  "BP":(lambda x: x>=0)}
dataMatch = {"LDAA"  :(lambda x: x.setReg("regA",x.parseOperand()))}
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
        self.bp = {"regA":"","regB":"","regX":"","regY":"","ram":""}
        
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
            if "w" in self.bp[args[0]]:
                self.breakpoint = True
                print(f"Break on {args[0]} write: \n{self.CurrentInstruction()}")
                return False
            else:
                return func(self, *args, **kwargs)
        return _check_regBP
    def check_ramBP(func):
        def _check_ramBP(self, *args, **kwargs):
            if "w" in self.bp["ram"]:
                self.breakpoint = True
                print(f"Break on ram write: \n{self.CurrentInstruction()}")
                return False
            else:
                return func(self, *args, **kwargs)
        return _check_ramBP
    def setBP(self,location,operation):
        if location in self.bp:
            self.bp[location] = operation
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
                buffer += f"{i[2:]}: {self.labels[i]}\n"
        return buffer
    def strRom(self):
        buffer = ""
        for i in self.rom:
            buffer += f"0x{i:0{3}X}: 0x{self.rom[i]:0{2}X}\n"
        return buffer
    def strRam(self):
        buffer = ""
        for i in self.ram:
            buffer += f"0x{i:0{3}X}: 0x{self.ram[i]:0{2}X}\n"
        return buffer
    def strRegs(self):
        buffer =f"REGA: {self.regA}\n"+\
                f"REGB: {self.regB}\n"+\
                f"REGX: {self.regX}\n"+\
                f"REGY: {self.regY}\n"
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
    def write(self,addr,data):
        if(addr < 0x1000 or addr > 0x1FFF):
            ram[addr] = data
        else:
            print("Invalid write operation at line: "+str(self.line))
            self.halt = True
    def parse(self, instruction):
        inst = instruction[0]
        operands = instruction[1]
        if inst in branchMatch:
            if branchMatch[inst](self.regA):
                if self.line == self.labels[operands[0]]:
                    print("Execution has reached an infinite loop and has halted")
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
        return True
    def parseOperand(self):
        return
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
    def step(self,debug=False):
        try:
            self.incStep = self.parse(self.instructions[self.line])
        except KeyError as e:
            print("Execution has reached an undefined "+\
                  "instruction at address: " + hex(self.line))
            self.halt = True
        if debug:
            print(self.CurrentInstruction())
        if self.breakpoint:
            self.breakpoint = False
            return False
        else:
            self.line += 1
            return True
        
    @check_status
    def run(self,debug=False):
        while not self.halt :
            if not self.step(debug):
                break
            
if len(sys.argv) == 1:
    print("gcpy.py FILENAME")
    exit()

cpu = Gcpu()
cpu.load(sys.argv[1])
cpu.setBP("regX","w")
cpu.run()
cpu.dump()
#DATA MOVEMENT