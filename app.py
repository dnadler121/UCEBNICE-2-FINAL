import os, json, unicodedata, random, html, re, base64, uuid, urllib.parse, urllib.request, urllib.error, zipfile, shutil, importlib.util, tempfile, threading, hmac, hashlib
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, render_template_string, request, jsonify, session, redirect, url_for, send_from_directory, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from markupsafe import Markup, escape
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / '.env')

# Na Renderu ukládáme všechna uživatelská data na Persistent Disk.
# Při lokálním spuštění zůstávají data ve složce projektu.
DATA_DIR = Path('/var/data') if Path('/var/data').is_dir() else BASE
DATA_DIR.mkdir(parents=True, exist_ok=True)

UPLOADS = DATA_DIR / 'uploads'
UPLOADS.mkdir(parents=True, exist_ok=True)

INTERACTIVE_LESSONS = DATA_DIR / 'interactive_lessons'
INTERACTIVE_LESSONS.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / 'montessori.db'

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-me')
# Nový název cookie odřízne staré přihlášení z předchozích testovacích verzí.
# Když aplikaci spustíš poprvé, vždy tě pošle na přihlášení.
app.config['SESSION_COOKIE_NAME'] = 'montessori_engine_v1_2_role_login'
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(DB_PATH)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    role = db.Column(db.String(20), default='student')
    password_hash = db.Column(db.String(255), nullable=False)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    icon = db.Column(db.String(20), default='🌱')

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    name = db.Column(db.String(60), nullable=False)
    subject = db.relationship('Subject', backref='grades')

class Block(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    grade_id = db.Column(db.Integer, db.ForeignKey('grade.id'), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    order = db.Column(db.Integer, default=1)
    grade = db.relationship('Grade', backref='blocks')

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    block_id = db.Column(db.Integer, db.ForeignKey('block.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    tip = db.Column(db.Text, default='')
    hero_image = db.Column(db.String(255), default='')
    order = db.Column(db.Integer, default=1)
    is_published = db.Column(db.Boolean, default=True)
    block = db.relationship('Block', backref='lessons')

class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    heading = db.Column(db.String(200), nullable=False)
    text = db.Column(db.Text, default='')
    interest = db.Column(db.Text, default='')
    image = db.Column(db.String(255), default='')
    activity = db.Column(db.Text, default='')
    order = db.Column(db.Integer, default=1)
    lesson = db.relationship('Lesson', backref='sections')

class InlineImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    file = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(255), default='')
    order = db.Column(db.Integer, default=1)
    section = db.relationship('Section', backref='inline_images')

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=True)
    area = db.Column(db.String(20), default='study')  # study/final
    qtype = db.Column(db.String(30), default='choice')
    question = db.Column(db.Text, nullable=False)
    options_json = db.Column(db.Text, default='[]')
    correct_json = db.Column(db.Text, default='0')
    roots_json = db.Column(db.Text, default='[]')
    hint = db.Column(db.Text, default='')
    order = db.Column(db.Integer, default=1)
    lesson = db.relationship('Lesson', backref='questions')
    section = db.relationship('Section', backref='questions')

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    percent = db.Column(db.Integer, default=0)
    grade = db.Column(db.Integer, default=5)
    score = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    focus_lost = db.Column(db.Integer, default=0)
    status = db.Column(db.String(60), default='dokončeno')
    user = db.relationship('User')
    lesson = db.relationship('Lesson')


class InteractiveLesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    subject = db.Column(db.String(40), nullable=False)
    school = db.Column(db.String(160), nullable=False)
    grade_name = db.Column(db.String(120), nullable=False)
    topic = db.Column(db.String(160), nullable=False)
    title = db.Column(db.String(220), nullable=False)
    description = db.Column(db.Text, default='')
    icon = db.Column(db.String(20), default='📘')
    package_dir = db.Column(db.String(255), nullable=False)
    is_published = db.Column(db.Boolean, default=True)
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)


class InteractiveResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    interactive_lesson_id = db.Column(db.Integer, db.ForeignKey('interactive_lesson.id'), nullable=False)
    percent = db.Column(db.Integer, default=100)
    grade = db.Column(db.Integer, default=1)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    focus_lost = db.Column(db.Integer, default=0)
    status = db.Column(db.String(60), default='dokončeno')
    user = db.relationship('User')
    interactive_lesson = db.relationship('InteractiveLesson')


class InteractiveProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    interactive_lesson_id = db.Column(db.Integer, db.ForeignKey('interactive_lesson.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    current_grade = db.Column(db.Integer, default=5)
    last_completed_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')
    interactive_lesson = db.relationship('InteractiveLesson')


class InformaticsLesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school = db.Column(db.String(160), default='')
    grade_name = db.Column(db.String(120), default='')
    topic = db.Column(db.String(180), default='')
    title = db.Column(db.String(220), nullable=False)
    intro = db.Column(db.Text, default='')
    html_original = db.Column(db.String(255), default='')
    html_stored = db.Column(db.String(255), default='')
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class InformaticsTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('informatics_lesson.id'), nullable=False)
    order = db.Column(db.Integer, default=1)
    title = db.Column(db.String(220), nullable=False)
    assignment = db.Column(db.Text, default='')
    source_original = db.Column(db.String(255), nullable=False)
    source_stored = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(40), default='')
    analysis_json = db.Column(db.Text, default='{}')
    checks_json = db.Column(db.Text, default='[]')
    image_file = db.Column(db.String(255), default='')
    lesson = db.relationship('InformaticsLesson', backref='tasks')


class InformaticsWorkFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('informatics_task.id'), nullable=False)
    token = db.Column(db.String(255), nullable=False, unique=True)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    downloaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')
    task = db.relationship('InformaticsTask')


class InformaticsSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('informatics_task.id'), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    feedback_json = db.Column(db.Text, default='[]')
    percent = db.Column(db.Integer, default=0)
    grade = db.Column(db.Integer, default=5)
    status = db.Column(db.String(60), default='kontrola')
    focus_lost = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')
    task = db.relationship('InformaticsTask')


class MathLesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school = db.Column(db.String(160), default='')
    grade_name = db.Column(db.String(120), default='')
    topic = db.Column(db.String(180), default='')
    title = db.Column(db.String(220), nullable=False)
    html_original = db.Column(db.String(255), default='')
    html_stored = db.Column(db.String(255), default='')
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MathExample(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('math_lesson.id'), nullable=False)
    order = db.Column(db.Integer, default=1)
    title = db.Column(db.String(220), default='')
    problem = db.Column(db.Text, nullable=False)
    lesson = db.relationship('MathLesson', backref='examples')


class MathStep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    example_id = db.Column(db.Integer, db.ForeignKey('math_example.id'), nullable=False)
    order = db.Column(db.Integer, default=1)
    instruction = db.Column(db.Text, nullable=False)
    expected = db.Column(db.Text, nullable=False)
    hint = db.Column(db.Text, default='')
    example = db.relationship('MathExample', backref='steps')


class MathAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('math_lesson.id'), nullable=False)
    completed_steps = db.Column(db.Integer, default=0)
    total_steps = db.Column(db.Integer, default=0)
    percent = db.Column(db.Integer, default=0)
    grade = db.Column(db.Integer, default=5)
    status = db.Column(db.String(60), default='rozpracováno')
    focus_lost = db.Column(db.Integer, default=0)
    answers_json = db.Column(db.Text, default='[]')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')
    lesson = db.relationship('MathLesson')


class LessonFocusSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_kind = db.Column(db.String(20), nullable=False)  # html / interactive
    lesson_key = db.Column(db.String(160), nullable=False)
    count = db.Column(db.Integer, default=0)
    terminated = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class StudentProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    current_step = db.Column(db.Integer, default=0)
    status = db.Column(db.String(40), default='rozpracováno')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')
    lesson = db.relationship('Lesson')

def ensure_informatics_columns():
    """Doplní nové sloupce do starší lokální/Render databáze bez mazání dat."""
    try:
        insp = inspect(db.engine)
        if 'informatics_lesson' not in insp.get_table_names():
            return
        cols = {c['name'] for c in insp.get_columns('informatics_lesson')}
        with db.engine.begin() as conn:
            if 'html_original' not in cols:
                conn.execute(text("ALTER TABLE informatics_lesson ADD COLUMN html_original VARCHAR(255) DEFAULT ''"))
            if 'html_stored' not in cols:
                conn.execute(text("ALTER TABLE informatics_lesson ADD COLUMN html_stored VARCHAR(255) DEFAULT ''"))
    except Exception as exc:
        print('Informatics migration warning:', exc)


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', str(s).lower()) if unicodedata.category(c) != 'Mn').strip()

def grade_from_percent(percent):
    if percent >= 95: return 1
    if percent >= 90: return 2
    if percent >= 85: return 3
    if percent >= 80: return 4
    return 5

def current_user():
    uid = session.get('uid')
    return db.session.get(User, uid) if uid else None


def touch_progress(lesson_id, step=0, status='rozpracováno'):
    u = current_user()
    if not u or u.role != 'student':
        return
    pr = StudentProgress.query.filter_by(user_id=u.id, lesson_id=lesson_id).first()
    if not pr:
        pr = StudentProgress(user_id=u.id, lesson_id=lesson_id)
        db.session.add(pr)
    pr.current_step = int(step or 0)
    pr.status = status
    pr.updated_at = datetime.utcnow()
    db.session.commit()

def last_result_for_student(user_id):
    return Result.query.filter_by(user_id=user_id).order_by(Result.created_at.desc()).first()

def current_progress_for_student(user_id):
    return StudentProgress.query.filter_by(user_id=user_id).order_by(StudentProgress.updated_at.desc()).first()

def last_informatics_submission_for_student(user_id):
    return InformaticsSubmission.query.filter(
        InformaticsSubmission.user_id == user_id,
        InformaticsSubmission.status != 'kontrola'
    ).order_by(InformaticsSubmission.created_at.desc()).first()

def last_math_attempt_for_student(user_id):
    return MathAttempt.query.filter(
        MathAttempt.user_id == user_id,
        MathAttempt.status != 'rozpracováno'
    ).order_by(MathAttempt.updated_at.desc()).first()

def student_overview_rows():
    rows = []
    for stu in User.query.filter_by(role='student').order_by(User.name).all():
        pr = current_progress_for_student(stu.id)
        res = last_result_for_student(stu.id)
        inf = last_informatics_submission_for_student(stu.id)
        math = last_math_attempt_for_student(stu.id)
        inf_grade = informatics_grade_from_percent(inf.percent) if inf else None
        rows.append({
            'student': stu,
            'progress': pr,
            'result': res,
            'informatics': inf,
            'informatics_grade': inf_grade,
            'math': math,
        })
    return rows

def require_login():
    if not current_user(): return redirect(url_for('login'))

def require_teacher():
    r = require_login()
    if r: return r
    if current_user().role != 'teacher': return redirect(url_for('dashboard'))

def role_home():
    u = current_user()
    if not u:
        return redirect(url_for('login'))
    if u.role == 'teacher':
        return redirect(url_for('teacher_home'))
    return redirect(url_for('dashboard'))

def completed_steps_for(lesson_id):
    done = session.get('completed_steps', {})
    return set(done.get(str(lesson_id), []))

def mark_step_complete(lesson_id, step):
    done = session.setdefault('completed_steps', {})
    key = str(lesson_id)
    arr = set(done.get(key, []))
    arr.add(int(step))
    done[key] = sorted(arr)
    session.modified = True

def lesson_ready_for_test(lesson):
    data = lesson_to_dict(lesson)
    needed = set(range(len(data['sections'])))
    return needed.issubset(completed_steps_for(lesson.id))

def q_to_dict(q):
    try:
        options = json.loads(q.options_json or '[]')
    except Exception:
        options = []
    d = {'id': q.id, 'type': q.qtype, 'question': q.question, 'options': options, 'hint': q.hint}
    if q.qtype in ['choice','image_choice']:
        d['correct'] = json.loads(q.correct_json or '0')
        if q.qtype == 'image_choice':
            d['images'] = options
            d['labels'] = [''] * len(options)
    else:
        # Krátká odpověď může mít také obrázek. Kvůli kompatibilitě ho ukládáme do options_json jako {"image": "soubor.jpg"}.
        d['roots'] = json.loads(q.roots_json or '[]')
        d['image'] = options.get('image','') if isinstance(options, dict) else ''
    return d

def lesson_to_dict(lesson):
    sections = []
    for s in sorted(lesson.sections, key=lambda x:x.order):
        sections.append({
            'id': s.id, 'heading': s.heading, 'text': s.text, 'interest': s.interest, 'image': s.image,
            'activity': s.activity,
            'questions': [q_to_dict(q) for q in sorted(s.questions, key=lambda x:x.order) if q.area=='study']
        })
    subject = lesson.block.grade.subject
    grade = lesson.block.grade
    return {
        '_id': lesson.id, '_slug': lesson.id, 'subject': subject.name, 'icon': subject.icon, 'grade': grade.name,
        'block': lesson.block.title, 'title': lesson.title, 'tip': lesson.tip, 'hero_image': lesson.hero_image,
        'sections': sections,
        # Test používá ty samé otázky jako procvičení pod výkladem. Nevytváříš je dvakrát.
        'final_test': [q for sec in sections for q in sec['questions']]
    }

def lesson_gallery(lesson):
    """Vrátí obrázky dostupné v editoru pro konkrétní lekci."""
    seen = []
    def add(name):
        if name and name not in seen:
            seen.append(name)
    if lesson:
        add(lesson.hero_image)
        for sec in lesson.sections:
            add(sec.image)
            for q in lesson.questions:
                try:
                    opts = json.loads(q.options_json or '[]')
                except Exception:
                    opts = []
                if q.qtype == 'image_choice':
                    for img in opts:
                        add(img)
                elif q.qtype == 'text' and isinstance(opts, dict):
                    add(opts.get('image',''))
    return seen

def course_from_lesson(lesson):
    if lesson:
        sub = lesson.block.grade.subject
        return {'subject': sub.name, 'grade': lesson.block.grade.name, 'block': lesson.block.title, 'icon': sub.icon}
    return {'subject': 'Montessori', 'grade': '', 'block': '', 'icon': '🌱'}

def visible_lessons():
    return Lesson.query.filter_by(is_published=True).join(Block).join(Grade).join(Subject).order_by(Subject.name, Grade.name, Block.order, Lesson.order).all()

@app.context_processor
def inject():
    u = current_user()
    last = None
    if u:
        res = Result.query.filter_by(user_id=u.id).order_by(Result.created_at.desc()).first()
        if res: last = {'lesson': res.lesson.title, 'percent': res.percent, 'grade': res.grade, 'score': res.score, 'total': res.total}
    return {'user': u, 'last_result': last}


def normalize_subject(value):
    value = strip_accents(value).replace(' ', '-')
    aliases = {'matematika': 'matematika', 'math': 'matematika',
               'informatika': 'informatika', 'ict': 'informatika'}
    return aliases.get(value, value)


def safe_package_slug(value):
    value = strip_accents(value)
    return re.sub(r'[^a-z0-9]+', '-', value).strip('-')[:120]


def interactive_groups_for(subject_kind):
    subject_value = 'matematika' if subject_kind == 'matematika' else 'informatika'
    lessons = InteractiveLesson.query.filter_by(
        subject=subject_value, is_published=True
    ).order_by(
        InteractiveLesson.school,
        InteractiveLesson.grade_name,
        InteractiveLesson.topic,
        InteractiveLesson.title
    ).all()

    grouped = {}
    for lesson in lessons:
        key = (lesson.school, lesson.grade_name)
        group = grouped.setdefault(key, {
            'school': lesson.school,
            'grade': lesson.grade_name,
            'topics': {}
        })
        group['topics'].setdefault(lesson.topic, []).append(lesson)
    return list(grouped.values())


def safe_extract_zip(zip_file, target):
    target = target.resolve()
    for member in zip_file.infolist():
        member_path = (target / member.filename).resolve()
        if target not in member_path.parents and member_path != target:
            raise ValueError('Balíček obsahuje nepovolenou cestu.')
    zip_file.extractall(target)


def find_package_root(temp_dir):
    candidates = list(temp_dir.rglob('lesson.json'))
    if len(candidates) != 1:
        raise ValueError('Balíček musí obsahovat právě jeden soubor lesson.json.')
    return candidates[0].parent


def load_interactive_module(lesson):
    module_file = BASE / lesson.package_dir / 'lesson_app.py'
    if not module_file.exists():
        return None
    module_name = f'interactive_{lesson.slug}_{module_file.stat().st_mtime_ns}'
    spec = importlib.util.spec_from_file_location(module_name, module_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def upsert_interactive_progress(lesson, percent=100, grade=None, focus_lost=0):
    user = current_user()
    if not user or user.role != 'student':
        return
    if grade is None:
        grade = grade_from_percent(percent)
    progress = InteractiveProgress.query.filter_by(
        user_id=user.id,
        interactive_lesson_id=lesson.id
    ).first()
    if not progress:
        progress = InteractiveProgress(
            user_id=user.id,
            interactive_lesson_id=lesson.id
        )
        db.session.add(progress)
    progress.completed = True
    progress.current_grade = int(grade)
    progress.last_completed_at = datetime.utcnow()
    progress.updated_at = datetime.utcnow()
    db.session.add(InteractiveResult(
        user_id=user.id,
        interactive_lesson_id=lesson.id,
        percent=int(percent),
        grade=int(grade),
        focus_lost=int(focus_lost or 0),
        status='dokončeno'
    ))
    db.session.commit()

def get_focus_session(kind, key, create=False):
    user = current_user()
    if not user or user.role != 'student':
        return None
    row = LessonFocusSession.query.filter_by(
        user_id=user.id, lesson_kind=str(kind), lesson_key=str(key)
    ).first()
    if not row and create:
        row = LessonFocusSession(
            user_id=user.id, lesson_kind=str(kind), lesson_key=str(key), count=0
        )
        db.session.add(row)
        db.session.flush()
    return row


def get_focus_count(kind, key):
    user = current_user()
    if not user:
        return 0
    row = LessonFocusSession.query.filter_by(
        user_id=user.id,
        lesson_kind=str(kind),
        lesson_key=str(key)
    ).first()
    return int(row.count or 0) if row else 0


def focus_attempt_marker(kind, key):
    return f'{str(kind)}:{str(key)}'


def begin_focus_attempt(kind, key):
    """Při prvním otevření lekce v novém přihlášení začne počítání od nuly.

    Přechody mezi částmi stejné lekce ani obnovení stránky počítadlo nemažou.
    Po automatickém ukončení nebo řádném dokončení může další otevření
    stejné lekce začít jako nový pokus.
    """
    user = current_user()
    if not user or user.role != 'student':
        return

    marker = focus_attempt_marker(kind, key)
    active = list(session.get('focus_active_attempts', []))
    if marker in active:
        return

    row = get_focus_session(kind, key, create=False)
    if row:
        db.session.delete(row)
        db.session.flush()

    active.append(marker)
    session['focus_active_attempts'] = active
    session.modified = True
    db.session.commit()


def end_focus_attempt(kind, key):
    marker = focus_attempt_marker(kind, key)
    active = list(session.get('focus_active_attempts', []))
    if marker in active:
        active.remove(marker)
        session['focus_active_attempts'] = active
        session.modified = True


def consume_focus_count(kind, key):
    row = get_focus_session(kind, key, create=False)
    count = int(row.count) if row else 0
    if row:
        db.session.delete(row)
    end_focus_attempt(kind, key)
    return count


@app.route('/api/focus-lost', methods=['POST'])
def api_focus_lost():
    r = require_login()
    if r:
        return jsonify({'ok': False, 'error': 'login'}), 401
    user = current_user()
    if user.role != 'student':
        return jsonify({'ok': True, 'ignored': True})

    data = request.get_json(silent=True) or {}
    kind = str(data.get('kind', '')).strip()
    key = str(data.get('key', '')).strip()
    if kind not in ('html', 'interactive', 'informatics', 'math') or not key:
        return jsonify({'ok': False, 'error': 'Neplatná lekce.'}), 400

    row = get_focus_session(kind, key, create=True)
    if row.terminated:
        return jsonify({'ok': True, 'count': row.count, 'terminated': True,
                        'redirect': url_for('focus_terminated')})

    row.count = min(3, int(row.count or 0) + 1)
    row.updated_at = datetime.utcnow()
    row.terminated = row.count >= 3

    if row.terminated:
        if kind == 'html':
            lesson_item = db.session.get(Lesson, int(key)) if key.isdigit() else None
            if lesson_item:
                db.session.add(Result(
                    user_id=user.id, lesson_id=lesson_item.id,
                    percent=0, grade=5, score=0, total=0,
                    focus_lost=3, status='ukončeno po 3 opuštěních'
                ))
                touch_progress(lesson_item.id, 0, 'ukončeno po 3 opuštěních')
        elif kind == 'interactive':
            lesson_item = InteractiveLesson.query.filter_by(slug=key).first()
            if lesson_item:
                db.session.add(InteractiveResult(
                    user_id=user.id, interactive_lesson_id=lesson_item.id,
                    percent=0, grade=5, focus_lost=3,
                    status='ukončeno po 3 opuštěních'
                ))
        elif kind == 'informatics':
            task_item = db.session.get(InformaticsTask, int(key)) if str(key).isdigit() else None
            if task_item:
                last = InformaticsSubmission.query.filter_by(
                    user_id=user.id, task_id=task_item.id
                ).order_by(InformaticsSubmission.created_at.desc()).first()
                percent = last.percent if last else 0
                db.session.add(InformaticsSubmission(
                    user_id=user.id, task_id=task_item.id,
                    original_name=(last.original_name if last else 'bez_souboru'),
                    stored_name=(last.stored_name if last else ''),
                    feedback_json=(last.feedback_json if last else '[]'),
                    percent=percent, grade=informatics_grade_from_percent(percent),
                    status='ukončeno po 3 opuštěních', focus_lost=3
                ))
        elif kind == 'math':
            lesson_item = db.session.get(MathLesson, int(key)) if str(key).isdigit() else None
            if lesson_item:
                total = MathStep.query.join(MathExample).filter(MathExample.lesson_id == lesson_item.id).count()
                attempt = MathAttempt.query.filter_by(user_id=user.id, lesson_id=lesson_item.id).first()
                done = attempt.completed_steps if attempt else 0
                percent = round(done / max(total,1) * 100)
                if not attempt:
                    attempt = MathAttempt(user_id=user.id, lesson_id=lesson_item.id)
                    db.session.add(attempt)
                attempt.completed_steps = done
                attempt.total_steps = total
                attempt.percent = percent
                attempt.grade = informatics_grade_from_percent(percent)
                attempt.status = 'ukončeno po 3 opuštěních'
                attempt.focus_lost = 3
                attempt.updated_at = datetime.utcnow()
        end_focus_attempt(kind, key)
        db.session.commit()
        return jsonify({'ok': True, 'count': 3, 'terminated': True,
                        'redirect': url_for('focus_terminated')})

    db.session.commit()
    return jsonify({'ok': True, 'count': row.count, 'terminated': False})


@app.route('/lesson-ukoncena')
def focus_terminated():
    r = require_login()
    if r:
        return r
    return render_template('terminated.html', course=course_from_lesson(None), lesson=None)


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip().lower()
        password = request.form.get('password','')
        u = User.query.filter_by(username=username).first()
        if u and check_password_hash(u.password_hash, password):
            session['uid'] = u.id
            if u.role == 'teacher':
                return redirect(url_for('teacher_home'))
            return redirect(url_for('portal'))
        return render_template('login.html', course=course_from_lesson(None), error='Špatné jméno nebo heslo.')
    return render_template('login.html', course=course_from_lesson(None), error=None)

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))

@app.route('/')
def index():
    r = require_login()
    if r: return r
    return redirect(url_for('portal'))

@app.route('/portal')
def portal():
    r = require_login()
    if r: return r
    counts = {
        'bio_obc': Lesson.query.join(Block).join(Grade).join(Subject).filter(
            db.or_(Subject.name.ilike('%bio%'), Subject.name.ilike('%občan%'), Subject.name.ilike('%obcan%')),
            Lesson.is_published.is_(True)
        ).count(),
        'matematika': Lesson.query.join(Block).join(Grade).join(Subject).filter(
            Subject.name.ilike('%matemat%'), Lesson.is_published.is_(True)
        ).count() + InteractiveLesson.query.filter_by(subject='matematika', is_published=True).count()
        + MathLesson.query.filter_by(is_published=True).count(),
        'informatika': Lesson.query.join(Block).join(Grade).join(Subject).filter(
            Subject.name.ilike('%informat%'), Lesson.is_published.is_(True)
        ).count() + InteractiveLesson.query.filter_by(subject='informatika', is_published=True).count()
        + InformaticsLesson.query.filter_by(is_published=True).count(),
    }
    return render_template('portal.html', course=course_from_lesson(None), lesson=None, counts=counts)

@app.route('/catalog/<kind>')
def subject_catalog(kind):
    r = require_login()
    if r: return r
    filters = {
        'bio-obc': lambda q: q.filter(db.or_(Subject.name.ilike('%bio%'), Subject.name.ilike('%občan%'), Subject.name.ilike('%obcan%'))),
        'matematika': lambda q: q.filter(Subject.name.ilike('%matemat%')),
        'informatika': lambda q: q.filter(Subject.name.ilike('%informat%')),
    }
    if kind not in filters:
        return 'Neznámý předmět', 404
    q = Subject.query
    subjects = filters[kind](q).order_by(Subject.name).all()
    titles = {
        'bio-obc': ('Biologie a občanská výchova', '🧬'),
        'matematika': ('Matematika', '➗'),
        'informatika': ('Informatika', '💻'),
    }
    title, icon = titles[kind]
    interactive_groups = interactive_groups_for(kind) if kind in ('matematika', 'informatika') else []
    informatics_lessons = InformaticsLesson.query.filter_by(is_published=True).order_by(
        InformaticsLesson.school, InformaticsLesson.grade_name, InformaticsLesson.topic, InformaticsLesson.title
    ).all() if kind == 'informatika' else []
    math_lessons = MathLesson.query.filter_by(is_published=True).order_by(
        MathLesson.school, MathLesson.grade_name, MathLesson.topic, MathLesson.title
    ).all() if kind == 'matematika' else []
    return render_template(
        'catalog.html',
        course={'subject': title, 'grade':'', 'block':'', 'icon':icon},
        lesson=None,
        subjects=subjects,
        interactive_groups=interactive_groups,
        informatics_lessons=informatics_lessons,
        math_lessons=math_lessons,
        kind=kind,
        title=title,
        icon=icon
    )



def _json_value(value, default):
    try:
        return json.loads(value) if value else default
    except Exception:
        return default


def export_html_lessons_backup():
    """Vyexportuje biologii a občanku z databáze do verzovaného JSON souboru."""
    exported = []
    for lesson_item in Lesson.query.order_by(Lesson.id).all():
        subject = lesson_item.block.grade.subject
        grade = lesson_item.block.grade
        block = lesson_item.block
        sections = []
        for sec in sorted(lesson_item.sections, key=lambda x: x.order):
            sections.append({
                'heading': sec.heading,
                'text': sec.text,
                'interest': sec.interest,
                'image': sec.image,
                'activity': sec.activity,
                'order': sec.order,
                'inline_images': [
                    {'file': img.file, 'caption': img.caption, 'order': img.order}
                    for img in sorted(sec.inline_images, key=lambda x: x.order)
                ]
            })
        questions = []
        for q in sorted(lesson_item.questions, key=lambda x: (x.area, x.order)):
            section_order = q.section.order if q.section else None
            questions.append({
                'section_order': section_order,
                'area': q.area,
                'qtype': q.qtype,
                'question': q.question,
                'options': _json_value(q.options_json, []),
                'correct': _json_value(q.correct_json, 0),
                'roots': _json_value(q.roots_json, []),
                'hint': q.hint,
                'order': q.order,
            })
        exported.append({
            'subject': {'name': subject.name, 'icon': subject.icon},
            'grade': grade.name,
            'block': {'title': block.title, 'order': block.order},
            'lesson': {
                'title': lesson_item.title,
                'tip': lesson_item.tip,
                'hero_image': lesson_item.hero_image,
                'order': lesson_item.order,
                'is_published': lesson_item.is_published,
            },
            'sections': sections,
            'questions': questions,
        })
    target = CONTENT_BACKUP / 'html_lessons.json'
    target.write_text(json.dumps({'version': 1, 'lessons': exported}, ensure_ascii=False, indent=2), encoding='utf-8')
    return target


def restore_html_lessons_backup():
    """Na novém Renderu obnoví chybějící HTML lekce ze souboru v GitHubu."""
    source = CONTENT_BACKUP / 'html_lessons.json'
    if not source.exists():
        return 0
    try:
        payload = json.loads(source.read_text(encoding='utf-8'))
    except Exception:
        return 0
    restored = 0
    for item in payload.get('lessons', []):
        sub_data = item.get('subject', {})
        subject_name = str(sub_data.get('name', '')).strip()
        grade_name = str(item.get('grade', '')).strip()
        block_data = item.get('block', {})
        block_title = str(block_data.get('title', '')).strip()
        lesson_data = item.get('lesson', {})
        title = str(lesson_data.get('title', '')).strip()
        if not all((subject_name, grade_name, block_title, title)):
            continue
        sub = Subject.query.filter_by(name=subject_name).first()
        if not sub:
            sub = Subject(name=subject_name, icon=sub_data.get('icon', '📘'))
            db.session.add(sub); db.session.flush()
        gr = Grade.query.filter_by(subject_id=sub.id, name=grade_name).first()
        if not gr:
            gr = Grade(subject_id=sub.id, name=grade_name)
            db.session.add(gr); db.session.flush()
        bl = Block.query.filter_by(grade_id=gr.id, title=block_title).first()
        if not bl:
            bl = Block(grade_id=gr.id, title=block_title, order=int(block_data.get('order', 1) or 1))
            db.session.add(bl); db.session.flush()
        existing = Lesson.query.filter_by(block_id=bl.id, title=title).first()
        if existing:
            continue
        les = Lesson(
            block_id=bl.id, title=title, tip=lesson_data.get('tip', ''),
            hero_image=lesson_data.get('hero_image', ''), order=int(lesson_data.get('order', 1) or 1),
            is_published=bool(lesson_data.get('is_published', True))
        )
        db.session.add(les); db.session.flush()
        section_by_order = {}
        for sec_data in item.get('sections', []):
            sec = Section(
                lesson_id=les.id, heading=sec_data.get('heading', 'Výklad'), text=sec_data.get('text', ''),
                interest=sec_data.get('interest', ''), image=sec_data.get('image', ''),
                activity=sec_data.get('activity', ''), order=int(sec_data.get('order', 1) or 1)
            )
            db.session.add(sec); db.session.flush()
            section_by_order[sec.order] = sec
            for img_data in sec_data.get('inline_images', []):
                db.session.add(InlineImage(
                    section_id=sec.id, file=img_data.get('file', ''), caption=img_data.get('caption', ''),
                    order=int(img_data.get('order', 1) or 1)
                ))
        for q_data in item.get('questions', []):
            sec = section_by_order.get(q_data.get('section_order'))
            db.session.add(Question(
                lesson_id=les.id, section_id=sec.id if sec else None,
                area=q_data.get('area', 'study'), qtype=q_data.get('qtype', 'choice'),
                question=q_data.get('question', ''),
                options_json=json.dumps(q_data.get('options', []), ensure_ascii=False),
                correct_json=json.dumps(q_data.get('correct', 0), ensure_ascii=False),
                roots_json=json.dumps(q_data.get('roots', []), ensure_ascii=False),
                hint=q_data.get('hint', ''), order=int(q_data.get('order', 1) or 1)
            ))
        restored += 1
    db.session.commit()
    return restored


def restore_interactive_lessons_from_files():
    restored = 0
    for meta_file in INTERACTIVE_LESSONS.glob('*/lesson.json'):
        try:
            meta = json.loads(meta_file.read_text(encoding='utf-8'))
            slug = safe_package_slug(meta.get('slug', meta_file.parent.name))
            if InteractiveLesson.query.filter_by(slug=slug).first():
                continue
            subject = normalize_subject(meta.get('subject', ''))
            if subject not in ('matematika', 'informatika'):
                continue
            db.session.add(InteractiveLesson(
                slug=slug, subject=subject, school=str(meta.get('school', '')).strip(),
                grade_name=str(meta.get('grade', '')).strip(), topic=str(meta.get('topic', '')).strip(),
                title=str(meta.get('title', slug)).strip(), description=str(meta.get('description', '')).strip(),
                icon=str(meta.get('icon', '➗' if subject == 'matematika' else '💻')).strip(),
                package_dir=str(meta_file.parent), is_published=bool(meta.get('is_published', True)),
                imported_at=datetime.utcnow()
            ))
            restored += 1
        except Exception:
            continue
    db.session.commit()
    return restored



@app.route('/teacher/interactive/import', methods=['GET', 'POST'])
def import_interactive_lesson():
    r = require_teacher()
    if r:
        return r

    if request.method == 'GET':
        return render_template(
            'import_interactive.html',
            course=course_from_lesson(None),
            lesson=None
        )

    package_file = (
        request.files.get('package')
        or request.files.get('zip_file')
        or request.files.get('lesson_zip')
        or request.files.get('file')
    )

    if not package_file or not package_file.filename:
        flash('Vyber ZIP balíček interaktivní lekce.')
        return redirect(url_for('import_interactive_lesson'))

    if not package_file.filename.lower().endswith('.zip'):
        flash('Balíček musí být ve formátu ZIP.')
        return redirect(url_for('import_interactive_lesson'))

    temp_root = Path(tempfile.mkdtemp(prefix='ucebnice_import_'))
    try:
        zip_path = temp_root / secure_filename(package_file.filename)
        package_file.save(zip_path)

        with zipfile.ZipFile(zip_path, 'r') as archive:
            extract_dir = temp_root / 'extracted'
            extract_dir.mkdir(parents=True, exist_ok=True)
            safe_extract_zip(archive, extract_dir)

        package_root = find_package_root(extract_dir)
        meta_file = package_root / 'lesson.json'
        meta = json.loads(meta_file.read_text(encoding='utf-8-sig'))

        subject = normalize_subject(meta.get('subject', ''))
        if subject not in ('matematika', 'informatika'):
            raise ValueError('V lesson.json musí být předmět matematika nebo informatika.')

        school = str(meta.get('school', '')).strip()
        grade_name = str(meta.get('grade', '')).strip()
        topic = str(meta.get('topic', '')).strip()
        title = str(meta.get('title', '')).strip()

        if not all((school, grade_name, topic, title)):
            raise ValueError(
                'V lesson.json musí být vyplněno school, grade, topic a title.'
            )

        slug = safe_package_slug(meta.get('slug') or title)
        if not slug:
            raise ValueError('Nepodařilo se vytvořit platný název lekce.')

        existing = InteractiveLesson.query.filter_by(slug=slug).first()
        if existing:
            raise ValueError(f'Interaktivní lekce se slugem „{slug}“ už existuje.')

        if not (package_root / 'templates' / 'index.html').exists():
            raise ValueError('Balíček musí obsahovat templates/index.html.')

        if not (package_root / 'lesson_app.py').exists():
            raise ValueError('Balíček musí obsahovat lesson_app.py.')

        destination = INTERACTIVE_LESSONS / slug
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(package_root, destination)

        item = InteractiveLesson(
            slug=slug,
            subject=subject,
            school=school,
            grade_name=grade_name,
            topic=topic,
            title=title,
            description=str(meta.get('description', '')).strip(),
            icon=str(
                meta.get(
                    'icon',
                    '➗' if subject == 'matematika' else '💻'
                )
            ).strip(),
            package_dir=str(destination),
            is_published=bool(meta.get('is_published', True)),
            imported_at=datetime.utcnow()
        )
        db.session.add(item)
        db.session.commit()

        flash(f'Interaktivní lekce „{title}“ byla úspěšně importována.')
        return redirect(url_for('teacher_home'))

    except zipfile.BadZipFile:
        db.session.rollback()
        flash('Soubor není platný ZIP balíček.')
    except (ValueError, json.JSONDecodeError) as exc:
        db.session.rollback()
        flash(str(exc))
    except Exception as exc:
        db.session.rollback()
        flash(f'Import se nepodařil: {exc}')
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    return redirect(url_for('import_interactive_lesson'))


@app.route('/interactive/<slug>')
def interactive_lesson(slug):
    r = require_login()
    if r:
        return r
    lesson_item = InteractiveLesson.query.filter_by(slug=slug, is_published=True).first()
    if not lesson_item:
        return 'Interaktivní lekce nebyla nalezena.', 404

    if current_user().role == 'student':
        begin_focus_attempt('interactive', slug)

    template_file = BASE / lesson_item.package_dir / 'templates' / 'index.html'
    if not template_file.exists():
        return 'Balíček lekce neobsahuje templates/index.html.', 500

    html_source = template_file.read_text(encoding='utf-8')
    if current_user().role == 'student':
        guard = render_template_string(
            '<script>window.UCEBNICE_FOCUS_GUARD={{ cfg|tojson }};</script>'
            "<script src=\"{{ url_for('static', filename='js/focus_guard.js') }}\"></script>",
            cfg={'kind': 'interactive', 'key': slug}
        )
        if '</body>' in html_source.lower():
            pos = html_source.lower().rfind('</body>')
            html_source = html_source[:pos] + guard + html_source[pos:]
        else:
            html_source += guard

    return render_template_string(
        html_source,
        package=lesson_item,
        lesson=lesson_item,
        user=current_user(),
        asset_url=lambda path: url_for('interactive_asset', slug=slug, filename=path),
        api_url=lambda action: url_for('interactive_api', slug=slug, action=action),
        complete_url=url_for('complete_interactive', slug=slug),
        portal_url=url_for('subject_catalog', kind=lesson_item.subject)
    )


@app.route('/interactive-assets/<slug>/<path:filename>')
def interactive_asset(slug, filename):
    r = require_login()
    if r:
        return r
    lesson_item = InteractiveLesson.query.filter_by(slug=slug).first_or_404()
    return send_from_directory(BASE / lesson_item.package_dir / 'static', filename)


@app.route('/interactive/<slug>/api/<action>', methods=['GET', 'POST'])
def interactive_api(slug, action):
    r = require_login()
    if r:
        return jsonify({'ok': False, 'error': 'login'}), 401

    lesson_item = InteractiveLesson.query.filter_by(slug=slug, is_published=True).first()
    if not lesson_item:
        return jsonify({'ok': False, 'error': 'lesson'}), 404

    module = load_interactive_module(lesson_item)
    if not module or not hasattr(module, 'handle'):
        return jsonify({'ok': False, 'error': 'Balíček neobsahuje lesson_app.py s funkcí handle().'}), 500

    payload = request.get_json(silent=True) if request.is_json else request.form.to_dict()
    payload = payload or {}
    try:
        result = module.handle(
            action=action,
            payload=payload,
            session=session,
            user={'id': current_user().id, 'username': current_user().username, 'name': current_user().name}
        )
        if not isinstance(result, dict):
            raise ValueError('Funkce handle() musí vrátit slovník.')
        session.modified = True
        return jsonify(result)
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400


@app.route('/interactive/<slug>/complete', methods=['POST'])
def complete_interactive(slug):
    r = require_login()
    if r:
        return jsonify({'ok': False, 'error': 'login'}), 401

    lesson_item = InteractiveLesson.query.filter_by(slug=slug, is_published=True).first_or_404()
    data = request.get_json(silent=True) or request.form.to_dict()
    try:
        percent = max(0, min(100, int(data.get('percent', 100))))
        grade = max(1, min(5, int(data.get('grade', grade_from_percent(percent)))))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'Neplatný výsledek.'}), 400

    focus_lost = consume_focus_count('interactive', slug)
    upsert_interactive_progress(lesson_item, percent=percent, grade=grade, focus_lost=focus_lost)
    return jsonify({
        'ok': True,
        'message': 'Dokončení lekce bylo uloženo.',
        'percent': percent,
        'grade': grade
    })


@app.route('/teacher/interactive/<int:lesson_id>/delete', methods=['POST'])
def delete_interactive_lesson(lesson_id):
    r = require_teacher()
    if r:
        return r
    item = db.session.get(InteractiveLesson, lesson_id)
    if item:
        InteractiveResult.query.filter_by(interactive_lesson_id=item.id).delete()
        InteractiveProgress.query.filter_by(interactive_lesson_id=item.id).delete()
        package_path = BASE / item.package_dir
        db.session.delete(item)
        db.session.commit()
        shutil.rmtree(package_path, ignore_errors=True)
        flash('Interaktivní lekce byla odstraněna.')
    return redirect(url_for('teacher_home'))


@app.route('/dashboard')
def dashboard():
    r = require_login()
    if r: return r
    subjects = Subject.query.order_by(Subject.name).all()
    lessons = [lesson_to_dict(l) for l in visible_lessons()]
    return render_template('dashboard.html', course=course_from_lesson(None), subjects=subjects, lessons=lessons, lesson=None)

@app.route('/lesson/<int:lesson_id>')
def lesson(lesson_id):
    r=require_login();
    if r: return r
    lesson = db.session.get(Lesson, lesson_id)
    if not lesson: return 'Lekce nenalezena', 404
    if current_user().role == 'student':
        begin_focus_attempt('html', lesson.id)
    step = int(request.args.get('step',0))
    data = lesson_to_dict(lesson)
    step = max(0, min(step, len(data['sections'])-1))
    related = Lesson.query.filter_by(block_id=lesson.block_id, is_published=True).order_by(Lesson.order).all()
    completed_steps = completed_steps_for(lesson.id)
    touch_progress(lesson.id, step, 'rozpracováno')
    return render_template('lesson.html', lesson=data, lessons=[lesson_to_dict(l) for l in related], course=course_from_lesson(lesson), step=step, completed_steps=completed_steps, ready_for_test=lesson_ready_for_test(lesson))

@app.route('/test/<int:lesson_id>')
def final_test(lesson_id):
    r=require_login();
    if r: return r
    lesson = db.session.get(Lesson, lesson_id)
    if not lesson: return 'Lekce nenalezena', 404
    if current_user().role == 'student':
        begin_focus_attempt('html', lesson.id)
    if not lesson_ready_for_test(lesson):
        flash('Nejdřív dokonči otázky k výkladu a aktivitu. Test se odemkne až potom.')
        return redirect(url_for('lesson', lesson_id=lesson.id))
    related = Lesson.query.filter_by(block_id=lesson.block_id, is_published=True).order_by(Lesson.order).all()
    touch_progress(lesson.id, 999, 'závěrečný test')
    return render_template('test.html', lesson=lesson_to_dict(lesson), lessons=[lesson_to_dict(l) for l in related], course=course_from_lesson(lesson))

@app.route('/finish/<int:lesson_id>', methods=['POST'])
def finish(lesson_id):
    r=require_login();
    if r: return r
    lesson = db.session.get(Lesson, lesson_id)
    data = lesson_to_dict(lesson)
    total = len(data['final_test']); score=0; detail=[]
    for q in data['final_test']:
        ans = request.form.get(f'q{q["id"]}','')
        ok = check_question(q, ans)
        if ok: score += 1
        detail.append(ok)
    percent = round(score/max(total,1)*100); grade = grade_from_percent(percent)
    focus_lost = consume_focus_count('html', lesson.id)
    Result.query.filter_by(user_id=current_user().id, lesson_id=lesson.id).filter(Result.status != 'dokončeno').delete(synchronize_session=False)
    partial = session.get('html_partial_progress', {})
    partial.pop(str(lesson.id), None)
    session['html_partial_progress'] = partial
    session.modified = True
    db.session.add(Result(user_id=current_user().id, lesson_id=lesson.id, percent=percent, grade=grade, score=score, total=total, focus_lost=focus_lost, status='dokončeno')); db.session.commit()
    touch_progress(lesson.id, 1000, 'dokončeno')
    return render_template('finish.html', lesson=data, course=course_from_lesson(lesson), score=score, total=total, percent=percent, grade=grade, detail=detail)

def check_question(q, ans):
    if q.get('type') in ['choice','image_choice']:
        return str(ans) == str(q.get('correct'))
    na = strip_accents(ans)
    return any(strip_accents(root) in na for root in q.get('roots',[]))

@app.route('/api/check', methods=['POST'])
def api_check():
    d = request.get_json(force=True)
    return jsonify({'ok': check_question(d.get('question',{}), d.get('answer',''))})

def save_html_partial_result(lesson, status='rozpracováno'):
    user = current_user()
    if not user or user.role != 'student':
        return None
    data = lesson_to_dict(lesson)
    progress_map = session.get('html_partial_progress', {})
    lesson_map = progress_map.get(str(lesson.id), {})
    total = 0
    score = 0
    for idx, section in enumerate(data.get('sections', [])):
        units = len(section.get('questions', [])) + 1  # + aktivita
        total += units
        saved = lesson_map.get(str(idx), {})
        score += min(units, int(saved.get('questions', 0)) + (1 if saved.get('activity') else 0))
    final_total = len(data.get('final_test', []))
    total += final_total
    final_saved = lesson_map.get('_final_test', {})
    score += min(final_total, int(final_saved.get('answered', 0)))
    percent = round(score / max(total, 1) * 100)
    row = Result.query.filter_by(user_id=user.id, lesson_id=lesson.id).filter(Result.status != 'dokončeno').order_by(Result.created_at.desc()).first()
    if not row:
        row = Result(user_id=user.id, lesson_id=lesson.id, created_at=datetime.utcnow())
        db.session.add(row)
    row.percent = percent
    row.grade = grade_from_percent(percent)
    row.score = score
    row.total = total
    row.focus_lost = get_focus_count('html', lesson.id)
    row.status = status
    row.created_at = datetime.utcnow()
    db.session.commit()
    touch_progress(lesson.id, 0, status)
    return row

@app.route('/api/html-progress', methods=['POST'])
def api_html_progress():
    r = require_login()
    if r:
        return jsonify({'ok': False, 'error': 'login'}), 401
    d = request.get_json(silent=True) or {}
    lesson_id = int(d.get('lesson_id', 0))
    step = int(d.get('step', 0))
    lesson = db.session.get(Lesson, lesson_id)
    if not lesson:
        return jsonify({'ok': False, 'error': 'lesson'}), 404
    data = lesson_to_dict(lesson)
    if step < 0 or step >= len(data.get('sections', [])):
        return jsonify({'ok': False, 'error': 'step'}), 400
    q_total = len(data['sections'][step].get('questions', []))
    q_done = max(0, min(q_total, int(d.get('questions', 0))))
    activity = bool(d.get('activity', False))
    progress_map = session.get('html_partial_progress', {})
    lesson_map = progress_map.setdefault(str(lesson_id), {})
    old = lesson_map.get(str(step), {})
    lesson_map[str(step)] = {
        'questions': max(int(old.get('questions', 0)), q_done),
        'activity': bool(old.get('activity')) or activity,
    }
    session['html_partial_progress'] = progress_map
    session.modified = True
    row = save_html_partial_result(lesson, str(d.get('status') or 'rozpracováno'))
    return jsonify({'ok': True, 'percent': row.percent if row else 0})

@app.route('/api/html-test-progress', methods=['POST'])
def api_html_test_progress():
    r = require_login()
    if r:
        return jsonify({'ok': False, 'error': 'login'}), 401
    d = request.get_json(silent=True) or {}
    lesson_id = int(d.get('lesson_id', 0))
    lesson = db.session.get(Lesson, lesson_id)
    if not lesson:
        return jsonify({'ok': False, 'error': 'lesson'}), 404
    data = lesson_to_dict(lesson)
    total = len(data.get('final_test', []))
    answered = max(0, min(total, int(d.get('answered', 0))))
    progress_map = session.get('html_partial_progress', {})
    lesson_map = progress_map.setdefault(str(lesson_id), {})
    old = lesson_map.get('_final_test', {})
    lesson_map['_final_test'] = {
        'answered': max(int(old.get('answered', 0)), answered)
    }
    session['html_partial_progress'] = progress_map
    session.modified = True
    row = save_html_partial_result(lesson, str(d.get('status') or 'závěrečný test – rozpracováno'))
    return jsonify({'ok': True, 'percent': row.percent if row else 0})

@app.route('/api/section-complete', methods=['POST'])
def api_section_complete():
    r = require_login()
    if r: return jsonify({'ok': False, 'error': 'login'}), 401
    d = request.get_json(force=True)
    lesson_id = int(d.get('lesson_id', 0))
    step = int(d.get('step', 0))
    lesson = db.session.get(Lesson, lesson_id)
    if not lesson:
        return jsonify({'ok': False, 'error': 'lesson'}), 404
    data = lesson_to_dict(lesson)
    if step < 0 or step >= len(data['sections']):
        return jsonify({'ok': False, 'error': 'step'}), 400
    mark_step_complete(lesson_id, step)
    touch_progress(lesson_id, step, 'splněná část lekce')
    return jsonify({'ok': True, 'ready_for_test': lesson_ready_for_test(lesson)})


# ============================================================
# INFORMATIKA – UNIVERZÁLNÍ ENGINE
# Učitel nahraje hotový referenční soubor pouze pro analýzu.
# Student jej nikdy nedostane a vytváří vlastní nový soubor od nuly.
# ============================================================

INFORMATICS_SOURCE_DIR = DATA_DIR / 'informatics_sources'
INFORMATICS_SUBMISSION_DIR = DATA_DIR / 'informatics_submissions'
INFORMATICS_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
INFORMATICS_SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)


def informatics_grade_from_percent(percent):
    percent = int(percent or 0)
    if percent >= 95: return 1
    if percent >= 90: return 2
    if percent >= 85: return 3
    if percent >= 80: return 4
    return 5


def render_informatics_html(filename):
    if not filename:
        return ''
    path = INFORMATICS_SOURCE_DIR / filename
    if not path.exists():
        return ''
    try:
        return path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return ''


def _safe_json(value, default):
    try:
        return json.loads(value or '')
    except Exception:
        return default


def _save_uploaded_file(file_storage, folder, prefix='file'):
    ext = Path(file_storage.filename or '').suffix.lower()
    name = f'{prefix}_{uuid.uuid4().hex}{ext}'
    folder.mkdir(parents=True, exist_ok=True)
    file_storage.save(folder / name)
    return name


def analyze_informatics_file(path, original_name):
    """Vrátí strukturu souboru a seznam kontrol, které lze studentovi nabídnout."""
    ext = Path(original_name).suffix.lower()
    info = {'extension': ext, 'name': original_name}
    checks = []

    if ext in ('.xlsx', '.xlsm'):
        info['type'] = 'Excel'
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, data_only=False)
            info['sheets'] = wb.sheetnames
            total_nonempty = 0
            total_formulas = 0
            functions = set()
            chart_count = 0
            sheet_specs = []
            for ws in wb.worksheets:
                nonempty = 0
                formulas = []
                max_row = min(ws.max_row or 1, 500)
                max_col = min(ws.max_column or 1, 50)
                headers = []
                for c in ws[1][:max_col]:
                    if c.value not in (None, ''):
                        headers.append(str(c.value))
                for row in ws.iter_rows(min_row=1, max_row=max_row, max_col=max_col):
                    for cell in row:
                        if cell.value not in (None, ''):
                            nonempty += 1
                        if isinstance(cell.value, str) and cell.value.startswith('='):
                            total_formulas += 1
                            formulas.append({'cell': cell.coordinate, 'formula': cell.value})
                            for fn in re.findall(r'([A-ZÁ-Ž][A-ZÁ-Ž0-9_.]*)\s*\(', cell.value.upper()):
                                functions.add(fn)
                total_nonempty += nonempty
                chart_count += len(getattr(ws, '_charts', []) or [])
                sheet_specs.append({
                    'name': ws.title,
                    'rows': ws.max_row or 0,
                    'cols': ws.max_column or 0,
                    'headers': headers,
                    'nonempty': nonempty,
                    'formulas': formulas[:40]
                })
            info.update({
                'sheet_specs': sheet_specs,
                'nonempty_count': total_nonempty,
                'formula_count': total_formulas,
                'formula_functions': sorted(functions),
                'chart_count': chart_count,
            })
        except Exception as exc:
            info['analysis_error'] = str(exc)

        checks = [
            {'code':'excel_sheets','label':'Počet a názvy listů'},
            {'code':'excel_headers','label':'Záhlaví tabulky'},
            {'code':'excel_size','label':'Rozsah tabulky / počet řádků a sloupců'},
            {'code':'excel_filled','label':'Vyplněné části tabulky'},
            {'code':'excel_formulas','label':'Použití vzorců'},
            {'code':'excel_functions','label':'Použití konkrétních funkcí (např. SUM, IF, AVERAGE)'},
            {'code':'excel_chart','label':'Graf, pokud je v učitelském souboru'},
        ]

    elif ext == '.docx':
        info['type'] = 'Word'
        try:
            from docx import Document
            doc = Document(path)
            paragraphs = [p for p in doc.paragraphs if p.text.strip()]
            headings = [p.text.strip() for p in paragraphs if str(p.style.name).lower().startswith(('heading','nadpis'))]
            words = [w for p in paragraphs for w in p.text.split()]
            info.update({
                'paragraph_count': len(paragraphs),
                'word_count': len(words),
                'heading_count': len(headings),
                'headings': headings[:30],
                'table_count': len(doc.tables),
                'image_count': len(doc.inline_shapes),
            })
        except Exception as exc:
            info['analysis_error'] = str(exc)

        checks = [
            {'code':'word_length','label':'Rozsah dokumentu'},
            {'code':'word_headings','label':'Nadpisy'},
            {'code':'word_table','label':'Tabulky'},
            {'code':'word_images','label':'Obrázky'},
        ]

    elif ext == '.pptx':
        info['type'] = 'PowerPoint'
        try:
            from pptx import Presentation
            prs = Presentation(path)
            titles = []
            image_count = 0
            for slide in prs.slides:
                if slide.shapes.title and slide.shapes.title.text.strip():
                    titles.append(slide.shapes.title.text.strip())
                for shape in slide.shapes:
                    if getattr(shape, 'shape_type', None) == 13:  # picture
                        image_count += 1
            info.update({
                'slide_count': len(prs.slides),
                'titles': titles[:50],
                'title_count': len(titles),
                'image_count': image_count,
            })
        except Exception as exc:
            info['analysis_error'] = str(exc)

        checks = [
            {'code':'ppt_slides','label':'Počet snímků'},
            {'code':'ppt_titles','label':'Nadpisy snímků'},
            {'code':'ppt_images','label':'Obrázky'},
        ]

    elif ext == '.py':
        info['type'] = 'Python'
        try:
            import ast
            source = Path(path).read_text(encoding='utf-8', errors='replace')
            tree = ast.parse(source)
            functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            variables = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)})
            imports = []
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    imports.extend(a.name for a in n.names)
                elif isinstance(n, ast.ImportFrom):
                    imports.append(n.module or '')
            calls = [getattr(n.func, 'id', '') for n in ast.walk(tree) if isinstance(n, ast.Call)]
            info.update({
                'functions': functions,
                'variables': variables[:80],
                'imports': sorted(set(x for x in imports if x)),
                'has_if': any(isinstance(n, ast.If) for n in ast.walk(tree)),
                'has_loop': any(isinstance(n, (ast.For, ast.While)) for n in ast.walk(tree)),
                'has_input': 'input' in calls,
                'has_print': 'print' in calls,
                'line_count': len(source.splitlines()),
            })
        except Exception as exc:
            info['syntax_error'] = str(exc)

        checks = [
            {'code':'py_syntax','label':'Program bez syntaktické chyby'},
            {'code':'py_function','label':'Vlastní funkce'},
            {'code':'py_condition','label':'Podmínka if'},
            {'code':'py_loop','label':'Cyklus for / while'},
            {'code':'py_io','label':'Vstup a výstup programu'},
            {'code':'py_imports','label':'Použité knihovny'},
            {'code':'py_required_names','label':'Názvy funkcí podle učitelského řešení'},
        ]
    else:
        info['type'] = 'Soubor'
        checks = [{'code':'file_type','label':'Správný typ souboru'}]

    return info, checks


def generated_assignment(info):
    """Návrh instrukcí. Učitel ho před zveřejněním může libovolně přepsat."""
    ext = info.get('extension','')
    lines = []

    if ext in ('.xlsx','.xlsm'):
        specs = info.get('sheet_specs') or []
        lines.append('Vytvoř nový prázdný sešit v Excelu a zpracuj jej podle následujících požadavků:')
        if info.get('sheets'):
            if len(info['sheets']) == 1:
                lines.append(f'• Pracuj v jednom listu. List pojmenuj „{info["sheets"][0]}“.')
            else:
                lines.append('• Vytvoř listy: ' + ', '.join(info['sheets']) + '.')
        for sp in specs[:5]:
            headers = [x for x in sp.get('headers',[]) if x]
            if headers:
                lines.append(f'• V listu „{sp["name"]}“ vytvoř záhlaví: ' + ' | '.join(headers) + '.')
            if sp.get('rows',0) > 1:
                lines.append(f'• Tabulka v listu „{sp["name"]}“ má mít přibližně {sp["rows"]} řádků včetně záhlaví.')
        funcs = info.get('formula_functions') or []
        if funcs:
            lines.append('• Pro výpočty použij funkce: ' + ', '.join(funcs) + '.')
        elif info.get('formula_count',0):
            lines.append(f'• Použij alespoň {info["formula_count"]} vzorec/vzorce.')
        if info.get('chart_count',0):
            lines.append(f'• Vytvoř {info["chart_count"]} graf/grafy.')
        lines.append('• Soubor ulož ve formátu Excel a nahraj ho do lekce ke kontrole.')

    elif ext == '.docx':
        lines.append('Vytvoř nový prázdný dokument ve Wordu a zpracuj jej podle následujících požadavků:')
        if info.get('heading_count',0):
            lines.append(f'• Použij alespoň {info["heading_count"]} nadpis/nadpisy.')
        if info.get('paragraph_count',0):
            lines.append(f'• Dokument rozděl přibližně do {info["paragraph_count"]} odstavců.')
        if info.get('word_count',0):
            lines.append(f'• Rozsah dokumentu má být přibližně {info["word_count"]} slov.')
        if info.get('table_count',0):
            lines.append(f'• Vlož {info["table_count"]} tabulku/tabulky.')
        if info.get('image_count',0):
            lines.append(f'• Vlož alespoň {info["image_count"]} obrázek/obrázky.')
        lines.append('• Hotový dokument ulož jako DOCX a nahraj ho do lekce.')

    elif ext == '.pptx':
        lines.append('Vytvoř novou prázdnou prezentaci v PowerPointu:')
        if info.get('slide_count',0):
            lines.append(f'• Prezentace má mít {info["slide_count"]} snímků.')
        if info.get('title_count',0):
            lines.append(f'• Použij nadpisy alespoň na {info["title_count"]} snímcích.')
        if info.get('image_count',0):
            lines.append(f'• Vlož alespoň {info["image_count"]} obrázek/obrázky.')
        lines.append('• Hotovou prezentaci ulož jako PPTX a nahraj ji do lekce.')

    elif ext == '.py':
        lines.append('Vytvoř nový Python soubor od nuly a naprogramuj řešení podle těchto požadavků:')
        funcs = info.get('functions') or []
        if funcs:
            lines.append('• Vytvoř funkci/funkce: ' + ', '.join(funcs) + '.')
        if info.get('has_if'):
            lines.append('• Použij podmínku if/else.')
        if info.get('has_loop'):
            lines.append('• Použij cyklus for nebo while.')
        if info.get('has_input'):
            lines.append('• Program má načíst vstup od uživatele.')
        if info.get('has_print'):
            lines.append('• Program má zobrazit výsledek uživateli.')
        if info.get('imports'):
            lines.append('• Použij knihovnu/knihovny: ' + ', '.join(info['imports']) + '.')
        lines.append('• Program ulož jako .py a nahraj ho do lekce.')

    else:
        lines.append('Vytvoř nový soubor podle zadání učitele a nahraj ho do lekce.')

    return '\n'.join(lines)


def check_hint(code):
    return {
        'excel_sheets':'Podívej se dole v Excelu na názvy a počet záložek listů.',
        'excel_headers':'Zkontroluj první řádek tabulky. Názvy sloupců musí odpovídat zadání.',
        'excel_size':'Zkontroluj, jestli má tabulka požadovaný počet řádků a sloupců.',
        'excel_filled':'Zkontroluj, zda v tabulce nezůstala místa, která mají být vyplněná.',
        'excel_formulas':'Výpočet v Excelu musí být vzorec – nezačínej výsledkem, ale znakem =.',
        'excel_functions':'Podívej se na funkci ve vzorci. Může jít například o SUM, AVERAGE nebo IF.',
        'excel_chart':'Označ vhodná data a zkus kartu Vložení → Graf.',
        'word_length':'Zkontroluj, zda dokument není kratší než požadovaný rozsah.',
        'word_headings':'Použij styl Nadpis, ne pouze větší nebo tučné písmo.',
        'word_table':'Tabulku vložíš přes Vložit → Tabulka.',
        'word_images':'Zkontroluj, zda jsou v dokumentu vložené požadované obrázky.',
        'ppt_slides':'Spočítej snímky v levém panelu PowerPointu.',
        'ppt_titles':'Zkontroluj, zda mají požadované snímky skutečný nadpis.',
        'ppt_images':'Zkontroluj, zda jsi vložil požadované obrázky.',
        'py_syntax':'Spusť program. Python ti v první chybové hlášce ukáže řádek, kde je problém.',
        'py_function':'Vlastní funkce začíná klíčovým slovem def.',
        'py_condition':'Podmínku vytvoříš pomocí if, případně elif a else.',
        'py_loop':'Pro opakování použij for nebo while.',
        'py_io':'Zkontroluj práci se vstupem a výstupem, například input() a print().',
        'py_imports':'Zkontroluj importy na začátku programu.',
        'py_required_names':'Porovnej názvy svých funkcí se zadáním.',
    }.get(code, 'Vrať se k zadání a zkontroluj tuto část práce krok po kroku.')


def evaluate_informatics_file(student_path, student_name, task):
    teacher = _safe_json(task.analysis_json, {})
    raw_checks = _safe_json(task.checks_json, [])
    checks = []
    for item in raw_checks:
        if isinstance(item, str):
            checks.append({'code': item, 'question': ''})
        elif isinstance(item, dict) and item.get('code'):
            checks.append(item)
    student, _ = analyze_informatics_file(student_path, student_name)
    results = []

    for check in checks:
        code = check.get('code','')
        question = check.get('question','')
        custom_hint = check.get('hint','')
        ok = True
        label = code

        if code == 'excel_sheets':
            want = teacher.get('sheets') or []
            have = student.get('sheets') or []
            ok = want == have
            label = 'Počet a názvy listů'
        elif code == 'excel_headers':
            want = teacher.get('sheet_specs') or []
            have = student.get('sheet_specs') or []
            if len(have) < len(want):
                ok = False
            else:
                for i, sp in enumerate(want):
                    if (sp.get('headers') or []) != (have[i].get('headers') or []):
                        ok = False; break
            label = 'Záhlaví tabulky'
        elif code == 'excel_size':
            want = teacher.get('sheet_specs') or []
            have = student.get('sheet_specs') or []
            ok = len(have) >= len(want)
            if ok:
                for i, sp in enumerate(want):
                    if have[i].get('rows',0) < sp.get('rows',0) or have[i].get('cols',0) < sp.get('cols',0):
                        ok=False; break
            label = 'Rozsah tabulky'
        elif code == 'excel_filled':
            ok = int(student.get('nonempty_count',0) or 0) >= int(teacher.get('nonempty_count',0) or 0)
            label = 'Vyplněné části tabulky'
        elif code == 'excel_formulas':
            ok = int(student.get('formula_count',0) or 0) >= int(teacher.get('formula_count',0) or 0)
            label = 'Použití vzorců'
        elif code == 'excel_functions':
            ok = set(teacher.get('formula_functions') or []).issubset(set(student.get('formula_functions') or []))
            label = 'Požadované funkce'
        elif code == 'excel_chart':
            ok = int(student.get('chart_count',0) or 0) >= int(teacher.get('chart_count',0) or 0)
            label = 'Graf'
        elif code == 'word_length':
            ok = int(student.get('word_count',0) or 0) >= int(teacher.get('word_count',0) or 0)
            label = 'Rozsah dokumentu'
        elif code == 'word_headings':
            ok = int(student.get('heading_count',0) or 0) >= int(teacher.get('heading_count',0) or 0)
            label = 'Nadpisy'
        elif code == 'word_table':
            ok = int(student.get('table_count',0) or 0) >= int(teacher.get('table_count',0) or 0)
            label = 'Tabulky'
        elif code == 'word_images':
            ok = int(student.get('image_count',0) or 0) >= int(teacher.get('image_count',0) or 0)
            label = 'Obrázky'
        elif code == 'ppt_slides':
            ok = int(student.get('slide_count',0) or 0) >= int(teacher.get('slide_count',0) or 0)
            label = 'Počet snímků'
        elif code == 'ppt_titles':
            ok = int(student.get('title_count',0) or 0) >= int(teacher.get('title_count',0) or 0)
            label = 'Nadpisy snímků'
        elif code == 'ppt_images':
            ok = int(student.get('image_count',0) or 0) >= int(teacher.get('image_count',0) or 0)
            label = 'Obrázky'
        elif code == 'py_syntax':
            ok = not student.get('syntax_error')
            label = 'Program bez syntaktické chyby'
        elif code == 'py_function':
            ok = len(student.get('functions') or []) >= len(teacher.get('functions') or [])
            label = 'Vlastní funkce'
        elif code == 'py_condition':
            ok = (not teacher.get('has_if')) or bool(student.get('has_if'))
            label = 'Podmínka if'
        elif code == 'py_loop':
            ok = (not teacher.get('has_loop')) or bool(student.get('has_loop'))
            label = 'Cyklus'
        elif code == 'py_io':
            ok = ((not teacher.get('has_input')) or student.get('has_input')) and ((not teacher.get('has_print')) or student.get('has_print'))
            label = 'Vstup a výstup'
        elif code == 'py_imports':
            ok = set(teacher.get('imports') or []).issubset(set(student.get('imports') or []))
            label = 'Použité knihovny'
        elif code == 'py_required_names':
            ok = set(teacher.get('functions') or []).issubset(set(student.get('functions') or []))
            label = 'Názvy funkcí'

        results.append({
            'code':code, 'label':label, 'question':question,
            'ok':bool(ok), 'hint':custom_hint or check_hint(code)
        })

    return results


def informatics_preview(path, original_name):
    ext = Path(original_name).suffix.lower()
    if ext in ('.xlsx','.xlsm'):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, data_only=False)
            ws = wb[wb.sheetnames[0]]
            rows = []
            for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row,25), max_col=min(ws.max_column,12)):
                rows.append([c.value for c in row])
            return {'kind':'table','title':ws.title,'rows':rows}
        except Exception as exc:
            return {'kind':'text','text':f'Náhled se nepodařilo vytvořit: {exc}'}
    if ext == '.docx':
        try:
            from docx import Document
            doc = Document(path)
            text_value = '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
            return {'kind':'text','text':text_value[:18000]}
        except Exception as exc:
            return {'kind':'text','text':f'Náhled se nepodařilo vytvořit: {exc}'}
    if ext == '.pptx':
        try:
            from pptx import Presentation
            prs = Presentation(path)
            lines = []
            for i, slide in enumerate(prs.slides[:25],1):
                texts = [sh.text.strip() for sh in slide.shapes if hasattr(sh,'text') and sh.text.strip()]
                lines.append(f'Snímek {i}: ' + ' | '.join(texts))
            return {'kind':'text','text':'\n'.join(lines)}
        except Exception as exc:
            return {'kind':'text','text':f'Náhled se nepodařilo vytvořit: {exc}'}
    if ext == '.py':
        return {'kind':'code','text':Path(path).read_text(encoding='utf-8', errors='replace')[:18000]}
    return {'kind':'text','text':'Soubor byl nahrán. Pro tento typ souboru zatím není náhled.'}


def _informatics_signature(user_id, task_id, nonce):
    secret = str(app.config.get('SECRET_KEY') or 'change-me').encode('utf-8')
    msg = f'{user_id}:{task_id}:{nonce}'.encode('utf-8')
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def _informatics_make_token(user_id, task_id):
    nonce = uuid.uuid4().hex
    sig = _informatics_signature(user_id, task_id, nonce)
    return f'UCEBNICE2:{user_id}:{task_id}:{nonce}:{sig}'


def _informatics_verify_token(token, user_id, task_id):
    try:
        prefix, uid, tid, nonce, sig = str(token or '').strip().split(':', 4)
        if prefix != 'UCEBNICE2' or int(uid) != int(user_id) or int(tid) != int(task_id):
            return False
        return hmac.compare_digest(sig, _informatics_signature(uid, tid, nonce))
    except Exception:
        return False


def _embed_work_token(path, ext, token):
    ext = ext.lower()
    if ext in ('.xlsx', '.xlsm'):
        import openpyxl
        wb = openpyxl.load_workbook(path, keep_vba=(ext == '.xlsm'))
        ws = wb['__UCEBNICE_ID__'] if '__UCEBNICE_ID__' in wb.sheetnames else wb.create_sheet('__UCEBNICE_ID__')
        ws['A1'] = token
        ws.sheet_state = 'veryHidden'
        wb.save(path)
        return
    if ext == '.docx':
        from docx import Document
        doc = Document(path)
        doc.core_properties.keywords = token
        doc.save(path)
        return
    if ext == '.pptx':
        from pptx import Presentation
        prs = Presentation(path)
        prs.core_properties.keywords = token
        prs.save(path)
        return
    if ext == '.py':
        text = Path(path).read_text(encoding='utf-8', errors='replace')
        Path(path).write_text(f'# UCEBNICE2-ID: {token}\n' + text, encoding='utf-8')


def _extract_work_token(path, ext):
    ext = ext.lower()
    try:
        if ext in ('.xlsx', '.xlsm'):
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=False, data_only=False, keep_vba=(ext == '.xlsm'))
            if '__UCEBNICE_ID__' not in wb.sheetnames:
                return ''
            return str(wb['__UCEBNICE_ID__']['A1'].value or '').strip()
        if ext == '.docx':
            from docx import Document
            return str(Document(path).core_properties.keywords or '').strip()
        if ext == '.pptx':
            from pptx import Presentation
            return str(Presentation(path).core_properties.keywords or '').strip()
        if ext == '.py':
            head = Path(path).read_text(encoding='utf-8', errors='replace')[:1000]
            m = re.search(r'UCEBNICE2-ID:\s*(UCEBNICE2:[^\s]+)', head)
            return m.group(1) if m else ''
    except Exception:
        return ''
    return ''


def _create_student_work_file(task, user):
    ext = Path(task.source_original).suffix.lower()
    user_dir = INFORMATICS_SUBMISSION_DIR / str(user.id) / 'workfiles'
    user_dir.mkdir(parents=True, exist_ok=True)
    safe_base = secure_filename(Path(task.source_original).stem) or f'ukol_{task.id}'
    filename = f'{safe_base}_student_{user.id}{ext}'
    path = user_dir / filename

    # Student dostává čistý pracovní soubor stejného typu, nikoli učitelovo hotové řešení.
    if ext in ('.xlsx', '.xlsm'):
        import openpyxl
        wb = openpyxl.Workbook()
        wb.active.title = 'List1'
        wb.save(path)
    elif ext == '.docx':
        from docx import Document
        Document().save(path)
    elif ext == '.pptx':
        from pptx import Presentation
        Presentation().save(path)
    elif ext == '.py':
        path.write_text('# Pracovní soubor – vypracuj zadání níže.\n', encoding='utf-8')
    else:
        raise ValueError('Nepodporovaný typ pracovního souboru.')

    token = _informatics_make_token(user.id, task.id)
    _embed_work_token(path, ext, token)
    row = InformaticsWorkFile.query.filter_by(user_id=user.id, task_id=task.id).first()
    if not row:
        row = InformaticsWorkFile(user_id=user.id, task_id=task.id, token=token, original_name=filename, stored_name=filename)
        db.session.add(row)
    else:
        row.token = token; row.original_name = filename; row.stored_name = filename; row.downloaded_at = datetime.utcnow()
    db.session.commit()
    return path, filename


@app.route('/informatics-task/<int:task_id>/download-workfile')
def download_informatics_workfile(task_id):
    r = require_login()
    if r: return r
    user = current_user()
    if not user or user.role != 'student':
        return 'Pracovní soubor stahuje student.', 403
    task = db.session.get(InformaticsTask, task_id)
    if not task or not informatics_task_unlocked(task):
        return 'Úkol není dostupný.', 404
    path, filename = _create_student_work_file(task, user)
    return send_file(path, as_attachment=True, download_name=filename)


def informatics_task_unlocked(task):
    u = current_user()
    if not u or u.role == 'teacher' or task.order <= 1:
        return True
    previous = InformaticsTask.query.filter_by(lesson_id=task.lesson_id, order=task.order-1).first()
    if not previous:
        return True
    last = InformaticsSubmission.query.filter_by(
        user_id=u.id, task_id=previous.id, status='odevzdáno'
    ).order_by(InformaticsSubmission.created_at.desc()).first()
    return bool(last and last.percent == 100)


@app.route('/teacher/informatics/new', methods=['GET','POST'])
def new_informatics_lesson():
    r = require_teacher()
    if r: return r

    if request.method == 'POST':
        school = request.form.get('school','').strip()
        grade_name = request.form.get('grade_name','').strip()
        topic = request.form.get('topic','').strip()
        title = request.form.get('title','').strip()
        intro = request.form.get('intro','').strip()
        html_file = request.files.get('lesson_html')
        html_original = ''
        html_stored = ''
        if html_file and html_file.filename:
            if Path(html_file.filename).suffix.lower() not in ('.html', '.htm'):
                flash('Společný výklad musí být HTML soubor.')
                return redirect(url_for('new_informatics_lesson'))
            html_original = html_file.filename
            html_stored = _save_uploaded_file(html_file, INFORMATICS_SOURCE_DIR, 'lesson_html')

        if not all((school, grade_name, topic, title)):
            flash('Vyplň školu/třídu, ročník, téma a název lekce.')
            return redirect(url_for('new_informatics_lesson'))

        source_files = request.files.getlist('task_files')
        task_titles = request.form.getlist('task_titles')
        valid = [(i,f) for i,f in enumerate(source_files) if f and f.filename]
        if not valid:
            flash('Přidej alespoň jeden hotový učitelský soubor k analýze.')
            return redirect(url_for('new_informatics_lesson'))

        allowed = {'.xlsx','.xlsm','.docx','.pptx','.py'}
        prepared = []
        for i, f in valid:
            ext = Path(f.filename).suffix.lower()
            if ext not in allowed:
                flash(f'{f.filename}: podporovaný je Excel, Word, PowerPoint nebo Python.')
                return redirect(url_for('new_informatics_lesson'))
            stored = _save_uploaded_file(f, INFORMATICS_SOURCE_DIR, 'teacher')
            analysis, suggested = analyze_informatics_file(INFORMATICS_SOURCE_DIR/stored, f.filename)
            prepared.append({
                'title': (task_titles[i].strip() if i < len(task_titles) else '') or f'Úkol {len(prepared)+1}',
                'source_original': f.filename,
                'source_stored': stored,
                'analysis': analysis,
                'suggested': suggested,
                'assignment': generated_assignment(analysis),
            })

        session['informatics_builder'] = {
            'school':school,'grade_name':grade_name,'topic':topic,'title':title,'intro':intro,
            'html_original':html_original,'html_stored':html_stored,
            'tasks':prepared
        }
        session.modified = True
        return redirect(url_for('review_informatics_lesson'))

    lessons = InformaticsLesson.query.order_by(InformaticsLesson.created_at.desc()).all()
    return render_template('informatics_new.html', course=course_from_lesson(None), lesson=None, lessons=lessons)


@app.route('/teacher/informatics/review', methods=['GET','POST'])
def review_informatics_lesson():
    r = require_teacher()
    if r: return r
    data = session.get('informatics_builder')
    if not data:
        flash('Nejdřív nahraj soubory k analýze.')
        return redirect(url_for('new_informatics_lesson'))

    if request.method == 'POST':
        lesson_row = InformaticsLesson(
            school=data['school'], grade_name=data['grade_name'], topic=data['topic'],
            title=data['title'], intro=data.get('intro',''),
            html_original=data.get('html_original',''), html_stored=data.get('html_stored',''),
            is_published=True
        )
        db.session.add(lesson_row); db.session.flush()

        for i, t in enumerate(data['tasks']):
            selected_codes = request.form.getlist(f'checks_{i}')
            check_items = []
            for code in selected_codes:
                q = request.form.get(f'question_{i}_{code}', '').strip()
                hint = request.form.get(f'hint_{i}_{code}', '').strip()
                if not q:
                    label = next((c.get('label','') for c in t.get('suggested',[]) if c.get('code') == code), code)
                    q = f'Splň požadavek: {label}.'
                if not hint:
                    hint = check_hint(code)
                check_items.append({'code': code, 'question': q, 'hint': hint})
            assignment = request.form.get(f'assignment_{i}', t['assignment']).strip()
            task_title = request.form.get(f'task_title_{i}', t['title']).strip() or t['title']
            db.session.add(InformaticsTask(
                lesson_id=lesson_row.id, order=i+1, title=task_title, assignment=assignment,
                source_original=t['source_original'], source_stored=t['source_stored'],
                file_type=t['analysis'].get('type',''),
                analysis_json=json.dumps(t['analysis'], ensure_ascii=False),
                checks_json=json.dumps(check_items, ensure_ascii=False),
                image_file=''
            ))

        db.session.commit()
        session.pop('informatics_builder', None)
        flash('Informatická lekce byla vytvořena a zveřejněna.')
        return redirect(url_for('informatics_lesson', lesson_id=lesson_row.id))

    for t in data.get('tasks', []):
        source_path = INFORMATICS_SOURCE_DIR / t.get('source_stored','')
        t['preview'] = informatics_preview(source_path, t.get('source_original','')) if source_path.exists() else None
    return render_template('informatics_review.html', course=course_from_lesson(None), lesson=None, data=data)


@app.route('/teacher/informatics/<int:lesson_id>/delete', methods=['POST'])
def delete_informatics_lesson(lesson_id):
    r = require_teacher()
    if r:
        return r

    item = db.session.get(InformaticsLesson, lesson_id)
    if not item:
        flash('Informatická lekce už neexistuje.')
        return redirect(url_for('teacher_home'))

    try:
        # Načteme si úkoly jako ORM objekty a mažeme je postupně.
        tasks = list(
            InformaticsTask.query.filter_by(lesson_id=item.id)
            .order_by(InformaticsTask.order)
            .all()
        )

        for task in tasks:
            # Nejprve všechny studentské výsledky k úkolu.
            submissions = list(
                InformaticsSubmission.query.filter_by(task_id=task.id).all()
            )
            for submission in submissions:
                db.session.delete(submission)

            db.session.flush()
            db.session.delete(task)

        db.session.flush()
        db.session.delete(item)
        db.session.commit()

        flash('Informatická lekce byla smazána.')
    except Exception:
        db.session.rollback()
        raise

    return redirect(url_for('teacher_home'))


@app.route('/informatics-lesson/<int:lesson_id>')
def informatics_lesson(lesson_id):
    r = require_login()
    if r: return r
    item = db.session.get(InformaticsLesson, lesson_id)
    if not item or (not item.is_published and current_user().role != 'teacher'):
        return 'Lekce nebyla nalezena.', 404
    tasks = sorted(item.tasks, key=lambda x:x.order)
    states = []
    for task in tasks:
        last = None
        if current_user().role == 'student':
            last = InformaticsSubmission.query.filter_by(user_id=current_user().id, task_id=task.id).order_by(InformaticsSubmission.created_at.desc()).first()
        states.append({'task':task,'unlocked':informatics_task_unlocked(task),'last':last})
    course = {'subject':'Informatika','grade':item.grade_name,'block':item.topic,'icon':'💻'}
    lesson_obj = {'title':item.title,'block':item.topic}
    html_content = render_informatics_html(item.html_stored)
    return render_template('informatics_lesson.html', course=course, lesson=lesson_obj, item=item, states=states, html_content=html_content)


@app.route('/informatics-task/<int:task_id>', methods=['GET','POST'])
def informatics_task(task_id):
    r = require_login()
    if r: return r
    task = db.session.get(InformaticsTask, task_id)
    if not task:
        return 'Úkol nebyl nalezen.', 404
    if not informatics_task_unlocked(task):
        flash('Nejdřív dokonči předchozí úkol na 100 %.')
        return redirect(url_for('informatics_lesson', lesson_id=task.lesson_id))

    if current_user().role == 'student':
        begin_focus_attempt('informatics', task.id)

    feedback = None
    preview = None
    percent = None
    grade = None
    checked_submission = None

    if request.method == 'POST':
        if current_user().role != 'student':
            flash('Soubor odevzdává student.')
            return redirect(url_for('informatics_task', task_id=task.id))

        action = request.form.get('action','check')

        if action == 'submit_existing':
            sid = int(request.form.get('submission_id',0) or 0)
            row = InformaticsSubmission.query.filter_by(
                id=sid, user_id=current_user().id, task_id=task.id, status='kontrola'
            ).first()
            if not row:
                flash('Nejdřív svůj soubor zkontroluj.')
                return redirect(url_for('informatics_task', task_id=task.id))
            row.status = 'odevzdáno'
            row.grade = informatics_grade_from_percent(row.percent)
            row.focus_lost = consume_focus_count('informatics', task.id)
            row.created_at = datetime.utcnow()
            db.session.commit()
            flash(f'Úkol byl odevzdán: {row.percent} %, známka {row.grade}.')
            return redirect(url_for('informatics_lesson', lesson_id=task.lesson_id))

        f = request.files.get('student_file')
        if not f or not f.filename:
            flash('Vyber svůj hotový soubor.')
        else:
            expected = Path(task.source_original).suffix.lower()
            got = Path(f.filename).suffix.lower()
            if got != expected:
                flash(f'Nahraj soubor typu {expected}. Vybral jsi {got or "soubor bez přípony"}.')
            else:
                user_dir = INFORMATICS_SUBMISSION_DIR / str(current_user().id)
                stored = _save_uploaded_file(f, user_dir, f'task{task.id}')
                path = user_dir / stored
                token = _extract_work_token(path, got)
                work_row = InformaticsWorkFile.query.filter_by(user_id=current_user().id, task_id=task.id).first()
                if not token or not work_row or token != work_row.token or not _informatics_verify_token(token, current_user().id, task.id):
                    try: path.unlink(missing_ok=True)
                    except Exception: pass
                    flash('Tento soubor nepochází z tvého pracovního souboru staženého z této stránky. Stáhni si svůj soubor tlačítkem „Stáhnout můj pracovní soubor“ a pracuj v něm.')
                    return redirect(url_for('informatics_task', task_id=task.id))
                feedback = evaluate_informatics_file(path, f.filename, task)
                ok_count = sum(1 for x in feedback if x['ok'])
                percent = round(ok_count / max(len(feedback),1) * 100)
                grade = informatics_grade_from_percent(percent)
                preview = informatics_preview(path, f.filename)
                checked_submission = InformaticsSubmission(
                    user_id=current_user().id, task_id=task.id, original_name=f.filename,
                    stored_name=stored, feedback_json=json.dumps(feedback, ensure_ascii=False),
                    percent=percent, grade=grade, status='kontrola',
                    focus_lost=get_focus_count('informatics', task.id)
                )
                db.session.add(checked_submission)
                db.session.commit()

    if current_user().role == 'student' and feedback is None:
        last = InformaticsSubmission.query.filter_by(
            user_id=current_user().id, task_id=task.id, status='kontrola'
        ).order_by(InformaticsSubmission.created_at.desc()).first()
        if last:
            feedback = _safe_json(last.feedback_json, [])
            percent = last.percent
            grade = informatics_grade_from_percent(percent)
            checked_submission = last
            p = INFORMATICS_SUBMISSION_DIR / str(current_user().id) / last.stored_name
            if p.exists():
                preview = informatics_preview(p, last.original_name)

    item = task.lesson
    course = {'subject':'Informatika','grade':item.grade_name,'block':item.topic,'icon':'💻'}
    lesson_obj = {'title':item.title,'block':item.topic}
    teacher_preview = None
    teacher_source = INFORMATICS_SOURCE_DIR / task.source_stored
    if teacher_source.exists():
        teacher_preview = informatics_preview(teacher_source, task.source_original)
    html_content = render_informatics_html(item.html_stored)
    return render_template('informatics_task.html', course=course, lesson=lesson_obj,
                           item=item, task=task, feedback=feedback, preview=preview,
                           teacher_preview=teacher_preview, percent=percent, grade=grade,
                           checked_submission=checked_submission, html_content=html_content)



# ============================================================
# MATEMATIKA – KROKOVÝ ENGINE
# ============================================================

def normalize_math_answer(value):
    value = str(value or '').strip().lower()
    value = value.replace(' ', '').replace(',', '.')
    value = value.replace('−','-').replace('–','-').replace(':','/')

    # Mocniny: přijímáme x^2 i x**2.
    supers = str.maketrans({'⁰':'0','¹':'1','²':'2','³':'3','⁴':'4','⁵':'5','⁶':'6','⁷':'7','⁸':'8','⁹':'9'})
    value = re.sub(r'([a-zA-Z0-9_)])([⁰¹²³⁴⁵⁶⁷⁸⁹]+)', lambda m: m.group(1) + '**' + m.group(2).translate(supers), value)
    value = value.replace('^', '**')

    # Odmocniny:
    # √x      -> sqrt(x)
    # √(x+1)  -> sqrt(x+1)
    # sqrt(x) zůstává beze změny.
    import re as _re

    # √(něco)
    value = _re.sub(r'√\(([^()]*)\)', r'sqrt(\1)', value)

    # √číslo nebo √proměnná
    value = _re.sub(r'√([a-zA-Z0-9_.]+)', r'sqrt(\1)', value)

    return value


def validate_math_expression(value):
    """Ověří, že učitelův matematický zápis umíme přečíst."""
    txt = normalize_math_answer(value)
    if not txt:
        return False, 'zápis je prázdný'

    # V29: učitel může zapisovat stupně jako 30deg, 45deg, ...
    # Pro validaci je převedeme na radiánový zápis, kterému SymPy rozumí.
    # Původní text zůstává beze změny pro studentský renderer, kde je celý
    # úhel (včetně znaku °) pevná konstrukce.
    txt = re.sub(r'(\d+(?:\.\d+)?)deg\b', r'(\1*pi/180)', txt, flags=re.IGNORECASE)
    try:
        import sympy as sp
        from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
        transformations = standard_transformations + (implicit_multiplication_application,)
        local_dict = {
            'sqrt': sp.sqrt, 'log': sp.log, 'ln': sp.log,
            'sin': sp.sin, 'cos': sp.cos, 'tan': sp.tan,
            'asin': sp.asin, 'acos': sp.acos, 'atan': sp.atan,
            'abs': sp.Abs, 'pi': sp.pi,
            'diff': sp.diff, 'integrate': sp.integrate,
        }
        # Samostatné '=' bereme jako rovnici; <=, >=, != necháme SymPy jako relaci.
        eq = re.search(r'(?<![<>=!])=(?!=)', txt)
        parts = [txt[:eq.start()], txt[eq.end():]] if eq else [txt]
        if any(not part for part in parts):
            return False, 'chybí část výrazu před nebo za ='
        for part in parts:
            parse_expr(part, transformations=transformations, evaluate=False, local_dict=local_dict)
        return True, ''
    except Exception:
        return False, 'tomuto matematickému zápisu aplikace nerozumí'


def format_math_display(value):
    """Vizuální převod učitelského matematického zápisu pro studentskou stránku."""
    text = str(value or '')
    text = re.sub(r'(\d+(?:[.,]\d+)?)\s*deg\b', lambda m: m.group(1) + '°', text, flags=re.IGNORECASE)
    text = re.sub(r'\balpha\b', 'α', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(sin|cos|tan)\(([^()]+)\)', r'\1 \2', text, flags=re.IGNORECASE)
    return text

app.jinja_env.filters['math_display'] = format_math_display

def math_input_layout(expected):
    """Vytvoří strom studentských políček.

    Student píše pouze číslice, proměnné a běžné operátory. Speciální
    matematické konstrukce (odmocniny, funkce, integrály, derivace, | |,
    pí, závorky, zlomková čára) vykresluje aplikace napevno.
    """
    raw = str(expected or '').replace('−', '-').replace('–', '-')
    compact = ''.join(ch for ch in raw if not ch.isspace())
    # Učitelský zápis jednoduché odmocniny x**(1/2) převedeme na sqrt(x).
    compact = re.sub(r'([A-Za-z0-9_.]+)\*\*\(1/2\)', r'sqrt(\1)', compact)
    # Učitelský zápis úhlů: 30deg -> 30°. Úhel i znak stupně jsou pro studenta pevné.
    field_index = 0

    def field(ch, super_=False):
        nonlocal field_index
        node={'kind':'field','index':field_index,'expected':ch,'super':super_}
        field_index += 1
        return node

    def split_args(text):
        args=[]; depth=0; last=0
        for j,ch in enumerate(text):
            if ch=='(': depth+=1
            elif ch==')': depth-=1
            elif ch==',' and depth==0:
                args.append(text[last:j]); last=j+1
        args.append(text[last:])
        return args

    def matching_paren(text, pos):
        depth=0
        for j in range(pos,len(text)):
            if text[j]=='(': depth+=1
            elif text[j]==')':
                depth-=1
                if depth==0: return j
        return -1

    special={'sqrt','log','ln','sin','cos','tan','asin','acos','atan','abs','integrate','diff'}

    def parse(text, super_mode=False):
        nodes=[]; i=0
        while i < len(text):
            # Speciální funkce: název a konstrukce jsou pevné, argumenty se dále rozloží.
            m=re.match(r'([A-Za-z]+)\(', text[i:])
            if m and m.group(1).lower() in special:
                name=m.group(1).lower(); op=i+len(m.group(1)); close=matching_paren(text,op)
                if close!=-1:
                    args=split_args(text[op+1:close])
                    if name=='sqrt' and args:
                        nodes.append({'kind':'sqrt','body':parse(args[0])})
                    elif name=='abs' and args:
                        nodes.append({'kind':'abs','body':parse(args[0])})
                    elif name=='integrate' and args:
                        nodes.append({'kind':'integral','body':parse(args[0]),'var':parse(args[1]) if len(args)>1 else []})
                    elif name=='diff' and args:
                        nodes.append({'kind':'derivative','body':parse(args[0]),'var':parse(args[1]) if len(args)>1 else [],'order':parse(args[2], True) if len(args)>2 else []})
                    else:
                        nodes.append({'kind':'function','name':name,'args':[parse(a) for a in args]})
                    i=close+1; continue
            if text.startswith('pi',i) and (i+2==len(text) or not text[i+2].isalpha()):
                nodes.append({'kind':'fixed','display':'π','answer':'pi'}); i+=2; continue
            # Řecký úhel alpha je speciální pevný symbol.
            if text.startswith('alpha',i) and (i+5==len(text) or not text[i+5].isalpha()):
                nodes.append({'kind':'fixed','display':'α','answer':'alpha'}); i+=5; continue
            # Stupně ve SPRÁVNÉ ODPOVĚDI: číslo vyplní student, znak ° je pevný.
            # Např. 30deg -> [3][0]° a 117deg -> [1][1][7]°.
            dm=re.match(r'(\d+(?:[.,]\d+)?)\s*deg\b', text[i:], re.IGNORECASE)
            if dm:
                number=dm.group(1)
                for digit in number:
                    if digit in '.,':
                        # desetinný oddělovač zůstává součástí odpovědi jako běžné políčko
                        nodes.append(field(digit, super_mode))
                    else:
                        nodes.append(field(digit, super_mode))
                nodes.append({'kind':'fixed','display':'°','answer':'deg'})
                i+=len(dm.group(0)); continue
            # Mocnina: ** je pevná konstrukce a exponent je horní index s inputy.
            if text.startswith('**',i):
                i+=2
                if i<len(text) and text[i]=='(':
                    close=matching_paren(text,i)
                    exp=text[i+1:close] if close!=-1 else text[i+1:]
                    i=(close+1 if close!=-1 else len(text))
                    nodes.append({'kind':'power','exp':parse(exp, True),'paren':True})
                else:
                    mexp=re.match(r'[A-Za-z0-9.+\-]+',text[i:])
                    exp=mexp.group(0) if mexp else (text[i:i+1] or '')
                    i+=len(exp)
                    nodes.append({'kind':'power','exp':parse(exp, True),'paren':False})
                continue
            # Jednoduchý zlomek: čára je pevná.
            fm=re.match(r'([A-Za-z0-9]+)/(?!/)([A-Za-z0-9]+)',text[i:])
            if fm:
                nodes.append({'kind':'fraction','num':parse(fm.group(1)),'den':parse(fm.group(2))})
                i+=len(fm.group(0)); continue
            ch=text[i]
            if ch in '(),[]{}':
                nodes.append({'kind':'fixed','display':ch,'answer':ch}); i+=1; continue
            # Operátory a relační znaky student doplňuje sám.
            if ch in '+-*/:<>=!':
                nodes.append(field(ch,super_mode)); i+=1; continue
            if ch=='√':
                nodes.append({'kind':'fixed','display':'√','answer':'√'}); i+=1; continue
            # Každá číslice a každé písmeno/proměnná = vlastní input.
            nodes.append(field(ch,super_mode)); i+=1
        return nodes

    return {'tokens':parse(compact),'field_count':field_index}


def _math_answer_nodes(nodes, form):
    out=[]
    for tok in nodes:
        k=tok['kind']
        if k=='field':
            val=(form.get(f'math_char_{tok["index"]}') or '').strip()
            out.append(val[:1])
        elif k=='fixed': out.append(tok.get('answer',''))
        elif k=='fraction': out.append(_math_answer_nodes(tok['num'],form)+'/'+_math_answer_nodes(tok['den'],form))
        elif k=='sqrt': out.append('sqrt('+_math_answer_nodes(tok['body'],form)+')')
        elif k=='abs': out.append('abs('+_math_answer_nodes(tok['body'],form)+')')
        elif k=='function': out.append(tok['name']+'('+','.join(_math_answer_nodes(a,form) for a in tok['args'])+')')
        elif k=='integral': out.append('integrate('+_math_answer_nodes(tok['body'],form)+','+_math_answer_nodes(tok['var'],form)+')')
        elif k=='derivative':
            args=[_math_answer_nodes(tok['body'],form),_math_answer_nodes(tok['var'],form)]
            if tok.get('order'): args.append(_math_answer_nodes(tok['order'],form))
            out.append('diff('+','.join(args)+')')
        elif k=='power':
            exp=_math_answer_nodes(tok['exp'],form)
            out.append('**'+(('('+exp+')') if tok.get('paren') else exp))
    return ''.join(out)


def math_answer_from_fields(expected, form):
    """Složí studentská políčka zpět do matematického zápisu."""
    layout=math_input_layout(expected)
    return _math_answer_nodes(layout['tokens'],form)


def render_math_input_layout(layout):
    """Vykreslí matematiku: speciální konstrukce pevně, obsah jako jednotlivé inputy."""
    def field_html(tok):
        cls='math-char math-char-super' if tok.get('super') else 'math-char'
        return f'<input class="{cls}" name="math_char_{tok["index"]}" maxlength="1" autocomplete="off" required aria-label="matematický znak {tok["index"]+1}">'
    def render(nodes):
        parts=[]
        for tok in nodes:
            k=tok['kind']
            if k=='field': parts.append(field_html(tok))
            elif k=='fixed': parts.append(f'<span class="math-fixed">{escape(tok.get("display",""))}</span>')
            elif k=='fraction': parts.append(f'<span class="math-fraction"><span class="math-num">{render(tok["num"])}</span><span class="math-den">{render(tok["den"])}</span></span>')
            elif k=='sqrt': parts.append(f'<span class="math-root"><span class="math-root-sign">√</span><span class="math-radicand">{render(tok["body"])}</span></span>')
            elif k=='abs': parts.append(f'<span class="math-abs">|&nbsp;{render(tok["body"])}&nbsp;|</span>')
            elif k=='function':
                args='<span class="math-fixed">,</span>'.join(render(a) for a in tok['args'])
                parts.append(f'<span class="math-function"><span class="math-fixed">{escape(tok["name"])}</span><span class="math-fixed">(</span>{args}<span class="math-fixed">)</span></span>')
            elif k=='integral': parts.append(f'<span class="math-integral"><span class="math-special">∫</span>{render(tok["body"])}<span class="math-fixed">d</span>{render(tok["var"])}</span>')
            elif k=='derivative':
                var=render(tok['var']); order=render(tok.get('order',[]))
                top='d'+(f'<sup>{order}</sup>' if order else '')
                bottom='d'+var+(f'<sup>{order}</sup>' if order else '')
                parts.append(f'<span class="math-derivative"><span class="math-deriv-frac"><span>{top}</span><span>{bottom}</span></span><span class="math-fixed">(</span>{render(tok["body"])}<span class="math-fixed">)</span></span>')
            elif k=='power': parts.append(f'<sup class="math-power">{render(tok["exp"])}</sup>')
        return ''.join(parts)
    return Markup('<div class="math-input-line">'+render(layout.get('tokens',[]))+'</div>')

def math_answers_equivalent(student_value, expected_value):
    """Porovnává matematický význam, ne přesný text.

    Příklady, které uzná jako ekvivalentní:
    x + 3 = 4   ↔   3 + x = 4
    x = 1       ↔   -1 = -x
    2*x = 2     ↔   x = 1

    Když SymPy výraz neumí bezpečně zpracovat, použije se původní
    normalizované textové porovnání.
    """
    a = normalize_math_answer(student_value)
    b = normalize_math_answer(expected_value)

    if a == b:
        return True

    try:
        import sympy as sp
        from sympy.parsing.sympy_parser import (
            parse_expr,
            standard_transformations,
            implicit_multiplication_application,
        )

        transformations = standard_transformations + (implicit_multiplication_application,)

        def parse_side(txt):
            local_dict = {
                'sqrt': sp.sqrt, 'log': sp.log, 'ln': sp.log,
                'sin': sp.sin, 'cos': sp.cos, 'tan': sp.tan,
                'abs': sp.Abs, 'pi': sp.pi, 'diff': sp.diff, 'integrate': sp.integrate,
            }
            return parse_expr(
                txt,
                transformations=transformations,
                evaluate=True,
                local_dict=local_dict
            )

        def relation_to_expr(txt):
            # Rovnici převedeme na výraz levá - pravá = 0.
            if '=' in txt:
                left, right = txt.split('=', 1)
                return sp.simplify(parse_side(left) - parse_side(right)), True
            return sp.simplify(parse_side(txt)), False

        expr_a, is_eq_a = relation_to_expr(a)
        expr_b, is_eq_b = relation_to_expr(b)

        # Rovnici s výrazem nemícháme.
        if is_eq_a != is_eq_b:
            return False

        # Běžné algebraické přeuspořádání.
        if sp.simplify(expr_a - expr_b) == 0:
            return True

        if not is_eq_a:
            return bool(sp.simplify(expr_a - expr_b) == 0)

        # U rovnic uznáme i násobek celé rovnice nenulovou konstantou:
        # 2x=2 je totéž jako x=1.
        if expr_b != 0:
            ratio = sp.simplify(expr_a / expr_b)
            if ratio != 0 and not getattr(ratio, 'free_symbols', set()):
                return True

        # Poslední kontrola: porovnáme množinu řešení pro všechny proměnné.
        symbols = sorted(expr_a.free_symbols | expr_b.free_symbols, key=lambda x: x.name)
        if len(symbols) == 1:
            x = symbols[0]
            sol_a = sp.solveset(expr_a, x, domain=sp.S.Reals)
            sol_b = sp.solveset(expr_b, x, domain=sp.S.Reals)
            return sol_a == sol_b

    except Exception:
        pass

    return a == b


def generated_math_variant(example, user_id):
    """Z jednoduché lineární rovnice ax±b=c vytvoří stabilní variantu pro konkrétního žáka.
    Když vzor nerozpozná, vrátí původní zadání a kroky beze změny.
    """
    problem = str(example.problem or '')
    compact = normalize_math_answer(problem).replace('**', '^')
    m = re.fullmatch(r'([+-]?\d*)\*?x([+-]\d+)=([+-]?\d+)', compact)
    if not m:
        return {'problem': problem, 'steps': {st.id:{'instruction':st.instruction,'expected':st.expected,'hint':st.hint} for st in example.steps}}
    a_txt, b_txt, c_txt = m.groups()
    if a_txt in ('', '+'): a0 = 1
    elif a_txt == '-': a0 = -1
    else: a0 = int(a_txt)
    b0, c0 = int(b_txt), int(c_txt)
    if a0 == 0 or (c0 - b0) % a0 != 0:
        return {'problem': problem, 'steps': {st.id:{'instruction':st.instruction,'expected':st.expected,'hint':st.hint} for st in example.steps}}
    x0 = (c0 - b0) // a0

    seed_src = f'{app.config.get("SECRET_KEY")}:{user_id}:{example.id}:math-variant'
    seed = int(hashlib.sha256(seed_src.encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    a = rng.randint(2, 9) * (-1 if a0 < 0 else 1)
    x = rng.randint(2, 12)
    b_abs = rng.randint(1, 15)
    b = b_abs if b0 >= 0 else -b_abs
    c = a*x + b
    ax = a*x

    # Hodnoty z učitelova vzoru nahradíme odpovídajícími hodnotami nové varianty.
    mapping = {a0:a, b0:b, c0:c, a0*x0:ax, x0:x}
    # Delší čísla první, aby např. 31 nebylo částečně nahrazeno jako 3 a 1.
    def transform(text_value):
        out = str(text_value or '')
        for old, new in sorted(mapping.items(), key=lambda kv: len(str(abs(kv[0]))), reverse=True):
            out = re.sub(rf'(?<![\d.]){re.escape(str(old))}(?![\d.])', str(new), out)
        return out

    sign = '+' if b >= 0 else '-'
    aa = '' if a == 1 else ('-' if a == -1 else str(a))
    new_problem = f'{aa}x {sign} {abs(b)} = {c}'
    steps = {st.id:{'instruction':transform(st.instruction),'expected':transform(st.expected),'hint':transform(st.hint)} for st in example.steps}
    return {'problem':new_problem, 'steps':steps}


def validate_math_payload(payload):
    for ei, ex in enumerate(payload, 1):
        ok, why = validate_math_expression(ex.get("problem", ""))
        if not ok:
            return f"Příklad {ei}: {why}. Oprav zadání a zkus to znovu."
        for si, st in enumerate(ex.get("steps") or [], 1):
            ok, why = validate_math_expression(st.get("expected", ""))
            if not ok:
                return f"Příklad {ei}, krok {si}: {why}. Oprav správný stav a zkus to znovu."
    return None


def math_lesson_total_steps(lesson_id):
    return MathStep.query.join(MathExample).filter(MathExample.lesson_id == lesson_id).count()


def get_math_attempt(user_id, lesson_id, create=False):
    row = MathAttempt.query.filter_by(user_id=user_id, lesson_id=lesson_id).first()
    if not row and create:
        row = MathAttempt(user_id=user_id, lesson_id=lesson_id)
        db.session.add(row)
        db.session.flush()
    return row


def math_current_position(lesson, user_id):
    examples = sorted(lesson.examples, key=lambda x:x.order)
    flat = []
    for ex in examples:
        for st in sorted(ex.steps, key=lambda x:x.order):
            flat.append((ex, st))
    attempt = get_math_attempt(user_id, lesson.id, create=True)
    idx = min(int(attempt.completed_steps or 0), len(flat))
    return flat, attempt, idx


@app.route('/teacher/math/new', methods=['GET','POST'])
def new_math_lesson():
    r = require_teacher()
    if r: return r
    if request.method == 'POST':
        school=request.form.get('school','').strip()
        grade_name=request.form.get('grade_name','').strip()
        topic=request.form.get('topic','').strip()
        title=request.form.get('title','').strip()
        if not all((school,grade_name,topic,title)):
            flash('Vyplň školu/třídu, ročník, téma a název lekce.')
            return redirect(url_for('new_math_lesson'))

        html_file=request.files.get('lesson_html')
        html_original=''; html_stored=''
        if html_file and html_file.filename:
            if Path(html_file.filename).suffix.lower() not in ('.html','.htm'):
                flash('Výklad musí být HTML soubor.')
                return redirect(url_for('new_math_lesson'))
            html_original=html_file.filename
            html_stored=_save_uploaded_file(html_file, INFORMATICS_SOURCE_DIR, 'math_html')

        lesson_row=MathLesson(
            school=school, grade_name=grade_name, topic=topic, title=title,
            html_original=html_original, html_stored=html_stored, is_published=True
        )
        db.session.add(lesson_row); db.session.flush()

        # Data přicházejí jako JSON z dynamického editoru.
        try:
            payload=json.loads(request.form.get('examples_json','[]') or '[]')
        except Exception:
            payload=[]
        if not payload:
            db.session.rollback()
            flash('Přidej alespoň jeden příklad.')
            return redirect(url_for('new_math_lesson'))
        math_error = validate_math_payload(payload)
        if math_error:
            db.session.rollback()
            flash('❌ ' + math_error)
            return redirect(url_for('new_math_lesson'))

        previous_steps=[]
        for ei, ex in enumerate(payload,1):
            ex_row=MathExample(
                lesson_id=lesson_row.id, order=ei,
                title=str(ex.get('title') or f'Příklad {ei}'),
                problem=str(ex.get('problem') or '').strip()
            )
            db.session.add(ex_row); db.session.flush()
            steps=ex.get('steps') or []
            if ex.get('copy_previous') and previous_steps and not steps:
                steps=[dict(x) for x in previous_steps]
            if not steps:
                db.session.rollback()
                flash(f'Příklad {ei} nemá žádné kroky.')
                return redirect(url_for('new_math_lesson'))
            previous_steps=[]
            for si, st in enumerate(steps,1):
                item={
                    'instruction':str(st.get('instruction') or '').strip(),
                    'expected':str(st.get('expected') or '').strip(),
                    'hint':str(st.get('hint') or '').strip()
                }
                previous_steps.append(item)
                db.session.add(MathStep(
                    example_id=ex_row.id, order=si,
                    instruction=item['instruction'], expected=item['expected'], hint=item['hint']
                ))
        db.session.commit()
        flash('Matematická lekce byla vytvořena.')
        return redirect(url_for('math_lesson', lesson_id=lesson_row.id))

    lessons=MathLesson.query.order_by(MathLesson.created_at.desc()).all()
    return render_template('math_new.html', course=course_from_lesson(None), lesson=None, lessons=lessons)


@app.route('/math-lesson/<int:lesson_id>', methods=['GET','POST'])
def math_lesson(lesson_id):
    r=require_login()
    if r:return r
    item=db.session.get(MathLesson,lesson_id)
    if not item:return 'Matematická lekce nebyla nalezena.',404

    if current_user().role=='student':
        begin_focus_attempt('math', item.id)

    examples=sorted(item.examples,key=lambda x:x.order)
    math_variants = {ex.id: generated_math_variant(ex, current_user().id) for ex in examples} if current_user().role=='student' else {}
    html_content=render_informatics_html(item.html_stored)
    current=None; attempt=None; idx=0; total=0; message=None; hint=None
    if current_user().role=='student':
        flat,attempt,idx=math_current_position(item,current_user().id)
        total=len(flat)
        if idx < total:
            current=flat[idx]
        if request.method=='POST':
            action=request.form.get('action','check')
            if action=='submit':
                percent=round((attempt.completed_steps or 0)/max(total,1)*100)
                attempt.total_steps=total; attempt.percent=percent
                attempt.grade=informatics_grade_from_percent(percent)
                attempt.status='odevzdáno'
                attempt.focus_lost=consume_focus_count('math',item.id)
                attempt.updated_at=datetime.utcnow()
                db.session.commit()
                flash(f'Lekce byla odevzdána: {percent} %, známka {attempt.grade}.')
                return redirect(url_for('subject_catalog',kind='matematika'))

            if current:
                ex,step=current
                expected_now = math_variants.get(ex.id, {}).get('steps', {}).get(step.id, {}).get('expected', step.expected)
                answer = math_answer_from_fields(expected_now, request.form)
                if math_answers_equivalent(answer, expected_now):
                    answers = _safe_json(attempt.answers_json, [])
                    answers.append({
                        'example_id': ex.id,
                        'step_id': step.id,
                        'answer': str(answer).strip()
                    })
                    attempt.answers_json = json.dumps(answers, ensure_ascii=False)
                    attempt.completed_steps=int(attempt.completed_steps or 0)+1
                    attempt.total_steps=total
                    attempt.percent=round(attempt.completed_steps/max(total,1)*100)
                    attempt.grade=informatics_grade_from_percent(attempt.percent)
                    attempt.status='rozpracováno'
                    attempt.focus_lost=get_focus_count('math',item.id)
                    attempt.updated_at=datetime.utcnow()
                    db.session.commit()
                    message='✅ Správně. Odemkl se další krok.'
                    flat,attempt,idx=math_current_position(item,current_user().id)
                    current=flat[idx] if idx < len(flat) else None
                else:
                    message='❌ Tento krok ještě není správně.'
                    hint=step.hint
        percent=round((attempt.completed_steps or 0)/max(total,1)*100) if attempt else 0
        grade=informatics_grade_from_percent(percent)
    else:
        percent=0;grade=None

    history_by_example = {}
    if attempt:
        for saved in _safe_json(attempt.answers_json, []):
            history_by_example.setdefault(str(saved.get('example_id')), []).append(saved.get('answer',''))

    current_example_number = current[0].order if current else (len(examples) if examples else 0)
    current_step_number = current[1].order if current else None

    current_input_html = None
    if current and current_user().role == 'student':
        ex_now, st_now = current
        expected_now = math_variants.get(ex_now.id, {}).get('steps', {}).get(st_now.id, {}).get('expected', st_now.expected)
        current_input_html = render_math_input_layout(math_input_layout(expected_now))

    course={'subject':'Matematika','grade':item.grade_name,'block':item.topic,'icon':'➗'}
    lesson_obj={'title':item.title,'block':item.topic}
    return render_template('math_lesson_engine.html',course=course,lesson=lesson_obj,item=item,
        examples=examples,current=current,attempt=attempt,total=total,idx=idx,
        percent=percent,grade=grade,message=message,hint=hint,html_content=html_content,
        history_by_example=history_by_example,
        current_example_number=current_example_number,
        current_step_number=current_step_number,
        math_variants=math_variants,current_input_html=current_input_html)




@app.route('/teacher/math/<int:lesson_id>/edit', methods=['GET','POST'])
def edit_math_lesson(lesson_id):
    r = require_teacher()
    if r: return r

    item = db.session.get(MathLesson, lesson_id)
    if not item:
        return 'Matematická lekce nebyla nalezena.', 404

    if request.method == 'POST':
        item.school = request.form.get('school', item.school).strip()
        item.grade_name = request.form.get('grade_name', item.grade_name).strip()
        item.topic = request.form.get('topic', item.topic).strip()
        item.title = request.form.get('title', item.title).strip()

        html_file = request.files.get('lesson_html')
        if html_file and html_file.filename:
            if Path(html_file.filename).suffix.lower() not in ('.html','.htm'):
                flash('Výklad musí být HTML soubor.')
                return redirect(url_for('edit_math_lesson', lesson_id=item.id))
            item.html_original = html_file.filename
            item.html_stored = _save_uploaded_file(html_file, INFORMATICS_SOURCE_DIR, 'math_html')

        try:
            payload = json.loads(request.form.get('examples_json','[]') or '[]')
        except Exception:
            payload = []

        if not payload:
            flash('Lekce musí obsahovat alespoň jeden příklad.')
            return redirect(url_for('edit_math_lesson', lesson_id=item.id))
        math_error = validate_math_payload(payload)
        if math_error:
            db.session.rollback()
            flash('❌ ' + math_error)
            return redirect(url_for('edit_math_lesson', lesson_id=item.id))

        old_example_ids = [e.id for e in item.examples]
        if old_example_ids:
            MathStep.query.filter(MathStep.example_id.in_(old_example_ids)).delete(synchronize_session=False)
            MathExample.query.filter(MathExample.id.in_(old_example_ids)).delete(synchronize_session=False)
        db.session.flush()

        previous_steps = []
        for ei, ex in enumerate(payload, 1):
            ex_row = MathExample(
                lesson_id=item.id,
                order=ei,
                title=str(ex.get('title') or f'Příklad {ei}'),
                problem=str(ex.get('problem') or '').strip()
            )
            db.session.add(ex_row)
            db.session.flush()

            steps = ex.get('steps') or []
            if ex.get('copy_previous') and previous_steps and not steps:
                steps = [dict(x) for x in previous_steps]

            if not steps:
                db.session.rollback()
                flash(f'Příklad {ei} nemá žádné kroky.')
                return redirect(url_for('edit_math_lesson', lesson_id=item.id))

            previous_steps = []
            for si, st in enumerate(steps, 1):
                step_data = {
                    'instruction': str(st.get('instruction') or '').strip(),
                    'expected': str(st.get('expected') or '').strip(),
                    'hint': str(st.get('hint') or '').strip(),
                }
                previous_steps.append(step_data)
                db.session.add(MathStep(
                    example_id=ex_row.id,
                    order=si,
                    instruction=step_data['instruction'],
                    expected=step_data['expected'],
                    hint=step_data['hint'],
                ))

        # Při změně struktury lekce vynulujeme staré rozpracované pokusy,
        # aby jejich počet kroků neodkazoval na starou strukturu.
        MathAttempt.query.filter_by(lesson_id=item.id).delete()
        db.session.commit()
        flash('Matematická lekce byla upravena.')
        return redirect(url_for('math_lesson', lesson_id=item.id))

    examples_data = []
    for ex in sorted(item.examples, key=lambda x:x.order):
        examples_data.append({
            'title': ex.title,
            'problem': ex.problem,
            'steps': [
                {
                    'instruction': st.instruction,
                    'expected': st.expected,
                    'hint': st.hint,
                }
                for st in sorted(ex.steps, key=lambda x:x.order)
            ]
        })

    return render_template(
        'math_edit.html',
        course=course_from_lesson(None),
        lesson=None,
        item=item,
        examples_json=json.dumps(examples_data, ensure_ascii=False)
    )

@app.route('/teacher/math/<int:lesson_id>/delete', methods=['POST'])
def delete_math_lesson(lesson_id):
    r = require_teacher()
    if r:
        return r

    item = db.session.get(MathLesson, lesson_id)
    if not item:
        flash('Matematická lekce už neexistuje.')
        return redirect(url_for('teacher_home'))

    try:
        # Nejdřív smažeme výsledky/pokusy studentů.
        MathAttempt.query.filter_by(lesson_id=item.id).delete(synchronize_session=False)

        # Kroky a příklady mažeme jako načtené ORM objekty.
        # Tím zabráníme StaleDataError při následném smazání lekce.
        examples = list(MathExample.query.filter_by(lesson_id=item.id).order_by(MathExample.order).all())

        for example in examples:
            steps = list(MathStep.query.filter_by(example_id=example.id).all())
            for step in steps:
                db.session.delete(step)
            db.session.flush()
            db.session.delete(example)

        db.session.flush()
        db.session.delete(item)
        db.session.commit()

        flash('Matematická lekce byla smazána.')
    except Exception:
        db.session.rollback()
        raise

    return redirect(url_for('teacher_home'))


@app.route('/teacher')
def teacher_home():
    r=require_teacher();
    if r: return r
    subjects = Subject.query.order_by(Subject.name).all()
    students = User.query.filter_by(role='student').order_by(User.name).all()
    interactive_lessons = InteractiveLesson.query.order_by(
        InteractiveLesson.subject,
        InteractiveLesson.school,
        InteractiveLesson.grade_name,
        InteractiveLesson.topic,
        InteractiveLesson.title
    ).all()
    informatics_lessons = InformaticsLesson.query.order_by(
        InformaticsLesson.school,
        InformaticsLesson.grade_name,
        InformaticsLesson.topic,
        InformaticsLesson.title
    ).all()
    math_lessons = MathLesson.query.order_by(
        MathLesson.school, MathLesson.grade_name, MathLesson.topic, MathLesson.title
    ).all()
    return render_template(
        'teacher.html',
        course=course_from_lesson(None),
        subjects=subjects,
        students=students,
        student_rows=student_overview_rows(),
        interactive_lessons=interactive_lessons,
        informatics_lessons=informatics_lessons,
        math_lessons=math_lessons
    )

@app.route('/teacher/students', methods=['GET','POST'])
def teacher_students():
    r=require_teacher();
    if r: return r
    if request.method == 'POST':
        username = request.form.get('username','').strip().lower()
        password = request.form.get('password','').strip()
        username = strip_accents(username).replace(' ', '.')
        username = re.sub(r'[^a-z0-9._-]+', '', username)
        username = re.sub(r'\.+', '.', username).strip('.')
        name = ' '.join(part.capitalize() for part in username.split('.') if part)
        if not username or '.' not in username or not password:
            flash('Zadej studenta ve tvaru jmeno.prijmeni a vyplň heslo.')
        elif User.query.filter_by(username=username).first():
            flash('Toto uživatelské jméno už existuje.')
        else:
            db.session.add(User(username=username, name=name or username, role='student', password_hash=generate_password_hash(password)))
            db.session.commit()
            flash('Student byl vytvořen. Může se přihlásit vlastním jménem a heslem.')
            return redirect(url_for('teacher_students'))
    students = User.query.filter_by(role='student').order_by(User.name).all()
    return render_template('students.html', course=course_from_lesson(None), students=students, student_rows=student_overview_rows())


@app.route('/teacher/database')
def teacher_database():
    r=require_teacher()
    if r: return r
    html_results = Result.query.order_by(Result.created_at.desc()).all()
    interactive_results = InteractiveResult.query.order_by(InteractiveResult.completed_at.desc()).all()
    informatics_results = InformaticsSubmission.query.filter(
        InformaticsSubmission.status != 'kontrola'
    ).order_by(InformaticsSubmission.created_at.desc()).all()
    math_results = MathAttempt.query.filter(
        MathAttempt.status != 'rozpracováno'
    ).order_by(MathAttempt.updated_at.desc()).all()
    return render_template(
        'database.html',
        course=course_from_lesson(None),
        student_rows=student_overview_rows(),
        html_results=html_results,
        interactive_results=interactive_results,
        informatics_results=informatics_results,
        math_results=math_results
    )


@app.route('/teacher/result/<int:result_id>/delete', methods=['POST'])
def delete_result(result_id):
    r=require_teacher()
    if r: return r
    result = db.session.get(Result, result_id)
    if result:
        db.session.delete(result)
        db.session.commit()
        flash('Výsledek byl smazán. Účet studenta ani jeho průběžný pokrok zůstaly zachované.')
    return redirect(url_for('teacher_database'))


@app.route('/teacher/interactive-result/<int:result_id>/delete', methods=['POST'])
def delete_interactive_result(result_id):
    r = require_teacher()
    if r:
        return r
    result = db.session.get(InteractiveResult, result_id)
    if result:
        db.session.delete(result)
        db.session.commit()
        flash('Výsledek interaktivní lekce byl smazán. Pokrok studenta zůstal zachovaný.')
    return redirect(url_for('teacher_database'))


@app.route('/teacher/informatics-result/<int:result_id>/delete', methods=['POST'])
def delete_informatics_result(result_id):
    r = require_teacher()
    if r:
        return r
    result = db.session.get(InformaticsSubmission, result_id)
    if result:
        db.session.delete(result)
        db.session.commit()
        flash('Výsledek informatického úkolu byl smazán.')
    return redirect(url_for('teacher_database'))


@app.route('/teacher/results/delete-all', methods=['POST'])
def delete_all_results():
    r=require_teacher()
    if r: return r
    Result.query.delete()
    InteractiveResult.query.delete()
    InformaticsSubmission.query.delete()
    MathAttempt.query.delete()
    db.session.commit()
    flash('Všechny výsledky byly smazány. Studenti a jejich průběžný pokrok ve všech předmětech zůstali zachováni.')
    return redirect(url_for('teacher_database'))

@app.route('/teacher/student/<int:user_id>/delete', methods=['POST'])
def delete_student(user_id):
    r=require_teacher()
    if r: return r
    stu = db.session.get(User, user_id)
    if stu and stu.role == 'student':
        Result.query.filter_by(user_id=stu.id).delete()
        StudentProgress.query.filter_by(user_id=stu.id).delete()
        InteractiveResult.query.filter_by(user_id=stu.id).delete()
        InteractiveProgress.query.filter_by(user_id=stu.id).delete()
        InformaticsSubmission.query.filter_by(user_id=stu.id).delete()
        MathAttempt.query.filter_by(user_id=stu.id).delete()
        db.session.delete(stu)
        db.session.commit()
        flash('Student byl smazán včetně jeho uloženého postupu a výsledků.')
    return redirect(url_for('teacher_students'))

@app.route('/teacher/lesson/<int:lesson_id>/archive', methods=['POST'])
def archive_lesson(lesson_id):
    r = require_teacher()
    if r: return r
    les = db.session.get(Lesson, lesson_id)
    if not les:
        flash('Lekce nebyla nalezena.')
        return redirect(url_for('teacher_home'))
    les.is_published = False
    db.session.commit()
    flash(f'Lekce „{les.title}“ byla archivována. Studentům se už nebude zobrazovat, ale výsledky zůstaly uložené.')
    return redirect(url_for('teacher_home'))

@app.route('/teacher/lesson/<int:lesson_id>/restore', methods=['POST'])
def restore_lesson(lesson_id):
    r = require_teacher()
    if r: return r
    les = db.session.get(Lesson, lesson_id)
    if not les:
        flash('Lekce nebyla nalezena.')
        return redirect(url_for('teacher_home'))
    les.is_published = True
    db.session.commit()
    flash(f'Lekce „{les.title}“ byla obnovena a studenti ji znovu uvidí.')
    return redirect(url_for('teacher_home'))

@app.route('/teacher/lesson/<int:lesson_id>/delete', methods=['POST'])
def delete_lesson(lesson_id):
    r = require_teacher()
    if r: return r
    les = db.session.get(Lesson, lesson_id)
    if not les:
        flash('Lekce nebyla nalezena.')
        return redirect(url_for('teacher_home'))
    title = les.title
    # Trvalé mazání: odstraníme výsledky, otázky, obrázky ve výkladu a sekce navázané na lekci.
    Result.query.filter_by(lesson_id=les.id).delete()
    StudentProgress.query.filter_by(lesson_id=les.id).delete()
    Question.query.filter_by(lesson_id=les.id).delete()
    section_ids = [sec.id for sec in les.sections]
    if section_ids:
        InlineImage.query.filter(InlineImage.section_id.in_(section_ids)).delete(synchronize_session=False)
        Section.query.filter(Section.id.in_(section_ids)).delete(synchronize_session=False)
    db.session.delete(les)
    db.session.commit()
    flash(f'Lekce „{title}“ byla trvale smazána.')
    return redirect(url_for('teacher_home'))



def import_docx_to_html(file_storage):
    """Starší nepoužívaná funkce pro DOCX import. Nově používáme CKEditor."""
    import mammoth
    if not file_storage or not file_storage.filename:
        return '', None
    if not file_storage.filename.lower().endswith('.docx'):
        raise ValueError('Podporovaný je pouze formát .docx')

    original_name = secure_filename(file_storage.filename)

    def convert_image(image):
        ext = 'png'
        if image.content_type and '/' in image.content_type:
            ext = image.content_type.split('/')[-1].replace('jpeg', 'jpg')
        img_name = datetime.now().strftime('%Y%m%d%H%M%S%f_') + 'docx_image.' + ext
        target = UPLOADS / img_name
        with image.open() as image_bytes:
            target.write_bytes(image_bytes.read())
        return {'src': url_for('uploads', filename=img_name)}

    try:
        file_storage.stream.seek(0)
        style_map = """
        p[style-name='Title'] => h1:fresh
        p[style-name='Subtitle'] => h2:fresh
        p[style-name='Heading 1'] => h2:fresh
        p[style-name='Heading 2'] => h3:fresh
        p[style-name='Heading 3'] => h4:fresh
        table => table.docx-table
        """
        result = mammoth.convert_to_html(
            file_storage.stream,
            convert_image=mammoth.images.img_element(convert_image),
            style_map=style_map
        )
    except Exception as exc:
        raise ValueError('DOCX se nepodařilo načíst. Zkontroluj, že jde opravdu o soubor .docx uložený z Wordu nebo LibreOffice.') from exc

    html_value = (result.value or '').strip()
    if not html_value:
        raise ValueError('DOCX se načetl, ale neobsahuje žádný převoditelný výklad.')

    messages = ''.join(f'<li>{html.escape(str(m))}</li>' for m in (result.messages or []))
    info = f'<div class="docx-import-note"><b>Importováno z DOCX:</b> {html.escape(original_name)}</div>'
    if messages:
        info += f'<details class="docx-import-warnings"><summary>Upozornění z převodu</summary><ul>{messages}</ul></details>'
    return info + '<div class="imported-docx-content">' + html_value + '</div>', original_name

@app.route('/teacher/lesson/new', methods=['GET','POST'])
def new_lesson():
    r=require_teacher();
    if r: return r
    if request.method == 'POST':
        subject_name = request.form.get('subject','').strip()
        icon = request.form.get('icon','').strip() or '🌱'
        grade_name = request.form.get('grade','').strip()
        block_title = request.form.get('block','').strip()
        title = request.form.get('title','').strip()
        if not subject_name or not grade_name or not block_title or not title:
            flash('Vyplň předmět, školu a ročník, téma i název lekce. Podle těchto údajů se lekce automaticky zařadí.')
            return render_template('lesson_form.html', course=course_from_lesson(None), lesson=None, section=None, subjects=Subject.query.all(), questions_json=request.form.get('questions_json','[]'), gallery_images=[])
        sub = Subject.query.filter_by(name=subject_name).first() or Subject(name=subject_name, icon=icon)
        sub.icon = icon
        db.session.add(sub); db.session.flush()
        gr = Grade.query.filter_by(subject_id=sub.id, name=grade_name).first() or Grade(subject_id=sub.id, name=grade_name)
        db.session.add(gr); db.session.flush()
        bl = Block.query.filter_by(grade_id=gr.id, title=block_title).first() or Block(grade_id=gr.id, title=block_title, order=Block.query.filter_by(grade_id=gr.id).count()+1)
        db.session.add(bl); db.session.flush()
        les = Lesson(block_id=bl.id, title=title, tip=request.form.get('tip',''), order=Lesson.query.filter_by(block_id=bl.id).count()+1)
        db.session.add(les); db.session.flush()
        html_import = import_html_to_lesson_html(request.files.get('html_file'), request.files.getlist('html_assets'))
        sec_text = html_import if html_import is not None else process_inline_images(request.form.get('text',''))
        sec = Section(lesson_id=les.id, heading=request.form.get('heading','Výklad'), text=sec_text, interest=request.form.get('interest',''), activity=request.form.get('activity',''), order=1)
        db.session.add(sec); db.session.flush()
        image_map = save_question_images()
        handle_images(les, sec, image_map)
        add_questions_from_payload(les.id, sec.id, 'study', request.form.get('questions_json',''), request.form.get('study_questions',''), image_map)
        db.session.commit()
        return redirect(url_for('lesson', lesson_id=les.id))
    return render_template('lesson_form.html', course=course_from_lesson(None), lesson=None, section=None, subjects=Subject.query.all(), questions_json='[]', gallery_images=[])

@app.route('/teacher/lesson/<int:lesson_id>/edit', methods=['GET','POST'])
def edit_lesson(lesson_id):
    r=require_teacher();
    if r: return r
    les = db.session.get(Lesson, lesson_id)
    if not les: return 'Lekce nenalezena', 404
    sec = sorted(les.sections, key=lambda s:s.order)[0] if les.sections else Section(lesson_id=les.id, heading='Výklad')
    if request.method == 'POST':
        les.block.grade.subject.name = request.form.get('subject', les.block.grade.subject.name)
        les.block.grade.subject.icon = request.form.get('icon', les.block.grade.subject.icon)
        les.block.grade.name = request.form.get('grade', les.block.grade.name)
        les.block.title = request.form.get('block', les.block.title)
        les.title = request.form.get('title', les.title)
        les.tip = request.form.get('tip','')
        sec.heading = request.form.get('heading','Výklad')
        existing_text = sec.text
        html_import = import_html_to_lesson_html(request.files.get('html_file'), request.files.getlist('html_assets'))
        if html_import is not None:
            sec.text = html_import
        else:
            sec.text = process_inline_images(request.form.get('text', existing_text) or existing_text)
        sec.interest = request.form.get('interest','')
        sec.activity = request.form.get('activity','')
        Question.query.filter_by(lesson_id=les.id).delete()
        image_map = save_question_images()
        handle_images(les, sec, image_map)
        add_questions_from_payload(les.id, sec.id, 'study', request.form.get('questions_json',''), request.form.get('study_questions',''), image_map)
        db.session.commit()
        return redirect(url_for('lesson', lesson_id=les.id))
    return render_template('lesson_form.html', course=course_from_lesson(les), lesson=les, section=sec, subjects=Subject.query.all(), questions_json=questions_editor_json(les, 'study'), gallery_images=lesson_gallery(les))

def questions_editor_json(lesson, area):
    arr=[]
    for q in sorted([q for q in lesson.questions if q.area==area], key=lambda x:x.order):
        if q.qtype == 'choice':
            arr.append({'type':'choice','question':q.question,'options':json.loads(q.options_json or '[]'),'correct':json.loads(q.correct_json or '0')})
        elif q.qtype == 'image_choice':
            arr.append({'type':'image_choice','question':q.question,'images':json.loads(q.options_json or '[]'),'correct':json.loads(q.correct_json or '0')})
        else:
            try:
                opts = json.loads(q.options_json or '{}')
            except Exception:
                opts = {}
            arr.append({'type':'text','question':q.question,'roots':json.loads(q.roots_json or '[]'),'image': opts.get('image','') if isinstance(opts, dict) else ''})
    return json.dumps(arr, ensure_ascii=False)

def add_questions_from_payload(lesson_id, section_id, area, payload, fallback_raw='', image_map=None):
    try:
        data = json.loads(payload or '[]')
    except Exception:
        data = []
    image_map = image_map or {}
    order = 1
    if data:
        for item in data:
            typ = item.get('type','choice')
            question = (item.get('question') or item.get('prompt') or '').strip()
            if not question: continue
            if typ == 'text':
                roots = [r.strip() for r in item.get('roots',[]) if str(r).strip()]
                img = str(item.get('image','') or '').strip()
                img = image_map.get(img, img)
                db.session.add(Question(lesson_id=lesson_id, section_id=section_id, area=area, qtype='text', question=question, options_json=json.dumps({'image': img}, ensure_ascii=False), roots_json=json.dumps(roots, ensure_ascii=False), hint='Odpověď najdeš ve výkladu.', order=order))
            elif typ == 'image_choice':
                imgs = [image_map.get(str(o).strip(), str(o).strip()) for o in item.get('images',[]) if str(o).strip()]
                if len(imgs) < 2:
                    continue
                while len(imgs) < 4:
                    imgs.append(imgs[-1])
                correct = int(item.get('correct',0) or 0)
                db.session.add(Question(lesson_id=lesson_id, section_id=section_id, area=area, qtype='image_choice', question=question, options_json=json.dumps(imgs[:4], ensure_ascii=False), correct_json=json.dumps(correct), hint='Odpověď najdeš ve výkladu.', order=order))
            else:
                opts = [str(o).strip() for o in item.get('options',[]) if str(o).strip()]
                while len(opts) < 2: opts.append('')
                correct = int(item.get('correct',0) or 0)
                db.session.add(Question(lesson_id=lesson_id, section_id=section_id, area=area, qtype='choice', question=question, options_json=json.dumps(opts, ensure_ascii=False), correct_json=json.dumps(correct), hint='Odpověď najdeš ve výkladu.', order=order))
            order += 1
        return
    add_questions_from_text(lesson_id, section_id, area, fallback_raw or '')

def add_questions_from_text(lesson_id, section_id, area, raw):
    # formát: otázka | odpověď A | odpověď B | odpověď C | číslo správné odpovědi 1-3
    order = 1
    for line in raw.splitlines():
        line=line.strip()
        if not line or line.startswith('#'): continue
        parts=[p.strip() for p in line.split('|')]
        if len(parts)>=5:
            correct = max(0, int(parts[4])-1) if parts[4].isdigit() else 0
            db.session.add(Question(lesson_id=lesson_id, section_id=section_id, area=area, qtype='choice', question=parts[0], options_json=json.dumps(parts[1:4], ensure_ascii=False), correct_json=json.dumps(correct), hint='Odpověď najdeš ve výkladu.', order=order))
            order += 1




def _save_raw_image_bytes(raw, ext='png'):
    ext = (ext or 'png').lower().strip('.').replace('jpeg','jpg')
    if ext not in {'png','jpg','jpeg','gif','webp','svg'}:
        ext = 'png'
    name = datetime.now().strftime('%Y%m%d%H%M%S_') + uuid.uuid4().hex[:10] + '.' + ext
    (UPLOADS / name).write_bytes(raw)
    return name


def _decode_text_bytes(data):
    for enc in ('utf-8-sig', 'utf-8', 'cp1250', 'windows-1250', 'latin-1'):
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode('utf-8', errors='ignore')


def import_html_to_lesson_html(html_file, asset_files):
    """Naimportuje hotový HTML výklad.

    Učitel si připraví výklad mimo aplikaci (např. převod DOCX -> HTML přes pandoc/Word).
    V aplikaci vybere HTML soubor a případně obrázky ze stejné složky.
    Funkce zkopíruje obrázky do trvalého úložiště uploads a přepíše cesty v HTML.
    """
    if not html_file or not html_file.filename:
        return None
    filename = secure_filename(html_file.filename or '')
    if not filename.lower().endswith(('.html', '.htm')):
        raise ValueError('Vyber soubor ve formátu .html nebo .htm.')

    html_text = _decode_text_bytes(html_file.read())

    # Pokud je to celá stránka, vezmeme hlavně obsah body, aby se do lekce netáhla hlavička dokumentu.
    m = re.search(r'<body[^>]*>(.*?)</body>', html_text, flags=re.I | re.S)
    if m:
        html_text = m.group(1)

    # Odstraníme prvky, které do vloženého výkladu nepatří.
    html_text = re.sub(r'<script\b[^>]*>.*?</script>', '', html_text, flags=re.I | re.S)
    html_text = re.sub(r'<style\b[^>]*>.*?</style>', '', html_text, flags=re.I | re.S)
    html_text = re.sub(r'<link\b[^>]*>', '', html_text, flags=re.I | re.S)
    html_text = re.sub(r'<meta\b[^>]*>', '', html_text, flags=re.I | re.S)

    # Uložíme všechny obrázky, které učitel přiložil k HTML, a namapujeme je podle názvu souboru.
    image_map = {}
    for f in asset_files or []:
        if not f or not f.filename:
            continue
        if not (f.mimetype or '').startswith('image/') and not f.filename.lower().endswith(('.png','.jpg','.jpeg','.gif','.webp','.svg')):
            continue
        original_name = Path(secure_filename(Path(f.filename).name)).name
        saved = save_upload(f)
        if saved:
            image_map[original_name] = saved
            image_map[original_name.lower()] = saved

    # Přepíšeme src obrázků. Umíme i data:image z HTML.
    def replace_src(match):
        prefix, src, suffix = match.group(1), match.group(2), match.group(3)
        src_clean = src.strip()
        if src_clean.startswith('data:image/'):
            dm = re.match(r'data:(image/[^;]+);base64,(.*)', src_clean, flags=re.I | re.S)
            if dm:
                mime = dm.group(1).lower()
                data = dm.group(2)
                ext = 'png'
                if 'jpeg' in mime or 'jpg' in mime: ext = 'jpg'
                elif 'gif' in mime: ext = 'gif'
                elif 'webp' in mime: ext = 'webp'
                elif 'svg' in mime: ext = 'svg'
                try:
                    saved = _save_raw_image_bytes(base64.b64decode(data), ext)
                    return f'{prefix}{url_for("uploads", filename=saved)}{suffix}'
                except Exception:
                    return match.group(0)
        if src_clean.startswith(('http://','https://','/uploads/','/static/','data:')):
            return match.group(0)
        parsed = urllib.parse.urlparse(src_clean)
        base = Path(urllib.parse.unquote(parsed.path)).name
        safe_base = secure_filename(base)
        saved = image_map.get(base) or image_map.get(base.lower()) or image_map.get(safe_base) or image_map.get(safe_base.lower())
        if saved:
            return f'{prefix}{url_for("uploads", filename=saved)}{suffix}'
        # Když obrázek nebyl přiložen, necháme cestu být a zobrazíme varování v náhledu přes alt/title pro snazší hledání.
        return match.group(0)

    html_text = re.sub(r'(src\s*=\s*["\'])([^"\']+)(["\'])', replace_src, html_text, flags=re.I)
    html_text = html_text.strip()
    if not html_text:
        raise ValueError('HTML soubor neobsahuje žádný výklad.')
    info = '<div class="docx-import-note"><b>Importováno z HTML:</b> ' + html.escape(filename) + '</div>'
    return info + '<div class="imported-html-content">' + html_text + '</div>'

def process_inline_images(html_text):
    """Uloží obrázky vložené do CKEditoru jako data:image/... a přepíše je na /uploads/...
    Tím zachráníme obrázky vložené přes Ctrl+V, které se jinak po uložení ztratí.
    """
    if not html_text:
        return ''

    def repl(match):
        mime = match.group(1).lower()
        data = match.group(2)
        ext = 'png'
        if 'jpeg' in mime or 'jpg' in mime:
            ext = 'jpg'
        elif 'gif' in mime:
            ext = 'gif'
        elif 'webp' in mime:
            ext = 'webp'
        elif 'svg' in mime:
            ext = 'svg'
        try:
            raw = base64.b64decode(data)
        except Exception:
            return match.group(0)
        name = datetime.now().strftime('%Y%m%d%H%M%S_') + uuid.uuid4().hex[:10] + '.' + ext
        (UPLOADS / name).write_bytes(raw)
        return 'src="' + url_for('uploads', filename=name) + '"'

    # src="data:image/png;base64,..."
    html_text = re.sub(r'src=["\']data:(image/[^;]+);base64,([^"\']+)["\']', repl, html_text)
    return html_text

def save_upload(file):
    if not file or not file.filename: return ''
    name = datetime.now().strftime('%Y%m%d%H%M%S_') + secure_filename(file.filename)
    file.save(UPLOADS / name)
    return name

def save_question_images():
    """Uloží obrázky vložené přímo u otázek.
    V JSONu editor používá odkaz ve tvaru __file__:nazev_pole.
    Tady ho převedeme na reálně uložený soubor v trvalém úložišti uploads.
    """
    image_map = {}
    for field_name, f in request.files.items():
        if not field_name.startswith('qimg_'):
            continue
        if not f or not f.filename:
            continue
        original = secure_filename(f.filename)
        saved = save_upload(f)
        if saved:
            image_map[f'__file__:{field_name}'] = saved
            image_map[original] = saved
            image_map[f.filename] = saved
    return image_map

# Starší název necháváme kvůli kompatibilitě, kdyby někde zůstal odkaz.
def save_gallery_images():
    return save_question_images()

def handle_images(les, sec, image_map=None):
    image_map = image_map or {}
    h = save_upload(request.files.get('hero_image'))
    if h: les.hero_image = h
    # Obrázky výkladu se vkládají přímo přes CKEditor a ukládají se v endpointu /teacher/upload-image.

@app.route('/uploads/<filename>')
def uploads(filename):
    return send_from_directory(UPLOADS, filename)

@app.route('/teacher/upload-image', methods=['POST'])
def upload_editor_image():
    r = require_teacher()
    if r:
        return jsonify({'error': 'Nepřihlášený uživatel.'}), 401
    f = request.files.get('upload')
    if not f or not f.filename:
        return jsonify({'error': 'Nebyl vybrán žádný obrázek.'}), 400
    if not (f.mimetype or '').startswith('image/'):
        return jsonify({'error': 'Soubor musí být obrázek.'}), 400
    saved = save_upload(f)
    if not saved:
        return jsonify({'error': 'Obrázek se nepodařilo uložit.'}), 400
    return jsonify({'url': url_for('uploads', filename=saved)})

@app.route('/lessons/<slug>/images/<filename>')
def old_img(slug, filename):
    return send_from_directory(BASE/'lessons'/slug/'images', filename)

@app.route('/img/<filename>')
def img(filename):
    return send_from_directory(UPLOADS, filename)

def ensure_schema_updates():
    inspector = inspect(db.engine)
    required = {
        'result': {
            'focus_lost': 'INTEGER DEFAULT 0',
            'status': "VARCHAR(60) DEFAULT 'dokončeno'"
        },
        'interactive_result': {
            'focus_lost': 'INTEGER DEFAULT 0',
            'status': "VARCHAR(60) DEFAULT 'dokončeno'"
        },
        'informatics_submission': {
            'grade': 'INTEGER DEFAULT 5',
            'status': "VARCHAR(60) DEFAULT 'kontrola'",
            'focus_lost': 'INTEGER DEFAULT 0'
        },
        'math_attempt': {
            'answers_json': "TEXT DEFAULT '[]'"
        }
    }
    for table_name, columns in required.items():
        existing = {c['name'] for c in inspector.get_columns(table_name)} if inspector.has_table(table_name) else set()
        for column_name, sql_type in columns.items():
            if column_name not in existing:
                db.session.execute(text(
                    f'ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}'
                ))
    db.session.commit()


def seed():
    db.create_all()
    ensure_informatics_columns()
    ensure_schema_updates()
    restore_interactive_lessons_from_files()
    tu = os.getenv('TEACHER_USERNAME', 'dnadler').lower()
    tp = os.getenv('TEACHER_PASSWORD', 'change-me')
    tn = os.getenv('TEACHER_NAME', 'Učitel')
    teacher = User.query.filter_by(username=tu).first()
    if not teacher:
        db.session.add(User(username=tu, name=tn, role='teacher', password_hash=generate_password_hash(tp)))
    else:
        # Učitelský účet je řízený přes .env, aby heslo nebylo natvrdo v kódu.
        teacher.name = tn
        teacher.role = 'teacher'
        teacher.password_hash = generate_password_hash(tp)

    # Starý anonymní demo účet student/student nechceme.
    demo = User.query.filter_by(username='student').first()
    if demo:
        db.session.delete(demo)
        db.session.flush()

    # Ukázkový konkrétní student pro vyzkoušení přihlášení. Další studenty vytvoří učitel v editoru.
    if not User.query.filter_by(username='jan.novak').first():
        db.session.add(User(username='jan.novak', name='Jan Novák', role='student', password_hash=generate_password_hash('zive123')))
    if Subject.query.count()==0:
        # zkopíruj ukázkové obrázky ze staré lekce do uploads
        old = BASE/'lessons'/'bio6_01_co_je_zive'/'images'
        for n in ['1.jpg','2.jpg','3.jpg']:
            if (old/n).exists() and not (UPLOADS/n).exists():
                (UPLOADS/n).write_bytes((old/n).read_bytes())
        sub=Subject(name='Biologie', icon='🌱'); db.session.add(sub); db.session.flush()
        gr=Grade(subject_id=sub.id, name='6. ročník'); db.session.add(gr); db.session.flush()
        bl=Block(grade_id=gr.id, title='Blok 1 – Život kolem nás', order=1); db.session.add(bl); db.session.flush()
        les=Lesson(block_id=bl.id, title='Co je živé a neživé', tip='Čti výklad jako detektiv. Každá odpověď je někde v textu.', hero_image='1.jpg', order=1); db.session.add(les); db.session.flush()
        sec=Section(lesson_id=les.id, heading='Jak poznáme živé organismy?', text='Živé organismy rostou, dýchají, přijímají živiny, reagují na okolí, rozmnožují se a skládají se z buněk. Neživé věci tyto znaky života samy nevykazují. Pes, strom nebo houba jsou živé organismy. Kámen, lavice nebo sklenice jsou neživé věci.', interest='Některé věci mohou vypadat jako živé, například plamen svíčky se pohybuje, ale není organismus.', image='2.jpg', activity='Rozhlédni se kolem sebe a napiš si 3 živé organismy a 3 neživé věci.', order=1); db.session.add(sec); db.session.flush()
        db.session.add(InlineImage(section_id=sec.id, file='3.jpg', caption='Ukázka přírody: živé organismy a neživé prostředí.', order=1))
        raw='''Který příklad je živý organismus? | pes | kámen | lavice | 1
Co patří mezi znaky života? | přijímání živin | tvrdost kamene | barva lavice | 1
Která věc je neživá? | strom | houba | sklenice | 3'''
        add_questions_from_text(les.id, sec.id, 'study', raw)
    db.session.commit()

with app.app_context():
    seed()

if __name__ == '__main__':
    app.run(debug=True)
