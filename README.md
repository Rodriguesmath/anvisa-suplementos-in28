# Constituintes de Suplementos Alimentares (Anvisa)

Dados extraídos diretamente do [painel Power BI da Anvisa](https://app.powerbi.com/view?r=eyJrIjoiNDU4Y2UxNmEtZjc0Yi00ZTkyLTk3N2EtZTEyZTI5MjdkNzQ2IiwidCI6ImI2N2FmMjNmLWMzZjMtNGQzNS04MGM3LWI3MDg1ZjVlZGQ4MSJ9) "Constituintes Autorizados para Uso em Suplementos Alimentares", que reúne a lista de constituintes da IN 28/2018 e, transitoriamente, aprovações publicadas por RE ainda não incorporadas ao texto consolidado da norma.

## Dados (`data/`)

### `constituintes_suplementos.csv`
Um constituinte autorizado por linha (múltiplas linhas por nome quando há mais de um fabricante/especificação aprovados).

| Coluna | Descrição |
|---|---|
| Constituintes Autorizados | Nome do constituinte |
| CAS | Número CAS, quando aplicável |
| Especificações | Especificação de referência aprovada (geralmente por fabricante) |
| Função | O que o constituinte fornece (nutriente/substância bioativa/enzima) |
| Alegações autorizadas e requisitos para uso da alegação | Alegações permitidas na rotulagem e condições de uso |
| Requisitos de Rotulagem Complementar e outros | Advertências obrigatórias na rotulagem |
| Outras Informações | Notas adicionais (ex. resoluções RE de aprovação transitória) |

### `limites_por_faixa_etaria.csv`
Limites mínimo/máximo por nutriente/substância e faixa etária.

| Coluna | Descrição |
|---|---|
| Categoria | Categoria do nutriente (ex. Minerais, Vitaminas, Lipídeos) |
| Nutriente/Substância Bioativa/Enzima | Nome do nutriente/substância |
| 0 a 6 meses | Limite mínimo/máximo de uso diário. "Não autorizado" — Art. 2º da IN 28/2018 exclui lactentes (0-12 meses) da lista geral; eles têm lista própria (Anexo II), fora do escopo deste painel |
| 7 a 11 meses | Idem acima — ainda dentro da faixa de lactentes excluída pelo Art. 2º |
| 1 a 3 anos | Idem acima — crianças de primeira infância, também excluídas pelo Art. 2º/3º |
| 4 a 8 anos | Limite mínimo/máximo de uso diário para essa faixa |
| 9 a 18 anos | Limite mínimo/máximo de uso diário para essa faixa |
| Maiores 19 anos | Limite mínimo/máximo de uso diário para adultos |
| Lactantes | Limite mínimo/máximo de uso diário para lactantes (mães amamentando, não confundir com "lactentes" = bebês) |
| Gestantes | Limite mínimo/máximo de uso diário para gestantes |
| Observações | Notas adicionais sobre o limite, quando houver |

## Como atualizar os dados

```bash
pip install -r requirements.txt
python src/raspar.py
```

Roda de qualquer diretório, sempre escreve em `data/`. Revise o `git diff` antes de commitar — é assim que se percebe uma atualização real do painel.

Pela aba **Actions** do GitHub também dá pra disparar manualmente (`workflow_dispatch`, `.github/workflows/raspar.yml`): ele roda a raspagem e já commita o `data/` se algo mudou.

## Como a raspagem funciona

O painel é um relatório Power BI embutido (`app.powerbi.com/view`) sem tabela HTML estática — os dados reais vêm de chamadas internas `POST /public/reports/querydata` para `wabi-*.analysis.windows.net`. `src/raspar.py` replica essa chamada diretamente (sem navegador), pedindo cada tabela inteira de uma vez (sem filtro de seleção de linha, com `Window.Count` alto o bastante para cobrir todas as linhas).

A resposta vem num formato comprimido (DSR) com dicionários de valores por coluna e codificação delta linha a linha. `src/dsr_decoder.py` decodifica isso — ver o docstring do módulo para o formato.

### Adicionar uma nova tabela do painel
1. Capture a chamada `querydata` correspondente no DevTools do navegador (aba Rede, filtro `querydata`), salve como HAR.
2. No corpo da requisição, identifique `Entity`, as colunas em `Select` e o `VisualId`.
3. Remova qualquer `Where` de seleção de linha (esses filtros vêm de clique numa linha específica) e aumente `DataReduction.Primary.Window.Count` o suficiente para cobrir todas as linhas da tabela.
4. Adicione uma entrada em `TABELAS` no `src/raspar.py`.

## Correções manuais de dados

O painel da Anvisa tem 2 erros de digitação confirmados contra o texto oficial da IN 28/2018 (DOU) e da IN 102/2021. `src/raspar.py` já corrige isso automaticamente a cada raspagem (ver `CORRECOES_CONSTITUINTES`/`CORRECOES_LIMITES`), então essas correções não somem numa atualização futura:

- **Succinato ácido de D-alfa-tocoferila**: CAS do painel é `893081` (formato inválido); o correto é `4345-03-3`.
- **Ácido Clorogênico** (faixa "Maiores 19 anos"): o painel tem 3 linhas (uma por fonte) com valores inconsistentes entre si; o correto, conforme Anexo III/IV, é `Mínimo: Não estabelecido / Máximo: 400 mg` (máximo com redação dada pela IN 102/2021).

## Fontes usadas na validação
- [IN 28/2018 — texto consolidado (PDF oficial)](https://anexosportal.datalegis.net/arquivos/1874597.pdf)
- [IN 102/2021 — texto oficial (DOU)](https://www.fukumaadvogados.com.br/wp-content/uploads/2021/10/IN-102-2021-Atualiza%C3%A7%C3%A3o-Lista-IN-28_18-Supl-Alim.pdf)
