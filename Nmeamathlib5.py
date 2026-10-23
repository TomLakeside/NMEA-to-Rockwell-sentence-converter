from math import *

import os,time,sys
from math import modf,cos,sin
from datetime import datetime
import datetime 

leapseconds=18 #(gps 18 seconds ahead of UTC but 10 sec correction)
printdebug=False


def latlonhtoxyzwgs84(lat,lon,h):
    # this function converts latitude,longitude and height above surface to earthcentered xyx
    # coordinates in wgs84
    # lat and ln in decimal degrees e.g. 52.724156, heigth in meters
    # for algoritm see https://en.wikipedia.org/wiki/Geographic_coordinate_conversion#From_geodetic_to_ECEF_coordinates
    # for values of a and b see https://en.wikipedia.org/wiki/Earth_radius#Radius_of_curvature
    a=6378137.0               #radius a of earth in meters cfr WGS84
    b=6356752.3             #radius b of earth in meters cfr WGS84
    e2=1-(b**2/a**2)
    latr=lat/90*0.5*pi      #latitude in radians
    lonr=lon/180*pi         #longituede in radians
    Nphi=a/sqrt(1-e2*sin(latr)**2)
    x=(Nphi+h)*cos(latr)*cos(lonr)
    y=(Nphi+h)*cos(latr)*sin(lonr)
    z=(b**2/a**2*Nphi+h)*sin(latr)
    return([x,y,z])
   

def float_to_binary(num):
    exponent=0
    shifted_num=num
    while shifted_num != int(shifted_num):
        shifted_num*=2
        exponent+=1
        #print(shifted_num)
        #print(exponent)
    if exponent==0:
        return '{0:0b}'.format(int(shifted_num))
    binary='{0:0{1}b}'.format(int(shifted_num),exponent+1)
    #print(bin(int(shifted_num)))
    #print(binary)
    integer_part=binary[:-exponent]
    fractional_part=binary[-exponent:].rstrip('0')
    return '{0}.{1}'.format(integer_part,fractional_part)

def twos_complement(signed_n, length):
    #maakt van een signed integer n het twoscomplement met een lengte van bits
    s = bin(signed_n & int("1"*length, 2))[2:]
    return ("0b"+"{0:0>%s}" % (length)).format(s)

def float_to_fpf(num,digits):
    #werkt alleen met positive getallen:
    #traceprint('in float_to_fpf met num: ' + str(num))
    if num<0:
        num=-1*num
    #stap 1: maak van num een binary met float_to_binary
    #stap 2: bepaal de positie van de decimale punt en verwijder deze
    #stap 3: de exponent wordt gelijk aan het -1* het aantal digits minus de positie van de decimale punt
    #stap 4: truncate de string op aantal digits
    binary='0b'+float_to_binary(abs(num))
    #traceprint(binary)
    db=binary.find('.')
    if (db>-1):
        exponent=-1*(len(binary)-db-1)
        binary=binary[0:db]+binary[db+1:]
    else:
        exponent=0
    #traceprint(binary)
    #print(exponent)
    #Als lengte > digits: x karakters van achter weghalen en exponent met x verhogen
    # LET OP binary bevat ook nog de '0b' vooraf: vandaar len(binary)-2 
    if (len(binary)-2)>digits:
        exponent+=(len(binary)-2-digits)
        binary=binary[0:digits+2]
    #if (num>=0): #vooraan nullen toevoegen
    binary='0b' + binary[2:].zfill(digits)
    #traceprint('na zfill' + binary)    
    if (num<0): #twos complemente van maken
        binary=bin(int(twos_complement(-1*int(binary,2),digits),2))
    #binary=binary[0:digits+2]
    #print(binary)
    l=[0,0]
    l[0]=binary
    l[1]=bin(exponent+128) #excess 128 coding
    return(l)

def fpf_bytes(num,digits):
    #traceprint('enter fpf_bytes')
    if (digits not in (24,40)):
        exit()
    l=float_to_fpf(abs(num),digits)
    #traceprint('In fpfbytes na return van float_to_fpf' +l[0]+' '+l[1])
    #Eerst left shiften tot eerste karakter een 1 is (Rockwell protocol)
    #
    p=l[0].find('1')
    #print(p)
    if (p==-1): #bij 0 een 1 toevogen op de lSB
        #traceprint(l[0])
        l[0]=l[0][0:digits+1]+'1'  #digits + 1 vanwege de '0b' aan de voorkant
       #traceprint(l[0])
        #exit() # waarde =0 nog afvangen
    p=l[0].find('1')
    if (p<2):
        #traceprint('fpf_bytes p<2')
        exit() # error
    mantissa=l[0]
    exponent=int(l[1],2)
    #print(mantissa)
    #print(exponent)
    #breng de eerst 1 naar voren
    mantissanew='0b'+mantissa[p:digits+2].ljust(digits,'0')
    exponent-=p-2
    exponent=bin(exponent)

    #print(mantissanew)
    #print(exponent)

    #print(p)
    b=[]
    if (digits==24):
        b=[0,0,0,0]
        if num!=0: # numeric zero means all digits zero
            if (num<0):
                b[0]=128 #tekenbit
            b[0]+=int(mantissanew[3:10],2)
            b[1]=int(mantissanew[10:18],2)
            b[2]=int(mantissanew[18:26],2)
            b[3]=int(exponent,2)+24
        
    if (digits==40):
        b=[0,0,0,0,0,0]
        if num!=0:
            if (num<0):
                b[0]=128 #tekenbit
            b[0]+=int(mantissanew[3:10],2)
            b[1]=int(mantissanew[10:18],2)
            b[2]=int(mantissanew[18:26],2)
            b[3]=int(mantissanew[26:34],2)
            b[4]=int(mantissanew[34:42],2)
            b[5]=int(exponent,2)+40
    #traceprint('exit fpf_bytes')
    return(b)  #Order is MSB to LSB
    

def float_to_fp(num):
    return fpf_bytes(num,24)

def float_to_efpf(num):
    return fpf_bytes(num,40)

def int_to_spif(num):
    tbytes=[0,0,0,0]
    tbytes[0]=int(num)
    tbytes[1]=twos_complement(int(num),16)
    tbytes[2]=int(tbytes[1][2:10],2)
    tbytes[3]=int(tbytes[1][10:18],2)
    return(tbytes)    #Order is MSB to LSB
    

def int_to_dpif(num):
    tbytes=[0,0,0,0,0,0]
    tbytes[0]=int(num)
    tbytes[1]=twos_complement(int(num),32)
    tbytes[2]=int(tbytes[1][2:10],2)
    tbytes[3]=int(tbytes[1][10:18],2)
    tbytes[4]=int(tbytes[1][18:26],2)
    tbytes[5]=int(tbytes[1][26:34],2)
    return(tbytes)   #Order is MSB to LSB
    
def int_to_spif2(num):  #werkt nog niet met bytes maar met words: niet nodig
    tbytes=[0,0,0,0]
    tbytes[0]=int(num)
    tbytes[1]=tbytes[0]&(2**16-1)
    tbytes[3]=int(tbytes[1]/2**16)  #MSB in 3/LSB in 2
    tbytes[2]=int(tbytes[1]%2**16)
    return(tbytes)

def rockwelheaderchecksum(tbytes,startwith=0,upto=7):
    return(rockweldatachecksum(tbytes,startwith,upto))

def rockweldatachecksumold(tbytes,startwith=10,upto=126):
    sum=0
    for i in range(startwith,upto):
        sum+=tbytes[i]
    return(int(twos_complement(-1*sum%2**16,16),base=2))
    #checksum is sommatie module 2^16 en daar het twoscomplement van met lengte 16


def rockweldatachecksum(tbytes,startwith=10,upto=126):
    sum=0
    i=startwith
    while i<upto:
        sum+=tbytes[i]+256*tbytes[i+1]
        i+=2
    return(int(twos_complement(-1*sum%2**16,16),base=2))
    #checksum is sommatie module 2^16 en daar het twoscomplement van met lengte 16   
def rockwel_sentence_102(tbytes,GSV,sequencenr):
     #header word 1-4
    tbytes[0]=(255)
    tbytes[1]=(129)
    
    tbytes[2]=(102)
    tbytes[3]=(0)

    tbytes[4]=(58)# 5 words per satellite =13``=nrosfsateleite
    tbytes[5]=(0)
    
    tbytes[6]=(0)
    tbytes[7]=(0) # no acknowledge
    # header checksum word 5
    result=int_to_spif(rockwelheaderchecksum(tbytes))
    tbytes[8]=(result[3])
    tbytes[9]=(result[2])

    #traceprint('Set time word 6-7')
   # dit is de inschakeltijd van het device
    #* 50 omdat de unit 20ms is.
    result=50*int(time.time()-starttime)
    result=int_to_dpif(result)
    tbytes[10]=(result[5])
    tbytes[11]=(result[4])
    tbytes[12]=(result[3])
    tbytes[13]=(result[2])

    tbytes[14]=(148) # no idea why
    tbytes[15]=((26*sequencenr/1920)%256)

    #sequenx in word9-10
    result=int_to_dpif(sequencenr)
    tbytes[16]=(result[5])
    tbytes[17]=(result[4])
    tbytes[18]=(result[3])
    tbytes[19]=(result[2])
    
    
def rockwel_sentence(tbytes,RMC,GGA,GSA,GSV,LOSD,starttime):
    #header word 1-4
    #print(deltagpstime,deltautctime)
    tbytes[0]=(255)
    tbytes[1]=(129)
    
    tbytes[2]=(103)
    tbytes[3]=(0)

    tbytes[4]=(58)
    tbytes[5]=(0)
    
    tbytes[6]=(0)
    tbytes[7]=(0) # no acknowledge
    # header checksum word 5
    result=int_to_spif(rockwelheaderchecksum(tbytes))
    tbytes[8]=(result[3])
    tbytes[9]=(result[2])
   
    #traceprint('Time of week word 6-8:')
    #We gebruiken hier utcnow() daar is discussie over maar zo belangrijk is het niet
    #print(datetime.utcnow())
    ts=RMC['TimeStamp']
    ds=RMC['DateStamp']
    #print(ds+ts)
    datetimeformat = "%d%m%y%H%M%S"
    utcnow = datetime.datetime.strptime(ds+ts,datetimeformat)
    #print(utcnow)
    
    resultutctoweek = utctoweekseconds(utcnow,leapseconds)
    #result= (24*3600*7*resultutctoweek[0]+resultutctoweek[2])
    #+resultutctoweek[3]/1000000
    result=resultutctoweek[2]
    #print(result)
    result=float_to_efpf(result)
    tbytes[10]=(result[5])
    tbytes[11]=(result[4])
    tbytes[12]=(result[3])
    tbytes[13]=(result[2])
    tbytes[14]=(result[1])
    tbytes[15]=(result[0])
    
   #traceprint('GPS weeknr word 9:')
    ######### waarom geeft VDO de goede gegeves als het GPS weeknummer 0 is? Omdat ik bij de time of week het aantal
    #seconden vanaf de epoch had geteld, dus nog 40 jaar verder
    result=int_to_spif(resultutctoweek[0])
    tbytes[16]=(result[3])
    tbytes[17]=(result[2])
    
    #UTC validity word 10

    if RMC['Validity']=='A':
        tbytes[18]=(1)
    else:
        tbytes[18]=(0)
        
    tbytes[19]=(0)
    
    #Time of day word 11-13
    #Warning: this is derived from RMC time of day and has not GPS \
    #microsecond accuracy.  Sufficient for marine purposes
    s=RMC['TimeStamp']
    result=int(s[4:6])+60*(int(s[2:4])+60*int(s[0:2]))
#    print(result)
#    print(s)
#    print('time of day'+str(result))
    result=float_to_efpf(result)
    tbytes[20]=(result[5])
    tbytes[21]=(result[4])
    tbytes[22]=(result[3])
    tbytes[23]=(result[2])
    tbytes[24]=(result[1])  
    tbytes[25]=(result[0])
    
   #traceprint('UTC day word 14')
    result=int_to_spif(int(RMC['DateStamp'][0:2]))
 #   result=int_to_spif(0)
#    print(result)
    tbytes[26]=(result[3])
    tbytes[27]=(result[2])
    
    #traceprint('Month word 15')
    result=int_to_spif(int(RMC['DateStamp'][2:4]))
#    print(result)
    tbytes[28]=(result[3])
    tbytes[29]=(result[2])
    
    #traceprint('UTC Year word 16')
    result=int_to_spif(int('20'+RMC['DateStamp'][4:6]))
#    result=int_to_spif(int(RMC['DateStamp'][4:6]))
#    print(result)
    tbytes[30]=(result[3])
    tbytes[31]=(result[2])

    #traceprint('Set time word 17-18')
   # dit is de inschakeltijd van het device
    #* 50 omdat de unit 20ms is.
    result=50*int(time.time()-starttime)
    result=int_to_dpif(result)
    tbytes[32]=(result[5])
    tbytes[33]=(result[4])
    tbytes[34]=(result[3])
    tbytes[35]=(result[2])
    

 
    xyz=latlonhtoxyzwgs84(RMC['Latitude'],RMC['Longitude'],GGA['AntennaAltitude'])
    wgs84X=xyz[0]
    wgs84Y=xyz[1]
    wgs84Z=xyz[2]
    #print(xyz) #testprint
    
   #traceprint('Position X word 19-21')
    result=float_to_efpf(wgs84X)
    tbytes[36]=(result[5])
    tbytes[37]=(result[4])
    tbytes[38]=(result[3])
    tbytes[39]=(result[2])
    tbytes[40]=(result[1])
    tbytes[41]=(result[0])
    #Position Y word 22-24
    result=float_to_efpf(wgs84Y)
    tbytes[42]=(result[5])
    tbytes[43]=(result[4])
    tbytes[44]=(result[3])
    tbytes[45]=(result[2])
    tbytes[46]=(result[1])
    tbytes[47]=(result[0])
    #Position Z word 25-27
    result=float_to_efpf(wgs84Z)
    tbytes[48]=(result[5])
    tbytes[49]=(result[4])
    tbytes[50]=(result[3])
    tbytes[51]=(result[2])
    tbytes[52]=(result[1])
    tbytes[53]=(result[0])
   #traceprint('Velocity East word 28-29')
    sog=RMC['SOG']
    cog=RMC['COG'] 
    #print(sog) #test
    #traceprint(cog)
    #traceprint('na cog')
    #result=sog*cos(-1*(cog-90)/180*pi)
    result=float_to_fp(sog*sin((cog)/180*pi)*1852/3600)
    #traceprint(result)
    #result=float_to_fp(result)
    #print("velocity east",result)
    #traceprint(result)
    tbytes[54]=(result[3])
    tbytes[55]=(result[2])
    tbytes[56]=(result[1])
    tbytes[57]=(result[0])
   #traceprint('Velocity North word 30-31')
    #result=float_to_fp(sog*sin(-1*(cog-90)/180*pi))
    result=float_to_fp(sog*cos((cog)/180*pi)*1852/3600)
    #print("velocity north" ,result)
    tbytes[58]=(result[3])
    tbytes[59]=(result[2])
    tbytes[60]=(result[1])
    tbytes[61]=(result[0])
    #Velocity Up word 32-33
    #assume zero
    result=float_to_fp(0)
    tbytes[62]=(result[3])
    tbytes[63]=(result[2])
    tbytes[64]=(result[1])
    tbytes[65]=(result[0])
    #Latitude word 34-36
    result=RMC['Latitude']/90*0.5*pi
    if RMC['NorthSouth']=='S': result*=-1
    #print('lattest',result)
    result=float_to_efpf(result)
    #print(result)
    tbytes[66]=(result[5])
    tbytes[67]=(result[4])
    tbytes[68]=(result[3])
    tbytes[69]=(result[2])
    tbytes[70]=(result[1])
    tbytes[71]=(result[0])
   #traceprint('Longituede X word 37-39')
    result=RMC['Longitude']/180*pi
    if RMC['LonEastWest']=='W': result*=-1
    #print('lontest',result)
    result=float_to_efpf(result)
    #print(result)
    tbytes[72]=(result[5])
    tbytes[73]=(result[4])
    tbytes[74]=(result[3])
    tbytes[75]=(result[2])
    tbytes[76]=(result[1])
    tbytes[77]=(result[0])
   #traceprint('Altitude word 40-41')
    result=GGA['AntennaAltitude']
    result=float_to_fp(result)
    tbytes[78]=(result[3])
    tbytes[79]=(result[2])
    tbytes[80]=(result[1])
    tbytes[81]=(result[0])
    #Horizontal dilution of precision word 42
    result=int_to_spif(int(GSA['HDOP']*100))
    #print(GSA['HDOP'])#testprint
    tbytes[82]=(result[3])
    tbytes[83]=(result[2])
    #Vertical dilution of precision word 43
    result=int_to_spif(int(GSA['VDOP']*100))
    tbytes[84]=(result[3])
    tbytes[85]=(result[2])
    #Position dilution of precision word 44
    result=int_to_spif(int(GSA['PDOP']*100))
    tbytes[86]=(result[3])
    tbytes[87]=(result[2])
   #traceprint('Time dilution of precision word 45')
    #Deze wordt niet doorgegeven dus ik neem het gemiddelde van de ander drie
    result=int_to_spif(int(int(GSA['HDOP']*100)
                           +int(GSA['VDOP']*100)
                           +int(GSA['PDOP']*100)/3))
    tbytes[88]=(result[3])
    tbytes[89]=(result[2])
    #Geometric dilution of precision word 46
    #zie vorige opmerking
    tbytes[90]=(result[3])
    tbytes[91]=(result[2])
    #Channel 1-5 Measurement state word 47
    #Alleen nrs < 32 toegestaan
    #Channels tussen 1 en 5 staan standaard op 1
    traceprint(GSA)
    for i in range(5):
        if GSA['PRN'][i].isnumeric():
            PRN=int(GSA['PRN'][i])
        else:
            PRN=0
        if (PRN>0):
           #traceprint(PRN)
            try:
                SNR=GSV['LOSD'][PRN]['SNR']
            except:
               #traceprint('PRN:'+str(PRN)+'not found in GSV')
                SNR=0
           #traceprint(str(PRN)+'snr:'+str(SNR))   #channel id nog toevoegen: 1 tot 5 in bit 12-14 = i*2**12 
            result=int_to_spif(PRN%32+2**8+2**9+2**11+(i+1)*2**12)
            tbytes[92+4*i]=(result[3])
            tbytes[93+4*i]=(result[2])
            result=int_to_spif(int(SNR)*2**8)
            tbytes[94+4*i]=(result[3])
            tbytes[95+4*i]=(result[2])
        else:
            tbytes[92+4*i]=(0)
            tbytes[93+4*i]=(0)
            tbytes[94+4*i]=(0)
            tbytes[95+4*i]=(0)
    #Expected Horizontal Position Error word 57
    #Stel 10 meter
    result=int_to_spif(6)  # uit sniffing
    tbytes[112]=(result[3])
    tbytes[113]=(result[2])
    #Expected Vertical Position Error word 58
    #Kopie van VDOP?
    result=int_to_spif(3) # uit sniffing
    tbytes[114]=(result[3])
    tbytes[115]=(result[2])
    #Expected Time Error word 59
    result=int_to_spif(2)  # uit sniifing
    tbytes[116]=(result[3])
    tbytes[117]=(result[2])
    #Expected Horizontal Velocity Error word 60
    tbytes[118]=(10) # is 0.1 m/s
    tbytes[119]=(0)
    #reserved word 61-62
    tbytes[120]=(0)
    tbytes[121]=(0)
    tbytes[122]=(1)  # komt uit sniffing de data
    tbytes[123]=(0)
    #Receiver engine status word 63
    #nr of satellites used in b4,b5,b6
    count=0
    l=GSA['PRN']
    for i in range(len(l)):
           if l[i] != '':count+=1
    b4=0
    b5=0
    b6=0
    if count>5:count=5
    if count>=4:
        b6=1
        count-=4
    if count>=2:
        b5=1
        count-=2
    b4=count
    if RMC['Validity']=='A':
        b3=1
    else:
        b3=0
    result=int_to_spif(b4*2**4+b5*2**5+b6*2**6+b3*2**3+2**8+2**2)
    #print(result) 
    tbytes[124]=(result[3])
    tbytes[125]=(result[2])
   
    #Data checksum word 64

    result=int_to_spif(rockweldatachecksum(tbytes))
    tbytes[126]=(result[3])
    tbytes[127]=(result[2])

def checksum(s):
#input condition: s is NMEA0183 string with first character is "$", string >= 2 characters
#output: input string + checksum    
    if (len(s)<3): return("")
    cs=ord(s[1])
    for i in range(2,len(s)):
        cs^=ord(s[i])
    csh=hex(cs).lstrip("0x").upper()
    if (len(csh)==0): csh="00"
    if (len(csh)==1): csh="0"+csh
    return(s+"*"+csh)

def checkchecksum(s):
# s is a NMEA string including checksum
    p=s.find('*')
    if s==checksum(s[0:s.find('*')]):
        return(True)
    else:
        return(False)
    



def utctoweekseconds(utc,leapseconds):
    """ Returns the GPS week, the GPS day, and the seconds 
        and microseconds since the beginning of the GPS week """
    import datetime, calendar
    datetimeformat = "%Y-%m-%d %H:%M:%S"
    epoch = datetime.datetime.strptime("1980-01-06 00:00:00",datetimeformat)
    tdiff = utc -epoch  + datetime.timedelta(seconds=leapseconds)
    gpsweek = tdiff.days // 7 
    gpsdays = tdiff.days - 7*gpsweek         
    gpsseconds = tdiff.seconds + 86400* (tdiff.days -7*gpsweek) 
    return gpsweek,gpsdays,gpsseconds,tdiff.microseconds

def minutestodegrees(s):
    # converts nmea lat and lon string to numerical degree term with base 100
    # instead of base 60
    # e.g 5231.1575 becomes 52+31.1575/60
    try:
        n=modf(float(s)/100)
    except:
        return(0)
    return(n[1]+100*n[0]/60)

def dictprint(d,maxkeylength):
    if maxkeylength==0:
        for i in d: maxkeylength=max(maxkeylength,len(i))
    for i in d: print(i.ljust(maxkeylength),'=',d[i])

def floatsafe(s):
    try:
        return(float(s))
    except:
        return(0)

def traceprint(s):
    if printdebug: print(s)

