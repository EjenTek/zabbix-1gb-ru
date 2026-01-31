# Рекомендации по безопасности

## Хранение токена

```bash
# Правильные права:
sudo chown root:zabbix /etc/1gb/token
sudo chmod 640 /etc/1gb/token

# Проверка:
ls -la /etc/1gb/token
# Должно быть: -rw-r----- 1 root zabbix
