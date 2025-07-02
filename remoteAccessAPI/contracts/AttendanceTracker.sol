// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract AttendanceTracker {
    // Struttura per memorizzare i record di presenza
    struct Record {
        string operationType; // Tipo di operazione: "Registrazione", "Lezione", "Esame"
        string courseName; // Nome del corso
        string additionalInfo; // Nome della lezione o data dell'esame; vuoto per le registrazioni
        string encryptedId; // ID dello studente criptato
    }

    // Array per memorizzare tutti i record
    Record[] private records;

    // Evento emesso ogni volta che un record viene creato
    event RecordCreated(string operationType, string courseName, string additionalInfo, string encryptedId);

    /**
     * @dev Aggiunge un nuovo record di presenza.
     * @param operationType Il tipo di operazione ("Registrazione", "Lezione", "Esame").
     * @param courseName Il nome del corso associato al record.
     * @param additionalInfo Informazioni aggiuntive (es. nome della lezione o data dell'esame).
     * @param encryptedId L'ID criptato dello studente.
     */
    function addRecord(string memory operationType, string memory courseName, string memory additionalInfo, string memory encryptedId) public {
        records.push(Record(operationType, courseName, additionalInfo, encryptedId));
        emit RecordCreated(operationType, courseName, additionalInfo, encryptedId);
    }

    /**
     * @dev Conta il numero di registrazioni per un dato corso.
     * @param courseName Il nome del corso.
     * @return Il numero di registrazioni trovate.
     */
    function countRegistrations(string memory courseName) public view returns (uint) {
        uint count = 0;
        for(uint i = 0; i < records.length; i++) {
            if(keccak256(bytes(records[i].operationType)) == keccak256(bytes("Registrazione")) && keccak256(bytes(records[i].courseName)) == keccak256(bytes(courseName))) {
                count++;
            }
        }
        return count;
    }

    /**
     * @dev Conta il numero di presenze per una data lezione di un dato corso.
     * @param courseName Il nome del corso.
     * @param lessonName Il nome della lezione.
     * @return Il numero di presenze trovate.
     */
    function countLessonAttendances(string memory courseName, string memory lessonName) public view returns (uint) {
        uint count = 0;
        for(uint i = 0; i < records.length; i++) {
            if(keccak256(bytes(records[i].operationType)) == keccak256(bytes("Lezione")) &&
            keccak256(bytes(records[i].additionalInfo)) == keccak256(bytes(lessonName)) &&
            keccak256(bytes(records[i].courseName)) == keccak256(bytes(courseName))) {
                count++;
            }
        }
        return count;
    }

    /**
     * @dev Conta il numero di partecipazioni a un dato esame di un dato corso.
     * @param courseName Il nome del corso.
     * @param examDate La data dell'esame.
     * @return Il numero di partecipazioni trovate.
     */
    function countExamParticipations(string memory courseName, string memory examDate) public view returns (uint) {
        uint count = 0;
        for(uint i = 0; i < records.length; i++) {
            if(keccak256(bytes(records[i].operationType)) == keccak256(bytes("Esame")) &&
            keccak256(bytes(records[i].additionalInfo)) == keccak256(bytes(examDate)) &&
            keccak256(bytes(records[i].courseName)) == keccak256(bytes(courseName))) {
                count++;
            }
        }
        return count;
    }

    /**
     * @dev Restituisce i record in base al tipo di operazione e ai dettagli specifici.
     * @param operationType Il tipo di operazione ("Registrazione", "Lezione", "Esame").
     * @param courseName Il nome del corso.
     * @param additionalInfo Informazioni aggiuntive (es. nome della lezione o data dell'esame).
     * @return Un array di record filtrati in base ai criteri specificati.
     */
    function getRecordsByOperation(string memory operationType, string memory courseName, string memory additionalInfo) public view returns (Record[] memory) {
        Record[] memory tempRecords = new Record[](records.length);
        uint count = 0;
        
        for(uint i = 0; i < records.length; i++) {
            bool matchOperationType = keccak256(bytes(records[i].operationType)) == keccak256(bytes(operationType));
            bool matchCourseName = keccak256(bytes(records[i].courseName)) == keccak256(bytes(courseName));
            bool matchAdditionalInfo = keccak256(bytes(records[i].additionalInfo)) == keccak256(bytes(additionalInfo)) || keccak256(bytes(additionalInfo)) == keccak256("");

            if(matchOperationType && matchCourseName && (matchAdditionalInfo || keccak256(bytes(operationType)) == keccak256(bytes("Registrazione")))) {
                tempRecords[count] = records[i];
                count++;
            }
        }
        
        Record[] memory filteredRecords = new Record[](count);
        for(uint j = 0; j < count; j++) {
            filteredRecords[j] = tempRecords[j];
        }
        
        return filteredRecords;
    }
}
