#!/usr/bin/python3

from threading import Thread
import sys, socket, select, argparse, os, time
import sys, socket, select, argparse, os, re
from colorama import Fore

def show_info(**kwargs):
    for key,value in kwargs.items():
        value = f"{value[0]}:{value[1]}" if key == 'Reenvia_a' else value
        key = key.replace("_"," ")
        print(f"{Fore.WHITE}{Fore.YELLOW}[*] {key.upper()}{Fore.WHITE} : {Fore.GREEN}{value}{Fore.WHITE}")

replace_payload = lambda payload: payload.replace("[lf]","\n").replace("[cr]","\r").replace("[crlf]","\r\n").encode()


class main(object):
    def __init__(self) -> None:
        self.args = self.parse_args()
        self.mode = str(self.args.connection_type)
        self.log_file = ''
        # regex SSH-2.0-.*
        self.regex_ssh_hotkey = re.compile("SSH-2.0-.*")

    def parse_args(self) -> dict:
        desc=f"""Simple proxy forwarding. {Fore.YELLOW}client {Fore.WHITE} <--> {Fore.GREEN}server_socket{Fore.WHITE} <--> {Fore.BLUE}remote_server{Fore.WHITE}"""
        parser = parser = argparse.ArgumentParser(description=desc)
        parser.add_argument("-p","--port",type=int,help="Puerto de escucha.(9090)",default=9090)
        parser.add_argument("-c","--connect",type=str,help="Direccion donde redireccionara todo el trafico. (127.0.0.1:22)",default="127.0.0.1:22")
        parser.add_argument("--connection-type",type=str,help="Redirecciona a un servidor OpenSSH o OpenVPN. (SSH)",default="SSH",choices=["SSH","OPENVPN"])
        parser.add_argument("--custom-response",help="Respuesta personalizada para enviar al cliente cuando se establece la conexion. ( None )",default="None",type=str)

        args = parser.parse_args()
        return args

    def run_the_server(self) -> None:
        try:
            bind_port = self.args.port
            connect_str = self.args.connect
            connect_to = (connect_str.split(":")[0],int(connect_str.split(":")[1]))
            custom_response = replace_payload(self.args.custom_response)

            self.log_file = f"/var/log/FenixManager/pysocks:{bind_port}-{connect_str}.log"
            os.remove(self.log_file) if os.path.exists(self.log_file) else None

            sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            sock.bind(("0.0.0.0",bind_port))
            sock.listen(0)
        
            while True:
                client_socket,address = sock.accept()
                client_socket.settimeout(30)
                proxy_socket(client_socket,custom_response,connect_to,address).start()

        except KeyboardInterrupt as er: sys.exit(130)
        except Exception as er:
            print(f"[ ERROR ]{Fore.RED}{bind_port}:{connect_str} {er} {Fore.WHITE}")
            exit(1)

class proxy_socket(Thread,main):
    def __init__(self,client_soket:tuple,custom_response:bytes,forwarding_to:tuple,addr:tuple) -> None:
        Thread.__init__(self)
        main.__init__(self)
        self.s = None
        self.conn,self.addr = client_soket,"{}:{}".format(addr[0],addr[1])
        self.connect_to = forwarding_to
        self.buffer_size = 4096 * 4
        self.custom_response = custom_response
        self.client_buffer = ''

    def run(self):
        count_packet=0
        if self.mode.lower() == 'openvpn':
            payload = self.conn.recv(self.buffer_size)
            print(f"{Fore.WHITE}{Fore.GREEN}[+] {Fore.WHITE}Payload {Fore.YELLOW}{self.addr}{Fore.WHITE} {payload}")
            self.conn.sendall(self.custom_response) 
            self.forward()
            self.incoming_connections()
        else:
            while True:
                payload = self.conn.recv(self.buffer_size)
                if not payload:
                    break
                else:
                    print(f"{Fore.WHITE}{Fore.GREEN}[+] {Fore.WHITE}Payload {Fore.YELLOW}{self.addr}{Fore.WHITE} {payload}")
                    if count_packet == 0:
                        self.conn.sendall(self.custom_response)
                        count_packet += 1
                    else:
                        try:
                            ssh_identifier = self.regex_ssh_hotkey.findall(str(payload.decode("utf-8")))
                            print(ssh_identifier[0])
                            self.forward()
                            self.remote.sendall(f"{ssh_identifier[0]}\r\n".encode())
                            self.incoming_connections()
                            
                        except:
                            pass
                
                
            
    
    def forward(self):
        try:
            self.remote = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.remote.connect(self.connect_to)
        except KeyboardInterrupt: sys.exit(130)
        except Exception as er:
            print(f"[ ERROR ] Fallo al conectar con el servidor remoto: {Fore.YELLOW}{self.connect_to}{Fore.WHITE}")
            self.conn.sendall("HTTP/1.1 503 Service Unavailable\r\n\r\n".encode())
            self.conn.close()
            exit(1)
    
    def incoming_connections(self):
        err = False
        self.inputs = [self.remote,self.conn]    
        

        if self.custom_response != b"None":            
            payload = self.conn.recv(self.buffer_size)
            self.conn.send(self.custom_response)

        while self.inputs:
            read, _, err = select.select(self.inputs, [],[],3)
            
            for self.s in read:
                try:    
                    self.data = self.s.recv(self.buffer_size)
                    if self.data:
                        if self.s == self.remote:
                            self.conn.sendall(self.data)
                        else:
                            while self.data:
                                bytes = self.remote.send(self.data)
                                self.data = self.data[bytes:]
                    else:
                        break
                except KeyboardInterrupt:
                    sys.exit(130)
                except Exception as er:
                    write_to_log(log_file,er)
                    #self.close()
                    break
            if err: break
        self.inputs = [self.remote,self.conn]
        

        while True:
                read, _,err = select.select(self.inputs, [],self.inputs,3)

                if  read:
                    for self.s in read:
                        try:
                            data = self.s.recv(self.buffer_size)
                            if len(data) == 0:
                                self.close()
                                break
                        
                            else:
                                if self.s == self.remote:
                                        self.conn.sendall(data)
                                else:
                                    while data:
                                        byte = self.remote.send(data)
                                        data = data[byte:]
                                    
                                        
                                        
                        except KeyboardInterrupt:
                            sys.exit(130)
                        except Exception as er:
                            #write_to_log(log_file,er)
                            break
                if err:
                    break
    def close(self):
        self.inputs = []
        self.remote.close()
        self.conn.close()

def write_to_log(log_file:str,msg:str):
    with open(log_file,"a") as f:
        f.write(f"{msg}\n")

if __name__ == "__main__":
    main().run_the_server()
