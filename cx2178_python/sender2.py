import socket
import time
import datetime
import threading
import sys
import struct
import binascii

senderport=8080
senderip='localhost'

filename=sys.argv[1]
remote_ip=sys.argv[2]
remote_port=int(sys.argv[3])
ack_port_num=int(sys.argv[4])
log_filename=sys.argv[5]
window_size=int(sys.argv[6])


mss_content=576
sequencenum=0
acknowlegenum=0
flags=0
acknum=0


packetset=list()
seqnumlist=list()
nextseqlist=list()
send_log=list()
flaglist=list()
acklist=[0]

#create UDP socket
s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

#create TCP socket
sack = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sack.bind((senderip,ack_port_num))
sack.listen(1)

# open file that intend to transmit
try:
    f=open(filename,'rb')
    f.seek(0,2)
    end=f.tell()
    #print end
except IOError:
    print 'file not found'


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


#divide file into small packets
def makepacket(byte):

    seqnum=0

    f.seek(0,0)
    while (seqnum+byte)<=(end-byte):

        seqnum=f.tell()
        nextseq=seqnum+byte
        flags=0b000000000000000
        flaglist.append(flags)
        a=f.read(byte)

        data=(senderport,remote_port,seqnum,acknowlegenum,flags,window_size,0,a)
        ss = struct.Struct('2H 2i 2H i'+str(mss_content)+'s')
        packed=ss.pack(*data)


        checksum=calchecksum(packed)
        #print checksum

        d=(senderport,remote_port,seqnum,acknowlegenum,flags,window_size,checksum,a)
        ss = struct.Struct('2H 2i 2H i'+str(mss_content)+'s')
        packed_data=ss.pack(*d)

        packetset.append(packed_data)
        seqnumlist.append(seqnum)
        nextseqlist.append(nextseq)

    if (seqnum+byte)>(end-byte):
        seqnum=f.tell()
        nextseq=end
        flags=0b0000000000000001
        flaglist.append(flags)
        a=f.read(byte)
        data=(senderport,remote_port,seqnum,acknowlegenum,flags,window_size,0,a)
        ss = struct.Struct('2H 2i 2H i'+str(len(a))+'s')
        packed_data=ss.pack(*data)

        checksum=0
        checksum=calchecksum(packed_data)
        #print checksum

        data=(senderport,remote_port,seqnum,acknowlegenum,flags,window_size,checksum,a)
        ss = struct.Struct('2H 2i 2H i'+str(len(a))+'s')
        packed_data=ss.pack(*data)


        packetset.append(packed_data)
        seqnumlist.append(seqnum)
        nextseqlist.append(nextseq)

    return packetset


#maintain sender logfile
def writelog_send(loglist):
    try:
        if log_filename=='stdout':
            pass

        else:

            logf=open(log_filename,'w')
            logf.writelines(loglist)
            logf.close
            #print 'logfile has been writen successfully'

    except IOError:
        print 'unable to create file'








#thread that receives ack from receiver
def recvackFunc(conn):
    while 1:
        try:
            ack=conn.recv(20)
            ackt=time.ctime()
            ack=ack.split()
            ack=ack[0]
            ack=int(ack)
            # ss = struct.Struct('i')
            # ack=ss.pack(ack)[0]
            acklist[0]=ack
            #print 'RECVack:',ack
            if ack:
                acklog='sendtime:'+str(ackt)+'   sourceport:'+str(remote_port)+'  destinationport:'+str(senderport)+'  seqnum:'+str(0)+'  acknum:'+str(ack)+'  flag:'+str(16)+'   estRTT:'+str(estrtt)+'\n'
                send_log.append(acklog)
        except IndexError:

            break




#calculate timeout interval and estimated RTT
def recaltimeout(samrtt,estrtt,devrtt):
    est=0.875*estrtt+0.125*samrtt
    dev=0.75*devrtt+0.25*abs(samrtt-est)
    newtimeout=est+4*dev
    return est,newtimeout

#main thread
while 1:
    ackconn,addr=sack.accept()
    #print 'connect by ',addr
    global timeout,st,at,timeoutstart,timeoutend
    timeout=0
    data='1'
    i=0
    global sendbase
    sendbase=0
    global timeoutinterval
    timeoutinterval=1
    #global samplertt
    samplertt=1
    #global estrtt
    estrtt=1
    #global devrtt
    devrtt=1
    sendflag=1
    retransnum=0
    totalsegsnum=0
    totalbytesnum=0

#divide file into packets
    pdataset=makepacket(mss_content)
#start the thread that receives ack
    tr=threading.Thread(target=recvackFunc,args=(ackconn,))
    tr.setDaemon(True)
    tr.start()
    #ack=recvackFunc(ackconn)


    #while (data):

    while i<(window_size+(sendbase/mss_content)) and i<len(pdataset):
        #send packet and get sending time
        if sendflag==1:
            s.sendto(pdataset[i],(remote_ip,remote_port))
            totalbytesnum+=len(pdataset[i])
            st=time.ctime()

            sendlog='sendtime:'+str(st)+'   sourceport:'+str(senderport)+'  remoteport:'+str(remote_port)+'  seqnum:'+str(seqnumlist[i])+'  acknum:'+str(acknowlegenum)+'  flag:'+str(flaglist[i])+'   estRTT:'+str(estrtt)+'\n'
            send_log.append(sendlog)
            #writelog_send(send_log)
            totalsegsnum+=1


        #get ack and get ack time
        ack=acklist[0]
        at=time.ctime()

        #the ack is new and correct
        if ack>sendbase and ack<=end:
            sendflag=1

            samplertt=(datetime.datetime.strptime(at, "%a %b %d %H:%M:%S %Y")-datetime.datetime.strptime(st, "%a %b %d %H:%M:%S %Y")).seconds
            estrtt,timeoutinterval=recaltimeout(samplertt,estrtt,devrtt)

            #move base
            sendbase=ack
            #print 'move base to:',sendbase
            i=i+1


        #all packets has sent and received by receriver
        elif ack>end:
            sendbase=end
            #acklog='sendtime:'+str(at)+'   sourceport:'+str(remote_port)+'  destinationport:'+str(senderport)+'  seqnum:'+str(0)+'  acknum:'+str(ack)+'  flag:'+str(16)+'   estRTT:'+str(estrtt)+'\n'
            #send_log.append(acklog)
            #print 'move base to:',sendbase
            #print 'finish'
            i=i+1

        #duplicate ack (wrong ack)
        elif ack<=sendbase:

            #stop to send, until a correct ack is received or timeout
            sendflag=0
            if (datetime.datetime.strptime(at, "%a %b %d %H:%M:%S %Y")-datetime.datetime.strptime(st, "%a %b %d %H:%M:%S %Y")).seconds<(datetime.timedelta(0,timeoutinterval)).seconds:
                pass
            else:
                sendflag=1
                retransnum+=1

                #s.sendto(pdataset[ack/mss_content],(remote_ip,remote_port))

        #i=i+1
    #write logfile
    writelog_send(send_log)
    if log_filename=='stdout':
        print "".join(list(send_log))

    #print statistics
    print 'Delivery completed successfully'
    print 'Total bytes sent = ',totalbytesnum
    print 'Segments sent = ',totalsegsnum
    print 'Segments retransmitted = ',retransnum


    break
sack.close()
s.close()













