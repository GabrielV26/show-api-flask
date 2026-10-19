# show-api-flask

API Flask para cadastro de usuários e gerenciamento de séries e episódios.

## Configuração

1. Crie e ative um ambiente virtual Python.
2. Instale as dependências: `pip install -r requirements.txt`.
3. Configure uma chave JWT forte no ambiente. Exemplo para Linux/macOS:

   ```bash
   export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
   ```

4. Opcionalmente configure `DATABASE_URL`. Sem essa variável, a aplicação usa SQLite local.
5. Inicie com `python app.py`.

A aplicação falha ao iniciar se `JWT_SECRET_KEY` não estiver configurada. O modo debug fica desativado por padrão; use `FLASK_DEBUG=true` somente em desenvolvimento local.

## Segurança de senhas

As senhas novas são armazenadas com hash Werkzeug e nunca retornadas pela API. Para compatibilidade durante a migração, uma senha antiga em texto puro é convertida para hash no primeiro login bem-sucedido. Como o arquivo SQLite antigo foi removido do repositório, configure um banco local novo ou restaure dados por um processo controlado.

**Importante:** a remoção de `data.db` desta versão não apaga o arquivo de commits antigos. Se o banco já foi publicado com dados reais, considere os dados expostos, altere as senhas das contas afetadas e avalie a remoção do histórico com cuidado.
