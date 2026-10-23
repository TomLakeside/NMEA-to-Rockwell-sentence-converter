import serial.tools.list_ports
import os,sys




def printlog(s):
    print(s)

def portseek(baudrate):
    inport =''
    outport=''
    while inport=='':
        portlist=serial.tools.list_ports.comports()
        for p in portlist:
            try:
                s=serial.Serial(p.device,baudrate,8,'N',1,timeout=1)
                line=str(s.readline(),'utf-8')      # bytestring to string
                if line.find('*')>0: inport=p.device
                s.close()
            except:
                printlog('Something went wrong while reading from '+p.device)
                #sys.exit()
        for p in portlist:
            if (p.device.find('USB')>0 or p.device.find('usb')>0) and p.device != inport:
                outport=p.device
    return(inport,outport)

def portlist():
        portlist=serial.tools.list_ports.comports()
        for p in portlist:
            print(p.device)
            


