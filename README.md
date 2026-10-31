# Coletor de imóveis

Projeto Python que consulta páginas de imobiliárias e consolida anúncios de aluguel em `geral.json`.

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

Com a .venv ativada, use python serve_local.py. Sem ativá-la, use ./.venv/bin/python serve_local.py.

### Acessar pela rede doméstica

O painel usa a porta 8501. O iniciador start_app.sh abre o proxy HTTP/HTTPS: endereços digitados sem esquema são redirecionados para HTTPS. Em WSL com rede NAT, abra PowerShell como administrador na pasta do projeto e execute .\permitir_acesso_rede.ps1 para encaminhar a porta e liberar a rede privada. Acesse por findimob.local:8501.
O certificado local e assinado pela CA em .tls/findimob-root-ca.crt. No Windows, execute .\\trust_local_ca_windows.ps1 para confiar nela no perfil atual. Em celulares, importe a mesma CA como autoridade confiavel e configure o DNS da rede para findimob.local apontar para o IPv4 do computador.

O IP do WSL pode mudar ao reiniciar a distribuição. Se isso acontecer, execute este script novamente como administrador.

### Inicialização com o Windows e acesso findimob.local

Para iniciar o painel automaticamente quando sua conta entrar no Windows, abra PowerShell como administrador na pasta do projeto e execute .\\configurar_inicializacao.ps1. A tarefa inicia o Streamlit no WSL, atualiza o encaminhamento de rede e adiciona findimob.local ao arquivo hosts deste computador. No próprio computador, use https://findimob.local:8501.


Em modo de rede espelhada do WSL, o encaminhamento pode não ser necessário, mas a regra do Firewall do Windows continua necessária.

O painel permite executar todos os coletores ou uma imobiliária, consultar os resultados agrupados por imobiliária, acompanha a saída em um terminal no formato tail, organiza o histórico por mês e expõe os erros registrados em `logs_erros.txt`.

O runner executa cada módulo de `scripts/` em ordem alfabética, continua mesmo que um coletor falhe, registra a saída da falha em `logs_erros.txt` e retorna código de erro ao final se houver falhas. Cada coletor persiste os anúncios encontrados em `geral.json`.

O JSON guarda os IDs e os dados dos anúncios para evitar coletá-los novamente em execuções futuras. Faça cópia desse arquivo antes de removê-lo ou editá-lo manualmente.

### Contas e segurança

O primeiro acesso usa o usuário admin e a senha provisória admin. A primeira entrada exige cadastrar uma nova senha forte e completar nome, nome de exibição, e-mail e telefone. As senhas são armazenadas com scrypt em um banco SQLite local com permissões restritas; após cinco tentativas inválidas, o identificador fica bloqueado por 15 minutos.

Novos cadastros enviam nome completo, como a pessoa quer ser chamada, e-mail, telefone, senha e foto opcional. O acesso fica pendente até aprovação do administrador. As fotos aceitas são JPEG, PNG ou WebP, limitadas a 2 MB e reprocessadas antes de serem guardadas.

O serviço MySQL84 está instalado no Windows, mas parado. A autenticação usa SQLite local com permissões restritas, sem precisar iniciar ou configurar o MySQL. O painel usa HTTPS com certificado local; importe a CA nos dispositivos e acesse pelo nome findimob.local para validar o certificado.

## Organização

- `runner.py`: orquestra os coletores e resume falhas.
- `app.py`: painel web para executar e acompanhar as coletas.
- `assets/findimob.svg`: marca do painel, usada como logo e favicon.
- `.streamlit/config.toml`: oculta os controles de desenvolvedor, incluindo “Deploy”.
- `scripts/`: adaptadores específicos para sites com HTML próprio e `catalog_collectors.py`, que trata em conjunto os oito portais com estruturas de cartões compartilhadas.
- `utils/funcs.py`: deduplicação e persistência do catálogo JSON.
- `utils/variables.py`: filtros e configuração dos caminhos.
- `script_teste/` e `teste.py`: experimento separado, não incluído na execução normal.

### Adicionar uma imobiliária

Se o site usar os cartões `.imovelcard` ou o layout de cartões Tailwind, adicione uma configuração em `PORTAIS_CARD` ou `PORTAIS_TAILWIND` dentro de `scripts/catalog_collectors.py`. Para um HTML diferente, crie um adaptador próprio em `scripts/`; o runner o encontra automaticamente.

Os seletores HTML e os formatos das URLs dependem dos sites de terceiros e podem precisar de atualização quando eles mudarem.

### Login com Google

O app inclui autenticação Google por OIDC do Streamlit. Copie o modelo em .streamlit/secrets.toml.example para .streamlit/secrets.toml, gere um cookie_secret aleatório e preencha client_id e client_secret do cliente Web no Google Cloud. Cadastros Google novos também aguardam aprovação administrativa.

O redirect_uri precisa apontar para HTTPS em um domínio público que você controla e deve ser cadastrado exatamente no Google Cloud Console. findimob.local não serve como endereço de retorno Google: domínios .local não têm um TLD público válido para OAuth Web. Para autenticação Google a partir do celular, publique um hostname HTTPS válido e acessível pelo celular; o fluxo local permanece disponível por senha.
