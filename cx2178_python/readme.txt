What's in the folder:
1.Sender program--sender2.py
2.Receiver program--receiver2.py
3.readme.txt

Develop environment:
Server.py and Client.py are developed in python 2.7.2.


Invoke the program:
sender program should be run first,invoked as follow:
	python PATH/sender2.py  PATH/filename.txt   10.211.55.2    41192      20000       PATH/logfile.txt     10
		               file intend to send   remote ip   remote port  ack_port       logfile path   window size

	remote ip and remote port could be the address of proxy or the receiver

receiver program should be run first,invoked as follow:
	python PATH/receiver2.py    PATH/file.txt          50007              localhost     20000              PATH/logr.txT
				  file to write data  receiver listening port  senderip  sender ack_port       logfile path  

	senderip and sender ack_port are used to establish TCP connection,senderip is set to be localhost in sender2.py, if you change it in sender2.py, the senderip in this command should be changed accordingly



a) TCP segment structure:
	Each segment includes data and a 20-byte header in the front. The MSS is set to 576, so except the last segment, the segment size is 596.
	|------------------32bits------------------|
	| 8bits source port |8bits destination port|
	|        32 bits sequence number           |
	|     32 bits acknowlegement number        |
	| 00000000000A000F  |16bits receive window |
	|             32bits checksum              |
	|------------------------------------------|
	|                                          |
	|                  data                    |
        ____________________________________________
	
	As it's an one-way transmission, so the acknowlege number in data segment sent by sender is always 0 and ACK bit in flag is set to 0. When it comes to the last segment, FIN bit in flag is set to 1, otherwise it's 0. So the last packet's flag is 1, others are 0. Checksum uses CRC.
	The flag of ack sent back by receiver is 16, means 0b0000000000010000, ACK bit is set to 1.


b)the states typically visited by sender and receiver:
	sender: (1)divides data into segments,start to send data according to window size, if no timer is running currently, start timer. (2)wait for ack,if the ack is correct, move send base to send next packet, stop timer. if the ack is wrong, wait for a new ack or timeout. (3)timeout, retranssmit, start timer
	receiver:(1)wait for packet, unpack. (2)computer checksum to check if it's not corrupt, if so, check sequence number, else discard. (3)if the sequence number is right, send ack with sequence number of next expecting packet, if wrong(duplicate packet or out of orde packet), discard and still send the old ack.


c)loss recovery:
	out of order packet: the receiver discards out-of-order packets and sent ack with sequence number of expecting in-orde packet. For example, the sender sends packet in the order:2,4,1,4,2, the receiver will discard the first two packets 2 and 4, and ack 1. After it receives 1, it will ack 2 and discard other packets until 2 comes.
	
	packet loss: the sender waits for timeout to resend the lost packet.

	packet corrupt: the sender computes a checksum based on the whole segment, then puts the checksum in header and sends the segment. After the receiver receives the segment, it first unpacks the segment to takes out checksum in header, then it computes a checksum dased on rest of the segment, finally it compares these two checksums. If they are same, the segment is correct, the receiver send ack of next expecting segment, if they are different, the segment is corrupt, the receiver discards the segment and asks for retransmission.
	
	packet delay: if delay time is smaller than timeoutinterval, then the receiver can always receives segments correctly, if delay time is bigger, the scenario will be treated the same as packet loss.

	duplicate packets: the receiver discards duplicate segments.

	Timeoutinterval: recompute each time when a correct ack arrives at the sender to make the transmission process more effcient.

d)logfiles contains information of data both send and receive. For sender are packets sent and ack received, for receiver are packets received and ack sent. acks sent by receiver are numbers.

When receiver receives a correct packet, it check its flag to see if it's the last packet. If the flag is 1, transmission ends, the receiver closes socket after sends ack.
On the other side, when sender receives an ack number biger than file size, it knows receivers has receives all data, it closes sockets.


