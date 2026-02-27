# SPNEGO Nginx Demo

Минимальная демонстрация Kerberos/SPNEGO аутентификации. **Nginx** выполняет SPNEGO, backend только отображает данные. Без Python GSSAPI, без компиляции — только apt и pip. Проверено на Debian 13 (Trixie).

## Архитектура

```
[Браузер] → [Nginx + auth_spnego] → [FastAPI]
                    ↓
              keytab, krb5.conf
```

- Nginx с модулем `libnginx-mod-http-auth-spnego` — Kerberos-аутентификация
- FastAPI — показывает заголовки и `X-Remote-User`

---

## 1. Подготовка на контроллере домена (AD)

### 1.1. Сервисная учётка

```powershell
New-ADUser -Name "svc-spnego-demo" `
  -SamAccountName "svc-spnego-demo" `
  -UserPrincipalName "svc-spnego-demo@DOMAIN.LOCAL" `
  -AccountPassword (ConvertTo-SecureString "ПАРОЛЬ" -AsPlainText -Force) `
  -Enabled $true -PasswordNeverExpires $true
```

### 1.2. AES-шифрование (обязательно)

```powershell
Set-ADUser svc-spnego-demo -KerberosEncryptionType AES128,AES256
```

### 1.3. Регистрация SPN

Замени `app.example.com` на свой FQDN:

```powershell
setspn -S HTTP/app.example.com svc-spnego-demo
```

### 1.4. Генерация keytab

```powershell
ktpass -princ HTTP/app.example.com@DOMAIN.LOCAL `
  -mapuser DOMAIN\svc-spnego-demo `
  -pass ПАРОЛЬ `
  -crypto AES256-SHA1 `
  -ptype KRB5_NT_PRINCIPAL `
  -out C:\spnego-demo.keytab
```

Скопировать keytab на Linux-сервер.

### 1.5. DNS

A-запись: `app.example.com` → IP сервера.

---

## 2. Установка на Linux-сервере

### 2.1. Зависимости

```bash
apt install libnginx-mod-http-auth-spnego krb5-user chrony
systemctl enable chrony && systemctl start chrony
```

**Важно:** Kerberos требует синхронизации времени (допуск ~5 мин). Без NTP — 403. Проверить: `timedatectl status`.

### 2.2. krb5.conf

Скопировать в стандартное место:

```bash
sudo cp krb5.conf.example /etc/krb5.conf
# отредактировать: default_realm, kdc, domain_realm
```

Nginx читает `/etc/krb5.conf` по умолчанию.

### 2.3. Keytab

Обычно кладут в `/etc/krb5.keytab` или `/etc/nginx/`. Права: владелец root, группа www-data, режим 640 — только nginx (www-data) может читать:

```bash
sudo chown root:www-data /etc/krb5.keytab
sudo chmod 640 /etc/krb5.keytab
```

### 2.4. Nginx server block

Скопировать `nginx.conf.example` в `/etc/nginx/sites-available/`, поправить:

- `server_name` — твой FQDN
- `auth_gss_keytab` — путь к keytab (дефолта нет, обычно `/etc/krb5.keytab`)
- `auth_gss_format_full 1` — чтобы `X-Remote-User` содержал `user@REALM` вместо только `user`

Включить:

```bash
sudo ln -s /etc/nginx/sites-available/app.example.com /etc/nginx/sites-enabled/
```

### 2.5. Python backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2.6. Запуск

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8080
```

### 2.7. Перезагрузка Nginx

```bash
nginx -t && sudo systemctl reload nginx
```

---

## 3. Настройка браузеров на доменных ПК

Без этого браузер не отправит Kerberos-тикет.

### Chrome / Edge (реестр, cmd от админа)

```cmd
reg add "HKLM\SOFTWARE\Policies\Google\Chrome" /v AuthServerAllowlist /t REG_SZ /d "app.example.com" /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v AuthServerAllowlist /t REG_SZ /d "app.example.com" /f
```

### GPO (централизованно)

```
Computer Configuration → Administrative Templates → Windows Components →
  Internet Explorer → Internet Control Panel → Security Page →
  Site to Zone Assignment List
```

Добавить: `app.example.com` = `1` (Local Intranet)

### Firefox

`about:config` → `network.negotiate-auth.trusted-uris` → `app.example.com`

### Проверка

`chrome://policy` → в списке должно быть `AuthServerAllowlist` = `app.example.com`

---

## 4. Проверка

### С сервера (без Kerberos — ожидается 401)

```bash
curl -vk -H "Host: app.example.com" https://127.0.0.1/
```

Должен быть заголовок `WWW-Authenticate: Negotiate`.

### С доменного ПК

Открыть в браузере: `https://app.example.com/`

Должна отобразиться страница с `X-Remote-User` и заголовками.

---

## 5. Диагностика

| Симптом | Причина | Решение |
|---------|---------|---------|
| 403 Forbidden при 401→403 в access.log | Время на хосте рассинхронизировано (Kerberos допускает ~5 мин) | chrony, см. 2.1 |
| 403 Forbidden, backend молчит | www-data не читает keytab | `chown root:www-data`, `chmod 640` |
| Браузер не шлёт тикет | Сайт не в AuthServerAllowlist | Проверить `chrome://policy` |

### Логи

```bash
tail -50 /var/log/nginx/error.log
journalctl -u nginx -n 20 --no-pager
```

---

## 6. Структура проекта

```
ce-spnego-nginx-demo/
├── app/
│   ├── main.py              # FastAPI — отображает заголовки
│   └── __init__.py
├── nginx.conf.example       # Пример server block
├── krb5.conf.example        # Пример конфига Kerberos
├── requirements.txt
├── .gitignore
└── README.md
```
