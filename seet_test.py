###Notes
# Want to track current schedule event  (row) and next schedule event (row)

# How do I print alarm values?? Will try to ask someone else

# Initial connection to the IDB and ODB taken directly from Daniel's Thermal Cycling code

# Need to define IDB and OBD classes when I get the chance

from socket import timeout
from urllib.parse import _NetlocResultMixinBase
import serial, time, csv
from math import floor
import numpy as np
from csv import writer 



# Global variables:

## COM Ports:
idb1_port = "COM49"
idb2_port = "COM52"
odb1_port = "COM38"
odb2_port = "COM50"
pwr_supply_port = "COM45"


#idb1_port = input("Enter COM port of the first unit's IDB (COMX): ")
#idb2_port = input("Enter COM port of the second unit's IDB (COMX): ")
#odb1_port = input("Enter COM port of the first unit's ODB (COMX): ")
#odb2_port = input("Enter COM port of the second unit's ODB (COMX): ")
#pwr_supply_port = input("Enter COM port of the power supply (COMX): ")


SEET_Test_Name1 = input("Enter Date and Name of first UUT (YYYYMMDD_UUTID): ")
SEET_Test_Name2 = input("Enter Date and Name of second UUT (YYYYMMDD_UUTID): ")
Masterspreadsheet_name = "Debug_SEET_Testing_Master_Spreadsheet.csv"


##Connect to IDBs
idb1 = serial.Serial(idb1_port,115200,rtscts = False,timeout=2,write_timeout=5) ##Enter Appropriate IDB ports
idb1.open()
idb2 = serial.Serial(idb2_port,115200,rtscts = False,timeout=2,write_timeout=5) ##Enter Appropriate IDB ports
idb2.open()


##Connect to ODBs
odb1 = serial.Serial()
odb1.setRTS(0)
odb1.setDTR(0)
odb1.port=odb1_port
odb1.baudrate = 115200
odb1.timeout = 5 
odb1.open()

odb2 = serial.Serial()
odb2.setRTS(0)
odb2.setDTR(0)
odb2.port=odb2_port
odb2.baudrate = 115200
odb2.timeout = 5 
odb2.open()

##Connect to Power Supply
PWSP = serial.Serial(pwr_supply_port,19200,8,"N",1)
PWSP.open()

def PortIDtoName(port_id):
    if port_id == "idb1":
        com_port = idb1_port
        return com_port
    
    elif port_id == "idb2":
        com_port = idb2_port
        return com_port
    
    elif port_id == "odb1":
        com_port = odb1_port
        return com_port
    
    if port_id == "odb2":
        com_port = odb2_port
        return com_port


def checkODBConnections(odb_id):
    print("Check odb connection on port: ",PortIDtoName(odb_id))
    while odb_id.isOpen() == False:
        print(f"COM port was closed, trying to reconnect to port: {PortIDtoName(odb_id)}")
        odb_id = serial.Serial()
        odb_id.setRTS(0)
        odb_id.setDTR(0)
        odb_id.port=PortIDtoName(odb_id)
        odb_id.baudrate = 115200
        odb_id.timeout = 5 
        odb_id.open()
        #time.sleep(1)
    odb_id.close()
    time.sleep(1)
    odb_id.open()
    return odb_id

def checkIDBConnections(idb_id):
    print("Check idb connection: ",PortIDtoName(idb_id))
    while idb_id.isOpen() == False:
        print(f"Trying to connect to port: {PortIDtoName(idb_id)}")
        idb_id = serial.Serial()
        idb_id.setRTS(0)
        idb_id.setDTR(0)
        idb_id.port=PortIDtoName(idb_id)
        idb_id.baudrate = 115200
        idb_id.timeout = 5 
        idb_id.open()
    idb_id.close()
    time.sleep(1)
    idb_id.open()
    return idb_id


def idbreset(idb_id):
    idb_id.close()
    idb_id.open()
    print("IDB closed and reopened!")
    time.sleep(3)
    idb_id.reset_input_buffer()
    print("IDB input buffer cleared!")
    idb_write(idb_id,"send_event_to_app_sm 2\r\n")
    time.sleep(5)
    print("Open fuse command sent!")



def odbreset(odb_id,current_odb_command):
    odb_id.close()
    time.sleep(2)
    odb_id.open()
    print(f"Resetting ODB: {odb_id}")
    odb_write(odb_id,current_odb_command)


def initODB(idb_id,odb_id): #Executed at the bening of the test to make sure startup is consistent
    attempts = 0
    odb_id.close()
    time.sleep(3)
    idb_write(idb_id,"send_event_to_app_sm 2\r\n") # One of the units requires that you send this immediately before opening obd port
    odb_id.open()
    odb_line = ''
    while "State loop starting" not in odb_line and attempts<=20: ##20 attempts have worked well so far
        print(attempts)
        print("Waiting for state loop starting!")
        try:
            odb_line = odb_readline(odb_id)

        except UnicodeDecodeError as err:
            odb_line = err
        attempts+=1
        


def odb_write(odb_id, command : str):
    print("Sending command to ODB '"+command+"'")
    try:
        byteswritten = 0
        bytestowrite = len(command)
        while byteswritten < bytestowrite:
            if odb_id.out_waiting == 0:
                odb_id.write(command[byteswritten].encode())
                byteswritten +=1
        odb_id.write(("\n").encode())
    
    except Exception as e:
        print("ODB write connection: ",e)
        checkODBConnections(odb_id)
    


def odb_readline(odb_id):
    odb_line = ''
    while odb_line == '':
        try:
            if odb_id.in_waiting>0:
                odb_line = odb_id.readline().decode('utf-8')
        except Exception as e:
            print("ODB read error",e)
            checkODBConnections(odb_id)
        time.sleep(0.5)
    return odb_line

def idb_write(idb_id,command:str):
    print("Sending command to IDB '"+command+"'")
    try:
        idb_id.flushOutput()
        idb_id.flushInput()
        idb_id.reset_input_buffer()
        if idb_id.out_waiting == 0:
            idb_id.write((command).encode())
    except Exception as e:
        print("IDB write error: ",e)
        checkIDBConnections(idb_id)


def idb_read(idb_id):
    idb_id.flushOutput()
    idb_id.flushInput()
    idb_id.reset_input_buffer
    counter = 0
    idb_line = ""
    while idb_line == "" and counter<10:    
        try:
            if idb_id.in_waiting == 0:
                idb_line = idb_id.readline().decode()
                counter+=1
                print(counter)

        except Exception as e:
            print("IDB read error: ",e)
            checkIDBConnections(idb_id)
        time.sleep(0.5)
    print("done with IDB read loop")
    return idb_line
    


class PWRSupply():
    def connect_PWRSupply():
        PWSP.open()       
        
    def disconnect_PWRSupply():
        PWSP.close()

    
    def PWR_Supply_write(command : str):
        print("Sending command to PWR Supply '"+command+"'")             
        PWSP.write((f"{command}\r\n").encode())
        return

    def PWRSupplyOn():
        PWRSupply.PWR_Supply_write("OUTP on")
    
    def PWRSupplyOff():
        PWRSupply.PWR_Supply_write("OUTP off")
    
    def PWRSupplySetACV(voltage:float):
        PWRSupply.PWR_Supply_write(f"SOUR:VOLT:AC {voltage}")

    def PWRSupplyreset(current_volt:float):
        print("resetting power supply")
        PWRSupply.PWRSupplyOff()
        time.sleep(10)
        PWRSupply.PWRSupplyOn()
        PWRSupply.PWRSupplySetACV(current_volt)
    
    def PWRSupplyrapidrest(current_volt):
        print("Rapid Reset Power Supply")
        PWRSupply.PWRSupplyOff()
        time.sleep(5)
        PWRSupply.PWRSupplyOn()
        PWRSupply.PWRSupplySetACV(current_volt)
    
    def PWRSupplyReadVAC():
        pass
        

def resetUnits(current_idb_command,current_odb_command,current_pwr_volt):
    print("Starting units reset sequence")
    #Power reset
    PWRSupply.PWRSupplyreset(current_pwr_volt)
    initODB(idb1,odb1)
    print("First unint has been reset!")
    initODB(idb2,odb2)
    print("Second unit has been reset!")

    odbreset(odb1,current_odb_command)
    odbreset(odb2,current_odb_command)


    print("ODBs have been reset!")
    print("Test reset sequence executed!")




## Read and excecute commands from Masterspreadsheet:
with open(fr"C:\Users\order\Downloads\{Masterspreadsheet_name}",newline='') as file:
    reader = csv.reader(file,delimiter=',')
    schedulefile = list(zip(*reader))[0::]

total_columns,total_rows = np.shape(schedulefile)

## Data file
datetimestr = time.strftime("%Y-%m-%d_%H%M%S")

datafile1 = open(fr"C:\Users\order\Downloads\{SEET_Test_Name1}"+".csv",'w')
datafile2 = open(fr"C:\Users\order\Downloads\{SEET_Test_Name2}"+".csv",'w')


current_row = 0
next_row = 1

## Value reads from the masterspreadsheet:
test_number = (schedulefile[1])
test_number = list(map(float,test_number))
step_number = (schedulefile[3])
step_number = list(map(float,step_number))
time_duration = (schedulefile[9])
time_duration = list(map(float,time_duration))
odb_command = schedulefile[11]
idb_command = schedulefile[13]
UUT_mode = schedulefile[15]
pwr_supply_volts_setting = (schedulefile[17])
pwr_supply_volts_setting = list(map(float,pwr_supply_volts_setting))
chatter = schedulefile [19] 



## Actions to run before everything else
current_row = 0

curr_time = time_duration[current_row]
curr_test_number = test_number[current_row]
curr_step_number = step_number[current_row]
curr_time_duration = time_duration[current_row]
curr_odb_command = odb_command[current_row]
curr_idb_command = idb_command[current_row]
curr_pwr_v = pwr_supply_volts_setting[current_row]



resetUnits(f"{curr_idb_command}\r\n",curr_odb_command,curr_pwr_v)

while(current_row<=total_rows):
    try:
        print("In schedule loop!")
        #idb_write(idb1,"set_log_level -t * -l 0\r\n")
        #idb_write(idb2,"set_log_level -t * -l 0\r\n")
        curr_time = time_duration[current_row]
        curr_pwr_v = pwr_supply_volts_setting[current_row]
        next_time = time_duration[current_row+1]
        step_dur = next_time - curr_time
        PWRSupply.PWRSupplySetACV(curr_pwr_v)
        time.sleep(0.5)
        odb_write(odb1,(odb_command[current_row]))
        idb_write(idb1,f"{idb_command[current_row]}\r\n")
        #time.sleep(0.5)
        odb_write(odb2,(odb_command[current_row]))
        idb_write(idb2,f"{idb_command[current_row]}\r\n")
        print("Step Number: ",step_number[current_row])
        time_start = time.time()
        time_end = time_start+step_dur

        if curr_pwr_v != 0:
            while time_start<=time_end:
                print("In timing loop!")
                idb_write(idb1,f"{idb_command[current_row]}\r\n")
                idb_write(idb2,f"{idb_command[current_row]}\r\n")
                data1 = odb_readline(odb1)
                data2 = odb_readline(odb2)
                datetime = time.strftime("%Y-%m-%d_%H-%M-%S")
                time_stamp = str(time.time())
                step_str = str(curr_step_number)
                data1=[time_stamp]+[data1]+[step_str]
                data2=[time_stamp]+[data2]+[step_str]

                datafile1.write(datetime+data1)
                datafile2.write(datetime+data2)

                print("ODB1 Line: ",data1)
                print("ODB2 Line: ",data2)
                time_start = time.time()
                time_left = time_end-time_start
                print(f"Unit modes are: {UUT_mode[current_row]}")
                print(f"Running step {step_number[current_row]} and test {test_number[current_row]} of the SEET")
                print("Time left running this step in seconds is: ",time_left)
                time.sleep(0.5)
        
        elif curr_pwr_v == 0:
            while time_start<=time_end:
                time_start = time.time()
                time_left = time_end-time_start
                print("In power off cycle")
                print(f"Unit modes are: {UUT_mode[current_row]}")
                print(f"Running step {step_number[current_row]} and test {test_number[current_row]} of the SEET")
                print("Time left running this step in seconds is: ",time_left)
                time.sleep(0.5)
                pass
        
        
        current_row+=1
        print("Current row: ",current_row)
        pass

    except Exception as e:
        print("Error in schedule loop is: ",e)

datafile1.close()
datafile2.close()