/* sudo gcc -o lora_app main.c LoRa.c -lwiringPi*/

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/select.h>
#include <stddef.h> // Required for offsetof()
#include "LoRa.h"

#define CMD_SOCKET_PATH "/tmp/lora_cmd.sock"
#define DATA_SOCKET_PATH "/tmp/lora_data.sock"
#define BUFFER_SIZE 255

// Global file descriptors for the established client connections
int cmd_client_fd = -1;
int data_client_fd = -1;

void send_to_python(uint8_t *data, uint8_t len)
{
    if (data_client_fd < 0)
        return; // Don't send if client is not connected

    // It's safer to check the return values of write
    if (write(data_client_fd, &len, 1) < 0)
    {
        perror("write len failed");
        data_client_fd = -1; // Mark connection as dead
        return;
    }
    if (write(data_client_fd, data, len) < 0)
    {
        perror("write data failed");
        data_client_fd = -1; // Mark connection as dead
    }
}

int main()
{
    // --- 1. Initialize Sockets ---
    int cmd_listen_fd, data_listen_fd;
    struct sockaddr_un addr;

    // Create listening socket for commands
    if ((cmd_listen_fd = socket(AF_UNIX, SOCK_STREAM, 0)) == -1)
    {
        perror("socket error (command)");
        return 1;
    }

    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, CMD_SOCKET_PATH, sizeof(addr.sun_path) - 1);
    unlink(CMD_SOCKET_PATH); // Remove old socket file if it exists

    // *** THE KEY FIX IS HERE: Calculate the correct address length ***
    socklen_t addr_len = offsetof(struct sockaddr_un, sun_path) + strlen(addr.sun_path);

    if (bind(cmd_listen_fd, (struct sockaddr *)&addr, addr_len) == -1)
    {
        perror("bind error (command)");
        return 1;
    }

    if (listen(cmd_listen_fd, 1) == -1)
    {
        perror("listen error (command)");
        return 1;
    }

    // Create listening socket for data
    if ((data_listen_fd = socket(AF_UNIX, SOCK_STREAM, 0)) == -1)
    {
        perror("socket error (data)");
        return 1;
    }

    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, DATA_SOCKET_PATH, sizeof(addr.sun_path) - 1);
    unlink(DATA_SOCKET_PATH);

    // *** APPLYING THE SAME FIX FOR THE DATA SOCKET ***
    addr_len = offsetof(struct sockaddr_un, sun_path) + strlen(addr.sun_path);

    if (bind(data_listen_fd, (struct sockaddr *)&addr, addr_len) == -1)
    {
        perror("bind error (data)");
        return 1;
    }

    if (listen(data_listen_fd, 1) == -1)
    {
        perror("listen error (data)");
        return 1;
    }
    // --- 2. Wait for Python client connections ---
    printf(" Waiting for Python client to connect to command socket...\n");
    if ((cmd_client_fd = accept(cmd_listen_fd, NULL, NULL)) == -1)
    {
        perror("accept command socket failed");
        return 1;
    }
    printf(" Command client connected.\n");

    printf(" Waiting for Python client to connect to data socket...\n");
    if ((data_client_fd = accept(data_listen_fd, NULL, NULL)) == -1)
    {
        perror("accept data socket failed");
        return 1;
    }
    printf(" Data client connected.\n");

    // Listening sockets are no longer needed after connections are established
    close(cmd_listen_fd);
    close(data_listen_fd);

    // --- 3. Initialize LoRa ---
    LoRa myLoRa = newLoRa();
    myLoRa.CS_pin = 8;
    myLoRa.reset_pin = 25;
    myLoRa.DIO0_pin = 17; // This should be the GPIO number, not the physical pin
    myLoRa.SPI_channel = 0;

    if (LoRa_init(&myLoRa) == LORA_OK)
    {
        send_to_python("Lora init", strlen("Lora init"));
    }
    else
    {
        send_to_python("Lora fail", strlen("Lora fail"));
        return 1;
	}
    
    // --- 4. Main Loop ---
    uint8_t RxBuffer[BUFFER_SIZE];
    uint8_t bytesReceived;
    LoRa_startReceiving(&myLoRa);
    printf(" Starting main loop...\n");

    while (1)
    {
        // Check for incoming LoRa data
        if (digitalRead(myLoRa.DIO0_pin) == HIGH)
        {
            bytesReceived = LoRa_receive(&myLoRa, RxBuffer, BUFFER_SIZE);
            if (bytesReceived > 0)
            {
                // printf("Received %d bytes from LoRa: '", bytesReceived);
                send_to_python(RxBuffer, bytesReceived);
            }
        }

        // Non-blocking check for commands from Python
        fd_set read_fds;
        FD_ZERO(&read_fds);
        FD_SET(cmd_client_fd, &read_fds);
        struct timeval timeout = {0, 10000}; // 10ms timeout

        if (select(cmd_client_fd + 1, &read_fds, NULL, NULL, &timeout) > 0)
        {
            uint8_t len;
            uint8_t buffer[BUFFER_SIZE];

            if (read(cmd_client_fd, &len, 1) > 0)
            {
                if (read(cmd_client_fd, buffer, len) > 0)
                {
                    //send_to_python(buffer, 4);
                    LoRa_transmit(&myLoRa,(uint8_t*)buffer,len,1000);
                }
            }
            else
            {
                // Connection closed by client
                printf("Python command client disconnected.\n");
                close(cmd_client_fd);
                cmd_client_fd = -1;
                break; // Exit loop if command client disconnects
            }
        }

        // Exit if data connection is also lost
        if (data_client_fd < 0)
        {
            printf("Python data client disconnected. Exiting.\n");
            break;
        }
    }

    // Cleanup
    if (cmd_client_fd > 0)
        close(cmd_client_fd);
    if (data_client_fd > 0)
        close(data_client_fd);
    printf("Program finished.\n");
    return 0;
} 
