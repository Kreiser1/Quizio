# Quizio

_Веб-приложение для многопользовательских соревнований._

Команда для клонирования:

```
git clone https://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@github.com/Kreiser1/Quizio.git
```

Команда для установки:

```
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

_Необходимо создать и заполнить файл **config.env**_

```
DATABASE_URI=sqlite:///./database.db
TOKEN_SECRET=<hex-string>
AUTH_SECRET=<hex-string>
ADMIN_USERNAME=<username>
ADMIN_PASSWORD=<password>
AUTH_EXPIRATION=1209600
TOKEN_EXPIRATION=600
AUTH_COST=65536
AUTH_COOLDOWN=2.5
IMAGE_SIZE_LIMIT=2097152
QUIZ_SIZE_LIMIT=8388608
FREQUENCY=4.0
DEBUG=FALSE
```

Команда для обновления:

```
git pull
```

Команда для запуска:

```
fastapi dev
```
