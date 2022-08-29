from socket import timeout
from urllib.parse import _NetlocResultMixinBase
import serial, time, csv
from math import floor
import numpy as np
from csv import writer 


idb1_port = input("Enter COM port of the first unit's IDB (COMX): ")
odb1_port = input("Enter COM port of the first unit's ODB (COMX): ")


onoffcycle_test_name1 = input("Enter Date and Name of first UUT (YYYYMMDD_UUTID): ")
datafile1 = open(fr"C:\Users\batau\Downloads\{onoffcycle_test_name1}"+".csv",'w')


##Connect to IDBs
idb1 = serial.Serial(idb1_port,115200,rtscts = False,timeout=2,write_timeout=5) ##Enter Appropriate IDB ports
#idb1.open()



##Connect to ODBs
odb1 = serial.Serial()
odb1.setRTS(0)
odb1.setDTR(0)
odb1.port=odb1_port
odb1.baudrate = 115200
odb1.timeout = 5 
odb1.open()


Numonoffcycles = int(input("Enter number of component cycles the units have to undergo: "))
Numvalvecycles = int(input("Enter number reversing valve cycles the units have to undergo: "))

class helperFunctions():
    def odb_numericalreads():
        odb_line = odb_readline(odb1)
        while odb_line.split(',')[0].isnumeric() == False:
            try:
                odb_line = odb_readline(odb1)   
            except Exception as e:
                print("Error parsing out only numerical ODB reads", e)
        odb_line = odb_line.split(',')
        return odb_line
        def PortIDtoName(port_id):
            if port_id == "idb1":
                com_port = idb1_port
                return com_port
    
            elif port_id == "odb1":
                com_port = odb1_port
                return com_port
    


def checkODBConnections(odb_id):
    print("Check odb connection on port: ",helperFunctions.PortIDtoName(odb_id))
    while odb_id.isOpen() == False:
        print(f"COM port was closed, trying to reconnect to port: {helperFunctions.PortIDtoName(odb_id)}")
        odb_id = serial.Serial()
        odb_id.setRTS(0)
        odb_id.setDTR(0)
        odb_id.port=helperFunctions.PortIDtoName(odb_id)
        odb_id.baudrate = 115200
        odb_id.timeout = 5 
        odb_id.open()
    return odb_id

def checkIDBConnections(idb_id):
    print("Check idb connection: ",helperFunctions.PortIDtoName(idb_id))
    while idb_id.isOpen() == False:
        print(f"Trying to connect to port: {helperFunctions.PortIDtoName(idb_id)}")
        idb_id = serial.Serial()
        idb_id.setRTS(0)
        idb_id.setDTR(0)
        idb_id.port=helperFunctions.PortIDtoName(idb_id)
        idb_id.baudrate = 115200
        idb_id.timeout = 5 
        idb_id.open()
    return idb_id


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
    attempts = 0
    while odb_line == '' and attempts<=3:
        try:
            if odb_id.in_waiting>0:
                odb_line = odb_id.readline().decode('utf-8')
        except Exception as e:
            print("ODB read error",e)
            checkODBConnections(odb_id)
        attempts+=1
        time.sleep(0.5)
    return odb_line

def idb_write(idb_id,command:str):
    print("Sending command to IDB '"+command+"'")
    try:
        idb_id.flushOutput()
        idb_id.flushInput()
        if idb_id.out_waiting == 0:
            idb_id.write((command).encode())
    except Exception as e:
        print("IDB write error: ",e)
        checkIDBConnections(idb_id)


def idb_read(idb_id):
    idb_id.flushOutput()
    idb_id.flushInput()
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


def idbreset(idb_id):
    idb_id.close()
    idb_id.open()
    print("IDB closed and reopened!")
    time.sleep(3)
    idb_id.reset_input_buffer()
    print("IDB input buffer has been cleared")
    time.sleep(2)
    idb_id.reset_outout_buffer()
    print("IDB output buffer has been cleared")
    idb_write(idb_id,"send_event_to_app_sm 2\r\n")
    time.sleep(5)
    print("Open fuse command sent!")


def odbreset(odb_id,current_odb_command):
    odb_id.close()
    time.sleep(2)
    odb_id.open()
    print(f"Resetting ODB: {odb_id}")
    odb_write(odb_id,current_odb_command)



def initUnits(idb_id,odb_id): #Executed at the bening of the test to make sure startup is consistent
    attempts = 0
    odb_id.close()
    time.sleep(3)
    idb_write(idb_id,"send_event_to_app_sm 2\r\n") # One of the units requires that you send this immediately before opening obd port
    odb_id.open()
    odb_line = ''
    while "State loop starting" not in odb_line and attempts<=5: ##20 attempts have worked well so far
        print(attempts)
        print("Waiting for state loop starting!")
        try:
            odb_line = odb_readline(odb_id)

        except Exception as err:
            odb_line = err
        attempts+=1


def settoheating(odb_id):
    try:
        odb_write(odb_id,"mock-alarm-input FLOW 1") ## Disable flow alarms
        odb_write(odb_id,"cert 3")
        time.sleep(5) #
        odb_line = helperFunctions.odb_numericalreads()
        print("ODB Line is: ",odb_line)
        print("Compressor RPM is: ",odb_line[12])
        compr_RPM = float(odb_line[12])
        
        print("Compressor RPM is: ",compr_RPM)
        while(compr_RPM<compr_RPM_threshold and compr_RPM<10000):
            compr_RPM = float(helperFunctions.odb_numericalreads()[12])
            print(f"Compressor ramping up to {compr_RPM_threshold}, current RPM is: ", compr_RPM)
        print("Unit in heating mode")
    
    except Exception as e:
        print("Error in set to heating function ",e)
    


def settocooling(odb_id):
    try:
        odb_write(odb_id,"mock-alarm-input FLOW 1") ## Disable flow alarms
        odb_write(odb_id,"cert -3")
        odb_line = helperFunctions.odb_numericalreads()
        print("ODB Line is: ",odb_line)
        print("Compressor RPM is: ",odb_line[12])
        compr_RPM = float(odb_line[12])
        print("Compressor RPM is: ",compr_RPM)

        while(compr_RPM<compr_RPM_threshold):
            compr_RPM = float(helperFunctions.odb_numericalreads()[12])
            print(f"Compressor ramping up to {compr_RPM_threshold}, current RPM is: ", compr_RPM)
        print("Unit in cooling mode")
    
    except Exception as e:
        print("Error in set to cooling function ",e)

def settooff(odb_id):
    try:
        odb_write(odb_id,"mock-alarm-input FLOW 1") ##Disable flow alarms
        odb_write(odb_id,"cert 0")
        P1 = float(helperFunctions.odb_numericalreads()[0])
        P2 = float(helperFunctions.odb_numericalreads()[1])
        deltaP = np.abs(P1-P2)
        while(deltaP>offdeltaP):
            P1 = float(helperFunctions.odb_numericalreads()[0])/100
            P2 = float(helperFunctions.odb_numericalreads()[1])/100
            deltaP = np.abs(P1-P2)
            
            print(f"Difference of discharge and suction pressures needs to be {offdeltaP}, currently at: ", deltaP)
        print("Unit in off state")
    except Exception as e:
        print("Error in set off function ",e)

        
state_duration = float(input("How many seconds do you want the unit to settle in each state? (Half cycle duration): ")) ## This is how long you want unit to run in a specific mode (Variable)
compr_RPM_threshold = 2500 ## This is variable
currentvalve_cycle = 1
offdeltaP = 200

initUnits(idb1,odb1)
while(currentvalve_cycle<=Numvalvecycles+1):
    print("In cycling loop now")
    try:
        print("Running reversing cycle: ",currentvalve_cycle)
        completed_onoffcycles_heating = 0
        completed_onoffcycles_cooling = 0

        ##heating cycles
        while(completed_onoffcycles_heating<Numonoffcycles):
            try:
                settoheating(odb1)
                time_start = time.time()
                time_end = time_start+state_duration
                while(time_start<=time_end):
                    datetime = time.strftime("%Y-%m-%d %H:%M:%S")
                    data1 = odb_readline(odb1)
                    datafile1.write(f"valve_cycle:{str(currentvalve_cycle)}"+",cert 3,"+datetime+","+data1)
                    time_start = time.time()
                    print(f"Unit running in heating mode for the next {time_end-time_start} seconds")
                    

                settooff(odb1)
                time_start = time.time()
                time_end = time_start+state_duration
                while(time_start<=time_end):
                    datetime = time.strftime("%Y-%m-%d %H:%M:%S")
                    data1 = odb_readline(odb1)
                    datafile1.write(f"valve_cycle:{str(currentvalve_cycle)}"+",cert 3,"+datetime+","+data1)
                    time_start = time.time()
                    print(f"Unit off for the next {time_end-time_start} seconds")
                
                settoheating(odb1)
                time_start = time.time()
                time_end = time_start+state_duration
                while(time_start<=time_end):
                    datetime = time.strftime("%Y-%m-%d %H:%M:%S")
                    data1 = odb_readline(odb1)
                    datafile1.write(f"valve_cycle:{str(currentvalve_cycle)}"+",cert 3,"+datetime+","+data1)
                    time_start = time.time()
                    print(f"Unit running in heating mode for the next {time_end-time_start} seconds")
                completed_onoffcycles_heating+=1
            except Exception as e:
                print(f"Error when going through heating cycles, unit has undergone {currentvalve_cycle} valve cycles",e)
    
        print(f"Just Completed {completed_onoffcycles_heating} on/off heating cycles")

        settooff(odb1)
        time_start = time.time()
        time_end = time_start+state_duration
        while(time_start<=time_end):
                datetime = time.strftime("%Y-%m-%d %H:%M:%S")
                data1 = odb_readline(odb1)
                datafile1.write(f"valve_cycle:{str(currentvalve_cycle)}"+",cert 3,"+datetime+","+data1)
                time_start = time.time()
                print(f"Unit turned off for the next {time_end-time_start} seconds")
        print("Now shifting to cooling cycles")

        ##cooling cycles
        while(completed_onoffcycles_cooling<Numonoffcycles):
            try:
                settocooling(odb1)
                time_start = time.time()
                time_end = time_start+state_duration
                while(time_start<=time_end):
                    datetime = time.strftime("%Y-%m-%d %H:%M:%S")
                    data1 = odb_readline(odb1)
                    datafile1.write(str(currentvalve_cycle)+",cert 3,"+datetime+","+data1)
                    time_start = time.time()
                    print(f"Unit running in cooling mode for the next {time_end-time_start} seconds")

                settooff(odb1)
                time_start = time.time()
                time_end = time_start+state_duration
                while(time_start<=time_end):
                    datetime = time.strftime("%Y-%m-%d_%H-%M-%S")
                    data1 = odb_readline(odb1)
                    datafile1.write(str(currentvalve_cycle)+",cert 3,"+datetime+","+data1)
                    time_start = time.time()
                    #print(f"Unit off for the next {time_end-time_start} seconds")
                
                settocooling(odb1)
                time_start = time.time()
                time_end = time_start+state_duration
                while(time_start<=time_end):
                    datetime = time.strftime("%Y-%m-%d %H:%M:%S")
                    data1 = odb_readline(odb1)
                    datafile1.write(str(currentvalve_cycle)+",cert 3,"+datetime+","+data1)
                    time_start = time.time()
                    #print(f"Unit running in cooling mode for the next {time_end-time_start} seconds")
                completed_onoffcycles_cooling+=1
            except Exception as e:
                print(f"Error when going cooling cycles, unit has undergone {currentvalve_cycle} valve cycles",e)

        print(f"{currentvalve_cycle} Valve cycles completed")

        ##Transitions cycle
        settooff(odb1)
        time_start = time.time()
        time_end = time_start+state_duration
        while(time_start<=time_end):
                datetime = time.strftime("%Y-%m-%d %H:%M:%S")
                data1 = odb_readline(odb1)
                datafile1.write(str(currentvalve_cycle)+",cert 3,"+datetime+","+data1)
                time_start = time.time()
                print(f"Unit turned off for the next {time_end-time_start} seconds")
        print("Now shifting to heating cycles")
        print(f"{currentvalve_cycle} Valve cycles completed")



        currentvalve_cycle+=1
        #runcert0
    except Exception as e:
        pass

odb_write(odb1,"cert 0")
datafile1.close()
print("Test Completed")