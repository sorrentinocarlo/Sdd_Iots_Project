import sys
import os
from web3 import Web3

# Connessione a Ganache
ganache_url = "http://172.20.10.14:7545"
web3 = Web3(Web3.HTTPProvider(ganache_url))

if web3.is_connected():
    print("Connesso a Ganache")
else:
    print("Connessione a Ganache fallita")


# ABI e indirizzo dello smart contract
contract_abi = [{'anonymous': False, 'inputs': [{'indexed': False, 'internalType': 'string', 'name': 'operationType', 'type': 'string'}, {'indexed': False, 'internalType': 'string', 'name': 'courseName', 'type': 'string'}, {'indexed': False, 'internalType': 'string', 'name': 'additionalInfo', 'type': 'string'}, {'indexed': False, 'internalType': 'string', 'name': 'encryptedId', 'type': 'string'}], 'name': 'RecordCreated', 'type': 'event'}, {'inputs': [{'internalType': 'string', 'name': 'operationType', 'type': 'string'}, {'internalType': 'string', 'name': 'courseName', 'type': 'string'}, {'internalType': 'string', 'name': 'additionalInfo', 'type': 'string'}, {'internalType': 'string', 'name': 'encryptedId', 'type': 'string'}], 'name': 'addRecord', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'}, {'inputs': [{'internalType': 'string', 'name': 'courseName', 'type': 'string'}], 'name': 'countRegistrations', 'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function', 'constant': True}, {'inputs': [{'internalType': 'string', 'name': 'courseName', 'type': 'string'}, {'internalType': 'string', 'name': 'lessonName', 'type': 'string'}], 'name': 'countLessonAttendances', 'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function', 'constant': True}, {'inputs': [{'internalType': 'string', 'name': 'courseName', 'type': 'string'}, {'internalType': 'string', 'name': 'examDate', 'type': 'string'}], 'name': 'countExamParticipations', 'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function', 'constant': True}, {'inputs': [{'internalType': 'string', 'name': 'operationType', 'type': 'string'}, {'internalType': 'string', 'name': 'courseName', 'type': 'string'}, {'internalType': 'string', 'name': 'additionalInfo', 'type': 'string'}], 'name': 'getRecordsByOperation', 'outputs': [{'components': [{'internalType': 'string', 'name': 'operationType', 'type': 'string'}, {'internalType': 'string', 'name': 'courseName', 'type': 'string'}, {'internalType': 'string', 'name': 'additionalInfo', 'type': 'string'}, {'internalType': 'string', 'name': 'encryptedId', 'type': 'string'}], 'internalType': 'struct AttendanceTracker.Record[]', 'name': '', 'type': 'tuple[]'}], 'stateMutability': 'view', 'type': 'function', 'constant': True}]
contract_address = '0x8F510086386477235FC73e11Bc585Bfdfd748a91' # Sostituisci ... con l'indirizzo effettivo del contract

# Creazione di un'istanza del contract
contract = web3.eth.contract(address=contract_address, abi=contract_abi)

def add_record(operation_type, course_name, additional_info, encrypted_id):
    accounts = web3.eth.accounts

    tx_hash = contract.functions.addRecord(operation_type, course_name, additional_info, encrypted_id).transact({
        'from': accounts[0],
        'gas': 500000
    })

    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print('Record aggiunto con successo!')

def count_registrations(course_name):
    count = contract.functions.countRegistrations(course_name).call()
    print(f'Numero di registrazioni per il corso {course_name}: {count}')
    return count

def count_lesson_attendances(course_name, lesson_name):
    count = contract.functions.countLessonAttendances(course_name, lesson_name).call()
    print(f'Numero di presenze per la lezione "{lesson_name}" del corso {course_name}: {count}')
    return count

def count_exam_participations(course_name, exam_date):
    count = contract.functions.countExamParticipations(course_name, exam_date).call()
    print(f'Numero di partecipazioni all\'esame di "{course_name}" del giorno "{exam_date}": {count}')
    return count

if __name__ == '__main__':
    if len(sys.argv) > 5:
        print("Uso: python sendTransaction.py <operation_type> <course_name> <additional_info> <encrypted_id>")
    elif len(sys.argv) == 5:
        # Aggiungere il record
        operation_type, course_name, additional_info, encrypted_id = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
        add_record(operation_type, course_name, additional_info, encrypted_id)
        if operation_type == "Registrazione":
            course_name = sys.argv[2]
            count_registrations(sys.argv[2])
        elif operation_type == "Lezione":
            course_name, lesson_name = sys.argv[2], sys.argv[3]
            count_lesson_attendances(course_name, lesson_name)
        elif operation_type == "Esame":
            course_name, exame_date = sys.argv[2], sys.argv[3]
            count_exam_participations(course_name, exame_date)