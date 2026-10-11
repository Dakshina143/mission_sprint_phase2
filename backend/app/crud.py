from flask import Blueprint, request

from .errors import ApiError, ok
from .extensions import db
from .validation import INT_MAX, validate


def register_crud(bp, path, Model, spec, *, filters=(), search=(), order=None, label=None,
                  before_save=None, after_save=None, after_delete=None, fk_models=None):
    """Registers list/create/get/update/delete endpoints for a model."""
    label = label or Model.__name__
    fk_models = fk_models or {}

    def get_or_404(id_):
        obj = db.session.get(Model, id_)
        if not obj:
            raise ApiError(f"{label} {id_} not found", 404)
        return obj

    def check_fks(clean):
        for field, M in fk_models.items():
            if clean.get(field) is not None and not db.session.get(M, clean[field]):
                raise ApiError("Validation failed", 422, {field: f"{M.__name__} {clean[field]} does not exist"})

    def list_():
        q = Model.query
        for f in filters:
            v = request.args.get(f)
            if v not in (None, ""):
                col = getattr(Model, f)
                if v == "null":
                    q = q.filter(col.is_(None))
                    continue
                if isinstance(col.type, db.Integer):
                    if not v.isdigit() or int(v) > INT_MAX:
                        raise ApiError("Validation failed", 422, {f: "must be a positive integer"})
                    v = int(v)
                q = q.filter(col == v)
        term = request.args.get("q", "").strip()
        if term and search:
            q = q.filter(db.or_(*[getattr(Model, c).ilike(f"%{term}%") for c in search]))
        q = q.order_by(*(order if order is not None else [Model.id.desc()]))
        return ok([o.to_dict() for o in q.all()])

    def create():
        clean = validate(spec, request.get_json(silent=True))
        check_fks(clean)
        obj = Model(**clean)
        if before_save:
            before_save(obj, None)
        db.session.add(obj)
        db.session.flush()
        if after_save:
            after_save(obj, {}, True)
        db.session.commit()
        return ok(obj.to_dict(), 201)

    def get(id_):
        return ok(get_or_404(id_).to_dict())

    def update(id_):
        obj = get_or_404(id_)
        clean = validate(spec, request.get_json(silent=True), partial=True)
        check_fks(clean)
        old = {k: getattr(obj, k, None) for k in clean}
        for k, v in clean.items():
            setattr(obj, k, v)
        if before_save:
            before_save(obj, old)
        if after_save:
            after_save(obj, old, False)
        db.session.commit()
        return ok(obj.to_dict())

    def delete(id_):
        obj = get_or_404(id_)
        info = obj.to_dict()
        db.session.delete(obj)
        if after_delete:
            after_delete(obj, info)
        db.session.commit()
        return ok({"id": id_, "deleted": True})

    n = path.strip("/").replace("-", "_")
    bp.add_url_rule(f"/{path}", f"{n}_list", list_, methods=["GET"])
    bp.add_url_rule(f"/{path}", f"{n}_create", create, methods=["POST"])
    bp.add_url_rule(f"/{path}/<int:id_>", f"{n}_get", get, methods=["GET"])
    bp.add_url_rule(f"/{path}/<int:id_>", f"{n}_update", update, methods=["PUT", "PATCH"])
    bp.add_url_rule(f"/{path}/<int:id_>", f"{n}_delete", delete, methods=["DELETE"])
