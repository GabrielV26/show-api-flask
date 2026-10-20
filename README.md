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

A aplicação falha ao iniciar se `JWT_SECRET_KEY` não estiver configurada. O modo debug fica desativado por padrão; use `FLASK_DEBUG=true` somente em desenvolvimento local. O limite padrão de corpo de requisição é 1 MiB; configure `MAX_CONTENT_LENGTH` conforme a necessidade real da API.

## Segurança de senhas

As senhas novas são armazenadas com hash Werkzeug e nunca retornadas pela API. A compatibilidade com senhas antigas em texto puro é temporária: o hash é atualizado no primeiro login válido. Se a migração falhar, o login é negado e o erro é registrado sem expor a senha. Antes de produção, prefira migrar ou redefinir senhas legadas por um processo controlado e remover o caminho de texto puro.

## Banco de dados e migrações

`db.create_all()` (usado internamente via `alchemy.create_all()`) cria tabelas ausentes, mas **não altera tabelas existentes**. Antes de usar um banco anterior, faça backup, identifique nomes de usuário duplicados e aplique uma migração de esquema explícita para restrições e tamanhos de coluna. Não aponte esta versão para um banco de produção sem revisar a migração e testar uma restauração.

## Testes

Execute localmente com:

```bash
pip install -r requirements.txt
JWT_SECRET_KEY=test-only-secret DATABASE_URL=sqlite:///:memory: pytest -q
```

O GitHub Actions executa os testes em pushes e pull requests. A chave usada nos testes é apenas para CI e nunca deve ser usada em produção.

## Antes de produção

- Configure uma chave JWT única, forte e secreta; armazene-a em um gerenciador de segredos.
- Coloque a API atrás de um servidor WSGI de produção e HTTPS. O servidor de desenvolvimento Flask não é apropriado para produção.
- Adicione limitação de tentativas de login/cadastro no gateway ou aplicação, com armazenamento compartilhado entre instâncias. O limite de tamanho de requisição não substitui rate limiting.
- Revise e planeje a migração do pacote legado `Flask-JWT` / `PyJWT` para uma solução mantida. Faça isso como mudança separada com testes de compatibilidade dos tokens; não foi atualizado automaticamente nesta alteração para evitar quebrar a API sem validação.
- Monitore erros sem registrar senhas, tokens ou cabeçalhos de autenticação.

## Histórico do banco de dados

A remoção de `data.db` da versão atual não apaga versões anteriores do histórico Git. Não foi possível confirmar se o banco histórico continha dados reais. Se houver possibilidade de dados de usuários, trate-os como potencialmente expostos, redefina credenciais afetadas e avalie com cuidado a limpeza do histórico e a rotação de segredos.
