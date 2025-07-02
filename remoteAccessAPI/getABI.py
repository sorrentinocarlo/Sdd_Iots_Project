import json

def load_contract_info(contract_name, network_id='5777'):
    # Carica il file JSON del contract dal percorso corretto
    path = f'/Users/laplace/Desktop/Iots_Sdd_Project/remoteAccessAPI/build/contracts/AttendanceTracker.json'  # Modifica qui per riflettere il percorso relativo
    with open(path, 'r') as file:
        contract_data = json.load(file)

    # Estrai l'ABI
    abi = contract_data['abi']

    # Estrai l'indirizzo del contract
    address = contract_data['networks'][network_id]['address']

    return abi, address

# Usa la funzione per ottenere l'ABI e l'indirizzo del tuo smart contract
contract_abi, contract_address = load_contract_info('AttendanceTracker')  # Assicurati che 'AttendanceTracker' sia il nome giusto del tuo contract
print("ABI:", contract_abi)
print("Address:", contract_address)
