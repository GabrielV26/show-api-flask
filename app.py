import hmac
import math
import os
from datetime import datetime, timedelta

from flask import Flask, jsonify, request
from flask_jwt import JWT, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash

from data import alchemy
from model import episode, show, user


def create_app():
    app = Flask(__name__)
    jwt_secret = os.environ.get("JWT_SECRET_KEY", "").strip()
    if not jwt_secret:
        raise RuntimeError(
            "JWT_SECRET_KEY must be configured in the environment. "
            "Generate a strong random secret and never commit it."
        )

    app.config["SECRET_KEY"] = jwt_secret
    app.config["JWT_SECRET_KEY"] = jwt_secret
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///data.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False
    # Bound request bodies to reduce memory exhaustion risk.
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", "1048576"))

    alchemy.init_app(app)

    def authenticate(username, password):
        if not isinstance(username, str) or not isinstance(password, str):
            return None
        account = user.UserModel.find_by_name(username.strip())
        if not account:
            return None

        stored_password = account.password or ""
        if stored_password.startswith(("pbkdf2:", "scrypt:")):
            try:
                valid = check_password_hash(stored_password, password)
            except (ValueError, TypeError):
                # A corrupt hash must fail closed, not cause an authentication 500.
                app.logger.warning("Invalid password hash for account id=%s", account.id)
                return None
        else:
            # Temporary compatibility path for legacy plaintext passwords.
            # Compare UTF-8 bytes so non-ASCII passwords work consistently.
            valid = hmac.compare_digest(
                stored_password.encode("utf-8"), password.encode("utf-8")
            )
            if valid:
                try:
                    account.password = generate_password_hash(password)
                    alchemy.session.commit()
                except Exception:
                    alchemy.session.rollback()
                    app.logger.exception("Unable to upgrade legacy password hash")
                    return None

        return account if valid else None

    def identity(payload):
        if not isinstance(payload, dict):
            return None
        username = payload.get("identity") or payload.get("user_name")
        if not isinstance(username, str):
            return None
        return user.UserModel.find_by_name(username)

    jwt = JWT(app, authenticate, identity)

    @jwt.jwt_payload_handler
    def make_payload(jwt_identity):
        now = datetime.utcnow()
        return {
            "identity": jwt_identity.name,
            "user_id": jwt_identity.id,
            "user_name": jwt_identity.name,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(hours=1),
        }

    @app.errorhandler(400)
    def bad_request(_error):
        return jsonify({"message": "Requisição inválida."}), 400

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"message": "Corpo da requisição excede o limite permitido."}), 413

    @app.errorhandler(500)
    def internal_error(_error):
        alchemy.session.rollback()
        app.logger.exception("Unexpected internal server error")
        return jsonify({"message": "Erro interno do servidor."}), 500

    @app.route("/", methods=["GET"])
    @jwt_required()
    def home():
        return "API Funcionando", 200

    @app.route("/signup", methods=["POST"])
    def signup():
        request_data = request.get_json(silent=True)
        if not isinstance(request_data, dict):
            return jsonify({"message": "Envie um JSON válido."}), 400

        username = request_data.get("username")
        password = request_data.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            return jsonify({"message": "username e password são obrigatórios."}), 400

        username = username.strip()
        if not username or len(username) > 80:
            return jsonify({"message": "username deve ter entre 1 e 80 caracteres."}), 400
        if len(password) < 12 or len(password) > 1024:
            return jsonify({"message": "password deve ter entre 12 e 1024 caracteres."}), 400

        if user.UserModel.find_by_name(username):
            return jsonify({"message": "Usuário já cadastrado."}), 409

        new_user = user.UserModel(
            name=username,
            password=generate_password_hash(password),
        )
        try:
            new_user.save_to_db()
        except Exception:
            alchemy.session.rollback()
            # Handles a duplicate created concurrently as well as other DB errors.
            if user.UserModel.find_by_name(username):
                return jsonify({"message": "Usuário já cadastrado."}), 409
            app.logger.exception("Unable to create user")
            return jsonify({"message": "Não foi possível criar o usuário."}), 500

        return jsonify({"name": new_user.name}), 201

    @app.route("/show", methods=["POST"])
    @jwt_required()
    def create_show():
        request_data = request.get_json(silent=True)
        name = request_data.get("name") if isinstance(request_data, dict) else None
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
            return jsonify({"message": "Informe um nome de série válido (até 80 caracteres)."}), 400

        new_show = show.ShowModel(name.strip())
        new_show.save_to_db()
        result = show.ShowModel.find_by_id(new_show.id)
        return jsonify(result.json()), 201

    @app.route("/show/<string:name>", methods=["GET"])
    @jwt_required()
    def get_show(name):
        result = show.ShowModel.find_by_name(name)
        if result:
            return jsonify(result.json()), 200
        return jsonify({"message": "Série não encontrada."}), 404

    @app.route("/show/<string:name>/item", methods=["POST"])
    @jwt_required()
    def create_episode_in_show(name):
        request_data = request.get_json(silent=True)
        if not isinstance(request_data, dict):
            return jsonify({"message": "Envie um JSON válido."}), 400

        episode_name = request_data.get("name")
        season = request_data.get("season")
        if not isinstance(episode_name, str) or not episode_name.strip() or len(episode_name.strip()) > 80:
            return jsonify({"message": "Informe um nome de episódio válido."}), 400
        if (
            isinstance(season, bool)
            or not isinstance(season, (int, float))
            or not math.isfinite(season)
            or season < 0
        ):
            return jsonify({"message": "season deve ser um número finito maior ou igual a zero."}), 400

        parent = show.ShowModel.find_by_name(name)
        if not parent:
            return jsonify({"message": "Não existe a série."}), 404

        new_episode = episode.EpisodeModel(
            name=episode_name.strip(), season=season, show_id=parent.id
        )
        new_episode.save_to_db()
        return jsonify(new_episode.json()), 201

    with app.app_context():
        # Creates missing tables only; this does NOT migrate existing schemas.
        alchemy.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    debug_enabled = os.environ.get("FLASK_DEBUG", "false").strip().lower() in {
        "1", "true", "yes", "on"
    }
    app.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=debug_enabled,
    )
