ЛЮБИТЕЛЬСКИЙ проект по сбору данных на Raspberry Pi 4 и системе датчиков на мк STM32f103c8t6
Код для сенсоров смотри https://github.com/MaratMakarchik/STM32-data-collection-system

Краткий гайд по настройки:
    1.Подключить модуль LoRa sx1278 к Raspberry pi 4:
        -3v3 = 1
        -GND = 6
        -reset_pin = 25
        -DIO0_pin = 17
        -SPI_channel0:
             CS_pin = 8
             MISO_pin = 9 
             MOSI_pin = 10 
             SCLK_pin = 11
    2.Выполнить в командной строке  git clone https://github.com/MaratMakarchik/LoRa_Python.git
    3.Создать в дириктории окружение python -m venv .venv и активировать его source .venv/bin/activate
    4.Установить дополнительные пакеты коммандами:
        -Для работы Telegramm бота:
            pip install aiogram python-dotenv
        -Для работы с LoRa:
            cd WiringPi
            ./build debian
            mv debian-template/wiringpi-3.x.deb .
            sudo apt install ./wiringpi-3.x.deb
    5.Создать Telegramm, получить токен, создать в python/bot файл .env, в него вставить
      BOT_TOKEN = "ВАШ ТОКЕН"
      Произвести настройку системы, добавив в этот же файл следующие поля
        SURVEY_TIME = 5*60
        SURVEY_TIME = 5*60
        BEACON_TIME = 2*60
        CONFIG_SENSOR = 'sensor.conf'
        ERROR_MESSAGE_LOG = 'error_message.log'
        (можно менять выводные файлы или времена опроса)
    7.Создать файла sensor.conf и заполнить по следующему образцу: номер_сенсора@расположение_сенсора
    8.Для автономной работы системы необходимо создать сервис sudo nano /etc/systemd/system/LoRa_script.service, вставить
        [Unit]
        Description=automatic data collection from LoRa

        [Service]
        ExecStart=ПУТЬ_К_ПРОЕКТУ/.venv/bin/python ПУТЬ_К_ПРОЕКТУ/start.py
        WorkingDirectory=ПУТЬ_К_ПРОЕКТУ/
        Restart=always
        User=ИМЯ_ПОЛЬЗОВАТЕЛЯ

        [Install]
        WantedBy=multi-user.target
    Выполнить:
        sudo systemctl daemon-reload
        sudo systemctl enable LoRa_script.service
        sudo systemctl start LoRa_script.service
    9.Для более точных настроек ознакомьтесь с исходным кодом)

Список изменений:

feature/bdrv:
    Разработка БДРВ:
        fix7:
            -добавлена сборка си файлов
            -добавлено создание и заполнение БД
            -добавлен разноцветный вывод информации в терминал
            -проведены УСПЕШНЫЕ тесты ПО
        fix8:
            -добавлен запуск lora_app из main.py
            -добавлен постоянный опрос датчиков и вывод полученных данных в терминал
            -мелкие улучшения по работе терминальной программы
            -проведены УСПЕШНЫЕ тесты ПО
        fix9:
            -добавлена фильтрация входящих сообщений
            -добавлен занос данных в бд
            -добавлен вывод не прошедших проверку данных в error_message.log
            -проведены УСПЕШНЫЕ тесты ПО

feature/bot:
    Разработка Telegramm бота:
        fix1:

order1:
    Переработка структуры проекта:
        fix1:
            -Строгое разделение дирикторий по функциональному назначению:
                -python/bdrv - работа с БД, опрос LoRa
                -python/bot - работа с Telegramm bot
                -python/help_fnc - доп функции для удобной отладки
                -python/LoRa - работа с LoRa
            -Добавлена входная точка в корне проекта start.py 
            -Добавлен телеграмм бот

fixpriblem:
    Решение различных накопившихся проблем:
        fix1:
            -Исправлено время в БД с UTC+0 на локальное с сервера 
            -Добавлена настройка основных параметров системы в .env
