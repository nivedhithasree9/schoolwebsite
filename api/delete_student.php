<?php

declare(strict_types=1);

require_once __DIR__ . '/db.php';
require_once __DIR__ . '/helpers.php';

requireAdmin();

$input = getJsonInput();
$id = (int) ($input['id'] ?? 0);

if ($id <= 0) {
    sendJson(['success' => false, 'message' => 'Invalid student id.'], 422);
}

$pdo = getDatabase();
$stmt = $pdo->prepare('DELETE FROM students WHERE id = :id');
$stmt->execute(['id' => $id]);

sendJson(['success' => true]);

