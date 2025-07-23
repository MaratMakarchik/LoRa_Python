#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "LoRa.h"
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
/*-------------------------------------------------*/
#define BUFFER_SIZE 16
#define CMD_SOCKET_PATH "/tmp/lora_cmd.sock"
#define DATA_SOCKET_PATH "/tmp/lora_data.sock"
/*-------------------------------------------------*/
int cmd_socket, data_socket;
struct sockaddr_un addr;
/*-------------------------------------------------*/
void init_sockets() {
    // Создаем командный сокет (прием от Python)
    cmd_socket = socket(AF_UNIX, SOCK_STREAM, 0);
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, CMD_SOCKET_PATH, sizeof(addr.sun_path)-1);
    unlink(CMD_SOCKET_PATH);
    bind(cmd_socket, (struct sockaddr*)&addr, sizeof(addr));
    listen(cmd_socket, 5);

    // Создаем сокет данных (отправка в Python)
    data_socket = socket(AF_UNIX, SOCK_STREAM, 0);
    strncpy(addr.sun_path, DATA_SOCKET_PATH, sizeof(addr.sun_path)-1);
    unlink(DATA_SOCKET_PATH);
    bind(data_socket, (struct sockaddr*)&addr, sizeof(addr));
    listen(data_socket, 5);
}

void handle_commands() {
    int client_fd = accept(cmd_socket, NULL, NULL);
    
    while(1) {
        uint8_t len;
        uint8_t buffer[256];
        
        // Читаем длину сообщения
        if(read(client_fd, &len, 1) <= 0) break;
        
        // Читаем данные
        ssize_t n = read(client_fd, buffer, len);
        if(n <= 0) break;
        
        // Вызываем функцию отправки в LoRa
        lora_send(buffer, len);
    }
    close(client_fd);
}

void send_to_python(uint8_t* data, uint8_t len) {
    int client_fd = accept(data_socket, NULL, NULL);
    write(client_fd, &len, 1);     // Отправляем длину
    write(client_fd, data, len);   // Отправляем данные
    close(client_fd);
}

/*-------------------------------------------------*/
int main() {
    init_sockets();
    LoRa myLoRa = newLoRa();
    myLoRa.CS_pin = 8;      // BCM GPIO 8
    myLoRa.reset_pin = 25;  // BCM GPIO 25
    myLoRa.DIO0_pin = 17;   // BCM GPIO 24
    myLoRa.SPI_channel = 0; // SPI Channel 0

    uint16_t status = LoRa_init(&myLoRa);
    if (status == LORA_OK) {
        send_to_python("LoRa module initialized successfully!\n", strlen("LoRa module initialized successfully!\n"));
    } 
    else {
        send_to_python("Error init LoRa\n", strlen("Error init LoRa\n"))
        return 1;
    }

    uint8_t RxBuffer[BUFFER_SIZE];
    uint8_t bytesReceived;
    int current_status;
    LoRa_startReceiving(&myLoRa);
    // В обработчике приема LoRa
    while(1) {
        current_status = digitalRead(myLoRa.DIO0_pin);
        if(current_status == HIGH){
            bytesReceived = LoRa_receive(&myLoRa, RxBuffer, BUFFER_SIZE);
            send_to_python(RxBuffer, BUFFER_SIZE);
        }
        // Неблокирующая проверка команд
        fd_set set;
        FD_ZERO(&set);
        FD_SET(cmd_socket, &set);
        struct timeval timeout = {0, 10000}; // 1 мс
        
        if(select(cmd_socket+1, &set, NULL, NULL, &timeout) > 0) {
            handle_commands();
        }
    }
}




int main(void){
    LoRa myLoRa = newLoRa();
    myLoRa.CS_pin = 8;      // BCM GPIO 8
    myLoRa.reset_pin = 25;  // BCM GPIO 25
    myLoRa.DIO0_pin = 17;   // BCM GPIO 24
    myLoRa.SPI_channel = 0; // SPI Channel 0

    uint16_t status = LoRa_init(&myLoRa);
    if (status == LORA_OK) {
        printf("LoRa module initialized successfully!\n");
    } 
    else {
        printf("Failed to initialize LoRa module: %d\n", status);
        return 1;
    }

    uint8_t RxBuffer[BUFFER_SIZE];
    uint8_t bytesReceived;

    LoRa_startReceiving(&myLoRa);
    
    while(1){
        int current_status = digitalRead(myLoRa.DIO0_pin);
        if(current_status == HIGH){
            bytesReceived = LoRa_receive(&myLoRa, RxBuffer, BUFFER_SIZE);
            for (int i = 0; i < bytesReceived; i++) {
                printf("%c",RxBuffer[i]);
            }
            printf("\n");

        }
        delay(10);
    }
    return 0;
}
