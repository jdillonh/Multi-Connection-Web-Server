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

	return method, path, version, reqHeaders
	

# main program

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


openConns.append(acceptSock) 

while 1:
	rlist, wlist, xlist = select.select(openConns, openConns, openConns, TIMEOUT)
       
	for sock in rlist:
                if sock in xlist: 
                    openConns.remove(sock)
                    sock.close()
                    continue

		if sock == acceptSock:
                        # add the new connection to openConns
			connSock, addr = acceptSock.accept()
			connSock.setblocking(0)
                        openConns.append(connSock)
		else: 
			data = sock.recv(1024) 
			if not data:
                                openConns.remove(sock)
                                sock.close()
                                continue
			reqMethod, reqPath, reqVersion, reqHeads = parseRequest(data)

			filePath = reqPath[1:] # Take off the / at the beginning of the path

			if os.path.isfile(filePath): # If the file exists, serve it
				if len(reqPath) >= 4 and (reqPath[len(reqPath)-4:] == '.htm' or reqPath[len(reqPath)-5:] == '.html'):
					statusCode = '200'
					phrase = 'OK'
					respVersion = 'HTTP/1.0'
					statusLine = respVersion + ' ' + statusCode + ' ' + phrase
					lastMod = datetime.datetime.fromtimestamp(os.path.getmtime(filePath))
					headers = (
                                                'Connection: close' + '\r\n' +
						'Date: ' + datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT') + '\r\n' +  
						'Server: ' + server + '\r\n' +  
						'Last Modified: ' + lastMod.strftime('%a, %d %b %Y %H:%M:%S GMT') + '\r\n' + 
						'Content-Type: ' + 'text/html' + '\r\n'
					)

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

			else: # The file does not exist
				statusCode = '404'
				phrase = 'Not Found'
				respVersion = 'HTTP/1.0'
				statusLine = respVersion + ' ' + statusCode + ' ' + phrase + '\n'
                                packetQ.append(statusLine)
                                socketQ.append(sock)

                        assert sock != acceptSock
                        assert sock is not None


        for i, sock in enumerate(socketQ):
                if sock in wlist:
                        packet = packetQ.pop(i)
                        curr = socketQ.pop(i)
                        sock.send(packet)
                        
                        openConns.remove(sock)
                        sock.close()

