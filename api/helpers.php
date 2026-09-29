<?php

declare(strict_types=1);

$allowedOrigins = [
    'http://127.0.0.1:5500',
    'http://localhost:5500',
];

$origin = $_SERVER['HTTP_ORIGIN'] ?? '';

if (in_array($origin, $allowedOrigins, true)) {
    header('Access-Control-Allow-Origin: ' . $origin);
    header('Access-Control-Allow-Credentials: true');
}

header('Access-Control-Allow-Headers: Content-Type');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'OPTIONS') {
    http_response_code(204);
    exit;
}

function sendJson(array $data, int $statusCode = 200): void
{
    http_response_code($statusCode);
    header('Content-Type: application/json');
    echo json_encode($data);
    exit;
}

function getJsonInput(): array
{
    $raw = file_get_contents('php://input');
    $data = json_decode($raw ?: '[]', true);

    return is_array($data) ? $data : [];
}

function handleApiException(Throwable $exception): void
{
    sendJson([
        'success' => false,
        'message' => $exception->getMessage(),
    ], 500);
}

function requireAdmin(): void
{
    session_start();

    if (empty($_SESSION['admin_logged_in'])) {
        sendJson(['success' => false, 'message' => 'Unauthorized'], 401);
    }
}
