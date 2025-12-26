#!/usr/bin/env bash
set -e

REPO_URL="https://github.com/blasterss/vpn_bot.git"
INSTALL_DIR="$HOME/vpn_bot"
SERVICE_NAME="vpn_bot.service"

echo "=== Установка vpn_bot ==="

### Проверка sudo ###
if [ "$EUID" -ne 0 ]; then
    echo "Скрипт будет использовать sudo"
    SUDO="sudo"
else
    SUDO=""
fi

### Определение пакетного менеджера ###
if command -v apt >/dev/null; then
    PKG="apt"
elif command -v dnf >/dev/null; then
    PKG="dnf"
elif command -v yum >/dev/null; then
    PKG="yum"
else
    echo "Неподдерживаемый пакетный менеджер"
    exit 1
fi

### Установка зависимостей ОС ###
install_packages() {
    case "$PKG" in
        apt)
            $SUDO apt update
            $SUDO apt install -y git python3 python3-venv python3-pip
            ;;
        dnf)
            $SUDO dnf install -y git python3 python3-virtualenv python3-pip
            ;;
        yum)
            $SUDO yum install -y git python3 python3-virtualenv python3-pip
            ;;
    esac
}

### Проверка и установка ###
if ! command -v git >/dev/null || ! command -v python3 >/dev/null; then
    echo "Устанавливаются git и python3..."
    install_packages
fi

### Клонирование ###
if [ ! -d "$INSTALL_DIR" ]; then
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

### venv ###
if [ ! -d venv ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

### .env ###
echo "==== ВВОД ПАРАМЕТРОВ ===="
echo "Введите параметры конфигурации"
read -s -p "BOT_TOKEN: " BOT_TOKEN
echo ""
read -s -p "SECRET_KEY: " SECRET_KEY


echo "=== ГЕНЕРАЦИЯ .env ==="
cat > .env <<EOF
SCRIPT_PATH=$HOME/openvpn-install.sh
WORKING_DIR=$HOME

BOT_TOKEN=$BOT_TOKEN
SECRET_KEY=$SECRET_KEY
EOF

echo "=== ГЕНЕРАЦИЯ vpn_bot.service ==="
cat > vpn_bot.service <<EOF
[Unit]
Description=VPN Telegram Bot
After=network.target

[Service]
Type=simple
User=${SUDO_USER:-$USER}
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/src/bot.py
CPUQuota=40%
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF


### systemd ###
$SUDO cp $INSTALL_DIR/$SERVICE_NAME /etc/systemd/system/$SERVICE_NAME
$SUDO systemctl daemon-reload
$SUDO systemctl enable $SERVICE_NAME
$SUDO systemctl restart $SERVICE_NAME

echo "=== Установка успешно завершена ==="
