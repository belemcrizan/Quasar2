# QUASAR2 — visão em português

O QUASAR2 trata a consulta observada como uma medição ruidosa de uma intenção
latente. Em vez de escolher uma única interpretação cedo demais, ele preserva
hipóteses concorrentes, busca evidências para cada uma, atualiza crenças e decide
entre:

- `ANSWER`: responder quando confiança, margem e evidência passam pelos gates;
- `EXPLORE`: fazer uma nova busca autônoma para separar as hipóteses líderes;
- `ASK`: pedir esclarecimento quando a evidência automática não é suficiente.

## Pergunta científica congelada

> Sob degradação controlada da query, hipóteses concorrentes + `EXPLORE`
> aumentam a resolução autônoma correta em comparação com controles compatíveis
> de compromisso único e sem exploração? Em quais regimes vencem, empatam,
> perdem ou precisam perguntar?

A POC não tenta provar que o QUASAR2 é um “motor geral de descoberta”. O código
foi construído para permitir que a hipótese falhe de forma mensurável.

## Executar

```bash
python -m venv .venv
python -m pip install -e .
quasar2 validate
quasar2 demo --domain astronomy --query "The starlight keeps dipping when something crosses the disk" --trace
quasar2 benchmark --config configs/poc.yaml
```

No Windows PowerShell, ative o ambiente com:

```powershell
.\.venv\Scripts\Activate.ps1
```

## O que a POC entrega

- 40 hipóteses e 40 intenções em astronomia e IA;
- 120 queries congeladas (`Q0`, `Q1`, `Q2`);
- 80 documentos, separados entre evidência central e discriminativa;
- BM25, proxy denso por hashing, híbrido e Rewrite+Hybrid;
- ablações `noHyp`, `noExplore`, `noUpdate` e `noAsk`;
- métricas de recuperação, ranking, resolução, abstinência, custo e latência;
- rastreio integral de cada decisão;
- benchmark reproduzível em JSON/CSV e testes automatizados.

## Leitura honesta do resultado atual

O `Full` melhora a recuperação sobre `noHyp` (0,975 contra 0,958) e aumenta a
resolução autônoma correta sobre `noExplore` (0,792 contra 0,742). Porém, não
supera o Hybrid neste corpus sintético fácil (0,975 contra 0,983); o intervalo
pareado inclui zero. Assim, existe um sinal interno favorável aos mecanismos,
mas a tese forte ainda não foi validada.

Esse é exatamente o tipo de resultado que uma POC científica séria deve ser
capaz de revelar.

Para os detalhes, leia o [README principal](README.md) e a
[tese científica](docs/SCIENTIFIC_THESIS.md).

