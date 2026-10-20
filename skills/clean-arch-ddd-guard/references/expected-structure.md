# Reference structure

`app/` is the application code root. The internal package name depends on the service type:

- Regular Python service: `app/src/` (default).
- Backend for Frontend: `app/bff/`.

Use only one of these names. Both contain the same layers:

```text
app/
├── src/                         # use bff/ instead of src/ for a BFF
│   ├── application/
│   │   ├── configuration/
│   │   ├── gateways/
│   │   └── usecases/
│   ├── domain/
│   │   ├── config/
│   │   ├── dtos/
│   │   ├── entities/
│   │   └── interfaces/
│   │       ├── adapters/
│   │       ├── gateways/
│   │       └── usecases/
│   └── infra/
│       ├── adapters/
│       ├── controllers/
│       ├── di/
│       ├── entrypoints/
│       ├── exceptions/
│       └── setup/
├── tests/
│   ├── integration/
│   │   └── health_check/
│   └── unitary/
│       ├── application/
│       ├── domain/
│       └── infra/
├── requirements.txt
├── requirements_tests.txt
├── pytest.ini
├── logging.conf
├── Dockerfile
└── run.py
```

Directories inside `controllers/` depend on business capabilities. The tree may include additional directories; check their purpose before treating them as a problem.

## Layer responsibilities

- `domain/`: entities, business rules, domain DTOs, and contracts; it does not depend on frameworks or other layers.
- `application/`: orchestrates use cases and accesses gateways defined by domain contracts.
- `infra/`: implements integrations, controllers, dependency injection, entry points, exceptions, and bootstrap.
- `tests/`: unit tests organized by the layer being tested, and integration tests.

Dependencies point inward: `infra` can depend on `application` and `domain`; `application` can depend on `domain`; `domain` does not depend on the other layers.

To validate a BFF, pass `--package-name bff` to the checker. Without this option, the `src` package is used.