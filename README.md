# feature-flag-service

REST API do zarządzania feature flagami z rollout procentowym i targetowaniem per user/group. Zero zewnętrznych zależności poza FastAPI.

## Strategies

| Strategy | Description |
|---|---|
| `all` | Flag enabled for everyone |
| `percentage` | Deterministic rollout by percentage (MD5 bucket) |
| `users` | Allowlist of specific user IDs |
| `groups` | Enable for specific user groups |

## Run
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## Test
```bash
pytest tests/ -v
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/flags` | Create flag |
| GET | `/flags` | List all flags |
| GET | `/flags/{key}` | Get flag |
| PATCH | `/flags/{key}` | Update flag |
| DELETE | `/flags/{key}` | Delete flag |
| POST | `/flags/{key}/evaluate` | Evaluate for user |
| POST | `/evaluate/batch` | Batch evaluate |
| GET | `/health` | Health check |
```

---

Struktura:
```
feature-flag-service/
├── main.py
├── requirements.txt
├── README.md
└── tests/
    └── test_flags.py
