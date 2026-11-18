# Conferência da entrega

Repositório: https://github.com/M4theus-fontes/wallet-api-capstone

## Evidências disponíveis

| Item do enunciado | Onde conferir |
|---|---|
| Requisitos e arquitetura | `RELATORIO_TECNICO.md`, seções 2 e 3 |
| Histórico com dois merges e ciclos Red-Green-Refactor | Seção 5, `git log --graph --all --oneline` e `evidencias/tdd-*.txt` |
| Testes unitários, integração, mocks, stubs e banco em memória | `tests/unit`, `tests/integration` e `tests/conftest.py` |
| E2E com HTTP real | `tests/e2e/test_http_server.py` inicia Uvicorn e verifica o fluxo completo |
| CI e controle de cobertura | `.github/workflows/ci.yml`, `scripts/check_coverage.py` e `tests/unit/test_coverage_gate.py` |
| Primeira CI aprovada | https://github.com/M4theus-fontes/wallet-api-capstone/actions/runs/44347880853 |
| Proteção da main | Regra 86534402: PR, uma aprovação, `quality` e sem bypass |
| Carga com 50 usuários e primeira onda sincronizada | `performance/locustfile.py`, `evidencias/carga_final.csv`, `evidencias/carga.log` e seção 7 do relatório |
| Conciliação após carga | `evidencias/carga-saldos.txt`: 23.324 débitos e créditos, zero falhas |

## Pendência que depende de outra pessoa

O trabalho está sendo feito individualmente. O pull request precisa de uma
revisão independente válida antes do merge. Os dois merges do bundle são
locais e não comprovam revisão no GitHub. Solicitar ao professor orientação
para a avaliação desse requisito em entrega individual. Não apresentar a
atividade como integralmente concluída enquanto essa pendência permanecer.

Após a aprovação e o merge, registrar o link da revisão no relatório, conferir
a execução da CI em `main` e entregar o link do repositório com o relatório.
Usar merge commit para preservar o histórico de integração.

## Reprodução no Windows

Na pasta do projeto, com Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ruff check src tests scripts performance
.\.venv\Scripts\python.exe -m pytest --cov=src --cov-branch --cov-report=xml:coverage.xml --junitxml=junit.xml
.\.venv\Scripts\python.exe scripts/check_coverage.py coverage.xml
```

O README contém as instruções de demonstração da API, do webhook e da carga.
