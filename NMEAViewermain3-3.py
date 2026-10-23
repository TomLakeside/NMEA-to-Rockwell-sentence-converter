#het verschil met versie 3-2 is dat je de tijden kunt manipuleren
#1/1/21: 14:37: volledig werkende versie ook na uit en aanzetten (ook netjes de python sheel stoppen)


import tkinter as tk
import serial,os,time,sys
import portseeker_dev as portseeker
from Nmeamathlib4 import *
from math import modf,cos,sin
import math
from datetime import datetime
import threading

baudrate=9600

RMCline=''
GGAline=''
GSAline=''
GSVline=''
RMCl=[]
GGAl=[]
GSAl=[]
GSVl=[]


def nmeareader():
        #leest NMEAregels totdat alle regels gelezen zijn en stopt na de RMC regel
        global RMCline,GGAline,GSAline,GSVline,nmea,logicout
        ggaready=False
        gsaready=False
        gsvready=False
        RMCl.clear()
        GGAl.clear()
        GSAl.clear()
        GSVl.clear()
        gsv=[]
        while True:
                try:
                        NmeaLine=str(nmea.readline(),"ascii")
                        #remove cr/lf:
                        #print(NmeaLine)
                        f=NmeaLine.find('\r')
                        if f>0:
                                NmeaLine=NmeaLine[0:f]
                        
                        while not checkchecksum(NmeaLine):  #check validity
                                print('Nmea line: ' + NmeaLine + ' is not valid')
                                NmeaLine=str(nmea.readline(),"ascii")
                                f=NmeaLine.find('\r')
                                if f>0:
                                        NmeaLine=NmeaLine[0:f]                                

                        l=NmeaLine.split(",")

                        if l[0]=="$GPRMC":
                                RMCline=NmeaLine
                                RMCl[:]=l
                                if ggaready and gsaready:
                                    #print(RMCline)
                                    #print(GSVl)
                                    return()
                        if l[0]=="$GPGGA":
                                GGAline=NmeaLine
                                GGAl[:]=l
                                ggaready=True
                        if l[0]=="$GPGSA":
                                GSAline=NmeaLine
                                GSAl[:]=l
                                gsaready=True
                        if l[0]=="$GPGSV":
                                gsv.clear()
                                gsv[:]=l
                                #print(gsv)
                                #print(gsv)
                                if gsv[2]=='1':GSVl.clear()
                                nrofsats=(len(gsv)-4)//4
                                for i in range(0,nrofsats):
                                    GSVl.append(gsv[4+4*i])
                                    GSVl.append(gsv[5+4*i])
                                    GSVl.append(gsv[6+4*i])
                                    sn=gsv[7+4*i]
                                    GSVl.append(sn[:sn.find('*')])

                                if gsv[2]==gsv[1]:
                                    #print(GSVl)
                                    for i in range(0,len(GSVl)):
                                        if GSVl[i]=='':GSVl[i]='0'
                                    #print(GSVl)
                                    gsvready=True
 
                except Exception as e:
                        #messagevar.set('Error reading from nmeaport')
                        print(e)
                        try:
                                inport,outport=portseeker.portseek(baudrate)
                                nmea=serial.Serial(inport,baudrate,8,'N',1)
                                logicout=serial.Serial(outport,9600,8,'O',1)
                                print('ports reset in nmeareader')
                        except:
                                print('ports reset in nmeareader unsuccesfull')
                                pass

lastwritetime=time.time()

def logicoutwriter():
        global lastwritetime,logicout
        if True:
                if True: #time.time()>lastwritetime+1:
                        try:
                                logicout.flush()

                                lastwritetime=time.time()
                                for i in range(len(tbytes)):
                                        a=logicout.write((tbytes[i]).to_bytes(1,byteorder='big'))
                                        time.sleep(0.0002) # prevent flooding of serial card
                                #print('data written to VDO')


                                #print('w')
                        except:
                            try:
                                        inport,outport=portseeker.portseek(baudrate)
                                        nmea=serial.Serial(inport,baudrate,8,'N',1)
                                        logicout=serial.Serial(outport,baudrate,8,'O',1)
                                        print('outputport reset in logicoutwriter succesvol')
                            except:
                                        print('outputport reset in logicoutwriter unsuccesfull')
                                        pass

          

def labelmaker(parentname,varname,caption,w,r,c):
    #exec('global '+varname+'var')
    exec('globals()[\''+varname+'var\']=tk.StringVar()')
    exec(varname+'var.set(\'No data\')')
    exec(varname+'txt=tk.Label('+parentname+',width='+str(w)+',text=\''+caption+':\',anchor=tk.W)')
    exec(varname+'label=tk.Label('+parentname+',width='+str(w)+',textvariable='+varname+'var,anchor=tk.W,relief=tk.FLAT)')
    exec(varname+'txt.grid(row='+str(r)+','+'column='+str(c)+',sticky=tk.W)')
    exec(varname+'label.grid(row='+str(r)+',column='+str(c+1)+',sticky=tk.W)')
        



def Updater():
    global prn
    while not killthread:
            nmeareader()
            if (RMCline!='' and GGAline!='' and GSAline!=''): #ipv try commande
                l=GGAline.split(',')
                #print(l)
                GGA.update({
                            'TimeStamp':str(int(floatsafe(l[1]))).rjust(6,'0'),
                            'Latitude':round(minutestodegrees(l[2]),6),
                            'NorthSouth':l[3],
                            'Longitude':round(minutestodegrees(l[4]),6),
                            'LonEastWest':l[5],
                            'Quality':l[6],
                            'NrOfSatellites':int(l[7]),
                            'HDOP':floatsafe(l[8]),
                            'AntennaAltitude':floatsafe(l[9]),
                            'UnitsOfAntennaAltitude':(l[10]),
                            'GeoidalSeperation':floatsafe(l[11]),
                            'UnitsOfGeoidalSeperation':l[12],
                            'AgeOfDiffGPSData':floatsafe(l[13]),
                            'DifferentialReferenceStationID':str(l[14]).split('*')[0],
                            'Checksum':'0x'+str(l[14]).split('*')[1][0:2],
                            })
                #print('\nGGA')
        #               dictprint(GGA,0)
                l=GSAline.split(',')
                prn.clear()
                prn = [l[3],l[4],l[5],l[6],l[7],l[8],l[9],l[10],l[11],l[12],l[13],l[14]]
                # we filteren satellieten met nummers > 31 er uit want dat kan de VDO niet aan
                i=0
                while i<len(prn):
                        if not prn[i].isnumeric():
                                del prn[i]
                        else:
                                if int(prn[i])>31: del prn[i]
                        i+=1
                        
                GSA.update({
                            'Mode1':l[1],
                            'Mode2':l[2],
                            'PRN':prn,
                            'PDOP':floatsafe(l[15]),
                            'HDOP':floatsafe(l[16]),
                            'VDOP':floatsafe(str(l[17]).split('*')[0]),
                            'Checksum':'0x'+str(l[17]).split('*')[1][0:2],
                            })
                        #print(l)
        #                print("\nGSA")
        #                dictprint(GSA,0)    
          
                l=GSVline.split(',') # wait for first GSV sentence
                #print(l)

                    # The GSV dictionary contains a list of satellite dictionaries (LOSD)
                    # PRN number,elevations,azimuth,SNR
                    # Every GSVsentence  containss max 4 satellites 
                    #
                if True:
                        if len(GSVl)>0:
                                #print(GSVl)

                                for i in range(0,len(GSVl)//4):
                                        LOSDnew[int(GSVl[4*i])]={
                                            'SVPRNnr':int(GSVl[4*i]),
                                            'Elevation':floatsafe(GSVl[4*i+1]),
                                            'Azimuth':floatsafe(GSVl[4*i+2]),
                                            'SNR':floatsafe(str(GSVl[4*i+3]))
                                            }
                                        GSV.update({
                                                'NrOfMessages':int(len(GSVl)//16),
                                                'TotalNrOfSVsInView':int(len(GSVl)//4),
                                                'LOSD':LOSDnew,
                                                })


                l=RMCline.split(',')


 
                RMC.update({
                            'TimeStamp':str(int(floatsafe(l[1]))).rjust(6,'0'),
                            'Validity':l[2],
                            'Latitude':round(minutestodegrees(l[3])+testcounter*testinterval,6),
                            'NorthSouth':l[4],
                            'Longitude':round(minutestodegrees(l[5])+testcounter*testinterval,6),
                            'LonEastWest':l[6],
                            'SOG':floatsafe(l[7]),
                            'COG':floatsafe(l[8]),
                            'DateStamp':l[9].rjust(6,'0'),
                            'Variation':floatsafe(l[10]),
                            'VarEastWest':l[11],
                            'UnkownField':str(l[12]).split('*')[0],
                            'Checksum':'0x'+str(l[12]).split('*')[1][0:2],
                            })
                
                #tbytes.clear()
                deltagpstime=dgt.get()#gpstimeentry.get() Dit blockes tot er iets verandert op het scherm
                if not deltagpstime.isnumeric(): deltagpstime=0
                deltagpstime=int(deltagpstime)
                deltautctime=dut.get()#utctimeentry.get()
                if not deltautctime.isnumeric(): deltautctime=0
                deltautctime=int(deltautctime)
                #print(deltagpstime,deltautctime)
                

                try:
                        rockwel_sentence(tbytes,RMC,GGA,GSA,GSV,LOSD,starttime,deltagpstime,deltautctime,utcval.get())
                        logicoutwriter()
                except:
                        print('Error in rockwel_sentence')

            try:
                s=RMC['TimeStamp']
                systimevar.set(s[0:2]+':'+s[2:4]+':'+s[4:6])
                s=RMC['DateStamp']
                #print(RMC)
                sysdatevar.set(s[0:2]+'/'+s[2:4]+'/'+s[4:6])
                longitudevar.set(floattodegrees(RMC['Longitude'])+' '+RMC['LonEastWest'])
                latitudevar.set(floattodegrees(RMC['Latitude'])+' '+RMC['NorthSouth'])
                cogvar.set(RMC['COG'])
                sogvar.set(RMC['SOG'])
                rlongitudevar.set(floattodegrees(efptofloat(37)/math.pi*180))
                rlatitudevar.set(floattodegrees(efptofloat(34)/math.pi*180))
                rsystimewvar.set(floattotime(int(efptofloat(6))))
                #utcvalidityvar.set(RMC['Validity'])
                rsystimedvar.set(floattotime(int(efptofloat(11))))
                rsysdatevar.set(str(spiftopositiveint(14))+'/'+str(spiftopositiveint(15))+'/'+str(spiftopositiveint(16)))
                velocitye=round(fptofloat(28)*3600/1852,6)
                velocityn=round(fptofloat(30)*3600/1852,6)
                if abs(velocityn)<0.00001: velocityn=0.00001
                #print(velocitye,velocityn,math.sqrt(velocitye**2+velocityn**2),math.atan(velocitye/velocityn))
                rsogvar.set(round(math.sqrt(velocitye**2+velocityn**2),3))
                rcog=round(math.atan(velocitye/velocityn)/math.pi*180,3)
                if velocityn<0: rcog+=180
                rcog=rcog%360
                rcogvar.set(rcog)

                l=GSA['PRN']
                #print(l)
                for i in range(0,12-len(l)):
                        l.append(0)
                for i in range(0,12):
                        if l[i]=='':l[i]='0'
                        if int(l[i]) >0:
                            s='sat'+str(i+1)+"var.set(GSV['LOSD'][int(l["+str(i)+"])]['SVPRNnr'])"
                            #print(s)
                            exec(s)
                            s='sn'+str(i+1)+"var.set(GSV['LOSD'][int(l["+str(i)+"])]['SNR'])"
                            #print(s)
                            exec(s)
                for i in range(0,5):
                        pr,id = rtoprnid(47+2*i)
                        sn=rtosn(48+2*i)
                        s='rsat'+str(i+1)+"var.set(pr)"
                        #print(s,pr)
                        exec(s)
                        s='rsn'+str(i+1)+"var.set(sn)"
                        #print(s)
                        exec(s)

                        

                pdopvar.set(GSA['PDOP'])
                hdopvar.set(GSA['HDOP'])
                vdopvar.set(GSA['VDOP'])
                rhdopvar.set(spiftoint(42))
                rvdopvar.set(spiftoint(43))
                rpdopvar.set(spiftoint(44))
                settimevar.set(dpiftoint(17))
                rdowvar.set(int(efptofloat(6)//3600//24))
                rposxvar.set(efptofloat(19)/1000)
                rposyvar.set(efptofloat(22)/1000)
                rposzvar.set(efptofloat(25)/1000)
                rherrvar.set(spiftoint(57))
                rverrvar.set(spiftoint(58))
                rterrvar.set(spiftoint(59))
                rserrvar.set(spiftoint(60))

                
                b=bin(spiftoint(63))
                b='0000000000000000'+b[2:]
                enginestatusvar.set(b[-16:-8]+' '+b[-8:])
                
            except Exception as e:
                #messagevar.set('Error setting stringvars')
                print(e)
                pass
        
            #time.sleep(1)

def floattotime(f):
    d=f//(24*3600)
    f-=d*24*3600
    h=f//3600
    f-=h*3600
    m=f//60
    f-=m*60
    s=f
    return(str(d)+' d:'+str(h)+':'+str(m)+':'+str(s))


def rtoprnid(w):
        i=spiftoint(w)
        prn=i&0b111111
        #print(i,prn)
        id=(i&(0b111000000000000))/2**8
        return(prn,id)
        
def rtosn(w):
        i=spiftoint(w)
        sn=(i&(0b11111100000000))/2**8
        #print('sn:',sn)
        return(sn)       

def efptofloat(startword):
    startbyte=2*(startword-1)  # tbytes begint met index 0
    sign=1
    if len(tbytes)<startbyte+5:
        print('tbytes has length: '+ str(len(tbytes)))
        return(0)
    if tbytes[startbyte+5]>=128: sign=-1
    return(sign*
           (0.5+ (tbytes[startbyte+5]%128)/256+
                tbytes[startbyte+4]/256**2+
                tbytes[startbyte+3]/256**3+
                tbytes[startbyte+2]/256**4+
                tbytes[startbyte+1]/256**5
            )*2**(tbytes[startbyte]-128))

def fptofloat(startword):
    startbyte=2*(startword-1)  # tbytes begint met index 0
    sign=1
    if tbytes[startbyte+3]>=128: sign=-1
    return(sign*
           (0.5+ (tbytes[startbyte+3]%128)/256+
                tbytes[startbyte+2]/256**2+
                tbytes[startbyte+1]/256**3
            )*2**(tbytes[startbyte]-128))
    

def floattodegrees(s):
    i=int(s)
    f=float(s)-i
    d=str(round(60*f,6))
    return(str(i)+chr(176)+d)

def spiftopositiveint(startword):
    startbyte=2*(startword-1)  # tbytes begint met index 0
    if tbytes[startbyte+1]>=128: sign=-1
    return((tbytes[startbyte+1]%128)*256+tbytes[startbyte])

def spiftoint(startword):
    startbyte=2*(startword-1)  # tbytes begint met index 0
    return(f2c16(tbytes[startbyte+1]*256+tbytes[startbyte]))

def dpiftoint(startword):
    startbyte=2*(startword-1)  # tbytes begint met index 0
    return(f2c32(tbytes[startbyte+3]*256**3+tbytes[startbyte+2]*256**2+tbytes[startbyte+1]*256+tbytes[startbyte]))
   
def f2c8(n): # 8bits 2 compl to signed numeric
    return(-(n//128)*128+n%128)
    
def f2c16(n): # 16bits 2 compl to signed numeric
    return(-(n//2**15)*2**15+n%2**15)

def f2c32(n): # 32bits 2 compl to signed numeric
    return(-(n//2**31)*2**31+n%2**31)

root=tk.Tk()
root.title('NMEAreader')
killthread=False
#labelmaker('root','filename','Filenaam',1,5)
labelmaker('root','systime','NMEA Time',12,1,1)
labelmaker('root','sysdate','NMEA Date',12,3,1)
labelmaker('root','longitude','Longitude',12,4,1)
labelmaker('root','latitude','Latitude',12,5,1)
labelmaker('root','cog','COG',12,6,1)
labelmaker('root','sog','SOG',12,7,1)
labelmaker('root','pdop','PDOP',12,13,1)
labelmaker('root','hdop','HDOP',12,14,1)
labelmaker('root','vdop','VDOP',12,15,1)

labelmaker('root','rsystimew','Rw time of w',12,1,5)
labelmaker('root','rsystimed','Rw time of d',12,2,5)
#labelmaker('root','utcvalidity','UTC validity',12,1,3)


dgt=tk.StringVar()
gpstimeentry=tk.Entry(root,textvariable=dgt)
gpstimeentry.grid(row=1,column=7)
dut=tk.StringVar()
utctimeentry=tk.Entry(root,textvariable=dut)
utctimeentry.grid(row=2,column=7)

utcval=tk.StringVar()
utcval.set('V')
utcvalentry=tk.Entry(root,textvariable=utcval)
utcvallabel=tk.Label(root,text='UTC Validity')
utcvallabel.grid(row=1,column=3)
utcvalentry.grid(row=1,column=4)

labelmaker('root','rsysdate','Rockwell Date',12,3,5)
labelmaker('root','rdow','Day of week',12,3,7)
labelmaker('root','rlongitude','Longitude',12,4,5)
labelmaker('root','rlatitude','Latitude',12,5,5)
labelmaker('root','rcog','COG',12,6,5)
labelmaker('root','rsog','SOG',12,7,5)
labelmaker('root','rpdop','PDOP',12,13,5)
labelmaker('root','rhdop','HDOP',12,14,5)
labelmaker('root','rvdop','VDOP',12,15,5)

f=tk.Frame(root)
f.grid(row=16,column=1, rowspan=12,columnspan=4,sticky=tk.NW)

labelmaker('f','sat1','Sat 1',6,1,1)
labelmaker('f','sn1','S/N ',  6,1,3)
labelmaker('f','sat2','Sat 2',6,2,1)
labelmaker('f','sn2','S/N ',  6,2,3)
labelmaker('f','sat3','Sat 3',6,3,1)
labelmaker('f','sn3','S/N ',  6,3,3)
labelmaker('f','sat4','Sat 4',6,4,1)
labelmaker('f','sn4','S/N ',  6,4,3)
labelmaker('f','sat5','Sat 5',6,5,1)
labelmaker('f','sn5','S/N ',  6,5,3)
labelmaker('f','sat6','Sat 6',6,6,1)
labelmaker('f','sn6','S/N ',  6,6,3)
labelmaker('f','sat7','Sat 7',6,7,1)
labelmaker('f','sn7','S/N ',  6,7,3)
labelmaker('f','sat8','Sat 8',6,8,1)
labelmaker('f','sn8','S/N ',  6,8,3)
labelmaker('f','sat9','Sat 9',6,9,1)
labelmaker('f','sn9','S/N ',  6,9,3)
labelmaker('f','sat10','Sat 10',6,10,1)
labelmaker('f','sn10','S/N ',  6,10,3)
labelmaker('f','sat11','Sat 11',6,11,1)
labelmaker('f','sn11','S/N ',  6,11,3)
labelmaker('f','sat12','Sat 12',6,12,1)
labelmaker('f','sn12','S/N ',  6,12,3)


rf=tk.Frame(root)
rf.grid(row=16,column=4, rowspan=5,columnspan=4,sticky=tk.NW)

labelmaker('rf','rsat1','Sat 1',6,1,1)
labelmaker('rf','rsn1','S/N ',  6,1,3)
labelmaker('rf','rsat2','Sat 2',6,2,1)
labelmaker('rf','rsn2','S/N ',  6,2,3)
labelmaker('rf','rsat3','Sat 3',6,3,1)
labelmaker('rf','rsn3','S/N ',  6,3,3)
labelmaker('rf','rsat4','Sat 4',6,4,1)
labelmaker('rf','rsn4','S/N ',  6,4,3)
labelmaker('rf','rsat5','Sat 5',6,5,1)
labelmaker('rf','rsn5','S/N ',  6,5,3)

labelmaker('root','settime','Set time',10,28,1)
labelmaker('root','enginestatus','Engine Status',16,28,3)


pf=tk.Frame(root)
pf.grid(row=21,column=4, columnspan=4,sticky=tk.NW)

labelmaker('pf','rposx','Pos X',6,1,1)
labelmaker('pf','rposy','Pos Y ',6,2,1)
labelmaker('pf','rposz','Pos Z',6,3,1)
labelmaker('pf','rherr','H Error',6,4,1)
labelmaker('pf','rverr','V Error',6,5,1)
labelmaker('pf','rterr','T Error',6,6,1)
labelmaker('pf','rserr','S Error',6,7,1)

tbytes=bytearray(128)
RMC={}
GGA={}
GSA={}
GSV={}
LOSD=[]
LOSDnew={}
prn=[]

printdebug=False


starttime=time.time()


inport,outport=portseeker.portseek(baudrate)
nmea=serial.Serial(inport,baudrate,8,'N',1)
logicout=serial.Serial(outport,baudrate,8,'O',1)

def tupdate():
        global root
        while True:
                root.update()
                time.sleep(0.1)

tu=threading.Thread(target=tupdate)
tu.start()

t=threading.Thread(target=Updater)
t.start()

demomode=False
testcounter=0
if demomode:
        testinterval=0.001
else:
        testinterval=0




root.mainloop()

killthread=True
time.sleep(3)
    
