import subprocess
import sys
from flask import request, jsonify, render_template, redirect, url_for, session
from flask_jwt_extended import create_access_token, jwt_required, set_access_cookies, unset_jwt_cookies
from models import User, db
import logging
from blockchain import contract

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

def decrypt_id_aes(ciphertext, iv, key):
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
    
    return plaintext

def execute_subprocess_command(comando):
    process = subprocess.run(comando, capture_output=True, text=True)
    if process.returncode == 0:
        return process.stdout.strip()  # Restituisce l'output come stringa, senza spazi bianchi aggiuntivi
    else:
        raise Exception(f"Subprocess error: {process.stderr}")

def configure_routes(app):

    @app.before_request
    def create_tables():
        db.create_all()
        admin_exists = User.query.filter_by(username='admin').first()
        if not admin_exists:
            admin = User(username='admin', password='pass')
            db.session.add(admin)
            db.session.commit()
            logging.info('Admin user and database tables created')

    @app.route('/')
    def home():
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return render_template('api_interface.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                access_token = create_access_token(identity=username)
                session['logged_in'] = True
                resp = redirect(url_for('home'))
                set_access_cookies(resp, access_token)
                logging.info(f'User {username} logged in successfully')
                return resp
            logging.warning('Invalid login attempt')
            return '<h1>Invalid username or password</h1>'
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session['logged_in'] = False
        resp = redirect(url_for('login'))
        unset_jwt_cookies(resp)
        logging.info('User logged out')
        return resp

    @app.route('/register', methods=['POST'])
    @jwt_required()
    def register():
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return 'Missing username or password', 400
        if User.query.filter_by(username=username).first():
            return 'Username already exists', 400
        new_user = User(username=username, password=password)
        try:
            db.session.add(new_user)
            db.session.commit()
            logging.info(f'User {username} registered successfully')
        except Exception as e:
            logging.error(f"Error saving user: {e}")
            db.session.rollback()
        return 'User created successfully', 201

    @app.route('/users')
    @jwt_required()
    def show_users():
        users = User.query.all()
        logging.info('Displayed all users')
        return render_template('users.html', users=users)

    @app.route('/remove_user/<int:user_id>', methods=['POST'])
    @jwt_required()
    def remove_user(user_id):
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        logging.info(f'User {user_id} removed')
        return redirect(url_for('show_users'))

    @app.route('/count_registrations/<course_name>', methods=['GET'])
    @jwt_required()
    def count_registrations(course_name):
        count = contract.functions.countRegistrations(course_name).call()
        logging.info(f'Queried registrations for {course_name}: {count}')
        return jsonify({'course_name': course_name, 'registrations': count})

    @app.route('/count_attendances/<course_name>/<lesson_name>', methods=['GET'])
    @jwt_required()
    def count_lesson_attendances(course_name, lesson_name):
        count = contract.functions.countLessonAttendances(course_name, lesson_name).call()
        logging.info(f'Queried attendances for course {course_name} and lesson {lesson_name}: {count}')
        return jsonify({'course_name': course_name, 'lesson_name': lesson_name, 'attendances': count})

    @app.route('/count_exam_participations/<course_name>/<exam_day>/<exam_month>/<exam_year>', methods=['GET'])
    @jwt_required()
    def count_exam_participations(course_name, exam_day, exam_month, exam_year):
        exam_date = exam_day + "/" + exam_month + "/" + exam_year
        count = contract.functions.countExamParticipations(course_name, exam_date).call()
        logging.info(f'Queried exam participations for course {course_name} on {exam_date}: {count}')
        return jsonify({'course_name': course_name, 'exam_date': exam_date, 'participations': count})

    @app.route('/get_records_by_operation/<operation_type>/<course_name>/<additional_info>', methods=['GET'])
    @app.route('/get_records_by_operation/<operation_type>/<course_name>/<exam_day>/<exam_month>/<exam_year>', methods=['GET'])
    @jwt_required()
    def get_records_by_operation(operation_type, course_name, additional_info=None, exam_day=None, exam_month=None, exam_year=None):
        try:
            if operation_type == "Esame":
                # Ricostruisce la data dell'esame dal giorno, mese e anno
                if exam_day and exam_month and exam_year:
                    exam_date = f"{exam_day}/{exam_month}/{exam_year}"
                    # Chiamata al contratto con la data dell'esame
                    result = contract.functions.getRecordsByOperation(operation_type, course_name, exam_date).call()
                    logging.info(f'Retrieved records for operation {operation_type} on course {course_name} with exam date {exam_date}')
                else:
                    logging.error("Missing date parts for exam")
                    return jsonify({'error': 'Missing date parts for exam.'}), 400
            else:
                # Chiamata al contratto con additional_info
                result = contract.functions.getRecordsByOperation(operation_type, course_name, additional_info).call()
                logging.info(f'Retrieved records for operation {operation_type} on course {course_name} with info {additional_info}')
        except Exception as e:
            logging.error(f"Error calling Solidity function: {e}")
            return jsonify({'error': 'Error retrieving records from blockchain.'}), 500

        # Log per verificare l'inizio del subprocesso
        logging.info('Starting subprocess to retrieve key and IV')
        
        try:
            # Preparazione dei parametri per il comando subprocesso
            op = str(operation_type)
            cs = str(course_name)
            ai = str(exam_date if operation_type == "Esame" else additional_info)

            # Comando per eseguire lo script getKeyIV.py
            comando = [sys.executable, "/Users/laplace/Desktop/Iots_Sdd_Project/remoteAccessAPI/AttendanceSystem/flaskApp/getKIV.py", op, cs, ai]
            
            # Esecuzione del comando subprocesso
            keyChainResult = execute_subprocess_command(comando)
            logging.info(f'Subprocess output: {keyChainResult}')  # Log dell'output del subprocesso

            if not keyChainResult:
                logging.error('Subprocess failed or returned empty result')
                return jsonify({'error': 'Subprocess failed or returned empty result.'}), 500
        except Exception as e:
            logging.error(f"Error executing subprocess: {e}")
            return jsonify({'error': 'Error executing subprocess.'}), 500

        try:
            resultski = keyChainResult.split()
            if len(resultski) >= 2:
                k, iv = eval(resultski[0]), eval(resultski[1])
                logging.info('Key and IV data successfully retrieved')
            else:
                logging.info('Key and IV data not found')
                return jsonify({'error': 'Dati Chiave ed IV non pervenuti.'}), 500
        except Exception as e:
            logging.error(f"Error processing subprocess output: {e}")
            return jsonify({'error': 'Error processing subprocess output.'}), 500

        records = []
        try:
            for rec in result:
                try:
                    encrypted_id = eval(rec[3])
                    decrypted_id = decrypt_id_aes(encrypted_id, iv, k)
                    decrypted_id_str = decrypted_id.decode('utf-8')
                    records.append({
                        'operationType': rec[0],
                        'courseName': rec[1],
                        'additionalInfo': rec[2],
                        'encryptedId': decrypted_id_str
                    })
                except Exception as e:
                    logging.error(f"Failed to decrypt or process record: {e}")
                    return jsonify({'error': 'Failed to decrypt or process record.'}), 500
        except Exception as e:
            logging.error(f"Error processing records: {e}")
            return jsonify({'error': 'Error processing records.'}), 500

        return jsonify(records)

    from errors import configure_error_handlers
    configure_error_handlers(app)
