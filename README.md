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

Para abrir o painel web local, use o iniciador, que chama o Streamlit da `.venv`:

```bash
bash start_app.sh
```

Se a `.venv` já estiver ativada, o comando equivalente é `python -m streamlit run app.py`. Sem ativá-la, use `./.venv/bin/python -m streamlit run app.py`.

### Acessar pela rede doméstica

O painel escuta na porta `8501`. Em uma instalação WSL com rede NAT, abra um PowerShell **como administrador**, execute `.permitir_acesso_rede.ps1` na pasta do projeto e confirme a solicitação do Windows. O script encaminha a porta para o IP atual do WSL e libera acesso TCP `8501` somente pela rede local privada. Ele mostra o endereço a usar no outro computador, por exemplo `http://192.168.5.101:8501`.

O IP do WSL pode mudar ao reiniciar a distribuição. Se isso acontecer, execute o script novamente como administrador.

Em modo de rede espelhada do WSL, o encaminhamento pode não ser necessário, mas a regra do Firewall do Windows continua necessária.

O painel permite executar todos os coletores ou uma imobiliária, consultar os resultados agrupados por imobiliária, acompanha a saída em um terminal no formato tail, organiza o histórico por mês e expõe os erros registrados em `logs_erros.txt`.

O runner executa cada módulo de `scripts/` em ordem alfabética, continua mesmo que um coletor falhe, registra a saída da falha em `logs_erros.txt` e retorna código de erro ao final se houver falhas. Cada coletor persiste novos anúncios em `geral.json` e acrescenta as novas linhas ao arquivo Excel da hora atual.

O caminho padrão do Excel é `/mnt/g/Meu Drive/Aluguel/`. Para usar outra pasta, configure `IMOVEIS_OUTPUT_DIR`, por exemplo:

```bash
IMOVEIS_OUTPUT_DIR="$PWD/saida" python3 runner.py
```

Se a pasta configurada estiver indisponível, as planilhas são salvas em `exports/` na raiz do projeto.

O JSON guarda os IDs e os dados dos anúncios para evitar coletá-los novamente em execuções futuras. Faça cópia desse arquivo antes de removê-lo ou editá-lo manualmente.

## Organização

- `runner.py`: orquestra os coletores e resume falhas.
- `app.py`: painel web para executar e acompanhar as coletas.
- `assets/findimob.svg`: marca do painel, usada como logo e favicon.
- `.streamlit/config.toml`: oculta os controles de desenvolvedor, incluindo “Deploy”.
- `scripts/`: adaptadores específicos para sites com HTML próprio e `catalog_collectors.py`, que trata em conjunto os oito portais com estruturas de cartões compartilhadas.
- `utils/funcs.py`: deduplicação, persistência e exportação para Excel.
- `utils/variables.py`: filtros e configuração dos caminhos.
- `script_teste/` e `teste.py`: experimento separado, não incluído na execução normal.

### Adicionar uma imobiliária

Se o site usar os cartões `.imovelcard` ou o layout de cartões Tailwind, adicione uma configuração em `PORTAIS_CARD` ou `PORTAIS_TAILWIND` dentro de `scripts/catalog_collectors.py`. Para um HTML diferente, crie um adaptador próprio em `scripts/`; o runner o encontra automaticamente.

Os seletores HTML e os formatos das URLs dependem dos sites de terceiros e podem precisar de atualização quando eles mudarem.
