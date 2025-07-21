#include "LoRa.h"
#include <string.h>
#include <stdint.h>
LoRa newLoRa() {
    LoRa new_LoRa;
    new_LoRa.frequency = 433;
    new_LoRa.spredingFactor = SF_7;
    new_LoRa.bandWidth = BW_125KHz;
    new_LoRa.crcRate = CR_4_5;
    new_LoRa.power = POWER_20db;
    new_LoRa.overCurrentProtection = 100;
    new_LoRa.preamble = 8;
    return new_LoRa;
}

void LoRa_reset(LoRa* _LoRa) {
    digitalWrite(_LoRa->reset_pin, LOW);
    delay(1);
    digitalWrite(_LoRa->reset_pin, HIGH);
    delay(100);
}

void LoRa_gotoMode(LoRa* _LoRa, int mode) {
    uint8_t read = LoRa_read(_LoRa, RegOpMode);
    uint8_t data = read;

    if (mode == SLEEP_MODE) {
        data = (read & 0xF8) | 0x00;
        _LoRa->current_mode = SLEEP_MODE;
    } else if (mode == STNBY_MODE) {
        data = (read & 0xF8) | 0x01;
        _LoRa->current_mode = STNBY_MODE;
    } else if (mode == TRANSMIT_MODE) {
        data = (read & 0xF8) | 0x03;
        _LoRa->current_mode = TRANSMIT_MODE;
    } else if (mode == RXCONTIN_MODE) {
        data = (read & 0xF8) | 0x05;
        _LoRa->current_mode = RXCONTIN_MODE;
    } else if (mode == RXSINGLE_MODE) {
        data = (read & 0xF8) | 0x06;
        _LoRa->current_mode = RXSINGLE_MODE;
    }

    LoRa_write(_LoRa, RegOpMode, data);
}

uint8_t LoRa_read(LoRa* _LoRa, uint8_t address) {
    uint8_t addr = address & 0x7F;
    uint8_t data[2] = {addr, 0};
    digitalWrite(_LoRa->CS_pin, LOW);
    wiringPiSPIDataRW(_LoRa->SPI_channel, data, 2);
    digitalWrite(_LoRa->CS_pin, HIGH);
    return data[1];
}

void LoRa_write(LoRa* _LoRa, uint8_t address, uint8_t value) {
    uint8_t addr = address | 0x80;
    uint8_t data[2] = {addr, value};
    digitalWrite(_LoRa->CS_pin, LOW);
    wiringPiSPIDataRW(_LoRa->SPI_channel, data, 2);
    digitalWrite(_LoRa->CS_pin, HIGH);
}

void LoRa_BurstWrite(LoRa* _LoRa, uint8_t address, uint8_t *value, uint8_t length) {
    uint8_t data[length + 1];
    data[0] = address | 0x80;
    memcpy(&data[1], value, length);
    digitalWrite(_LoRa->CS_pin, LOW);
    wiringPiSPIDataRW(_LoRa->SPI_channel, data, length + 1);
    digitalWrite(_LoRa->CS_pin, HIGH);
}

uint8_t LoRa_isvalid(LoRa* _LoRa) {
    return 1;
}

void LoRa_setLowDaraRateOptimization(LoRa* _LoRa, uint8_t value) {
    uint8_t read = LoRa_read(_LoRa, RegModemConfig3);
    uint8_t data = value ? (read | 0x08) : (read & 0xF7);
    LoRa_write(_LoRa, RegModemConfig3, data);
    delay(10);
}

void LoRa_setAutoLDO(LoRa* _LoRa) {
    double BW[] = {7.8, 10.4, 15.6, 20.8, 31.25, 41.7, 62.5, 125.0, 250.0, 500.0};
    LoRa_setLowDaraRateOptimization(_LoRa, (long)((1 << _LoRa->spredingFactor) / BW[_LoRa->bandWidth]) > 16.0);
}

void LoRa_setFrequency(LoRa* _LoRa, int freq) {
    uint32_t F = (freq * 524288) >> 5;
    LoRa_write(_LoRa, RegFrMsb, F >> 16);
    delay(5);
    LoRa_write(_LoRa, RegFrMid, F >> 8);
    delay(5);
    LoRa_write(_LoRa, RegFrLsb, F);
    delay(5);
}

void LoRa_setSpreadingFactor(LoRa* _LoRa, int SF) {
    if (SF > 12) SF = 12;
    if (SF < 7) SF = 7;
    uint8_t read = LoRa_read(_LoRa, RegModemConfig2);
    delay(10);
    LoRa_write(_LoRa, RegModemConfig2, (SF << 4) | (read & 0x0F));
    delay(10);
    LoRa_setAutoLDO(_LoRa);
}

void LoRa_setPower(LoRa* _LoRa, uint8_t power) {
    LoRa_write(_LoRa, RegPaConfig, power);
    delay(10);
}

void LoRa_setOCP(LoRa* _LoRa, uint8_t current) {
    if (current < 45) current = 45;
    if (current > 240) current = 240;
    uint8_t OcpTrim = (current <= 120) ? (current - 45) / 5 : (current + 30) / 10;
    OcpTrim |= (1 << 5);
    LoRa_write(_LoRa, RegOcp, OcpTrim);
    delay(10);
}

void LoRa_setTOMsb_setCRCon(LoRa* _LoRa) {
    uint8_t read = LoRa_read(_LoRa, RegModemConfig2);
    LoRa_write(_LoRa, RegModemConfig2, read | 0x07);
    delay(10);
}

void LoRa_setSyncWord(LoRa* _LoRa, uint8_t syncword) {
    LoRa_write(_LoRa, RegSyncWord, syncword);
    delay(10);
}

uint8_t LoRa_transmit(LoRa* _LoRa, uint8_t* data, uint8_t length, uint16_t timeout) {
    int mode = _LoRa->current_mode;
    LoRa_gotoMode(_LoRa, STNBY_MODE);
    uint8_t read = LoRa_read(_LoRa, RegFiFoTxBaseAddr);
    LoRa_write(_LoRa, RegFiFoAddPtr, read);
    LoRa_write(_LoRa, RegPayloadLength, length);
    LoRa_BurstWrite(_LoRa, RegFiFo, data, length);
    LoRa_gotoMode(_LoRa, TRANSMIT_MODE);
    while (1) {
        read = LoRa_read(_LoRa, RegIrqFlags);
        if (read & 0x08) {
            LoRa_write(_LoRa, RegIrqFlags, 0xFF);
            LoRa_gotoMode(_LoRa, mode);
            return 1;
        }
        if (--timeout == 0) {
            LoRa_gotoMode(_LoRa, mode);
            return 0;
        }
        delay(1);
    }
}

void LoRa_startReceiving(LoRa* _LoRa) {
    LoRa_gotoMode(_LoRa, RXCONTIN_MODE);
}

uint8_t LoRa_receive(LoRa* _LoRa, uint8_t* data, uint8_t length) {
    uint8_t read, number_of_bytes, min = 0;
    for (int i = 0; i < length; i++) data[i] = 0;
    LoRa_gotoMode(_LoRa, STNBY_MODE);
    read = LoRa_read(_LoRa, RegIrqFlags);
    if (read & 0x40) {
        LoRa_write(_LoRa, RegIrqFlags, 0xFF);
        number_of_bytes = LoRa_read(_LoRa, RegRxNbBytes);
        read = LoRa_read(_LoRa, RegFiFoRxCurrentAddr);
        LoRa_write(_LoRa, RegFiFoAddPtr, read);
        min = (length >= number_of_bytes) ? number_of_bytes : length;
        for (int i = 0; i < min; i++) data[i] = LoRa_read(_LoRa, RegFiFo);
    }
    LoRa_gotoMode(_LoRa, RXCONTIN_MODE);
    return min;
}

int LoRa_getRSSI(LoRa* _LoRa) {
    uint8_t read = LoRa_read(_LoRa, RegPktRssiValue);
    return -164 + read;
}

uint16_t LoRa_init(LoRa* _LoRa) {
    if (wiringPiSetupGpio() == -1) return LORA_UNAVAILABLE;
    pinMode(_LoRa->CS_pin, OUTPUT);
    digitalWrite(_LoRa->CS_pin, HIGH);

    pinMode(_LoRa->reset_pin, OUTPUT);
    digitalWrite(_LoRa->reset_pin, HIGH);
    pinMode(_LoRa->DIO0_pin, INPUT);
    if (wiringPiSPISetup(_LoRa->SPI_channel, SPI_SPEED) < 0) return LORA_UNAVAILABLE;

    LoRa_gotoMode(_LoRa, SLEEP_MODE);
    delay(10);

    uint8_t read = LoRa_read(_LoRa, RegOpMode);
    delay(10);
    LoRa_write(_LoRa, RegOpMode, read | 0x80);
    delay(100);

    LoRa_setFrequency(_LoRa, _LoRa->frequency);
    LoRa_setPower(_LoRa, _LoRa->power);
    LoRa_setOCP(_LoRa, _LoRa->overCurrentProtection);
    LoRa_write(_LoRa, RegLna, 0x23);
    LoRa_setTOMsb_setCRCon(_LoRa);
    LoRa_setSpreadingFactor(_LoRa, _LoRa->spredingFactor);
    LoRa_write(_LoRa, RegSymbTimeoutL, 0xFF);

    uint8_t data = (_LoRa->bandWidth << 4) | (_LoRa->crcRate << 1);
    LoRa_write(_LoRa, RegModemConfig1, data);
    LoRa_setAutoLDO(_LoRa);

    LoRa_write(_LoRa, RegPreambleMsb, _LoRa->preamble >> 8);
    LoRa_write(_LoRa, RegPreambleLsb, _LoRa->preamble);

    read = LoRa_read(_LoRa, RegDioMapping1);
    LoRa_write(_LoRa, RegDioMapping1, read | 0x3F);

    LoRa_gotoMode(_LoRa, STNBY_MODE);
    _LoRa->current_mode = STNBY_MODE;
    delay(10);

    read = LoRa_read(_LoRa, RegVersion);
    return (read == 0x12) ? LORA_OK : LORA_NOT_FOUND;
}
