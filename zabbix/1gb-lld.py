#!/usr/bin/env python3
"""
LLD парсер для 1gb.ru доменов
Преобразует вывод "домен|дни" → валидный JSON для Zabbix
"""

import sys
import json
import subprocess

def main():
    try:
        # Запускаем основной скрипт и читаем вывод
        result = subprocess.run(
            ["/usr/local/bin/1gb-monitor.py", "domains"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode != 0:
            print(f"Ошибка выполнения скрипта: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        
        # Парсим строки вида "домен|дни"
        domains = []
        for line in result.stdout.strip().splitlines():
            if not line or "|" not in line:
                continue
            zone, _ = line.split("|", 1)
            domains.append({"{#DOMAIN}": zone.strip()})
        
        # Формируем валидный LLD JSON
        output = {"data": domains}
        print(json.dumps(output, ensure_ascii=False))
    
    except Exception as e:
        print(f"LLD_ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
