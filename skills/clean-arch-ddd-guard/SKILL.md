---
name: clean-arch-ddd-guard
description: Verifica projetos Python contra a convenção de pastas Clean Architecture + DDD desta skill e detecta dependências entre camadas. Use quando o projeto adota esse template, ao auditar sua estrutura ou localizar arquivos. `src/` é o padrão para serviços comuns; `bff/` é reservado a Backend for Frontend.
---

# Guardião de Clean Architecture + DDD

Esta skill valida uma convenção de projeto baseada em Clean Architecture e Domain Driven Design. Use-a quando a equipe tiver adotado esta estrutura e quiser auditar diretórios, imports e posicionamento de testes. Ela não determina que todo backend Python deva usar essas camadas: para orientação geral e escolha proporcional da arquitetura, use `python-backend`.

## Estrutura esperada

A estrutura de referência está em `references/estrutura-esperada.md`, com a responsabilidade de cada pasta. O diretório `app/` é a raiz do código; use um único pacote interno conforme o tipo de aplicação:

```
app/
├── src/                    # serviço Python comum (padrão)
│   ├── application/        configuration/ · gateways/ · usecases/
│   ├── domain/             config/ · dtos/ · entities/ · interfaces/{adapters,gateways,usecases}/
│   └── infra/              adapters/ · controllers/
│                           di/ · entrypoints/ · exceptions/ · setup/
├── tests/
│   ├── integration/health_check/
│   └── unitary/{application,domain,infra}/
├── requirements.txt
├── requirements_tests.txt
├── pytest.ini
├── logging.conf
├── Dockerfile
└── run.py
```

Para projetos BFF, use `bff/` no lugar de `src/`, mantendo as mesmas camadas e subpastas. Na imagem original a árvore aparece truncada (há reticências), então pastas extras não são erro por si só. Trate pasta ou arquivo fora do esquema como *aviso* para confirmar com o usuário. Só pasta ou arquivo obrigatório ausente é *erro*.

Os subdiretórios de `controllers/` representam módulos de negócio e variam por projeto; não são diretórios obrigatórios globais.

## Fluxo de trabalho

### 1. Rode o verificador

O script faz a parte mecânica (existência de pastas, imports entre camadas, frameworks no domínio), que é determinística e não deve depender da sua leitura.

```bash
python <skill-dir>/scripts/check_structure.py <raiz-do-projeto>
```

- `<raiz-do-projeto>` é a pasta `app/` ou a pasta que a contém. O script localiza sozinho.
- `src/` é o padrão para serviços comuns. Para um BFF, acrescente `--package-name bff`.
- Exemplo para um BFF: `python <skill-dir>/scripts/check_structure.py <raiz-do-projeto> --package-name bff`.
- Use `--json` para saída estruturada e `--strict` para tratar avisos como erros (útil em CI).
- O script devolve código de saída 1 quando há erros.

### 2. Interprete o resultado com o critério de DDD

O script não enxerga o que está dentro das classes. Depois dele, leia os arquivos suspeitos e aplique `references/checklist-ddd.md`: entidades anêmicas, regra de negócio vazando para controllers, DTOs no lugar de entidades, contratos sem implementação, entre outros. Vale a pena ler essa checklist sempre que revisar mais do que a estrutura de pastas.

### 3. Reporte de forma acionável

Agrupe por gravidade e sempre diga *onde o arquivo deveria estar* e *por quê*. Formato sugerido:

```
## Resultado
✅ N verificações ok · ❌ N erros · ⚠️ N avisos

## Erros
- `app/src/domain/entities/pedido.py:3` importa `src.infra...`
  → o domínio não pode depender de infra. Crie a interface em `domain/interfaces/adapters/` e injete a implementação via `infra/di/`.

## Avisos
- `app/src/utils/` não faz parte do esquema. Se for helper de domínio, mova para `domain/`; se for técnico, para `infra/`.

## Sugestão de correção
(comandos `mkdir`/`git mv` ou o diff, se o usuário pedir para aplicar)
```

Não mova nem apague arquivos sem o usuário pedir. Proponha o plano e espere confirmação, porque mover arquivos quebra imports e histórico.

### 4. Ao criar código novo em um projeto que adotou este template, escolha a camada antes de escrever

Use esta tabela de decisão:

| Estou criando… | Vai em | Observação |
|---|---|---|
| Regra de negócio, objeto com identidade/comportamento | `domain/entities/` | Python puro, sem frameworks |
| Estrutura de dados que trafega entre camadas | `domain/dtos/` | Sem lógica de negócio |
| Contrato (ABC/Protocol) de um use case, gateway ou adapter | `domain/interfaces/{usecases,gateways,adapters}/` | Só a assinatura |
| Interface de configuração | `domain/config/` | Só o contrato |
| Orquestração de um caso de uso | `application/usecases/` | Implementa uma interface de `domain/interfaces/usecases/` |
| Acesso a sistema externo feito pela aplicação | `application/gateways/` | Implementa uma interface de `domain/interfaces/gateways/` |
| Leitura/carga de configuração da aplicação | `application/configuration/` | |
| Cliente HTTP, banco, fila, SDK externo | `infra/adapters/` | Implementa uma interface de `domain/interfaces/adapters/` |
| Endpoint REST | `infra/controllers/<modulo>/` | Fino: valida entrada, chama use case, formata saída |
| Montagem das dependências | `infra/di/` | Único lugar que conhece todas as implementações |
| Ponto de entrada (app factory, handlers) | `infra/entrypoints/` | |
| Exceção customizada | `infra/exceptions/` | |
| Bootstrap, logging, inicialização | `infra/setup/` | |
| Teste | `tests/unitary/<camada>/` ou `tests/integration/` | Espelha a camada testada |

Se o pedido do usuário não deixar claro onde algo vai, escolha pela tabela, diga a escolha em uma linha e siga em frente.

## Regra de dependência

As setas apontam para dentro: `infra → application → domain`. Quem está dentro nunca conhece quem está fora.

- `domain` não importa `application` nem `infra`, e não importa frameworks (FastAPI, Flask, SQLAlchemy, requests, boto3, pydantic de transporte etc.). Isso mantém o núcleo testável sem subir nada e trocável sem reescrever regra de negócio.
- `application` importa `domain`. Não importa `infra`. Fala com o mundo externo só pelas interfaces do domínio.
- `infra` pode importar `domain` e `application`. É onde as implementações concretas são ligadas (via `di/`).
- `tests/` pode importar qualquer camada, mas cada teste unitário deve ficar na pasta da camada que testa.

O script valida essas regras por análise estática dos `import` (resolvendo também imports relativos).

## Quando o projeto não bate com o esquema

Para serviços comuns, use o pacote `src/` (padrão); para BFFs, use `bff/` e rode o verificador com `--package-name bff`. Se a raiz ou outras convenções forem diferentes, não invente erros em massa. Explique a incompatibilidade e adapte uma cópia de `references/spec.json` com `--spec meu_spec.json`.

## Arquivos da skill

- `scripts/check_structure.py`: verificador (estrutura, dependências, frameworks no domínio, espelhamento de testes).
- `references/estrutura-esperada.md`: árvore completa com a responsabilidade de cada pasta.
- `references/checklist-ddd.md`: checklist de revisão para o que a análise estática não alcança.
- `references/spec.json`: o esquema em formato de dados, usado pelo script (editável).