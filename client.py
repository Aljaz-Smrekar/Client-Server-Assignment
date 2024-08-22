import socket
import sys

# Constants
MAGIC_NUM = 0x36FB
REQUEST_DATE = 0x0001
REQUEST_TIME = 0x0002

class Client:
    def __init__(self, args):
        self.args = args
        self.request_type = None
        self.hostname = None
        self.port = None
        self.sock = None
        self.address = None

    def check_number_of_arguments(self):
        """Ensure there are exactly 3 arguments (excluding script name)"""
        if len(self.args) != 4:
            sys.exit("ERROR: Incorrect number of command line arguments")

    def user_chooses_parameter(self):
        """Determine if the user requested 'date' or 'time'"""
        request_type_str = self.args[1].lower()
        if request_type_str == "date":
            self.request_type = REQUEST_DATE
        elif request_type_str == "time":
            self.request_type = REQUEST_TIME
        else:
            sys.exit(f"ERROR: Request type '{request_type_str}' is not valid")

    def check_hostname_and_port(self):
        """Resolve hostname and validate port number using getaddrinfo"""
        try:
            self.port = int(self.args[3])
            if self.port < 0:
                sys.exit(f"ERROR: Given port '{self.port}' is not a positive integer")
            if self.port < 1024 or self.port > 64000:
                sys.exit(f"ERROR: Given port '{self.port}' is not in the range [1024, 64000]")
        except ValueError:
            sys.exit(f"ERROR: Given port '{self.args[3]}' is not a positive integer")
        
        try:
            # getaddrinfo soprry forgot this code
            addr_info = socket.getaddrinfo(self.args[2], self.port, socket.AF_INET, socket.SOCK_DGRAM)
            family, data_type, proto, canno, self.address = addr_info[0]
        except socket.gaierror:
            sys.exit("ERROR: Hostname resolution failed")

    def create_and_send_packet(self):
        """Create the request packet and send it to the server"""
        try:
        # Create the UDP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except OSError:
            sys.exit(f"ERROR: Socket creation failed")
        
        packet = bytearray()
        packet.extend(MAGIC_NUM.to_bytes(2, 'big'))
        packet.extend(0x0001.to_bytes(2, 'big')) 
        packet.extend(self.request_type.to_bytes(2, 'big'))
        
        try:
            self.sock.sendto(packet, self.address)
            if self.request_type == REQUEST_DATE:
                print(f"Date request sent to {self.address[0]}:{self.address[1]}")
            else:
                print(f"Time request sent to {self.address[0]}:{self.address[1]}")
        except OSError:
            self.sock.close()
            sys.exit("ERROR: Sending failed")

    def receive_and_process_response(self):
        """Receive the server response and process it"""
        self.sock.settimeout(1)
        try:
            received_packet, _ = self.sock.recvfrom(1024)
        except socket.timeout:
            sys.exit("ERROR: Receiving timed out")
        except socket.error:
            sys.exit(f"ERROR: Receiving failed")
        finally:
            self.sock.close()
        
        self.process_packet(received_packet)

    def process_packet(self, received_packet):
        """Process the server's response packet"""
        if len(received_packet) < 13:
            sys.exit("ERROR: Packet is too small to be a DT_Response")

        magic_no = int.from_bytes(received_packet[0:2], 'big')
        packet_type = int.from_bytes(received_packet[2:4], 'big')
        language_type = int.from_bytes(received_packet[4:6], 'big')
        year = int.from_bytes(received_packet[6:8], 'big')
        month = received_packet[8]
        day = received_packet[9]
        hour = received_packet[10]
        minute = received_packet[11]
        length = received_packet[12]

        if magic_no != MAGIC_NUM:
            sys.exit("ERROR: Packet magic number is incorrect")
        elif packet_type != 0x0002:
            sys.exit("ERROR: Packet is not a DT_Response")
        elif language_type not in (0x0001, 0x0002, 0x0003):
            sys.exit("ERROR: Packet has invalid language")
        elif year > 2100:
            sys.exit("ERROR: Packet has invalid year")
        elif month < 1 or month > 12:
            sys.exit("ERROR: Packet has invalid month")
        elif day < 1 or day > 31:
            sys.exit("ERROR: Packet has invalid day")
        elif hour < 0 or hour > 23:
            sys.exit("ERROR: Packet has invalid hour")
        elif minute < 0 or minute > 59:
            sys.exit("ERROR: Packet has invalid minute")
        elif len(received_packet) != 13 + length:
            sys.exit("ERROR: Packet text length is incorrect")

        self.print_packet_stuff(received_packet)

    def print_packet_stuff(self, received_packet):
        magic_no = int.from_bytes(received_packet[0:2], 'big')
        packet_type = int.from_bytes(received_packet[2:4], 'big')
        language_type = int.from_bytes(received_packet[4:6], 'big')
        year = int.from_bytes(received_packet[6:8], 'big')
        month = received_packet[8]
        day = received_packet[9]
        hour = received_packet[10]
        minute = received_packet[11]
        length = received_packet[12]

        try:
            text = received_packet[13:].decode('utf-8')
        except UnicodeDecodeError:
            sys.exit("ERROR: Packet has invalid text")
            
        print(f"{self.language_select(language_type)} response received:")
        print(f"Text: {text}")
        print(f"Date: {day}/{month}/{year}")
        print(f"Time: {hour:02}:{minute:02}")

    def language_select(self, language_type):
        """Convert language type to human-readable format"""
        languages = {
            0x0001: "English",
            0x0002: "Māori",
            0x0003: "German"
        }
        return languages.get(language_type)
    
def main():
    client = Client(sys.argv)
    client.check_number_of_arguments()
    client.user_chooses_parameter()
    client.check_hostname_and_port()
    client.create_and_send_packet()
    client.receive_and_process_response()


main()
