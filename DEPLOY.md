# Publicar gratuitamente no Streamlit Community Cloud

O ponto de entrada para a hospedagem é `cloud_app.py`. O painel local continua
usando `bash start_app.sh` e seus arquivos SQLite/JSON enquanto `DATABASE_URL`
não estiver definido.

## Configuração da publicação

1. Entre em https://share.streamlit.io e conecte o GitHub.
2. Clique em **Create app**, escolha o repositório privado `fabiofz/find-imob`,
   a branch `codex/hospedagem-gratuita` e o arquivo `cloud_app.py`.
3. Em **Advanced settings**, selecione Python 3.12 e configure os secrets:

```toml
DATABASE_URL = "CONEXAO_POSTGRES_POOLED"
DATABASE_DIRECT_URL = "CONEXAO_POSTGRES_DIRETA"
# Apenas para banco novo, sem a conta administrativa migrada:
# FINDIMOB_ADMIN_PASSWORD = "SENHA_FORTE_EXCLUSIVA"
```

As conexões são obtidas em **Connect** no projeto Neon `find-imob`.
Nunca coloque as conexões, senhas ou arquivos SQLite no GitHub.

4. Clique em **Deploy**. O Streamlit fornece HTTPS e um subdomínio gratuito.
5. Confirme login, resultados, favoritos e uma coleta individual. Reinicie o app
   pelo painel de hospedagem e confira se os dados continuam disponíveis.

O projeto Neon utilizado é `wild-sky-94610276`, branch de produção `main`.
A branch `deployment-validation` contém somente dados de teste.

## Migração dos dados existentes

`migrate_to_cloud.py` copia contas (incluindo hashes das senhas e fotos), avaliações,
catálogo, favoritos, exclusões, parâmetros e histórico da instalação local.
Sessões de login não são copiadas: entre novamente no site publicado.
O script exige banco sem contas e registra um marcador ao concluir para impedir
importações repetidas. Faça a migração antes de abrir o painel público.

```bash
export DATABASE_URL='CONEXAO_POSTGRES'
./.venv/bin/python migrate_to_cloud.py
```

Após migrar, remova `DATABASE_URL` do terminal local para continuar usando os
arquivos locais. A instalação local e a hospedada passam a ter dados independentes.

## Login Google

O login por senha funciona com as contas migradas. Para habilitar Google, adicione
os parâmetros `[auth]` de `.streamlit/secrets.toml.example` aos secrets do Streamlit
e registre o callback HTTPS real no Google Cloud. Não use `findimob.local`.

## Limites

A hospedagem e o banco gratuitos têm limites de uso. Não dependem do computador
local ligado. Coletas de sites externos podem ser bloqueadas pelos próprios sites.
Os coletores novos limitam cada fonte a 30 páginas e registram quando retornam dados
parciais. Os arquivos de execução ativa são temporários; as contas, o catálogo e o
estado do painel ficam no PostgreSQL.

## Validação

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

Para incluir os testes online, forneça `TEST_DATABASE_URL` de um banco isolado.
Não aponte os testes para a produção: eles criam registros artificiais.
