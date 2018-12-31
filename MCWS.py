import socket
import sys
import os.path
import datetime
import select

def parseRequest(req):
	reqHeaders = {}
	reqLine = ''
	lineNum = 0

	for line in req.splitlines():
		if line == '':
			break
		elif lineNum == 0:
			reqLine = line
			lineNum = 1
		else:
			splitLine = line.split(' ', 1)
			reqHeaders[splitLine[0]] = splitLine[1]

	splitReqLine = reqLine.split(' ')
	method = splitReqLine[0]
	path = splitReqLine[1]
	version = splitReqLine[2]
	# print 'method: ', method
	# print 'path: ', path
	# print 'version: ', version

	return method, path, version, reqHeaders
	

###main program###

HOST = ''
PORT = int(sys.argv[1])
server = sys.argv[0] 
TIMEOUT = None 

acceptSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
acceptSock.bind((HOST, PORT))
acceptSock.listen(5) # backlog is currently 5, can change

openConns = []
writeList = [] 

socketQ = []
packetQ = []


#moved out of loop, we don't want to add this multiple times
#acceptSock.setblocking(0)
openConns.append(acceptSock) 


while 1:
        # print "top of main loop"
	#readList = openConns #openConns is redundant with readList

	# Call select on read list (https://pymotw.com/2/select/ -- given in project instructions):

	rlist, wlist, xlist = select.select(openConns, openConns, openConns, TIMEOUT)
        # print rlist, '\n', wlist, '\n', xlist
        # print "rlist is ", len(rlist), " readable connections long"
        # print "wlist is ", len(wlist), " writable connections long"
        
	for sock in rlist:
                if sock in xlist: 
                    # print "found a socket in xlist"
                    openConns.remove(sock)
                    sock.close()
                    continue

		if sock == acceptSock:
                        # print "the accept socket"
                        #then add the new connection to openConns
			connSock, addr = acceptSock.accept()
			connSock.setblocking(0)
                        openConns.append(connSock)
		else: # Perform steps 4.b through 4.f from part 2
                        # print "an active connection"
			data = sock.recv(1024) # TODO: Check what this buffer size should be
			if not data:
                                # print "recv sent no data!"
                                openConns.remove(sock)
                                #sock.close()
                                continue
			# print data
			reqMethod, reqPath, reqVersion, reqHeads = parseRequest(data)

			filePath = reqPath[1:] # Take off the / at the beginning of the path

			if os.path.isfile(filePath): # If the file exists
				if len(reqPath) >= 4 and (reqPath[len(reqPath)-4:] == '.htm' or reqPath[len(reqPath)-5:] == '.html'):
					statusCode = '200'
					phrase = 'OK'
					respVersion = 'HTTP/1.0'
					statusLine = respVersion + ' ' + statusCode + ' ' + phrase
					lastMod = datetime.datetime.fromtimestamp(os.path.getmtime(filePath))
					headers = (
                                                'Connection: close' + '\r\n' +
						#'Connection: keep-alive' + '\r\n' + 
                                                #'Keep-Alive: 300 \r\n' +
						'Date: ' + datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT') + '\r\n' +  
						'Server: ' + server + '\r\n' +  # TODO: Not sure what should be the server header
						'Last Modified: ' + lastMod.strftime('%a, %d %b %Y %H:%M:%S GMT') + '\r\n' + 
						# 'Content-Length: ' + str(os.path.getsize(filePath)) + '\r\n' + 
						'Content-Type: ' + 'text/html' + '\r\n')
					# contents = open(filePath, 'r')
					# print statusLine
					# print headers
					# print contents.read()
					#print len(open(filePath, 'r').read())
					
					#connSock.sendall(statusLine + headers + contents.read())
				        #sock.sendall(statusLine)
					#sock.sendall(headers)
					#sock.sendall(open(filePath, 'r').read())

                                        packet = statusLine + headers + open(filePath, 'r').read()
                                        packetQ.append(packet)
                                        socketQ.append(sock)
				else: # The file exists but is not a .htm or .html file
					statusCode = '403'
					phrase = 'Forbidden'
					respVersion = 'HTTP/1.0'
					statusLine = respVersion + ' ' + statusCode + ' ' + phrase + '\n'
                                        packetQ.append(statusLine)
                                        socketQ.append(sock)
                                        #sock.sendall(statusLine)
					#print statusLine
			else: # The file does not exist
				statusCode = '404'
				phrase = 'Not Found'
				respVersion = 'HTTP/1.0'
				statusLine = respVersion + ' ' + statusCode + ' ' + phrase + '\n'
                                packetQ.append(statusLine)
                                socketQ.append(sock)
				#sock.sendall(statusLine)

                        assert sock != acceptSock
                        assert sock is not None
			#openConns.remove(sock)
                        #openConns.remove(sock) 
                        #TODO We don't just want to remove them, what if the ask again for something new?
                        #We have to figure out when they are dead, then close. Right?
			#sock.close() TODO close upon sending to the socket

        for i, sock in enumerate(socketQ):
                # print "checking socket", i
                if sock in wlist:
                        # print "sending to socket #",i
                        packet = packetQ.pop(i)
                        curr = socketQ.pop(i)
                        #print packet
                        #print sock == curr
                        sock.send(packet)

                        
                        openConns.remove(sock)
                        sock.close()

