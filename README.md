# Zabbix Monitoring for 1gb.ru

[![Zabbix 7.0+](https://img.shields.io/badge/Zabbix-7.0%2B-1A8FE3)](https://www.zabbix.com/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Мониторинг баланса аккаунта и сроков регистрации доменов в [1gb.ru](https://www.1gb.ru) через официальное API.

![Zabbix Dashboard Preview](docs/screenshot.png)

## ✨ Возможности

- 📊 Текущий баланс аккаунта
- ⏳ Дней до следующего списания
- 💰 Сумма предстоящего платежа
- 🌐 Автообнаружение доменов (LLD)
- ⚠️ Триггеры по логике:
  - `баланс < сумма_платежа` + `дней_до_оплаты ≤ 30` → **Предупреждение**
  - `баланс < сумма_платежа` + `дней_до_оплаты ≤ 7` → **Критично**
  - `дней_до_истечения_домена ≤ 30/14/7` → **Уведомления о продлении**

## 🛠 Требования

| Компонент | Версия |
|-----------|--------|
| Zabbix Server | 7.0+ |
| Zabbix Agent | 2 (на узле мониторинга) |
| ОС узла | Ubuntu 24.04 LTS |
| Python | 3.12+ |
| Пакеты | `python3-requests` |

## 🚀 Установка

### 1. Настройка узла мониторинга (Ubuntu 24.04)

```bash
# Установка зависимостей
sudo apt update && sudo apt install -y python3 python3-requests zabbix-agent2

# Создание структуры каталогов
sudo mkdir -p /etc/1gb /var/log/1gb /usr/local/bin

# Копирование скриптов
sudo cp scripts/1gb-monitor.py /usr/local/bin/
sudo cp scripts/1gb-lld.py /usr/local/bin/
sudo chmod 755 /usr/local/bin/1gb-*.py

# Сохранение токена API (получить через /api/auth/login)
echo "ВАШ_ТОКЕН" | sudo tee /etc/1gb/token > /dev/null
sudo chmod 640 /etc/1gb/token
sudo chown root:zabbix /etc/1gb/token

# Настройка прав на логи
sudo mkdir -p /var/log/1gb
sudo chown zabbix:zabbix /var/log/1gb
sudo chmod 755 /var/log/1gb

# Конфигурация агента
sudo cp zabbix/userparameter_1gb.conf /etc/zabbix/zabbix_agent2.d/
sudo systemctl restart zabbix-agent2

```

3


