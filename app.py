from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from sqlalchemy.orm import scoped_session
from models.model import Database, Student, Question2, Option2, Answer2, Result2, Result40
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import random

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'
db_session = scoped_session(Database.get_session)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        matricula = request.form['matricula']
        password = request.form['password']

        new_student = Student(
            first_name=first_name,
            last_name=last_name,
            email=email,
            matricula=matricula,
            password=password
        )

        try:
            db_session.add(new_student)
            db_session.commit()

            session['student_id'] = new_student.student_id
            session['attempt_count'] = 0  # Inicializa el contador de intentos

        except IntegrityError as e:
            db_session.rollback()
            if 'email' in str(e.orig):
                return "El correo electrónico ya está registrado.", 400
            elif 'matricula' in str(e.orig):
                return "La matrícula ya está registrada.", 400
            else:
                return "Error en el registro.", 400

        return redirect(url_for('menu'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        matricula = request.form['matricula']
        password = request.form['password']

        student = db_session.query(Student).filter_by(matricula=matricula, password=password).first()

        if student:
            session['student_id'] = student.student_id
            return redirect(url_for('menu'))
        else:
            return "Matrícula o contraseña incorrectos.", 400

    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

@app.route('/menu')
def menu():
    student_id = session.get('student_id')
    if not student_id:
        return redirect(url_for('login'))
    
    result_20 = db_session.query(Result2).filter_by(student_id=student_id).first()
    attempts_20 = result_20.intentos if result_20 else 0

    attempts_40 = db_session.query(Result40).filter_by(student_id=student_id).count()

    return render_template('menu.html', attempts_20=attempts_20, attempts_40=attempts_40)

@app.route('/start_quiz')
def start_quiz():
    student_id = session.get('student_id')
    if not student_id:
        return redirect(url_for('login'))
    
    result = db_session.query(Result2).filter_by(student_id=student_id).first()
    attempt_count = result.intentos if result else 0

    if attempt_count >= 5:
        return redirect(url_for('limit_reached'))

    session['current_question_index'] = 0
    session['correct_answers'] = 0  # Inicializa el contador de respuestas correctas

    # Seleccionar 20 preguntas aleatoriamente de la tabla Question2
    questions = db_session.query(Question2).all()
    selected_questions = random.sample(questions, 20)
    session['questions'] = [question.question_id for question in selected_questions]

    return redirect(url_for('show_question'))

@app.route('/question')
def show_question():
    current_question_index = session.get('current_question_index', 0)
    questions = session.get('questions', [])

    if current_question_index >= len(questions):
        return redirect(url_for('quiz_complete'))

    question_id = questions[current_question_index]
    question = db_session.query(Question2).filter_by(question_id=question_id).first()
    options = db_session.query(Option2).filter_by(question_id=question.question_id).all()
    
    return render_template('question.html', question=question, options=options)

@app.route('/answer', methods=['POST'])
def answer_question():
    try:
        student_id = session['student_id']
        question_id = request.form['question_id']
        selected_option_id = request.form.get('option')

        if selected_option_id is None:
            register_incorrect_answer(student_id, question_id)
        else:
            selected_option = db_session.query(Option2).filter_by(option_id=selected_option_id).first()

            if selected_option.is_correct:
                session['correct_answers'] += 1

            new_answer = Answer2(
                student_id=student_id,
                question_id=question_id,
                selected_option_id=selected_option_id
            )

            db_session.add(new_answer)
            db_session.commit()

            session['current_question_index'] += 1

        return redirect(url_for('show_question'))
    except Exception as e:
        return str(e), 400

@app.route('/quiz_complete')
def quiz_complete():
    try:
        student_id = session.get('student_id')
        if not student_id:
            return "Error: student_id no encontrado en la sesión", 400

        correct_answers = session.get('correct_answers', 0)
        total_questions = len(session.get('questions', []))

        # Cada reactivo vale 5 puntos
        total_points = correct_answers * 5
        max_points = total_questions * 5
        score_percentage = (total_points / max_points) * 100

        # Determinar el nivel de inglés basado en los aciertos
        if score_percentage >= 90:
            nivel = 'Avanzado'
        elif score_percentage >= 70:
            nivel = 'Intermedio'
        else:
            nivel = 'Básico'

        aprobado = score_percentage >= 70

        print(f"student_id: {student_id}, correct_answers: {correct_answers}, total_points: {total_points}, score_percentage: {score_percentage}, nivel: {nivel}, aprobado: {aprobado}")

        # Intentar obtener el resultado existente
        result = db_session.query(Result2).filter_by(student_id=student_id).first()
        if result:
            print("Resultado existente encontrado, actualizando...")
            result.intentos += 1
            result.puntaje_total = correct_answers
            result.nivel = nivel
            result.aprobado = aprobado
            result.score_percentage = score_percentage
            result.total_points = total_points
        else:
            print("No se encontró resultado existente, creando uno nuevo...")
            # Si no existe, crear uno nuevo
            result = Result2(
                student_id=student_id,
                puntaje_total=correct_answers,
                intentos=1,
                nivel=nivel,
                aprobado=aprobado,
                score_percentage=score_percentage,
                total_points=total_points
            )
            db_session.add(result)

        # Confirmar los cambios
        db_session.commit()

        return render_template('quiz_complete.html', 
                               correct_answers=correct_answers, 
                               total_questions=total_questions, 
                               total_points=total_points,
                               score_percentage=score_percentage, 
                               nivel=nivel, 
                               aprobado=aprobado, 
                               intentos=result.intentos)
    except IntegrityError as e:
        db_session.rollback()
        return f"IntegrityError: {str(e)}", 500
    except Exception as e:
        db_session.rollback()  # Asegurar rollback en caso de cualquier otro error
        return f"Error: {str(e)}", 500

@app.route('/start_quiz_40')
def start_quiz_40():
    student_id = session.get('student_id')
    if not student_id:
        return redirect(url_for('login'))

    attempt_count = db_session.query(Result40).filter_by(student_id=student_id).count()
    if attempt_count >= 2:
        return redirect(url_for('limit_reached'))

    session['current_question_index'] = 0
    session['correct_answers'] = 0  # Inicializa el contador de respuestas correctas

    # Seleccionar 40 preguntas aleatoriamente de la tabla Question2
    questions = db_session.query(Question2).all()
    selected_questions = random.sample(questions, 40)
    session['questions'] = [question.question_id for question in selected_questions]

    return redirect(url_for('show_question_40'))

@app.route('/question_40')
def show_question_40():
    current_question_index = session.get('current_question_index', 0)
    questions = session.get('questions', [])

    if current_question_index >= len(questions):
        return redirect(url_for('quiz_complete_40'))

    question_id = questions[current_question_index]
    question = db_session.query(Question2).filter_by(question_id=question_id).first()
    options = db_session.query(Option2).filter_by(question_id=question.question_id).all()
    
    return render_template('question_40.html', question=question, options=options)

@app.route('/answer_40', methods=['POST'])
def answer_question_40():
    try:
        student_id = session['student_id']
        question_id = request.form['question_id']
        selected_option_id = request.form.get('option')

        if selected_option_id is None:
            register_incorrect_answer(student_id, question_id)
        else:
            selected_option = db_session.query(Option2).filter_by(option_id=selected_option_id).first()

            if selected_option.is_correct:
                session['correct_answers'] += 1

            new_answer = Answer2(
                student_id=student_id,
                question_id=question_id,
                selected_option_id=selected_option_id
            )

            db_session.add(new_answer)
            db_session.commit()

            session['current_question_index'] += 1

        return redirect(url_for('show_question_40'))
    except Exception as e:
        return str(e), 400

@app.route('/quiz_complete_40')
def quiz_complete_40():
    try:
        student_id = session['student_id']
        correct_answers = session.get('correct_answers', 0)
        total_questions = len(session.get('questions', []))

        # Cada reactivo vale 2.5 puntos
        total_points = correct_answers * 2.5
        max_points = total_questions * 2.5
        score_percentage = (total_points / max_points) * 100

        # Determinar el nivel de inglés basado en los aciertos
        if score_percentage >= 90:
            nivel = 'Avanzado'
        elif score_percentage >= 70:
            nivel = 'Intermedio'
        else:
            nivel = 'Básico'

        aprobado = score_percentage >= 70

        attempt_count = db_session.query(Result40).filter_by(student_id=student_id).count() + 1

        if attempt_count <= 2:  # Asegúrate de que el número de intentos no exceda el límite
            new_resultado = Result40(
                student_id=student_id,
                puntaje_total=correct_answers,
                intento=attempt_count,
                nivel=nivel,
                aprobado=aprobado,
                score_percentage=score_percentage,
                total_points=total_points
            )

            db_session.add(new_resultado)
            db_session.commit()

        return render_template('quiz_complete_40.html', 
                               correct_answers=correct_answers, 
                               total_questions=total_questions, 
                               total_points=total_points,
                               score_percentage=score_percentage, 
                               nivel=nivel, 
                               aprobado=aprobado, 
                               intentos=attempt_count)
    except IntegrityError as e:
        db_session.rollback()
        return f"IntegrityError: {str(e)}", 500
    except Exception as e:
        db_session.rollback()  # Asegurar rollback en caso de cualquier otro error
        return f"Error: {str(e)}", 500

@app.route('/time_up', methods=['POST'])
def time_up():
    data = request.get_json()
    student_id = data.get('student_id')
    question_id = data.get('question_id')

    if student_id and question_id:
        # Marcar la respuesta como incorrecta
        new_answer = Answer2(
            student_id=student_id,
            question_id=question_id,
            selected_option_id=None  # Opción seleccionada como None para indicar que no respondió
        )

        db_session.add(new_answer)
        db_session.commit()

        # Avanzar a la siguiente pregunta
        session['current_question_index'] += 1

    return jsonify({"message": "Time is up"}), 200

def register_incorrect_answer(student_id, question_id):
    new_answer = Answer2(
        student_id=student_id,
        question_id=question_id,
        selected_option_id=None  # Opción seleccionada como None para indicar que no respondió
    )

    db_session.add(new_answer)
    db_session.commit()

    session['current_question_index'] += 1


@app.route('/limit_reached')
def limit_reached():
    return render_template('limit_reached.html')

if __name__ == '__main__':
    app.run(debug=True)
