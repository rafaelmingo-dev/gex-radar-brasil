# GEX Radar Brasil — Streamlit Multi-Horizonte

Painel separado do GARCH Radar Brasil, baseado na V21 validada no Google Colab.

## O que o painel faz

- usa arquivos públicos da B3 (Cadastro de Instrumentos, PriceReport e Prêmio de Referência);
- calcula/estima IV, Gamma, Gross Gamma e Net GEX Proxy;
- calcula Call Wall W1/W2/W3 e Put Wall W1/W2/W3;
- mostra **30, 60, 90 e 180 dias simultaneamente**, sem seletor superior de horizonte;
- a tabela principal usa somente Call W1, Put W1 ou confluência Call/Put W1;
- W2/W3 permanecem nos detalhes e gráficos;
- ordena os ativos pela menor distância absoluta a uma Wall W1 em qualquer horizonte;
- mantém Qualidade dos dados por horizonte;
- mostra gráficos de preço B3 COTAHIST com as Walls;
- mantém Net GEX / Strike, Gross Gamma, Vencimentos, Séries, Qualidade e Metodologia;
- Gamma Flip continua apenas interno e não aparece como zona de atenção;
- Probability Engine permanece removido;
- BTC-USD aparece somente como N/D, sem inventar GEX fora da B3.

## Estrutura do projeto

```text
gex-radar-brasil-streamlit/
├── app.py
├── gex_core.py
├── requirements.txt
├── README.md
├── .gitignore
└── .streamlit/
    └── config.toml
```

## Ativos B3 monitorados

PSSA3, BBSE3, CXSE3, BBAS3, EGIE3, ITSA4, EQTL3, ITUB4, BBDC4, CPFE3,
ABEV3, CMIG4, SBSP3, CPLE3, BPAC11, VALE3, B3SA3, GGBR4, PETR4, WEGE3 e BOVA11.

BTC-USD permanece visível apenas para espelhar a lista do GARCH.

## Publicar no GitHub

1. Crie um repositório separado, por exemplo `gex-radar-brasil`.
2. Não altere o repositório do GARCH.
3. Extraia o ZIP deste projeto no computador.
4. No novo repositório, escolha **Add file → Upload files**.
5. Envie os arquivos da pasta preservando `.streamlit/config.toml`.
6. Confirme que `app.py`, `gex_core.py` e `requirements.txt` estão na raiz.
7. Faça o commit.

## Publicar no Streamlit Community Cloud

1. Entre no Streamlit Community Cloud.
2. Escolha **Create app / New app**.
3. Selecione o repositório `gex-radar-brasil`.
4. Branch: `main`.
5. Main file path: `app.py`.
6. Clique em **Deploy**.
7. Na primeira execução, o cálculo pode levar mais tempo porque o app baixa e processa a base B3 dos 21 ativos.

## Atualização

O botão **ATUALIZAR DADOS B3** força uma nova tentativa de localizar a sessão completa mais recente.
A lógica preserva a exigência de Cadastro + PriceReport + Prêmio de Referência na mesma sessão.

## Observações metodológicas

- Net GEX Proxy: calls positivas e puts negativas; não representa dealer Gamma observado.
- Open interest do PriceReport é usado diretamente; o lote de alocação não é multiplicado novamente.
- AMER/EURO indicam estilo de exercício das opções B3, não mercado dos Estados Unidos.
- As Walls são regiões de concentração de Gross Gamma; proximidade não é sinal de compra/venda nem afirma suporte/resistência.
