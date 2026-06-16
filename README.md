# System Zarządzania Sylabusami

## Uruchamianie

### 1. Przygotowanie środowiska

```bash
cp .env.example .env
# Edytuj .env – wpisz SECRET_KEY i dane dostępowe
```

### 2. Uruchomienie przez Docker Compose

```bash
docker compose up -d
```

Dostępne usługi po starcie:

| Usługa       | URL                        |
|--------------|----------------------------|
| Backend API  | http://localhost:8000/api/docs |
| Frontend     | http://localhost:3000      |
| Grafana      | http://localhost:3001      |
| Prometheus   | http://localhost:9090      |
| MinIO        | http://localhost:9001      |

### 3. Migracje bazy danych

```bash
# Wewnątrz kontenera backend:
docker exec -it sylabus_backend bash

# Inicjalizacja Alembic (pierwsze uruchomienie)
alembic init alembic
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 4. Testy

```bash
docker exec -it sylabus_backend pytest --cov=app tests/
```

## Architektura

```
Frontend (React + TS)
      │  REST API
      ▼
Backend (FastAPI + Python)
      ├── Auth service    – JWT + OAuth2/SSO
      ├── Syllabus service – CRUD + wersjonowanie + diff
      └── Export service  – PDF (WeasyPrint) + DOCX (python-docx)
      │
      ├── PostgreSQL  – dane główne
      ├── Redis       – cache + kolejki Celery
      └── MinIO       – pliki PDF/DOCX
```

## SSO (konto uczelniane)

Ustaw w `.env`:

```env
SSO_ENABLED=true
SSO_CLIENT_ID=<id z uczelnianego IdP>
SSO_CLIENT_SECRET=<secret>
SSO_AUTHORIZATION_URL=https://sso.uczelnia.pl/oauth/authorize
SSO_TOKEN_URL=https://sso.uczelnia.pl/oauth/token
SSO_USERINFO_URL=https://sso.uczelnia.pl/oauth/userinfo
```

Obsługiwane protokoły: OAuth2 Authorization Code (OIDC). 
Dla uczelni z Shibboleth/SAML – wymagana dodatkowa biblioteka `pysaml2`.

## Wersjonowanie sylabusów

Każda zmiana syllabusa tworzy nowy rekord `SyllabusVersion`.  
Stany: `DRAFT → PENDING → APPROVED → ARCHIVED`  
Historia zmian przechowywana w tabeli `syllabus_changes` (diff JSON).

## Walidacja godzin ECTS

- 1 ECTS = 25–30 godzin łącznie
- Suma wag metod oceniania musi wynosić 100%
- Numer semestru: 1–12
