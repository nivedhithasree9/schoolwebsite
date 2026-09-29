<?php

declare(strict_types=1);

require_once __DIR__ . '/db.php';
require_once __DIR__ . '/helpers.php';

try {
    $input = getJsonInput();

    $data = [
        'name' => trim((string) ($input['name'] ?? '')),
        'gender' => trim((string) ($input['gender'] ?? '')),
        'aadhaar' => trim((string) ($input['aadhaar'] ?? '')),
        'phone' => trim((string) ($input['phone'] ?? '')),
        'father' => trim((string) ($input['father'] ?? '')),
        'focc' => trim((string) ($input['focc'] ?? '')),
        'faadhaar' => trim((string) ($input['faadhaar'] ?? '')),
        'mother' => trim((string) ($input['mother'] ?? '')),
        'mocc' => trim((string) ($input['mocc'] ?? '')),
        'maadhaar' => trim((string) ($input['maadhaar'] ?? '')),
        'school' => trim((string) ($input['school'] ?? '')),
        'class_name' => trim((string) ($input['class_name'] ?? '')),
        'medium' => trim((string) ($input['medium'] ?? '')),
        'nation' => trim((string) ($input['nation'] ?? '')),
        'state_name' => trim((string) ($input['state_name'] ?? '')),
        'religion' => trim((string) ($input['religion'] ?? '')),
        'caste' => trim((string) ($input['caste'] ?? '')),
        'remarks' => trim((string) ($input['remarks'] ?? '')),
    ];

    if ($data['name'] === '') {
        sendJson(['success' => false, 'message' => 'Name is required.'], 422);
    }

    if (!preg_match('/^\d{12}$/', $data['aadhaar'])) {
        sendJson(['success' => false, 'message' => 'Aadhaar must be 12 digits.'], 422);
    }

    if (!preg_match('/^\d{10}$/', $data['phone'])) {
        sendJson(['success' => false, 'message' => 'Phone must be 10 digits.'], 422);
    }

    $pdo = getDatabase();
    $stmt = $pdo->prepare(
        'INSERT INTO students (
            name, gender, aadhaar, phone, father, focc, faadhaar, mother, mocc, maadhaar,
            school, class_name, medium, nation, state_name, religion, caste, remarks
        ) VALUES (
            :name, :gender, :aadhaar, :phone, :father, :focc, :faadhaar, :mother, :mocc, :maadhaar,
            :school, :class_name, :medium, :nation, :state_name, :religion, :caste, :remarks
        )'
    );

    $stmt->execute($data);

    sendJson(['success' => true, 'message' => 'Saved successfully.']);
} catch (Throwable $exception) {
    handleApiException($exception);
}
