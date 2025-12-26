
# Быстрый старт

Получение установочного скрипта для развертывания бота:

```bash
curl -O https://raw.githubusercontent.com/blasterss/vpn_bot/main/install.sh
chmod +x install.sh
```

Запуск установки бота:

```bash
sudo ./install.sh
```

При установке бота выполняется:  
1. Установка python и git  
2. Клонирование репозитория с ботом  
3. Создание виртуального окружения  
4. Установка зависимостей  
5. Создание файла .env  
    - Вводится токен бота (возьмите свой токен от BotFather)  
    - Вводится секретный ключ для администратора сервера (предоставляет возможность отслеживания активности сервера /__secure_server_activity)  
6. Создание файла vpn_bot.service для systemd  
7. Запуск процесса бота  

После установки бота, есть возможность отслеживать его работу через systemd:
```bash
sudo journalctl -u vpn_bot.service -n 200 --no-pager
```
Для остановки бота:
```bash
sudo systemctl stop vpn_bot.service
```
