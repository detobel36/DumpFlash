from array import array as Array

import traceback
import sys
from pyftdi.ftdi import *

import tkinter

DEBUG = True


def print_debug(message):
    if DEBUG:
        print("[DEBUG]:", message)

NAND_CMD_READID=0x90
NAND_CMD_RESET=0xff

class NandIO:

    ADR_CE=0x10
    ADR_WP=0x20
    ADR_CL=0x40
    ADR_AL=0x80



    def __init__(self):
        self.Ftdi = Ftdi()
        try:
            self.Ftdi.open(0x0403,0x6010,interface=1)
        except:
            traceback.print_exc(file=sys.stdout)
            raise ReferenceError("Error with the chip (check consol log)")

        self.Ftdi.set_bitmode(0, self.Ftdi.BITMODE_MCU)

        self.debug_write(Array('B', [Ftdi.DISABLE_CLK_DIV5]))
        
        # Default in python2: 1 (in python3: 12 (don't know why this difference))
        self.Ftdi.set_latency_timer(Ftdi.LATENCY_MIN)

    def debug_write(self, data):
        str_data = [str(hex(elem)) for elem in data]
        print("write_data ", str_data)
        self.Ftdi.write_data(data)

    def GetID(self):
        self.sendCmd(NAND_CMD_READID)
        self.sendAddr(0,1)
        id=self.readFlashData(8)
        return id

    def print_id(self):
        for elem in self.id:
            print(hex(elem))

    def nandWrite(self,cl,al,data):
        cmds=[]
        cmd_type=0
        if cl==1:
            cmd_type|=self.ADR_CL
        if al==1:
            cmd_type|=self.ADR_AL

        cmds+=[Ftdi.WRITE_EXTENDED, cmd_type, 0, ord(data[0])]
        for i in range(1,len(data),1):
            #if i == 256:
            #   cmds+=[Ftdi.WRITE_SHORT, 0, ord(data[i])]
            cmds+=[Ftdi.WRITE_SHORT, 0, ord(data[i])]
        print_cmd = [str(hex(elem)) for elem in cmds]
        self.Ftdi.write_data(Array('B', cmds))
        return cmds

    def sendCmd(self,cmd):
        print("sendCmd", hex(cmd))
        return self.nandWrite(1,0,chr(cmd))

    def sendReset(self):
        self.sendCmd(NAND_CMD_RESET)

    def readFlashData(self,count):
        return self.nandRead(0,0,count)

    def sendAddr(self,addr,count):
        print("send Addr")
        data = ''

        for i in range(0,count,1):
            data += chr(addr & 0xff)
            addr = addr >> 8

        return self.nandWrite(0,1,data)

    def nandRead(self,cl,al,count):
        cmds=[]
        cmd_type=0
        if cl==1:
            cmd_type|=self.ADR_CL
        if al==1:
            cmd_type|=self.ADR_AL

        cmds+=[Ftdi.READ_EXTENDED, cmd_type, 0]

        for i in range(1,count,1):
            cmds+=[Ftdi.READ_SHORT, 0]

        cmds.append(Ftdi.SEND_IMMEDIATE)
        self.Ftdi.write_data(Array('B', cmds))
        data = self.Ftdi.read_data_bytes(count)
        return data.tolist()

class Interface:

    def __init__(self):
        super().__init__()

        self.planned_command = list()
        self.list_button_control_io = list()

        self.top = tkinter.Tk()
        self.init_button()
        self.top.mainloop()

    def init_button(self):
        tkinter.Grid.rowconfigure(self.top, 0, weight=1)
        tkinter.Grid.columnconfigure(self.top, 0, weight=1)

        init_button = tkinter.Button(self.top, text="Init connection", command=self.button_init_con)
        init_button.grid(row=0, column=0)

        reset_button = tkinter.Button(self.top, text="Reset", command=self.button_reset, 
            state=tkinter.DISABLED)
        reset_button.grid(row=0, column=1)
        self.list_button_control_io.append(reset_button)

        get_id_button = tkinter.Button(self.top, text="GetId", command=self.button_get_id, 
            state=tkinter.DISABLED)
        get_id_button.grid(row=0, column=2)
        self.list_button_control_io.append(get_id_button)

        read_button = tkinter.Button(self.top, text="Read", command=self.button_read, 
            state=tkinter.DISABLED)
        read_button.grid(row=0, column=3)
        self.list_button_control_io.append(read_button)

        self.event_text, ybar = self._init_text_scroll()
        self.event_text.grid(row=1, column=0, columnspan=4, rowspan=3, sticky=tkinter.N+tkinter.S+tkinter.E+tkinter.W)
        ybar.grid(row=1, column=5, rowspan=3, sticky=tkinter.N+tkinter.S+tkinter.E+tkinter.W)

        # FRAME to display planned commands
        frame = tkinter.Frame(self.top)
        frame.grid(row=1, column=7, sticky=tkinter.N+tkinter.S+tkinter.E+tkinter.W)        

        tkinter.Label(frame, text="Planned commands").grid(row=0, column=0, columnspan=4)

        self.planed_cmd_text, ybar = self._init_text_scroll(frame)
        self.planed_cmd_text.grid(row=1, column=0, columnspan=3, sticky=tkinter.N+tkinter.S+tkinter.E+tkinter.W)
        ybar.grid(row=1, column=4, sticky=tkinter.N+tkinter.S+tkinter.E+tkinter.W)        
        self.next_instruction_button = tkinter.Button(frame, text="Next", 
            command=self.button_next_instruction, state=tkinter.DISABLED)
        self.next_instruction_button.grid(row=2, column=0, columnspan=3)

        # Display 
        tkinter.Label(self.top, text="Encoded executed commands").grid(row=2, column=6, columnspan=3)

        self.cmd_text, ybar = self._init_text_scroll()
        self.cmd_text.grid(row=3, column=6, columnspan=3, sticky=tkinter.N+tkinter.S+tkinter.E+tkinter.W)
        ybar.grid(row=3, column=10, sticky=tkinter.N+tkinter.S+tkinter.E+tkinter.W)


    def _init_text_scroll(self, parent=None):
        if parent is None:
            parent = self.top
        ybar = tkinter.Scrollbar(parent)
        scroll_text = tkinter.Text(parent, height=10, width=30)
        ybar.config(command=scroll_text.yview)
        scroll_text.config(yscrollcommand=ybar.set)
        return scroll_text, ybar

    def button_get_id(self):
        self.add_planned_cmd(NAND_CMD_READID)
        self.add_planned_addresse((0, 1))

    def button_read(self):
        pass  # TODO

    def button_reset(self):
        self.add_planned_cmd(NAND_CMD_RESET)

    def button_next_instruction(self):
        command = self.planned_command.pop(0)
        key, value = command

        self.write_info_log("Execute: " + self._cmd_to_string(command))

        if key == "CMD":
            result = self.io.sendCmd(value)
        elif key == "ADR":
            result = self.io.sendAddr(value[0], value[1])
        else:
            self.write_error_log("Could not execute this command (unknow operation) !")

        self.cmd_text.insert("end", " ".join([hex(elem) for elem in result]) + "\n")

        self.planed_cmd_text.delete("1.0", "2.0")
        self.planed_cmd_text.update()

        if len(self.planned_command) == 0:
            self.next_instruction_button.config(state=tkinter.DISABLED)

    def button_init_con(self):
        try:
            self.io = NandIO()
        except ReferenceError as es:
            self.write_error_log(str(es))
            return

        for button in self.list_button_control_io:
            button.config(state="normal")

    def add_planned_cmd(self, cmd_code):
        self.add_planned_command_line(("CMD", cmd_code))

    def add_planned_addresse(self, addresse):
        self.add_planned_command_line(("ADR", addresse))

    def add_planned_command_line(self, command):
        self.planned_command.append(command)
        self.planed_cmd_text.insert("end", self._cmd_to_string(command) + "\n")
        self.next_instruction_button.config(state="normal")

    def _cmd_to_string(self, command):
        key = command[0]
        if key == "CMD":
            value = str(hex(command[1]))
        elif key == "ADR":
            # Display the two addresses
            value = str(command[1][0]) + ", " + str(command[1][1])
        else:
            value = str(command[1])

        return "[" + key + "] " + value

    def write_error_log(self, message):
        self._write_log("[ERROR] " + message)

    def write_info_log(self, message):
        self._write_log("[INFO] " + message)

    def _write_log(self, message):
        self.event_text.insert("end", message + "\n")
        self.event_text.see(tkinter.END)
        self.event_text.edit_modified(0)


Interface()
