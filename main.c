#include <stdio.h>
#include <stdint.h>
#include "LoRa.h"
#define BUFFER_SIZE 8

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
