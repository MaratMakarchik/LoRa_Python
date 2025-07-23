import time
import socket
import subprocess
import threading
import queue

class LoraController:
    """
    Manages LoRa communication using separate sockets for commands and data.
    Data reception is handled in a non-blocking background thread.
    """
    def __init__(self):
        """Initializes sockets and communication primitives."""
        self.cmd_socket = None
        self.data_socket = None
        
        # A thread-safe queue to hold incoming messages
        self.data_queue = queue.Queue()
        # An event to signal the receiver thread to stop
        self.stop_event = threading.Event()
        self.receiver_thread = None

        try:
            # Connect the command socket
            self.cmd_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.cmd_socket.connect('/tmp/lora_cmd.sock')
            print("Connected to command socket.")

            # Connect the data socket
            self.data_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.data_socket.connect('/tmp/lora_data.sock')
            print("Connected to data socket.")

        except ConnectionRefusedError:
            print("Connection refused. Make sure the C program is running.")
            self.close_sockets()
            raise

    def start(self):
        """Starts the background thread for receiving data."""
        if self.receiver_thread is None:
            self.stop_event.clear()
            self.receiver_thread = threading.Thread(target=self._data_receiver_loop, daemon=True)
            self.receiver_thread.start()
            print("Data receiver thread started.")

    def _data_receiver_loop(self):
        """
        The main loop for the receiver thread.
        Listens for data and puts it into the queue.
        """
        while not self.stop_event.is_set():
            if not self.data_socket:
                break 

            try:
                # First, read the message length (1 byte)
                # Set a timeout to periodically check the stop_event
                self.data_socket.settimeout(1.0) 
                len_byte = self.data_socket.recv(1)

                if not len_byte:
                    print("Data connection closed by server.")
                    self.data_socket = None
                    break
                
                length = len_byte[0]
                # Read exactly as many bytes as specified by the length
                data = self.data_socket.recv(length)
                
                # Process and put the data into the queue
                processed_data = self._process_data(data)
                self.data_queue.put(processed_data)

            except socket.timeout:
                # This is expected, allows the loop to check stop_event
                continue
            except socket.error as e:
                print(f"Socket error on receive: {e}")
                self.data_socket = None
                break
        
        print("Data receiver thread stopped.")

    def stop(self):
        """Stops the receiver thread and closes all sockets."""
        print("Stopping controller...")
        if self.receiver_thread and self.receiver_thread.is_alive():
            self.stop_event.set()
            self.receiver_thread.join() # Wait for the thread to finish
        self.close_sockets()

    def send_command(self, data: bytes):
        """Sends a command through the established connection."""
        if not self.cmd_socket:
            print("Command socket is not connected.")
            return
        try:
            # Send length (1 byte), then the data itself
            self.cmd_socket.sendall(bytes([len(data)]) + data)
        except BrokenPipeError:
            print("Connection lost while sending command.")
            self.cmd_socket = None
            
    def get_message(self):
        """
        Retrieves one message from the queue, if available.
        This is non-blocking and returns None if the queue is empty.
        """
        try:
            # The "flag" is the presence of an item in the queue
            return self.data_queue.get_nowait()
        except queue.Empty:
            # This is normal, just means no new messages
            return None

    def _process_data(self, raw_data):
        """Processes raw bytes into a string or list."""
        if not raw_data:
            return None
        try:
            return raw_data.decode('utf-8')
        except UnicodeDecodeError:
            return list(raw_data)

    def close_sockets(self):
        """Properly closes all sockets."""
        if self.cmd_socket:
            self.cmd_socket.close()
            self.cmd_socket = None
            print("Command socket closed.")
        if self.data_socket:
            self.data_socket.close()
            self.data_socket = None
            print("Data socket closed.")


if __name__ == "__main__":
    #-----------------------------------------------------------
    controller = None
    c_process = None
    try:
        # Use Popen to run the C program in the background
        c_process = subprocess.Popen(["./lora_app"])
        print(f"Started C process with PID: {c_process.pid}")
        time.sleep(2) # Give the C program time to set up sockets

        controller = LoraController()
        controller.start() # Start the background listener

        print("--- Starting main application loop ---")
        last_command_time = time.time()
    #------------------------------------------------------------  
        while True:
            message = controller.get_message() #проверка и получение сообщения
            
            if message:
                print(f"MAIN LOOP | Received data: {message} | {time.strftime("%H:%M:%S", time.localtime())}")

            controller.send_command(b'Hello') #отправка сообщения 

            
            if not controller.cmd_socket and not controller.data_socket:#аварийный выход
                 print("MAIN LOOP | Both connections lost. Exiting.")
                 break

            time.sleep(0.5) # Main loop delay

    except ConnectionRefusedError:
        print("Could not start the controller. Aborting.")
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Shutting down.")
    finally:
        if controller:
            controller.stop()
        if c_process:
            c_process.terminate() # Terminate the C subprocess
            c_process.wait()
            print("C process terminated.")
        print("Application finished.")
