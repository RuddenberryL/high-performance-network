import socket
import sys,getopt
import commands
import math
from mpi4py import MPI
from logi import *
def resend():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("192.168.137.1", 3333))
    s.send('RESEND')
def bytes(integer):
    return divmod(integer, 0x100)
def FPGA_checksum(result):
    for ele in result:#FPGA algorithm
        high,low = hex(ele)
        logiWrite(0x000B,(bytes(high),bytes(low)))#flashing the lights
        logiWrite(0x0000,(bytes(high),bytes(low)))#add checksum
        return logiRead(0x0000,2)

def FPGA_errorcheck(result):
    for ele in result:#FPGA algorithm
        high,low = hex(ele)
        logiWrite(0x000B,(bytes(high),bytes(low)))#flashing the lights
        logiWrite(0x0011,(bytes(high),bytes(low)))#add checksum
        return logiRead(0x0011,2)

def socketlistener(host,sock):
    retData = [host]
    recvData = host

    while recvData != "TERMINATE":
        data, recvData = sock.recvfrom(1024)
        print "{} receives: {}".format(host,data)
        recvData = str(data)
        if(recvData != "TERMINATE"):
            retData.append(recvData)

    print "{} finished listening".format(str(host))
    return retData

def main(argv):
    #Initializing MPI environment
    comm = MPI.COMM_WORLD
    size = comm.Get_size()
    rank = comm.Get_rank()
    host = commands.getoutput("hostname")

    sock_start = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
    sock_recv = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    #A behavior
    if(rank == 0):
        print "{} starts listening".format(str(host))
        sock_start.bind(("192.168.137.101",5005))

        sock_recv.bind(("192.168.137.101",3333))

        while True:
            st = sock_start.recvfrom(1024)
            if str(st[0]) == "START":
                ret_A = socketlistener(host,sock_recv)
                comm.send({"content":ret_A},dest=2,tag=0)
    #B behavior
    elif(rank == 1):
        print "{} starts listening".format(str(host))
        sock_start.bind(("192.168.137.102",5005))
        sock_recv.bind(("192.168.137.102",3333))
        while True:
            st = sock_start.recvfrom(1024)
            if str(st[0]) == "START":
                ret_B = socketlistener(host,sock_recv)
                comm.send({"content":ret_B},dest=2,tag=0)
    #Master behavior
    elif(rank == 2):
        print "{} starts listening".format(str(host))
        sock_start.bind(("192.168.137.103",5005))

        while True:
            st = sock_start.recvfrom(1024)
            if str(st[0]) == "START":
                data_A = comm.recv(source=0,tag=0)
                data_B = comm.recv(source=1,tag=0)
                a = data_A["content"][1:]
                b = data_B["content"][1:]
                # result = a + list(set(b) - set(a))
                # print "Length of merged list:",len(result)
                for ele in a:#FPGA algorithm
                    checksumA = FPGA_checksum(ele)
                    if not checksumA:
                        a.remove(ele)
                for ele in b:
                    checksumB = FPGA_checksum(ele)
                    if not checksumB:
                        b.remove(ele)
                result =  a + list(set(b) - set(a))
                for ele in result:
                    errorcheck = FPGA_errorcheck(ele)
                if not errorcheck:
                    resend();

if __name__ == "__main__":
    main(sys.argv[1:])