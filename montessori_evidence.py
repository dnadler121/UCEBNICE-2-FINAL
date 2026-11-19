"""Teacher-only Montessori curriculum coverage tracking, separate from test scores."""
from flask import request, redirect, url_for, flash, render_template_string
from sqlalchemy import UniqueConstraint

SUBJECTS = ('Zeměpis', 'Biologie', 'Matematika', 'Fyzika', 'Chemie')
LEVELS = (0, 25, 50, 75, 100)

def register(app, db, User, require_teacher):
    class MontessoriStudent(db.Model):
        __tablename__ = 'montessori_evidence_student'
        id = db.Column(db.Integer, primary_key=True)
        first_name = db.Column(db.String(100), nullable=False)
        last_name = db.Column(db.String(100), nullable=False)
        grade = db.Column(db.Integer, nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=True)

    class MontessoriTopic(db.Model):
        __tablename__ = 'montessori_evidence_topic'
        id = db.Column(db.Integer, primary_key=True)
        subject = db.Column(db.String(30), nullable=False)
        grade = db.Column(db.Integer, nullable=False)
        title = db.Column(db.String(200), nullable=False)
        description = db.Column(db.Text, default='')
        __table_args__ = (UniqueConstraint('subject', 'grade', 'title', name='uq_montessori_topic'),)

    class MontessoriCoverage(db.Model):
        __tablename__ = 'montessori_evidence_coverage'
        id = db.Column(db.Integer, primary_key=True)
        student_id = db.Column(db.Integer, db.ForeignKey('montessori_evidence_student.id'), nullable=False)
        topic_id = db.Column(db.Integer, db.ForeignKey('montessori_evidence_topic.id'), nullable=False)
        level = db.Column(db.Integer, nullable=False, default=0)
        note = db.Column(db.Text, default='')
        __table_args__ = (UniqueConstraint('student_id', 'topic_id', name='uq_montessori_coverage'),)

    def teacher_only():
        return require_teacher()

    @app.route('/teacher/montessori', methods=['GET'])
    def montessori_evidence():
        denied = teacher_only()
        if denied: return denied
        students = MontessoriStudent.query.order_by(MontessoriStudent.last_name, MontessoriStudent.first_name).all()
        topics = MontessoriTopic.query.order_by(MontessoriTopic.subject, MontessoriTopic.grade, MontessoriTopic.title).all()
        selected = request.args.get('student', type=int)
        student = next((s for s in students if s.id == selected), None) if selected else (students[0] if students else None)
        topics = [t for t in topics if t.grade == student.grade] if student else []
        coverage = {c.topic_id: c for c in MontessoriCoverage.query.filter_by(student_id=student.id).all()} if student else {}
        return render_template_string(PAGE, students=students, student=student, topics=topics, coverage=coverage, subjects=SUBJECTS, levels=LEVELS)

    @app.route('/teacher/montessori/students', methods=['POST'])
    def montessori_add_student():
        denied = teacher_only()
        if denied: return denied
        first = request.form.get('first_name', '').strip()
        last = request.form.get('last_name', '').strip()
        grade = request.form.get('grade', type=int)
        if not first or not last or grade not in (6,7,8,9):
            flash('Vyplň jméno, příjmení a ročník 6–9.')
        else:
            s = MontessoriStudent(first_name=first, last_name=last, grade=grade)
            db.session.add(s); db.session.commit()
            return redirect(url_for('montessori_evidence', student=s.id))
        return redirect(url_for('montessori_evidence'))

    @app.route('/teacher/montessori/topics', methods=['POST'])
    def montessori_add_topic():
        denied = teacher_only()
        if denied: return denied
        subject = request.form.get('subject', '')
        grade = request.form.get('grade', type=int)
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        if subject not in SUBJECTS or grade not in (6,7,8,9) or not title:
            flash('Vyplň předmět, ročník a název tématu.')
        elif MontessoriTopic.query.filter_by(subject=subject, grade=grade, title=title).first():
            flash('Toto téma už existuje.')
        else:
            db.session.add(MontessoriTopic(subject=subject, grade=grade, title=title, description=description))
            db.session.commit()
        return redirect(url_for('montessori_evidence', student=request.form.get('student', type=int)))

    @app.route('/teacher/montessori/coverage', methods=['POST'])
    def montessori_save_coverage():
        denied = teacher_only()
        if denied: return denied
        sid = request.form.get('student', type=int)
        tid = request.form.get('topic', type=int)
        level = request.form.get('level', type=int)
        student_record = db.session.get(MontessoriStudent, sid) if sid is not None else None
        topic_record = db.session.get(MontessoriTopic, tid) if tid is not None else None
        if not student_record or not topic_record or student_record.grade != topic_record.grade or level not in LEVELS:
            flash('Neplatné hodnocení.')
        else:
            item = MontessoriCoverage.query.filter_by(student_id=sid, topic_id=tid).first()
            if item is None:
                item = MontessoriCoverage(student_id=sid, topic_id=tid)
                db.session.add(item)
            item.level = level
            item.note = request.form.get('note', '').strip()[:3000]
            db.session.commit()
        return redirect(url_for('montessori_evidence', student=sid) + '#tema-' + str(tid))

PAGE = '''<!doctype html><html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evidence výuky Montessori</title><style>
:root{font-family:system-ui,Arial;color:#142b49;background:#f3f7fd}*{box-sizing:border-box}body{margin:0}header{background:#12335b;color:white;padding:18px 28px;display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap}a{color:inherit}.layout{display:grid;grid-template-columns:290px minmax(0,1fr);gap:20px;padding:20px;max-width:1500px;margin:auto}.panel{background:white;border:1px solid #d8e2ef;border-radius:14px;padding:18px;margin-bottom:16px;box-shadow:0 2px 8px #163c6110}h1,h2,h3{margin:0 0 14px}h1{font-size:24px}h2{font-size:19px}input,select,textarea,button{font:inherit;padding:9px;border:1px solid #b9c9dc;border-radius:8px;max-width:100%}input,textarea{width:100%}button{background:#1164c1;color:white;cursor:pointer;border:0;font-weight:650}.student{display:block;padding:12px;border-radius:9px;text-decoration:none;border-bottom:1px solid #e5edf5}.student.active{background:#dcecff;color:#064b9e;font-weight:700}.row{display:flex;gap:9px;flex-wrap:wrap;align-items:center}.row>*{flex:1;min-width:80px}.topics{margin-top:14px}.topic{border:1px solid #dce6f0;border-radius:10px;margin:8px 0;overflow:hidden}.topic summary{cursor:pointer;padding:12px;background:#f2f7ff;display:flex;justify-content:space-between;gap:12px}.topic form{padding:12px}.choices{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}.choices label{padding:8px 10px;border:1px solid #c3d2e2;border-radius:7px;cursor:pointer}.choices label:has(input:checked){background:#b6ddff;border-color:#1164c1}.choices input{width:auto}.muted{color:#60748c;font-size:13px}.subject{border-top:2px solid #d9e6f5;padding-top:14px;margin-top:18px}.pill{background:#d8eaff;border-radius:30px;padding:5px 12px}.notice{background:#fff1d6;padding:12px;border-radius:8px;margin-bottom:12px}@media(max-width:760px){.layout{grid-template-columns:1fr;padding:10px}}
</style></head><body><header><strong>📘 Učebnice Final · Evidence výuky Montessori</strong><a href="{{ url_for('teacher_home') }}">← Zpět do administrace</a></header><div class="layout"><aside><div class="panel"><h2>Studenti Montessori</h2>{% for s in students %}<a class="student {% if student and student.id==s.id %}active{% endif %}" href="{{url_for('montessori_evidence',student=s.id)}}">🎓 {{s.first_name}} {{s.last_name}} <span class="muted">{{s.grade}}. ročník</span></a>{% else %}<p class="muted">Zatím žádní studenti.</p>{% endfor %}</div><div class="panel"><h3>+ Přidat studenta</h3><form action="{{url_for('montessori_add_student')}}" method="post"><p><input name="first_name" placeholder="Jméno" required></p><p><input name="last_name" placeholder="Příjmení" required></p><p><select name="grade" required>{% for g in [6,7,8,9] %}<option value="{{g}}">{{g}}. ročník</option>{% endfor %}</select></p><button>Uložit studenta</button></form></div></aside><main>{% with messages=get_flashed_messages() %}{% for m in messages %}<div class="notice">{{m}}</div>{% endfor %}{% endwith %}<div class="panel"><h2>+ Nové společné téma</h2><p class="muted">Téma se automaticky zobrazí pouze studentům vybraného ročníku, včetně nově přidaných. Výchozí hodnocení je 0 %.</p><form method="post" action="{{url_for('montessori_add_topic')}}"><input type="hidden" name="student" value="{{student.id if student else ''}}"><div class="row"><select name="subject">{% for sub in subjects %}<option>{{sub}}</option>{% endfor %}</select><select name="grade">{% for g in [6,7,8,9] %}<option value="{{g}}">{{g}}. ročník</option>{% endfor %}</select><input name="title" placeholder="Název tématu (např. Přímočarý pohyb)" required></div><p><input name="description" placeholder="Cíl tématu (nepovinné)"></p><button>Přidat téma vybranému ročníku</button></form></div>{% if student %}<div class="panel"><h1>🎓 {{student.first_name}} {{student.last_name}} <span class="pill">{{student.grade}}. ročník</span></h1><p class="muted">Hodnocení znamená míru probrání tématu, nikoli známku ani výsledek testu.</p>{% for sub in subjects %}<section class="subject"><h2>{{sub}}</h2>{% set st = topics|selectattr('subject','equalto',sub)|list %}{% if st %}{% for g in [6,7,8,9] %}{% set gt = st|selectattr('grade','equalto',g)|list %}{% if gt %}<h3>{{g}}. ročník</h3><div class="topics">{% for t in gt %}{% set c = coverage.get(t.id) %}<details class="topic" id="tema-{{t.id}}"><summary><strong>{{t.title}}</strong><span class="pill">{{c.level if c else 0}} %</span></summary><form method="post" action="{{url_for('montessori_save_coverage')}}"><input type="hidden" name="student" value="{{student.id}}"><input type="hidden" name="topic" value="{{t.id}}">{% if t.description %}<p>{{t.description}}</p>{% endif %}<strong>Úroveň probraného tématu</strong><div class="choices">{% for lvl in levels %}<label><input type="radio" name="level" value="{{lvl}}" {% if (c.level if c else 0)==lvl %}checked{% endif %}> {{lvl}} %</label>{% endfor %}</div><label>Poznámka učitele<textarea name="note" rows="2" placeholder="Co student zvládl, co ještě procvičit">{{c.note if c and c.note else ''}}</textarea></label><p><button>Uložit hodnocení</button></p></form></details>{% endfor %}</div>{% endif %}{% endfor %}{% else %}<p class="muted">Zatím bez témat. Přidej je formulářem nahoře.</p>{% endif %}</section>{% endfor %}</div>{% else %}<div class="panel">Nejprve přidej studenta vlevo.</div>{% endif %}</main></div></body></html>'''
