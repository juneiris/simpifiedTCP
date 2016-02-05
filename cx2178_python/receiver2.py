import socket
import time
import sys
import struct
import binascii

filename=sys.argv[1]
listening_port=int(sys.argv[2])
sender_ip=sys.argv[3]
sender_port=int(sys.argv[4])
log_filename=sys.argv[5]


receiverip='localhost'
receiverport=50007
mss_content=576

#create UDP socket for file transmission
s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind((receiverip,listening_port))
#create TCP connection for ack transmission
sack = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sack.connect((sender_ip,sender_port))

# unpack packets that received
def unpack(packet,packetlen):
    s = struct.Struct('2H 2i 2H i'+str(packetlen)+'s')
    unpack_data=s.unpack(packet)
    senderport=unpack_data[0]
    #print senderport
    remote_port=unpack_data[1]
    #print remote_port
    sequencenum=unpack_data[2]
    #print sequencenum
    acknum=unpack_data[3]
    acknowlegenum=sequencenum+mss_content
    flag=unpack_data[4]
    flags=0b0000000000010000+flag
    #print flags
    window_size=unpack_data[5]
    #print window_size
    checksum=unpack_data[6]
    #print checksum
    #data=unpack_data[8:]
    data=unpack_data[7:]
    #print data
    return senderport,remote_port,sequencenum,acknum,acknowlegenum,flag,window_size,checksum,data


#calculate checksum.if the python version doesn't support binascii.crc32(),just uncomment lines in the function to compute checksum
def calchecksum(packet):
    # csum=0
    # for i in range(0,len(packet),2):
    #     temp = (ord(packet[i]) << 8) + (ord(packet[i+1]))
    #     csum = csum+temp
    # csum = (csum>>16) + (csum&0xffff)
    # csum += (csum>>16)
    # csum = ~csum & 0xffff
    return binascii.crc32(packet)
    #return csum


#function that write logfile for receiver
def writelog_recv(loglist):
    try:
        if log_filename=='stdout':
            print "".join(list(recv_log))
        else:
            logf=open(log_filename,'w')
            logf.writelines(loglist)
            logf.close
        #print 'logfile has been writen successfully'

    except IOError:
        print 'unable to create file'


#open file to write
f = open(filename,'wb')
expectack=int(0)
data='1'
recv_log=list()

while(data):
    #recv packets
    pdata,addr=s.recvfrom(2048)
    timestamp=time.ctime()
    plen=len(pdata)
    #caledcheck=calchecksum(pdata)
    #print 'expect checksum:',caledcheck

    #compute checksum
    source,dest,seq,recvack,ack,fla,win,check,data=unpack(pdata,plen-20)
    #print source,dest,seq,ack,fla,win,check
    #print data
    data="".join(tuple(data))
    d=(source,dest,seq,recvack,fla,win,0,data)
    ss = struct.Struct('2H 2i 2H i'+str(plen-20)+'s')
    pd=ss.pack(*d)
    caledcheck=calchecksum(pd)
    #print 'expect checksum:',caledcheck

    recvlog='timestamp:'+str(timestamp)+'    sourceport:'+str(source)+'   destinationport:'+str(receiverport)+'   sequencenum:'+str(seq)+'   acknum:'+str(recvack)+'   flags:'+str(fla)+'\n'
    recv_log.append(recvlog)

    #if the packet is not corrupt
    if check==caledcheck:
        #if the packet is what the receiver is expecting, write into file
        if seq==expectack:
            expectack=ack
            #print 'expecting:',expectack
            sack.send(str(ack)+'   ')
            timestamp2=time.ctime()

            data="".join(tuple(data))

            f.write(data)
            f.flush()
            #all packets has received
            if fla==1:

                print 'Delivery completed successfully'
                sendlog='timestamp:'+str(timestamp2)+'   sourceport:'+str(receiverport)+'   destinationport:'+str(sender_port)+'   sequencenum:'+str(recvack)+'   acknum:'+str(ack)+'   flags:'+str(16)+'\n'
                recv_log.append(sendlog)
                break
    #if the packet is corrupt or in wrong order, discard,send the sender the expecting acknumber
        else:
            #print 'wrong order,expecting:',expectack
            exack=str(expectack)
            sack.send(exack+'   ')
            timestamp2=time.ctime()
    else:
        #print 'corrupt !Seq:',seq,'expecting:',expectack
        exack=str(expectack)
        sack.send(exack+'   ')
        timestamp2=time.ctime()


    sendlog='timestamp:'+str(timestamp2)+'   sourceport:'+str(receiverport)+'   destinationport:'+str(sender_port)+'   sequencenum:'+str(recvack)+'   acknum:'+str(expectack)+'   flags:'+str(16)+'\n'
    recv_log.append(sendlog)

writelog_recv(recv_log)
sack.close()
s.close()






