# Relatório técnico | Wallet API

## 1. Objetivo e escopo

O microsserviço mantém contas digitais e permite conciliar cada transferência
com um débito na origem e um crédito no destino. A entrega inclui API REST,
suítes automatizadas, pipeline de integração contínua e medição de concorrência
em ambiente local.

## 2. Especificação de requisitos (SRS)

| ID | Requisito funcional | Critério de aceitação |
|---|---|---|
| RF-01 | Criar conta digital | `POST /accounts` retorna 201 para titular válido e saldo inicial entre zero e R$ 9.999.999.999,99, com até duas casas decimais. |
| RF-02 | Consultar saldo | `GET /accounts/{id}` retorna titular e saldo atual. Conta inexistente retorna 404. |
| RF-03 | Transferir valores | `POST /transfers` registra a transferência, atualiza os dois saldos e grava dois lançamentos. Origem e destino devem ser diferentes. |
| RF-04 | Rejeitar operações inválidas | Saldo insuficiente, conta inexistente ou estouro do limite de destino devolvem 400 e preservam os saldos e extratos. |
| RF-05 | Processar reenvios com idempotência | A mesma chave com o mesmo conteúdo devolve o ID existente e `created: false`. Alterar os dados com a mesma chave devolve 400. |
| RF-06 | Consultar extrato | `GET /accounts/{id}/statement` aceita `kind=debit\|credit`, `start` e `end`. Os limites de data são inclusivos e instantes sem fuso são interpretados em UTC. |
| RF-07 | Notificar gateway antifraude fictício | Com URL configurada, cada nova transferência tenta enviar um POST com identificador, origem, destino e valor. Reenvios idempotentes preservam a contagem de um envio. |

| ID | Requisito não funcional | Evidência esperada |
|---|---|---|
| RNF-01 | Manter consistência sob concorrência | Com saldo para uma única operação, duas solicitações simultâneas geram somente um débito efetivo. |
| RNF-02 | Aplicar metas de cobertura separadas | Pelo menos 85% de linhas e 80% de branches de todo `src/`. |
| RNF-03 | Automatizar lint e testes | GitHub Actions executa lint, testes unitários, integração, E2E e verificação de cobertura. |
| RNF-04 | Rastrear falhas do pipeline | O job publica XML de cobertura, JUnit e logs mesmo quando uma verificação falha. |
| RNF-05 | Medir comportamento sob concorrência | O Locust dispara uma onda inicial de 50 usuários e registra volume, falhas e latência de transferências. |
| RNF-06 | Proteger a integração ao trunk | Pull requests curtos, revisão e verificação `quality` obrigatória em `main` no repositório da equipe. |

## 3. Arquitetura e consistência

- **Controllers** validam o formato HTTP, normalizam os filtros de data e convertem erros de domínio em respostas HTTP.
- **Domínio** contém modelos de conta, transferência e lançamento e regras monetárias testadas isoladamente.
- **Serviços** coordenam as operações e o gateway. O cadastro aceita um validador injetável e a integração antifraude aceita um notificador injetável.
- **Persistência** usa SQLAlchemy e SQLite. O débito só é aplicado se o saldo atual for suficiente. O crédito só é aplicado se o saldo de destino respeitar o limite. Ambos os saldos, a transferência e os lançamentos são gravados na mesma transação. O SQLite arredonda as atualizações para duas casas decimais e o serviço aplica o limite monetário testado.
- **Idempotência** usa uma chave única no banco. Se duas solicitações disputarem a mesma chave, a transação perdedora reverte alterações e consulta a vencedora. O serviço compara o conteúdo para distinguir reenvio legítimo de conflito.
- **Antifraude** usa timeout de dois segundos e envia após o commit, quando a transferência já existe. Falhas HTTP são registradas em log. O simulador local responde 202 e torna a demonstração reproduzível.

## 4. Pirâmide de testes e Test Doubles

| Camada | Cobertura de cenários |
|---|---|
| Unitária | Valores inválidos, precisão, limite monetário, cálculo de débito e saldo insuficiente. |
| Integração | SQLite em memória para persistência, estorno transacional e precisão. SQLite temporário em disco para exercitar conexões independentes em disputa por saldo e por chave de idempotência. |
| E2E | FastAPI TestClient para cenários de API e `test_http_server.py` para o fluxo completo por TCP/HTTP real contra um subprocesso Uvicorn, com banco temporário exclusivo: cadastro, transferência, reenvio idempotente, saldos, filtros de extrato e saldo insuficiente. |

O **stub** cadastral responde com base em um titular fixo para reproduzir
aceitação e rejeição. O **mock** do notificador verifica uma chamada com a
transferência esperada. O mock do cliente HTTP verifica URL, payload, timeout e
o efeito de uma resposta HTTP 503. Esses testes verificam que uma indisponibilidade
do gateway preserva os saldos já confirmados.

## 5. TDD e controle de versão

A estratégia adotada é **Trunk-Based Development**, com branches curtas
integradas em `main` e commits com prefixos `test`, `fix`, `refactor` e `chore`.

| Ciclo | Red | Green | Refactor |
|---|---|---|---|
| Limite monetário no débito | `04d4360` | `b08f090` | `14a46c7` |
| Filtros de extrato com fusos mistos | `379e101` | `5b2b1ce` | `7e024d2` |

Os logs de cada etapa estão em `evidencias/tdd-*.txt`. O primeiro merge local
(`931ef50`) integra a correção de datas. O segundo integra a branch
`feature/qualidade-capstone`, com o ciclo financeiro, os testes de concorrência,
a CI e o cenário de carga. O bundle permite recuperar os commits e inspecionar
os dois merges com `git log --merges --oneline`.

Os dois merges acima e os ciclos de TDD pertencem ao histórico local importado
do bundle; não representam pull requests revisados no GitHub. O envio inicial
de `main` foi feito antes da criação da proteção de branch. Essa sequência é
registrada explicitamente, pois a proteção atual não valida retroativamente o
histórico anterior.

### Evidências remotas verificadas em 18/11/2026

- Repositório público: [M4theus-fontes/wallet-api-capstone](https://github.com/M4theus-fontes/wallet-api-capstone).
- Primeira CI em `main`: [execução 44347880853](https://github.com/M4theus-fontes/wallet-api-capstone/actions/runs/44347880853), concluída com sucesso no commit `e6cb94c`.
- Artefato dessa execução: `wallet-ci-reports` (ID `14446267900`), com cobertura, JUnit e logs.
- [Regra de proteção da main](https://github.com/M4theus-fontes/wallet-api-capstone/settings/branch_protection_rules/86534402): pull request obrigatório, uma aprovação, check `quality` do GitHub Actions, branch atualizada antes do merge e proibição de bypass inclusive por administradores. Force push e exclusão estão desabilitados. A página de configurações requer acesso administrativo.
- A revisão final adiciona um teste E2E sobre HTTP real e seis casos de teste para os limites de cobertura. As Actions foram atualizadas para versões que usam Node.js 24.

**Pendência de avaliação:** o autor informou que realiza a atividade sozinho.
Ainda é necessária revisão independente do pull request por outra pessoa com
permissão adequada e sua integração pelo fluxo protegido. Não se declara
aprovação ou revisão por equipe enquanto isso não ocorrer. Se a entrega
individual for uma exceção permitida, ela deve ser alinhada com o professor;
não se remove a proteção apenas para contornar essa exigência.

[GitHub Docs sobre proteção de branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

## 6. Integração contínua e cobertura

O workflow é disparado por pushes em `main`, `feature/**` e `hotfix/**`, e por
pull requests direcionados a `main`. O job valida o código com Ruff, executa
as três camadas de teste e compara separadamente os contadores de linhas e
branches do XML. Os limites são aplicados sobre os valores exatos, antes do
arredondamento de exibição. O artefato `wallet-ci-reports` recebe cobertura,
JUnit e os logs das verificações.

A execução local original da entrega registrou **26 testes aprovados**, **98,62% de
linhas (214/217)** e **96,00% de branches (48/50)**. Os relatórios brutos e a saída
dos comandos estão em `evidencias/`.

Na validação complementar em Windows, Python 3.12.10, em 18/11/2026, foram
aprovados **33 testes**, com os mesmos **214/217** pontos de linha e **48/50**
branches cobertos. Ruff e o gate também passaram. O processo Uvicorn do teste
HTTP é encerrado ao final e usa banco isolado. A cobertura informada é a
coletada no processo principal do pytest, sem atribuir cobertura adicional ao
subprocesso. Os seis testes do gate verificam aprovação nos limites exatos,
rejeição de 84,99% de linhas ou 79,99% de branches e relatórios sem instrumentação.

Permanece um aviso de depreciação do uso de `httpx` pelo TestClient da versão
instalada de Starlette; ele não causou falha nos testes. Os relatórios da nova
execução remota ficam no artefato `wallet-ci-reports` do PR correspondente.

## 7. Teste de carga

A medição usou Locust 2.47.0, Python 3.12.14 e Uvicorn local com um processo,
em Debian 13. O arquivo SQLite foi criado para a execução e o webhook ficou
desativado. Os 50 usuários sincronizaram a primeira onda de solicitações e
continuaram por 60 segundos, transferindo R$ 1,00 entre as mesmas duas contas.
Cada chamada usou uma chave de idempotência própria.

| Métrica de `POST /transfers` | Resultado |
|---|---:|
| Usuários concorrentes | 50 |
| Requisições finalizadas | 23.324 |
| Falhas HTTP ou timeout | 0 |
| Taxa de erro | 0,00% |
| Latência média | 27,78 ms |
| Mediana | 10 ms |
| P95 | 110 ms |
| P99 | 240 ms |
| Vazão média | 389,92 req/s |

A origem começou com R$ 1.000.000,00 e terminou com R$ 976.676,00. O destino
começou zerado e terminou com R$ 23.324,00. Os extratos apresentaram 23.324
débitos e 23.324 créditos, em concordância com o total observado pelo cliente.
O Locust encerrou normalmente e o verificador de saldos confirmou a
conciliação. Os dados finais estão em `evidencias/carga_final.csv` e
`evidencias/carga-saldos.txt`.

## 8. Limites da demonstração

As medições representam o cenário local descrito. A aplicação acadêmica usa
SQLite, não autentica clientes e não integra instituições bancárias. O
webhook é de melhor esforço e a falha de entrega é registrada em log.
Uma implantação financeira exigiria representação exata do dinheiro na
persistência, autenticação, controle de acesso e entrega durável de eventos.
