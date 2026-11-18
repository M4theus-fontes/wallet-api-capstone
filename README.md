# Wallet API | Capstone Self-Testing CI

API acadêmica de carteira digital em Python, FastAPI, SQLAlchemy e SQLite.
O [relatório técnico](RELATORIO_TECNICO.md) apresenta os requisitos, as decisões
de implementação, o histórico de TDD e os resultados medidos.

Veja a [conferência da entrega](ENTREGA.md) para os links das evidências e a
pendência de revisão independente do pull request.

## Executar no Windows

Abra o PowerShell na pasta deste README. Use Python 3.12.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn src.main:app --port 8000
```

Abra [Swagger](http://127.0.0.1:8000/docs). Crie duas contas em
`POST /accounts` com `{"owner":"Ana","initial_balance":"100.00"}` e
`{"owner":"Bia","initial_balance":"0.00"}`. Em `POST /transfers`, use os IDs
retornados em `source_id` e `destination_id`, envie `"amount":"25.00"` e
`"idempotency_key":"demo-001"`. Repita o envio e confira o mesmo ID com
`created: false`. Consulte o saldo e o extrato de cada conta.

## Rodar as verificações

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests scripts performance
.\.venv\Scripts\python.exe -m pytest --cov=src --cov-branch --cov-report=term-missing --cov-report=xml:coverage.xml --junitxml=junit.xml
.\.venv\Scripts\python.exe scripts/check_coverage.py coverage.xml
```

## Demonstrar o webhook

Em um terminal separado, inicie `.\.venv\Scripts\python.exe -m uvicorn scripts.mock_antifraud:app --port 8001`.
No terminal da API, defina `$env:ANTIFRAUD_WEBHOOK_URL = "http://127.0.0.1:8001/webhook"` antes de iniciar
a aplicação. O gateway responde HTTP 202 para notificações válidas e registra
a requisição no log do servidor. Cada nova transferência gera uma tentativa.

## Repetir a carga

Use uma base dedicada. Antes de iniciar a API, defina
`$env:DATABASE_URL = "sqlite:///./wallet-carga.db"`. Mantenha a configuração
opcional do webhook desativada para comparar os tempos com a medição entregue.

```powershell
.\.venv\Scripts\python.exe -m locust -f performance/locustfile.py --headless -u 50 -r 50 -t 60s --stop-timeout 10 --host http://127.0.0.1:8000 --csv carga-local
.\.venv\Scripts\python.exe scripts/check_load.py carga-local_final.csv 1 2
```

O último comando pressupõe uma base vazia. Use os dois IDs impressos pelo
Locust se já houver contas cadastradas. A primeira onda é liberada após os
50 usuários ficarem prontos. Em seguida, o Locust mantém a carga até o fim da
janela. Os usuários disputam saldo no mesmo par de contas.

## Entregar com o histórico Git

O ZIP contém o código e `wallet-historico.bundle`. Para restaurar os commits,
execute **na pasta que contém o bundle**:

```powershell
git clone wallet-historico.bundle wallet-api
cd wallet-api
git log --graph --all --oneline
```

No GitHub, crie um repositório vazio e ajuste o remoto para a URL criada. O
bundle atual aponta para um arquivo local como origem.

```powershell
git remote set-url origin https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git
git push -u origin main
```

Depois da primeira execução da CI, configure a proteção de `main` para exigir
pull request, uma aprovação, a verificação `quality` e bloqueio de bypass.
Mantenha merges habilitados para preservar o histórico de integração. Para a
evidência remota do barema, registre no relatório a URL da execução, a regra
ativa e os links de PRs revisados no repositório da equipe.
