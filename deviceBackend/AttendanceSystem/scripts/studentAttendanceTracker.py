import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

import json
import sqlite3
import subprocess
import sys
from datetime import datetime

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import threading


class AttendanceSystem:
    def __init__(self):
        self.conn = None
        self.course_name = ""
        self.student_id = ""
        self.student_name = ""
        self.student_surname = ""
        self.tag_id = ""
        self.aes_key = None
        self.aes_iv = None
        self.lesson_number = ""
        self.exam_date = ""
        self.students_list = []

        self.init_gui()

    def create_connection(self, database):
        """Crea una connessione a un database SQLite specificato."""
        self.conn = None
        try:
            self.conn = sqlite3.connect(database)
            print(f"Connessione al database {database} avvenuta con successo.")
        except sqlite3.Error as e:
            print("Connessione al database fallita.")
        return self.conn

    def create_table(self):
        """Crea la tabella degli studenti se non esiste già."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS studenti (
                    id TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    cognome TEXT NOT NULL,
                    matricola TEXT NOT NULL
                )
            """)
        except sqlite3.Error as e:
            print(e)

    def insert_student(self, id, nome, cognome, matricola):
        """
        Inserisce un nuovo studente nel database.
        Controlla prima se lo studente esiste già basandosi sulla matricola.
        """
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM studenti WHERE matricola = ?"
            cursor.execute(query, (matricola,))
            if cursor.fetchone():
                print("Studente già presente nel db.")
                return 0
            else:
                cursor.execute("""
                    INSERT INTO studenti (id, nome, cognome, matricola)
                    VALUES (?, ?, ?, ?)
                """, (id, nome, cognome, matricola))
                self.conn.commit()
                print("Studente inserito con successo.")
                return 1
        except sqlite3.Error as e:
            print(e)

    def get_student_by_id(self, student_id):
        """Recupera i dati dello studente dal database basandosi sull'ID."""
        try:
            cursor = self.conn.cursor()
            query = "SELECT nome, cognome, matricola FROM studenti WHERE id = ?"
            cursor.execute(query, (student_id,))
            result = cursor.fetchone()
            if result:
                print(f"Dati trovati: {result}.")
                return list(result)
            else:
                print(f"Nessun dato trovato per lo studente con ID {student_id}.")
                return []
        except sqlite3.Error as e:
            print(f"Errore durante il recupero dello studente con ID {student_id}: {e}.")
            return []

    # Funzioni di cifratura

    def generate_aes_key(self):
        """Genera una chiave AES casuale di 32 byte evitando spazi vuoti."""
        while True:
            key = os.urandom(32)
            if not any(b == 32 for b in key):  # Evita chiavi con byte di spazio (32)
                return key

    def generate_aes_iv(self):
        """Genera un vettore di inizializzazione (IV) AES casuale di 16 byte evitando spazi vuoti."""
        while True:
            iv = os.urandom(16)
            if not any(b == 32 for b in iv):
                return iv

    def encrypt_id_aes(self, id_bytes, iv, key):
        """Cifra un ID utilizzando AES in modalità CFB."""
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(id_bytes) + padder.finalize()

        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        return ciphertext

    def decrypt_id_aes(self, ciphertext, iv, key):
        """Decifra un ID utilizzando AES in modalità CFB."""
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
        decryptor = cipher.decryptor()

        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
        return plaintext

    # Funzioni di utilità

    def execute_subprocess_command(self, comando):
        """Esegue un comando subprocess e ritorna l'output."""
        process = subprocess.run(comando, capture_output=True, text=True)
        if process.returncode == 0:
            return process.stdout.strip()  # Restituisce l'output come stringa, senza spazi bianchi aggiuntivi
        else:
            raise Exception(f"Subprocess error: {process.stderr}")

    def load_image(self, path, width, height):
        """Carica un'immagine, ridimensiona e la converte in un oggetto compatibile con Tkinter."""
        if not os.path.exists(path):
            messagebox.showerror("Error", f"Image file not found: {path}")
            return None
        image = Image.open(path).resize((width, height), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)

    def center_window(self, window, width, height):
        """Centra la finestra Tkinter sullo schermo."""
        screen_width, screen_height = window.winfo_screenwidth(), window.winfo_screenheight()
        x, y = (screen_width // 2) - (width // 2), (screen_height // 2) - (height // 2)
        return f'{width}x{height}+{x}+{y}'

    # Funzioni GUI e di controllo 

    def check_course_name(self):
        """Verifica se il nome del corso è stato inserito e abilita i pulsanti appropriati."""
        self.course_name = self.course_entry.get().strip()
        state = tk.NORMAL if self.course_name else tk.DISABLED
        self.registration_button.config(state=state)
        self.lesson_button.config(state=state)
        self.exam_button.config(state=state)

    def on_button_click(self, button):
        """Gestisce il click dei pulsanti per selezionare diverse operazioni."""
        self.course_name = self.course_entry.get().strip()
        if not self.course_name:
            messagebox.showwarning("Input Required", "Please enter the course name before proceeding.")
            return

        database = f"{self.course_name}.db"
        self.create_connection(database)

        if button == "Registration":
            self.show_registration_fields(True)
            self.registration_frame.pack(fill=tk.X, padx=20, pady=10)
        elif button == "Lesson":
            self.show_lesson_fields(True)
            self.lesson_frame.pack(fill=tk.X, padx=20, pady=10)
        elif button == "Exam":
            self.show_exam_fields(True)
            self.exam_frame.pack(fill=tk.X, padx=20, pady=10)

        if button == "Registration":
            self.id_entry.focus_set()
        elif button == "Lesson":
            self.lesson_number_entry.focus_set()
        elif button == "Exam":
            self.exam_date_entry.focus_set()

    def show_registration_fields(self, visible):
        """Mostra o nasconde i campi di registrazione."""
        if visible:
            self.registration_frame.pack(fill=tk.X, padx=20, pady=10)
            self.lesson_frame.pack_forget()
            self.exam_frame.pack_forget()
        else:
            self.registration_frame.pack_forget()

    def show_lesson_fields(self, visible):
        """Mostra o nasconde i campi per la lezione."""
        if visible:
            self.lesson_frame.pack(fill=tk.X, padx=20, pady=10)
            self.registration_frame.pack_forget()
            self.exam_frame.pack_forget()
        else:
            self.lesson_frame.pack_forget()

    def show_exam_fields(self, visible):
        """Mostra o nasconde i campi per l'esame."""
        if visible:
            self.exam_frame.pack(fill=tk.X, padx=20, pady=10)
            self.registration_frame.pack_forget()
            self.lesson_frame.pack_forget()
        else:
            self.exam_frame.pack_forget()

    def submit_student(self):
        """Gestisce l'invio dei dati dello studente per la registrazione."""
        self.student_id = self.id_entry.get().strip()
        self.student_name = self.name_entry.get().strip()
        self.student_surname = self.surname_entry.get().strip()

        if not (self.student_id and self.student_name and self.student_surname):
            messagebox.showwarning("Input Required", "Please fill in all fields before proceeding.")
            return

        comando = [sys.executable, "/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/scripts/createGsheet.py", "R", "Registrazione", self.course_name]
        self.execute_subprocess_command(comando)

        if self.conn is not None:
            self.create_table()

            # Genera chiave e IV e controlla se già esistono delle vecchie chiavi
            self.aes_key = self.generate_aes_key()
            self.aes_iv = self.generate_aes_iv()

            # Salva la chiave in Google Sheets
            comando = [sys.executable, "/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/scripts/keyChainGsheet.py", "R", "Registrazione", self.course_name, str(self.aes_key), str(self.aes_iv)]
            keyChainResult = self.execute_subprocess_command(comando)

            # Controlla se l'output contiene i dati necessari, ovvero se già esistevano delle chiavi
            if keyChainResult:
                results = keyChainResult.split()
                if len(results) >= 2:
                    resultKey, resultIV = results[0], results[1]
                    self.aes_key = eval(resultKey)
                    self.aes_iv = eval(resultIV)
                    print("La chiave e l'IV già esistono nel wallet.")
                else:
                    print("Nuova chiave e IV aggiunti al wallet del corso.")

            self.open_scanning_window("Scan Tag", self.submit_tag_id)

        # Resetta i campi di input
        self.id_entry.delete(0, tk.END)
        self.name_entry.delete(0, tk.END)
        self.surname_entry.delete(0, tk.END)

    def submit_lesson(self):
        """Gestisce l'invio dei dati per la registrazione di una lezione."""
        self.lesson_number = self.lesson_number_entry.get().strip()

        if not self.lesson_number:
            messagebox.showwarning("Input Required", "Please enter the lesson name before proceeding.")
            return

        comando = [sys.executable, "/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/scripts/createGsheet.py", "L", self.lesson_number, self.course_name]
        self.execute_subprocess_command(comando)

        self.students_list = []

        if self.conn is not None:
            self.create_table()

            # Genera chiave e IV per la lezione
            self.aes_key = self.generate_aes_key()
            self.aes_iv = self.generate_aes_iv()

            # Salva chiave in Google Sheets
            comando = [sys.executable, "/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/scripts/keyChainGsheet.py", "L", self.lesson_number, self.course_name, str(self.aes_key), str(self.aes_iv)]
            keyChainResult = self.execute_subprocess_command(comando)

            # Controlla se l'output contiene i dati necessari
            if keyChainResult:
                results = keyChainResult.split()
                if len(results) >= 2:
                    resultKey, resultIV = results[0], results[1]
                    self.aes_key = eval(resultKey)
                    self.aes_iv = eval(resultIV)
                    print("La chiave e l'IV già esistono nel wallet.")
                else:
                    print("Nuova chiave e IV aggiunti al wallet del corso.")

            self.open_scanning_window("Lesson Registration", self.submit_tag_id)

        self.lesson_number_entry.delete(0, tk.END)

    def submit_exam(self):
        """Gestisce l'invio dei dati per la registrazione di un esame."""
        self.exam_date = self.exam_date_entry.get().strip()

        if not self.exam_date:
            messagebox.showwarning("Input Required", "Please enter the exam date before proceeding.")
            return

        comando = [sys.executable, "/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/scripts/createGsheet.py", "E", self.exam_date, self.course_name]
        self.execute_subprocess_command(comando)

        self.students_list = []

        if self.conn is not None:
            self.create_table()

            # Genera chiave e IV per l'esame
            self.aes_key = self.generate_aes_key()
            self.aes_iv = self.generate_aes_iv()

            # Salva chiave in Google Sheets
            comando = [sys.executable, "/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/scripts/keyChainGsheet.py", "E", self.exam_date, self.course_name, str(self.aes_key), str(self.aes_iv)]
            keyChainResult = self.execute_subprocess_command(comando)

            # Controlla se l'output contiene i dati necessari
            if keyChainResult:
                results = keyChainResult.split()
                if len(results) >= 2:
                    resultKey, resultIV = results[0], results[1]
                    self.aes_key = eval(resultKey)
                    self.aes_iv = eval(resultIV)
                    print("La chiave e l'IV già esistono nel wallet.")
                else:
                    print("Nuova chiave e IV aggiunti al wallet del corso.")

            self.open_scanning_window("Exam Registration", self.submit_tag_id)

        self.exam_date_entry.delete(0, tk.END)

    def open_scanning_window(self, title, submit_function):
        """Apre una finestra per la scansione del tag e l'inserimento del tag ID."""
        scanning_window = tk.Toplevel(self.root)
        scanning_window.title(title)
        scanning_window.geometry(self.center_window(scanning_window, 500, 400))
        scanning_window.resizable(False, False)

        frame = tk.Frame(scanning_window)
        frame.pack(expand=True)

        tk.Label(frame, text="Hold the tag over the reader for scanning or insert the tag id manually:", font=('Arial', 12), wraplength=480).pack(pady=10, padx=20)

        img = self.load_image('/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/scan.png', 120, 120)
        if img:
            img_label = tk.Label(frame, image=img)
            img_label.image = img  # Mantieni il riferimento all'immagine
            img_label.pack(pady=10)

        tag_id_entry = tk.Entry(frame, bd=2, width=30)
        tag_id_entry.pack(padx=20, pady=10)

        tk.Button(frame, text="Submit Tag ID", command=lambda: submit_function(tag_id_entry.get(), scanning_window, tag_id_entry)).pack(pady=10)
        
        if title in ["Lesson Registration", "Exam Registration"]:
            tk.Button(frame, text="End Registration", command=lambda: self.end_registration(scanning_window)).pack(pady=10)

        try:
            self.root.grab_release()
        except:
            pass  
        
        try:
            scanning_window.grab_set()
        except tk.TclError:
            print("Unable to grab the window due to another active grab.")
            messagebox.showwarning("Warning", "Unable to grab the window due to another active grab.")

        scanning_window.protocol("WM_DELETE_WINDOW", lambda: self.on_close_window(scanning_window))

    def submit_tag_id(self, tag_id, window, entry):
        """Gestisce l'invio dell'ID del tag durante la scansione."""
        GPIO.setwarnings(False)
        reader = SimpleMFRC522()

        if window.title() == "Scan Tag":
            # Gestione della scansione per la registrazione degli studenti
            if entry.get() == "":
                try:
                    self.tag_id = reader.read()[0]
                    entry.delete(0, tk.END)
                    entry.insert(0, str(self.tag_id))
                except Exception as e:
                    print(f"Errore lettura tag: {e}")
            else:
                self.tag_id = entry.get()
            
            entry.delete(0, tk.END)
            print(f"Tag letto: {self.tag_id}")
            
            result = self.insert_student(self.tag_id, self.student_name, self.student_surname, self.student_id)
            if result:
                # Per ogni studente registrato ed inserito nel db, aggiornare il file di registrazione 
                comando = [sys.executable, "/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/scripts/updateGsheet.py", "Registrazione", self.course_name, "'" + str(self.tag_id), self.student_name, self.student_surname, "'" + str(self.student_id)]
                self.execute_subprocess_command(comando)  

                # Cifra l'ID con k e iv
                id_cifrato = self.encrypt_id_aes(str(self.tag_id).encode(), self.aes_iv, self.aes_key)
                print("ID_Cifrato: ", id_cifrato)

                id_decifrato = self.decrypt_id_aes(id_cifrato, self.aes_iv, self.aes_key)
                print("ID_De_Cifrato: ", id_decifrato)
                                
                # Salva su blockchain tipo_operazione, nome_corso, id_cifrato
                comando = [sys.executable, "/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/scripts/sendTransaction.py", "Registrazione", self.course_name, " ", str(id_cifrato)]
                self.execute_subprocess_command(comando)

                self.show_success_message(True)
            else:
                self.show_success_message(False)
            
            window.destroy()
            
        elif window.title() == "Lesson Registration":
            # Gestione della scansione per la registrazione delle lezioni
            if entry.get() == "":
                try:
                    self.tag_id = reader.read()[0]
                    entry.delete(0, tk.END)
                    entry.insert(0, str(self.tag_id))
                except Exception as e:
                    print(f"Errore lettura tag: {e}")
            else:
                self.tag_id = entry.get()
            
            entry.delete(0, tk.END)
            print(f"Tag letto: {self.tag_id}")
            
            if self.tag_id not in self.students_list:
                self.students_list.append(self.tag_id)

                info_studente = self.get_student_by_id(self.tag_id)
                if not info_studente:
                    print("Studente non trovato.")
                else:
                    orario = datetime.now().strftime("%H:%M:%S")

                    # Per ogni studente registrato ed inserito nel db, aggiornare il file Lezione_#  
                    comando = [sys.executable, "/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/scripts/updateGsheet.py", self.lesson_number, self.course_name, "'" + str(self.tag_id), info_studente[0], info_studente[1], "'" + str(info_studente[2]), "'" + orario ]
                    self.execute_subprocess_command(comando)  

                    # Cifra l'ID con k e iv
                    id_cifrato = self.encrypt_id_aes(str(self.tag_id).encode(), self.aes_iv, self.aes_key)
                    print("ID_Cifrato: ", id_cifrato)

                    id_decifrato = self.decrypt_id_aes(id_cifrato, self.aes_iv, self.aes_key)
                    print("ID_De_Cifrato: ", id_decifrato)
        
                    # Salva su blockchain tipo_operazione, nome_corso, id_cifrato
                    comando = [sys.executable, "/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/scripts/sendTransaction.py", "Lezione", self.course_name, self.lesson_number, str(id_cifrato)]
                    self.execute_subprocess_command(comando)
            else:
                print("Studente gia' registrato a lezione.")
        
        elif window.title() == "Exam Registration":
            # Gestione della scansione per la registrazione degli esami
            if entry.get() == "":
                try:
                    self.tag_id = reader.read()[0]
                    entry.delete(0, tk.END)
                    entry.insert(0, str(self.tag_id))
                except Exception as e:
                    print(f"Errore lettura tag: {e}")
            else:
                self.tag_id = entry.get()
            
            entry.delete(0, tk.END)
            print(f"Tag letto: {self.tag_id}")
            
            if self.tag_id not in self.students_list:
                self.students_list.append(self.tag_id)

                info_studente = self.get_student_by_id(self.tag_id)
                if not info_studente:
                    print("Studente non trovato.")
                else:
                    voto = " "

                    # Per ogni studente registrato ed inserito nel db, aggiornare il file giorno/mese/anno  
                    comando = [sys.executable, "/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/scripts/updateGsheet.py", self.exam_date, self.course_name, "'" + str(self.tag_id), info_studente[0], info_studente[1], "'" + str(info_studente[2]), voto]
                    self.execute_subprocess_command(comando)  

                    # Cifra l'ID con k e iv
                    id_cifrato = self.encrypt_id_aes(str(self.tag_id).encode(), self.aes_iv, self.aes_key)
                    print("ID_Cifrato: ", id_cifrato)

                    id_decifrato = self.decrypt_id_aes(id_cifrato, self.aes_iv, self.aes_key)
                    print("ID_De_Cifrato: ", id_decifrato)
             
                    # Salva su blockchain tipo_operazione, nome_corso, id_cifrato
                    comando = [sys.executable, "/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/scripts/sendTransaction.py", "Esame", self.course_name, self.exam_date, str(id_cifrato)]
                    self.execute_subprocess_command(comando)
            else:
                print("Studente gia' registrato per l'esame.")

    def end_registration(self, window):
        """Termina la registrazione e chiude la finestra attuale."""
        print("Registrazione Terminata.")
        window.destroy()

    def on_close_window(self, window):
        """Gestisce la chiusura della finestra con conferma da parte dell'utente."""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            window.destroy()

    def show_success_message(self, success):
        """Mostra un messaggio di successo o fallimento della registrazione."""
        success_window = tk.Toplevel(self.root)
        success_window.title("Registration Status")
        success_window.geometry(self.center_window(success_window, 400, 250))
        success_window.resizable(False, False)

        frame = tk.Frame(success_window)
        frame.pack(expand=True)

        img_path = "/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/success.png" if success else "/home/charpi/Desktop/IOT_Project/AttendanceSystemPI/AttendanceSystem/error.png"
        message_text = "Registration Successful" if success else "Registration Unsuccessful"

        img = self.load_image(img_path, 100, 100)
        if img:
            img_label = tk.Label(frame, image=img)
            img_label.image = img  
            img_label.pack(pady=10)
            tk.Label(frame, text=message_text, font=('Arial', 14)).pack(expand=True, padx=20, pady=20)
        else:
            tk.Label(frame, text="Image not found", font=('Arial', 14)).pack(expand=True, padx=20, pady=20)

        success_window.grab_set()
        success_window.after(2000, lambda: self.close_success_window(success_window))

    def close_success_window(self, window):
        """Chiude la finestra del messaggio di successo e mostra di nuovo i campi di registrazione."""
        window.destroy()
        self.show_registration_fields(True)

    def init_gui(self):
        """Inizializza l'interfaccia utente di Tkinter."""
        self.root = tk.Tk()
        self.root.title("Attendance System Interface")
        self.root.geometry(self.center_window(self.root, 500, 550))
        self.root.resizable(False, False)

        main_frame = tk.Frame(self.root)
        main_frame.pack(expand=True)

        header_frame = tk.Frame(main_frame, height=50)
        header_frame.pack(fill=tk.X)
        tk.Label(header_frame, text="Welcome!\n Please enter the Course Name\n and select an Operation.", font=('Arial', 16)).pack(pady=20)

        course_frame = tk.Frame(main_frame)
        course_frame.pack(fill=tk.X, padx=20, pady=10)

        self.course_entry = tk.Entry(course_frame, bd=2, width=30)
        self.course_entry.pack(pady=10)
        self.course_entry.bind("<KeyRelease>", lambda event: self.check_course_name())

        buttons_frame = tk.Frame(main_frame)
        buttons_frame.pack(pady=20)
        self.registration_button = tk.Button(buttons_frame, text="Registration", font=('Arial', 12), state=tk.DISABLED, command=lambda: self.on_button_click('Registration'))
        self.lesson_button = tk.Button(buttons_frame, text="Lesson", font=('Arial', 12), state=tk.DISABLED, command=lambda: self.on_button_click('Lesson'))
        self.exam_button = tk.Button(buttons_frame, text="Exam", font=('Arial', 12), state=tk.DISABLED, command=lambda: self.on_button_click('Exam'))
        self.registration_button.pack(side=tk.LEFT, padx=10)
        self.lesson_button.pack(side=tk.LEFT, padx=10)
        self.exam_button.pack(side=tk.LEFT, padx=10)

        self.registration_frame = tk.Frame(main_frame)
        tk.Label(self.registration_frame, text="ID:").pack(anchor="w", padx=10)
        self.id_entry = tk.Entry(self.registration_frame, bd=2)
        self.id_entry.pack(fill=tk.X, padx=10)
        tk.Label(self.registration_frame, text="First name:").pack(anchor="w", padx=10)
        self.name_entry = tk.Entry(self.registration_frame, bd=2)
        self.name_entry.pack(fill=tk.X, padx=10)
        tk.Label(self.registration_frame, text="Last name:").pack(anchor="w", padx=10)
        self.surname_entry = tk.Entry(self.registration_frame, bd=2)
        self.surname_entry.pack(fill=tk.X, padx=10)
        tk.Button(self.registration_frame, text="Register New Tag", command=self.submit_student).pack(pady=10)

        self.lesson_frame = tk.Frame(main_frame)
        tk.Label(self.lesson_frame, text="Lesson name:").pack(anchor="w", padx=10)
        self.lesson_number_entry = tk.Entry(self.lesson_frame, bd=2)
        self.lesson_number_entry.pack(fill=tk.X, padx=10)
        tk.Button(self.lesson_frame, text="Start Registration", command=self.submit_lesson).pack(pady=10)

        self.exam_frame = tk.Frame(main_frame)
        tk.Label(self.exam_frame, text="Exam date:").pack(anchor="w", padx=10)
        self.exam_date_entry = tk.Entry(self.exam_frame, bd=2)
        self.exam_date_entry.pack(fill=tk.X, padx=10)
        tk.Button(self.exam_frame, text="Start Registration", command=self.submit_exam).pack(pady=10)

        self.show_registration_fields(False)
        self.show_lesson_fields(False)
        self.show_exam_fields(False)

        # Avvia l'interfaccia utente principale di Tkinter
        self.root.mainloop()

# Avvia l'applicazione
if __name__ == "__main__":
    AttendanceSystem()






