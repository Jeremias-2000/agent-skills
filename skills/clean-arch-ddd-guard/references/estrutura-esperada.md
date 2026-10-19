# Estrutura de referência

`app/` representa a raiz do código da aplicação. O nome do pacote interno depende do tipo de serviço:

- Serviço Python comum: `app/src/` (padrão).
- Backend for Frontend: `app/bff/`.

Use apenas um dos nomes. Ambos contêm as mesmas camadas:

```text
app/
├── src/                         # use bff/ no lugar de src/ se for um BFF
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

Os diretórios dentro de `controllers/` dependem das capacidades do negócio. A árvore pode incluir pastas adicionais; confira a função delas antes de classificá-las como problema.

## Responsabilidades das camadas

- `domain/`: entidades, regras de negócio, DTOs de domínio e contratos; não depende de frameworks nem de outras camadas.
- `application/`: orquestra casos de uso e acessa gateways definidos por contratos do domínio.
- `infra/`: implementa integrações, controllers, injeção de dependências, entrypoints, exceções e bootstrap.
- `tests/`: testes unitários organizados pela camada testada e testes de integração.

As dependências apontam para dentro: `infra` pode depender de `application` e `domain`; `application` pode depender de `domain`; `domain` não depende das outras camadas.

Para validar um BFF, informe `--package-name bff` ao verificador. Sem essa opção, o pacote `src` é usado.