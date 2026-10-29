# Coletor de imóveis

Projeto Python que consulta páginas de imobiliárias e consolida anúncios de aluguel em `geral.json` e em uma planilha `.xlsx`.

## Requisitos

- Python 3.10 ou superior
- Dependências de `requirements.txt`
- Acesso à internet

Instale as dependências com:

```bash
python3 -m pip install -r requirements.txt
```

## Executar

Na raiz do projeto:

```bash
python3 runner.py
```

Para abrir o painel web local:

```bash
streamlit run app.py
```

O painel permite executar todos os coletores ou uma imobiliária, acompanha a saída do processo em um terminal visual e organiza o histórico por mês.

O runner executa cada módulo de `scripts/` em ordem alfabética, continua mesmo que um coletor falhe e retorna código de erro ao final se houver falhas. Cada coletor persiste novos anúncios em `geral.json` e acrescenta as novas linhas ao arquivo Excel da hora atual.

O caminho padrão do Excel é `/mnt/g/Meu Drive/Aluguel/`. Para usar outra pasta, configure `IMOVEIS_OUTPUT_DIR`, por exemplo:

```bash
IMOVEIS_OUTPUT_DIR="$PWD/saida" python3 runner.py
```

O JSON guarda os IDs e os dados dos anúncios para evitar coletá-los novamente em execuções futuras. Faça cópia desse arquivo antes de removê-lo ou editá-lo manualmente.

## Organização

- `runner.py`: orquestra os coletores e resume falhas.
- `scripts/`: adaptadores específicos para sites com HTML próprio e `catalog_collectors.py`, que trata em conjunto os oito portais com estruturas de cartões compartilhadas.
- `utils/funcs.py`: deduplicação, persistência e exportação para Excel.
- `utils/variables.py`: filtros e configuração dos caminhos.
- `script_teste/` e `teste.py`: experimento separado, não incluído na execução normal.

### Adicionar uma imobiliária

Se o site usar os cartões `.imovelcard` ou o layout de cartões Tailwind, adicione uma configuração em `PORTAIS_CARD` ou `PORTAIS_TAILWIND` dentro de `scripts/catalog_collectors.py`. Para um HTML diferente, crie um adaptador próprio em `scripts/`; o runner o encontra automaticamente.

Os seletores HTML e os formatos das URLs dependem dos sites de terceiros e podem precisar de atualização quando eles mudarem.
