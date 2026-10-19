# Checklist de revisão DDD / Clean Architecture

O script `check_structure.py` cobre estrutura de pastas e imports. Esta checklist cobre o que só leitura de código revela. Use nos arquivos que o script apontou e nos que foram alterados recentemente.

## Domínio

- [ ] **Entidades têm comportamento.** Uma classe só com atributos e getters/setters, com a regra espalhada em use cases, é uma entidade anêmica. Mova a regra para a entidade.
- [ ] **Entidades protegem invariantes.** Estado inválido deve ser impossível de construir ou de alcançar (validação no construtor ou em métodos de negócio).
- [ ] **Identidade explícita.** Entidades comparam por identidade (id), não por todos os atributos.
- [ ] **DTOs não carregam regra.** Se um DTO tem `if` de negócio, o código pertence a uma entidade.
- [ ] **Sem tipos de transporte no domínio.** Nada de request/response de framework, modelos ORM ou serializers dentro de `entities/`.
- [ ] **Linguagem ubíqua.** Nomes de classes e métodos usam o vocabulário do negócio (ex.: `ConcessionRequest`, `approve`), não termos técnicos (`Manager`, `Helper`, `Data`).

## Interfaces (contratos)

- [ ] Toda interface em `domain/interfaces/<x>/` tem ao menos uma implementação no lugar correspondente (`usecases` → `application/usecases`, `gateways` → `application/gateways`, `adapters` → `infra/adapters`).
- [ ] Toda implementação em `application/usecases`, `application/gateways` e `infra/adapters` declara qual interface implementa.
- [ ] Interfaces só têm assinatura, sem lógica.

## Application

- [ ] Um use case representa uma intenção do usuário/sistema, com um método público claro (por exemplo `execute`).
- [ ] Use case recebe dependências por construtor, tipadas pelas **interfaces** do domínio, nunca pelas classes concretas.
- [ ] Use case não conhece HTTP (status code, headers, request) nem detalhes de banco.
- [ ] Gateways traduzem formatos externos para DTOs/entidades do domínio, para que o formato do sistema externo não vaze para dentro.

## Infra

- [ ] Controllers são finos: validam entrada, chamam um use case, convertem resultado em resposta. Regra de negócio num controller deve ir para entidade ou use case.
- [ ] Nenhum controller instancia adapters ou use cases diretamente; recebe tudo via `di/`.
- [ ] `di/` é o único ponto que importa implementações concretas para montá-las.
- [ ] Exceções de infra são convertidas em erros de domínio/aplicação antes de subir, ou mapeadas para resposta HTTP em um único lugar (`exceptions/`).
- [ ] Configuração lida de ambiente em `setup/` ou `application/configuration/`, nunca com `os.environ` espalhado pelo domínio.

## Testes

- [ ] Teste unitário de domínio não usa mock de infra (se precisou, o domínio está acoplado).
- [ ] Teste unitário de use case usa fakes/mocks das **interfaces** do domínio.
- [ ] Cada camada nova tem testes em `tests/unitary/<camada>/`.
- [ ] Testes de integração ficam em `tests/integration/` e sobem a aplicação montada.

## Sinais de alerta rápidos

| Sintoma | Provável causa |
|---|---|
| `import requests`/`sqlalchemy`/`fastapi` em `domain/` | Detalhe técnico vazou para o núcleo |
| Use case com muitos `if status_code ==` | Camada HTTP vazou para application |
| Controller com mais de ~30 linhas de lógica | Regra de negócio no lugar errado |
| Pasta `utils/`, `helpers/`, `common/` na raiz de uma camada | Falta de um conceito de domínio ou de camada definida |
| Teste de domínio que precisa de banco ou rede | Domínio acoplado à infra |