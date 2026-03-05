# Python_supervisory

## Bibliotecas necessárias

Para rodar a aplicação, você precisa instalar:

- `pymcprotocol` (comunicação com PLC Mitsubishi via protocolo MC 3E)

Comando:

```bash
pip install pymcprotocol
```

## Banco de dados

- O cadastro de falhas usa SQLite no arquivo local `faults.db`.
- Não é necessário instalar biblioteca extra para SQLite (já incluso na biblioteca padrão do Python via `sqlite3`).

## Dependências já inclusas no Python

- `tkinter`
- `sqlite3`
- `threading`
- `time`
- `datetime`

> Observação: `tkinter` faz parte da biblioteca padrão do Python, mas em alguns Linux pode ser necessário instalar o pacote do sistema (`python3-tk`).


## Como conectar ao PLC na interface

- Abra a aba **Conexão PLC**.
- Informe **IP** e **porta** manualmente.
- Clique em **Conectar / Iniciar** para iniciar o monitoramento.
- Use **Pausar** para pausar as leituras.
- Após iniciar, o sistema tenta **reconexão automática** em caso de perda de comunicação.
