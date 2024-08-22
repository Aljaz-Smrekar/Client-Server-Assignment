import socket
import sys
from select import select
import datetime

# Constants
MAGIC_NUM = 0x36FB
REQUEST_DATE = 0x0001
REQUEST_TIME = 0x0002

# Month names in different languages
MONTH_NAMES = {
    'English': ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"],
    'Māori': ["Kohi-tātea", "Hui-tanguru", "Poutū-te-rangi", "Paenga-whāwhā",
              "Haratua", "Pipiri", "Hōngingoi", "Here-turi-kōkā", "Mahuru",
              "Whiringa-ā-nuku", "Whiringa-ā-rangi", "Hakihea"],
    'German': ["Januar", "Februar", "März", "April", "Mai", "Juni",
               "Juli", "August", "September", "Oktober", "November", "Dezember"]
}

def tell_it_what_it_is(date_time, language, request_type):
    """Creates a representation of the date or time based on language selected"""
    month = MONTH_NAMES[language][date_time.month - 1]
    day = date_time.day
    year = date_time.year
    hour = date_time.hour
    minute = date_time.minute

    if request_type == REQUEST_DATE:
        if language == 'English':
            return f"Today's date is {month} {day}, {year}"
        elif language == 'Māori':
            return f"Ko te rā o tēnei rā ko {month} {day}, {year}"
        elif language == 'German':
            return f"Heute ist der {day}. {month} {year}"
    if request_type == REQUEST_TIME:
        if language == 'English':
            return f"The current time is {hour:02}:{minute:02}"
        elif language == 'Māori':
            return f"Ko te wā o tēnei wā {hour:02}:{minute:02}"
        elif language == 'German':
            return f"Die Uhrzeit ist {hour:02}:{minute:02}"

class Server:
    def __init__(self, ports):
        """Initialize server with given ports."""
        self.ports = ports
        self.sockets = []
        self.ensock = None
        self.masock = None
        self.gersock = None

    def check_number_of_arguments(self):
        """Ensure exactly 3 ports are provided."""
        if len(sys.argv) != 4:
            sys.exit("ERROR: Incorrect number of command line arguments")

    def check_port(self):
        """Check that ports are unique, positive integers within valid range."""
        ports = self.ports

        if self.ports[0] == self.ports[1] or self.ports[0] == self.ports[2] or self.ports[1] == self.ports[2]:
            sys.exit("ERROR: Duplicate ports given")
        
        for port in self.ports:
            try:
                port = int(port)
                if port <= 0:
                    sys.exit(f"ERROR: Given port '{str(port)}' is not a positive integer")
                if not (1024 <= port <= 64000):
                    sys.exit(f"ERROR: Given port '{str(port)}' is not in the range [1024, 64000]")
            except ValueError:
                sys.exit(f"ERROR: Given port '{str(port)}' is not a positive integer")
        self.ports = list(map(int, ports))

    def open_and_bind_socket(self):
        """Create and bind sockets for each language."""
        try:
            print(f"Binding English to port {self.ports[0]}")
            self.ensock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                self.sockets.append(self.ensock)
                self.ensock.bind(("localhost", self.ports[0]))
            except:
                self.close_sockets()
                sys.exit("ERROR: Socket binding failed")
    
            print(f"Binding Māori to port {self.ports[1]}")
            self.masock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                self.sockets.append(self.masock)
                self.masock.bind(("localhost", self.ports[1]))
            except:
                self.close_sockets()
                sys.exit("ERROR: Socket binding failed")

            print(f"Binding German to port {self.ports[2]}")
            self.gersock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                self.sockets.append(self.gersock)
                self.gersock.bind(("localhost", self.ports[2]))
            
            except:
                self.close_sockets()
                sys.exit("ERROR: Socket binding failed")
                
        except socket.error:
            self.close_sockets()
            sys.exit("ERROR: Socket creation failed")

    def close_sockets(self):
        """Close all open sockets."""
        for sock in self.sockets:
            sock.close()
        self.sockets = []

    def waiting_for_request(self):
        """Handle incoming requests in an infinite loop."""
        
        try:
            while True:
                print("Waiting for requests...")
                readable, _, _ = select(self.sockets, [], [])
                if not readable:
                    continue

                for sock in readable:
                    try:
                        data, address = sock.recvfrom(1024)
                        if not self.valid_dt_request(data):
                            continue

                        language = self.get_language(sock)
                        #print(data)
                        request_type = (data[4] << 8) + data[5]
                        
                        print(f"{language} received {'date' if request_type == REQUEST_DATE else 'time'} request from {address[0]}")
                        
                        response = self.create_response(language, request_type)
                        if len(response) >= 255:
                            sys.exit("ERROR: Text too long, dropping packet")

                        try:
                            sock.sendto(response, address)
                            print("Response sent")
                        except socket.error:
                            print("ERROR: Sending failed, dropping packet")
                            continue
                            
                    except socket.timeout:
                        print("ERROR: Receiving timed out, dropping packet")
                        continue
                    
                    except socket.error:
                        print("ERROR: Receiving failed, dropping packet")
                        continue

        except Exception as error:
            self.close_sockets()
            sys.exit(f"ERROR: {error}")
        finally:
            self.close_sockets()
            

    def create_response(self, language, request_type):
        """Create a response based on the request type"""
        current_time = datetime.datetime.now()
        textual_representation = tell_it_what_it_is(current_time, language, request_type)

        response = bytearray()

        magic_no = MAGIC_NUM
        packet_type = 0x0002  # DT-Response
        lang_code = 0x0001 if language == 'English' else 0x0002 if language == 'Māori' else 0x0003
        year = current_time.year
        month = current_time.month
        day = current_time.day
        hour = current_time.hour
        minute = current_time.minute
        length = len(textual_representation.encode('utf-8'))  # Ensure length is based on utf-8 encoding

        response.extend(magic_no.to_bytes(2, 'big'))
        response.extend(packet_type.to_bytes(2, 'big'))
        response.extend(lang_code.to_bytes(2, 'big'))
        response.extend(year.to_bytes(2, 'big'))
        response.extend(month.to_bytes(1, 'big'))
        response.extend(day.to_bytes(1, 'big'))
        response.extend(hour.to_bytes(1, 'big'))
        response.extend(minute.to_bytes(1, 'big'))
        response.extend(length.to_bytes(1, 'big'))
        response.extend(textual_representation.encode('utf-8'))  # Use utf-8 encoding
        
        return response

    def valid_dt_request(self, packet):
        """Validate the DT-Request packet."""
        if len(packet) != 6:
            print("ERROR: Packet length incorrect for a DT_Request, dropping packet")
            return False
        
        magic_num = (packet[0] << 8) + packet[1]
        if magic_num != MAGIC_NUM:
            print("ERROR: Packet magic number is incorrect, dropping packet")
            return False
        
        packet_type = (packet[2] << 8) + packet[3]
        if packet_type != 0x0001:
            print("ERROR: Packet is not a DT_Request, dropping packet")
            return False

        request_type = (packet[4] << 8) + packet[5]
        if request_type not in (REQUEST_DATE, REQUEST_TIME):
            print("ERROR: Packet has invalid type, dropping packet")
            return False
        
        return True

    def get_language(self, sock):
        """Determine the language based on the socket."""
        if sock == self.ensock:
            return 'English'
        elif sock == self.masock:
            return 'Māori'
        elif sock == self.gersock:
            return 'German'

def main():
    """Main function to start the server."""
    if len(sys.argv) != 4:
        sys.exit("ERROR: Incorrect number of command line arguments")

    ports = sys.argv[1:4]
    server = Server(ports) 
    server.check_number_of_arguments()
    server.check_port()
    server.open_and_bind_socket()
    server.waiting_for_request()


main()