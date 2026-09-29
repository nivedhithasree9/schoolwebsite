<?php

declare(strict_types=1);

require_once __DIR__ . '/db.php';
require_once __DIR__ . '/helpers.php';

session_start();

$input = getJsonInput();
$username = trim((string) ($input['username'] ?? ''));
$password = trim((string) ($input['password'] ?? ''));

if ($username === '' || $password === '') {
    sendJson(['success' => false, 'message' => 'Username and password are required.'], 422);
}

$pdo = getDatabase();
$stmt = $pdo->prepare('SELECT id FROM admin_users WHERE username = :username AND password = :password LIMIT 1');
$stmt->execute([
    'username' => $username,
    'password' => $password,
]);

$admin = $stmt->fetch();

if (!$admin) {
    sendJson(['success' => false, 'message' => 'Wrong username or password.'], 401);
}

$_SESSION['admin_logged_in'] = true;
$_SESSION['admin_id'] = (int) $admin['id'];

sendJson(['success' => true]);

