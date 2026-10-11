from datetime import date, datetime, timezone

from .extensions import db


def now():
    return datetime.now(timezone.utc)


def _choices(col, values):
    return db.CheckConstraint(f"{col} IN ({', '.join(repr(v) for v in values)})", name="ck_" + col + "_" + "_".join(values))


PRIORITIES = ("low", "medium", "high", "critical")
MISSION_STATUS = ("planning", "active", "on_hold", "completed")
SPRINT_STATUS = ("planned", "active", "completed")
STORY_STATUS = ("backlog", "in_sprint", "done")
TASK_STATUS = ("todo", "in_progress", "in_review", "done")
BLOCKER_STATUS = ("open", "in_progress", "resolved")
ACTION_STATUS = ("open", "in_progress", "done")


class Base(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now, nullable=False)

    def to_dict(self):
        out = {}
        for c in self.__table__.columns:
            v = getattr(self, c.name)
            out[c.name] = v.isoformat() if isinstance(v, (date, datetime)) else v
        return out


class Mission(Base):
    __tablename__ = "missions"
    __table_args__ = (_choices("priority", PRIORITIES), _choices("status", MISSION_STATUS),
                      db.CheckConstraint("end_date IS NULL OR start_date IS NULL OR end_date >= start_date", name="ck_mission_dates"))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    priority = db.Column(db.String(20), default="medium", nullable=False)
    status = db.Column(db.String(20), default="planning", nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    tasks = db.relationship("Task", backref="mission", lazy="dynamic")
    stories = db.relationship("UserStory", backref="mission", lazy="dynamic")

    @property
    def progress(self):
        total = self.tasks.count()
        if not total:
            return 0
        return round(100 * self.tasks.filter_by(status="done").count() / total, 1)

    def to_dict(self):
        d = super().to_dict()
        d["progress"] = self.progress
        d["task_count"] = self.tasks.count()
        return d


class Sprint(Base):
    __tablename__ = "sprints"
    __table_args__ = (_choices("status", SPRINT_STATUS),
                      db.CheckConstraint("end_date >= start_date", name="ck_sprint_dates"))
    name = db.Column(db.String(200), nullable=False)
    goal = db.Column(db.Text, default="", nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="planned", nullable=False)
    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))
    committed_points = db.Column(db.Integer)  # frozen when the sprint is completed (history)
    delivered_points = db.Column(db.Integer)
    stories = db.relationship("UserStory", backref="sprint", lazy="dynamic")
    tasks = db.relationship("Task", backref="sprint", lazy="dynamic")

    def points(self):
        if self.status == "completed" and self.committed_points is not None:
            return self.committed_points, self.delivered_points
        total = sum(s.story_points for s in self.stories)
        done = sum(s.story_points for s in self.stories if s.status == "done")
        return total, done

    def to_dict(self):
        d = super().to_dict()
        total, done = self.points()
        d.update(total_points=total, completed_points=done, story_count=self.stories.count())
        return d


class UserStory(Base):
    __tablename__ = "user_stories"
    __table_args__ = (_choices("priority", PRIORITIES), _choices("status", STORY_STATUS),
                      db.CheckConstraint("story_points >= 0", name="ck_story_points"))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    acceptance_criteria = db.Column(db.Text, default="", nullable=False)
    priority = db.Column(db.String(20), default="medium", nullable=False)
    story_points = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(20), default="backlog", nullable=False)
    rank = db.Column(db.Integer, default=0, nullable=False)
    mission_id = db.Column(db.Integer, db.ForeignKey("missions.id", ondelete="SET NULL"))
    sprint_id = db.Column(db.Integer, db.ForeignKey("sprints.id", ondelete="SET NULL"))
    tasks = db.relationship("Task", backref="story", lazy="dynamic")


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (_choices("priority", PRIORITIES), _choices("status", TASK_STATUS))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    status = db.Column(db.String(20), default="todo", nullable=False)
    priority = db.Column(db.String(20), default="medium", nullable=False)
    assignee = db.Column(db.String(120))
    due_date = db.Column(db.Date)
    completed_at = db.Column(db.DateTime(timezone=True))
    mission_id = db.Column(db.Integer, db.ForeignKey("missions.id", ondelete="SET NULL"))
    story_id = db.Column(db.Integer, db.ForeignKey("user_stories.id", ondelete="SET NULL"))
    sprint_id = db.Column(db.Integer, db.ForeignKey("sprints.id", ondelete="SET NULL"))
    blockers = db.relationship("Blocker", backref="task", lazy="dynamic")


class Blocker(Base):
    __tablename__ = "blockers"
    __table_args__ = (_choices("severity", PRIORITIES), _choices("status", BLOCKER_STATUS))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    severity = db.Column(db.String(20), default="medium", nullable=False)
    status = db.Column(db.String(20), default="open", nullable=False)
    reported_date = db.Column(db.Date, default=date.today, nullable=False)
    resolved_at = db.Column(db.DateTime(timezone=True))
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id", ondelete="SET NULL"))


class Retrospective(Base):
    __tablename__ = "retrospectives"
    sprint_id = db.Column(db.Integer, db.ForeignKey("sprints.id", ondelete="CASCADE"), nullable=False)
    went_well = db.Column(db.Text, default="", nullable=False)
    needs_improvement = db.Column(db.Text, default="", nullable=False)
    sprint = db.relationship("Sprint", backref=db.backref("retrospectives", lazy="dynamic", cascade="all, delete-orphan"))
    action_items = db.relationship("ActionItem", backref="retrospective", cascade="all, delete-orphan", order_by="ActionItem.id")

    def to_dict(self):
        d = super().to_dict()
        d["sprint_name"] = self.sprint.name if self.sprint else None
        d["action_items"] = [a.to_dict() for a in self.action_items]
        return d


class ActionItem(Base):
    __tablename__ = "action_items"
    __table_args__ = (_choices("status", ACTION_STATUS),)
    retrospective_id = db.Column(db.Integer, db.ForeignKey("retrospectives.id", ondelete="CASCADE"), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    owner = db.Column(db.String(120))
    status = db.Column(db.String(20), default="open", nullable=False)


class Notification(Base):
    __tablename__ = "notifications"
    type = db.Column(db.String(40), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    ref_type = db.Column(db.String(40))
    ref_id = db.Column(db.Integer)
    dedupe_key = db.Column(db.String(120), unique=True)


class ProgressSnapshot(Base):
    """Real measurements of sprint progress, recorded when work changes. Source of burndown history."""
    __tablename__ = "progress_snapshots"
    __table_args__ = (db.UniqueConstraint("sprint_id", "snapshot_date", name="uq_snapshot_sprint_day"),)
    sprint_id = db.Column(db.Integer, db.ForeignKey("sprints.id", ondelete="CASCADE"), nullable=False)
    snapshot_date = db.Column(db.Date, nullable=False)
    total_points = db.Column(db.Integer, nullable=False)
    completed_points = db.Column(db.Integer, nullable=False)
    remaining_points = db.Column(db.Integer, nullable=False)


class Activity(Base):
    __tablename__ = "activities"
    message = db.Column(db.String(500), nullable=False)
    entity = db.Column(db.String(40))
    entity_id = db.Column(db.Integer)
