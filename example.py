import sys
from gcpy import Gcpu
            
if len(sys.argv) == 1:
    print("example.py FILENAME")
    exit()

cpu = Gcpu()
cpu.load(sys.argv[1])
#print(cpu.bpline)
while not cpu.halt:
    cpu.run()
    #cpu.dump()
    #print(cpu.strRegs())
cpu.dump()
