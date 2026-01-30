#!/usr/bin/env python3
"""
Мониторинг 1gb.ru API для Zabbix
Версия: 1.0 (продакшен)
"""

import sys
import os
import json
from datetime import datetime
import requests
from requests.exceptions import RequestException

# === Настройки ===
TOKEN_FILE = "/etc/1gb/token"
LOG_FILE = "/var/log/1gb/monitor.log"
API_BASE = "https://www.1gb.ru/api"
TIMEOUT = 10

# === Отказоустойчивое логирование ===
def log_message(level, message):
    """Пишет в лог-файл если есть права, иначе в stderr. Не влияет на основной вывод."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"{timestamp} [{level}] {message}\n"
    
    # Пытаемся записать в файл
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line)
    except (PermissionError, OSError, IOError):
        # Нет прав на запись — пишем в stderr (zabbix_agent2 перехватит)
        print(log_line.strip(), file=sys.stderr)

def read_token() -> str:
    """Чтение токена из защищённого файла (без излишней проверки прав)"""
    try:
        if not os.path.exists(TOKEN_FILE):
            log_message("ERROR", f"Файл токена не найден: {TOKEN_FILE}")
            sys.exit(1)
        
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            token = f.read().strip()
        
        if not token:
            log_message("ERROR", "Токен пустой")
            sys.exit(1)
        
        return token
    except Exception as e:
        log_message("ERROR", f"Ошибка чтения токена: {e}")
        sys.exit(1)

def api_request(endpoint: str, token: str) -> list:
    """Выполнение запроса к API 1gb.ru (всегда возвращает список)"""
    url = f"{API_BASE}{endpoint}"
    params = {"_token_": token}
    
    try:
        response = requests.get(url, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else [data]
    except RequestException as e:
        log_message("ERROR", f"Ошибка сети/таймаут {endpoint}: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        log_message("ERROR", f"Ошибка парсинга JSON от {endpoint}: {e}")
        sys.exit(1)
    except Exception as e:
        log_message("ERROR", f"Неизвестная ошибка запроса {endpoint}: {e}")
        sys.exit(1)

def get_billing_info(token: str) -> dict:
    """Получение финансовой информации"""
    billing_list = api_request("/billing/info", token)
    if not billing_list:
        log_message("ERROR", "Пустой ответ от /billing/info")
        sys.exit(1)
    
    billing = billing_list[0]
    
    # Баланс
    balance_str = billing.get("balance", "0")
    try:
        balance = float(balance_str.replace(",", "."))
    except (ValueError, AttributeError):
        balance = 0.0
    
    # Дата следующей оплаты
    days_to_payment = None
    next_payment_str = billing.get("__expires", "")
    if next_payment_str and next_payment_str != "00.00.0000":
        try:
            next_payment_date = datetime.strptime(next_payment_str, "%d.%m.%Y")
            days_to_payment = (next_payment_date - datetime.now()).days
        except (ValueError, TypeError):
            pass
    
    # Сумма платежа
    payment_amount_str = billing.get("__period_price", "0")
    try:
        payment_amount = float(payment_amount_str)
    except (ValueError, AttributeError):
        payment_amount = 0.0
    
    return {
        "balance": balance,
        "days_to_payment": days_to_payment,
        "payment_amount": payment_amount
    }

def get_domains(token: str) -> list:
    """Получение списка доменов с фильтрацией"""
    domains_raw = api_request("/dns/list", token)
    domains = []
    now = datetime.now()
    
    for d in domains_raw:
        # Только основные домены (type=2)
        if d.get("type") != "2":
            continue
        
        # Исключаем делегированные домены
        if d.get("pay") == "0" and d.get("sid_reg") == "-1":
            continue
        
        # Исключаем технические домены
        zone = d.get("zone", "").strip()
        if not zone or zone.endswith(".1gb.ru") or zone == "1gb.ru":
            continue
        
        # Убираем точку в начале (если есть)
        if zone.startswith("."):
            zone = zone[1:]
        
        # Основной способ: дата из v2_expires
        days_left = None
        expires_raw = d.get("v2_expires", "0000-00-00 00:00:00")
        if expires_raw != "0000-00-00 00:00:00":
            try:
                expires_date = datetime.strptime(expires_raw, "%Y-%m-%d %H:%M:%S")
                days_left = (expires_date - now).days
            except (ValueError, TypeError):
                pass
        
        # Резервный способ: последнее продление + 1 год
        if days_left is None:
            last_prolong = d.get("last_prolong_service", "0000-01-01 00:00:00")
            if last_prolong not in ["0000-01-01 00:00:00", "0000-00-00 00:00:00", "2000-01-01 00:00:00"]:
                try:
                    prolong_date = datetime.strptime(last_prolong, "%Y-%m-%d %H:%M:%S")
                    expires_date = prolong_date.replace(year=prolong_date.year + 1)
                    days_left = (expires_date - now).days
                except (ValueError, TypeError):
                    pass
        
        if days_left is not None:
            domains.append({"zone": zone, "days_left": days_left})
    
    return domains

def main():
    if len(sys.argv) < 2:
        print("Использование: 1gb-monitor.py <balance|days|amount|domains|all>", file=sys.stderr)
        sys.exit(1)
    
    action = sys.argv[1]
    token = read_token()
    
    try:
        if action == "balance":
            billing = get_billing_info(token)
            # Только число в stdout — критично для Zabbix
            print(f"{billing['balance']:.2f}")
        
        elif action == "days":
            billing = get_billing_info(token)
            days = billing['days_to_payment'] if billing['days_to_payment'] is not None else -1
            print(days)
        
        elif action == "amount":
            billing = get_billing_info(token)
            print(f"{billing['payment_amount']:.2f}")
        
        elif action == "domains":
            domains = get_domains(token)
            for d in domains:
                # Формат: домен|дни — для простого парсинга в Zabbix
                print(f"{d['zone']}|{d['days_left']}")
        
        elif action == "all":
            billing = get_billing_info(token)
            domains = get_domains(token)
            
            print(f"balance={billing['balance']:.2f}")
            print(f"days_to_payment={billing['days_to_payment'] if billing['days_to_payment'] is not None else -1}")
            print(f"payment_amount={billing['payment_amount']:.2f}")
            
            for d in domains:
                print(f"domain:{d['zone']}={d['days_left']}")
        
        else:
            log_message("ERROR", f"Неизвестное действие: {action}")
            print(f"Неизвестное действие: {action}", file=sys.stderr)
            sys.exit(1)
    
    except SystemExit as e:
        # sys.exit() уже обработан — пропускаем
        raise
    except Exception as e:
        log_message("CRITICAL", f"Необработанное исключение: {e}")
        print(f"CRITICAL: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
