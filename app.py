import os, json, unicodedata, random, html, re, base64, uuid, urllib.parse, urllib.request, urllib.error, zipfile, shutil, importlib.util, tempfile, threading
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, render_template_string, request, jsonify, session, redirect, url_for, send_from_directory, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
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

def student_overview_rows():
    rows = []
    for stu in User.query.filter_by(role='student').order_by(User.name).all():
        pr = current_progress_for_student(stu.id)
        res = last_result_for_student(stu.id)
        rows.append({'student': stu, 'progress': pr, 'result': res})
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
    if kind not in ('html', 'interactive') or not key:
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
        else:
            lesson_item = InteractiveLesson.query.filter_by(slug=key).first()
            if lesson_item:
                db.session.add(InteractiveResult(
                    user_id=user.id, interactive_lesson_id=lesson_item.id,
                    percent=0, grade=5, focus_lost=3,
                    status='ukončeno po 3 opuštěních'
                ))
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
        ).count() + InteractiveLesson.query.filter_by(subject='matematika', is_published=True).count(),
        'informatika': Lesson.query.join(Block).join(Grade).join(Subject).filter(
            Subject.name.ilike('%informat%'), Lesson.is_published.is_(True)
        ).count() + InteractiveLesson.query.filter_by(subject='informatika', is_published=True).count(),
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
    return render_template(
        'catalog.html',
        course={'subject': title, 'grade':'', 'block':'', 'icon':icon},
        lesson=None,
        subjects=subjects,
        interactive_groups=interactive_groups,
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
    return render_template(
        'teacher.html',
        course=course_from_lesson(None),
        subjects=subjects,
        students=students,
        student_rows=student_overview_rows(),
        interactive_lessons=interactive_lessons
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
    return render_template(
        'database.html',
        course=course_from_lesson(None),
        student_rows=student_overview_rows(),
        html_results=html_results,
        interactive_results=interactive_results
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


@app.route('/teacher/results/delete-all', methods=['POST'])
def delete_all_results():
    r=require_teacher()
    if r: return r
    Result.query.delete()
    InteractiveResult.query.delete()
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
