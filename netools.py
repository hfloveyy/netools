#!/opt/local/bin/python2.7
# -*- coding: utf-8 -*-
import sys
import socket
import getopt
import threading
import thread
import subprocess
import time
import platform
import os
import re

# define some global variables
listen             = False
command            = False
upload             = False
execute            = ""
target             = ""
upload_destination = ""
port               = 0

# this runs a command and returns the output
def run_command(command):
        
        # trim the newline
        command = command.rstrip()
        
        # run the command and get the output back
        try:
                output = subprocess.check_output(command,stderr=subprocess.STDOUT, shell=True)
        except:
                output = "Failed to execute command.\r\n"
        
        # send the output back to the client
        return output

# this handles incoming client connections
def client_handler(client_socket):
        global upload
        global execute
        global command
        
        # check for upload
        if len(upload_destination):
                
                # read in all of the bytes and write to our destination
                file_buffer = ""
                
                # keep reading data until none is available
                while True:
                        data = client_socket.recv(1024)
                        
                        if not data:
                                break
                        else:
                                file_buffer += data
                                
                # now we take these bytes and try to write them out
                try:
                        file_descriptor = open(upload_destination,"wb")
                        file_descriptor.write(file_buffer)
                        file_descriptor.close()
                        
                        # acknowledge that we wrote the file out
                        client_socket.send("Successfully saved file to %s\r\n" % upload_destination)
                except:
                        client_socket.send("Failed to save file to %s\r\n" % upload_destination)
                        
                
        
        # check for command execution
        if len(execute):
                
                # run the command
                output = run_command(execute)
                
                client_socket.send(output)
        
        
        # now we go into another loop if a command shell was requested
        if command:
                
                while True:
                        # show a simple prompt
                        client_socket.send("<root@shell#> ")
                        
                        # now we receive until we see a linefeed (enter key)
                        cmd_buffer = ""
                        while "\n" not in cmd_buffer:
                                cmd_buffer += client_socket.recv(1024)
                
                        
                        # we have a valid command so execute it and send back the results
                        response = run_command(cmd_buffer)
                        
                        # send back the response
                        client_socket.send(response)
        
# this is for incoming connections
def server_loop():
        global target
        global port
        
        # if no target is defined we listen on all interfaces
        if not len(target):
                target = "0.0.0.0"
                
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((target,port))
        
        server.listen(5)        
        
        while True:
                client_socket, addr = server.accept()
                
                # spin off a thread to handle our new client
                client_thread = threading.Thread(target=client_handler,args=(client_socket,))
                client_thread.start()
                

# if we don't listen we are a client....make it so.
def client_sender(buffer):
        
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                
        try:
                # connect to our target host
                client.connect((target,port))
                
                # if we detect input from stdin send it 
                # if not we are going to wait for the user to punch some in
                
                if len(buffer):
                        
                        client.send(buffer)
                
                while True:
                        
                        # now wait for data back
                        recv_len = 1
                        response = ""
                        
                        while recv_len:
                                data     = client.recv(4096)
                                recv_len = len(data)
                                response+= data
                                
                                if recv_len < 4096:
                                        break
                        
                        print response, 
                        
                        # wait for more input
                        buffer = raw_input("")
                        buffer += "\n"                        
                        
                        # send it off
                        client.send(buffer)
                        
                
        except:
                # just catch generic errors - you can do your homework to beef this up
                print "[*] Exception! Exiting."
                
                # teardown the connection                  
                client.close()  
                        
                        
        

def usage():
        print u"Netools 内网工具箱   CTRL-C 退出！"
        print "Usage: netools.py -t target_host -p port"
        print u"-l --listen                - 服务器端监听模式 Examples:netools -l 或者 netools --listen"
        print u"-t --target                - 客户端模式 设置服务器端ip地址"
        print u"-c --command               - 返回shell"
        print u"-s --scan                  - 扫描当前网段存活主机 netools -s 192.168.1.1"
        print
        print u"例子: "
        print u"服务器端："
        print u"netools.py  -l -c"
        print u"客户端："
        print "netools.py -t 192.168.0.1 -p 5555 -c"

        sys.exit(0)

#get mac addr
def get_mac(ip_address):
    
    cmd = ["arp", "-a", ip_address]
    output = os.popen(" ".join(cmd)).readlines()
    m = re.search('[0-9a-z]{2}-[0-9a-z]{2}-[0-9a-z]{2}-[0-9a-z]{2}-[0-9a-z]{2}-[0-9a-z]{2}',str(output))
    if m:
        return m.group(0)
    else:
        return u"没有找到"

def get_os():
    u'''
    get os 类型
    '''
    os = platform.system()
    if os == "Windows":
        return "n"
    else:
        return "c"
     
def ping_ip(ip_str):
    cmd = ["ping", "-{op}".format(op=get_os()),
           "1", ip_str]
    output = os.popen(" ".join(cmd)).readlines()
     
    flag = False
    for line in list(output):
        if not line:
            continue
        if str(line).upper().find("TTL") >=0:
            flag = True
            break
    if flag:
        get_mac(ip_str)
        print u"[*]ip: %s 可以ping通"%ip_str
        print u"物理地址： {mac}".format(mac=get_mac(ip_str))

def find_ip(ip_prefix):
    u'''
    给出当前的127.0.0 ，然后扫描整个段所有地址
    '''
    ip_prefix = '.'.join(ip_prefix.split('.')[:-1])
    for i in range(1,256):
        ip = '%s.%s'%(ip_prefix,i)
        thread.start_new_thread(ping_ip, (ip,))
        time.sleep(0.3)




def main():
        global listen
        global port
        global execute
        global command
        global upload_destination
        global target
        
        if not len(sys.argv[1:]):
                usage()
                
        # read the commandline options
        try:
                opts, args = getopt.getopt(sys.argv[1:],"hle:t:p:cu:s:",["help","listen","execute","target","port","command","upload","scan"])
        except getopt.GetoptError as err:
                print str(err)
                usage()
                
                
        for o,a in opts:
                if o in ("-h","--help"):
                        usage()
                elif o in ("-l","--listen"):
                        listen = True
                elif o in ("-e", "--execute"):
                        execute = a
                elif o in ("-c", "--commandshell"):
                        command = True
                elif o in ("-u", "--upload"):
                        upload_destination = a
                elif o in ("-t", "--target"):
                        target = a
                elif o in ("-p", "--port"):
                        port = int(a)
                elif o in ("-s","--scan"):
                        find_ip(a)
                else:
                        assert False,"Unhandled Option"
        

        # are we going to listen or just send data from stdin
        if not listen and len(target) and port > 0:
                # read in the buffer from the commandline
                # this will block, so send CTRL-D if not sending input
                # to stdin
                buffer = sys.stdin.read()
                # send data off
                client_sender(buffer)   
        
        # we are going to listen and potentially 
        # upload things, execute commands and drop a shell back
        # depending on our command line options above
        if listen:
                server_loop()



if __name__ == '__main__':
    try:
        main()
    except Exception,e:
        print u'退出程序！' 
    except KeyboardInterrupt:      
        print u'退出netools！'
        sys.exit(0)