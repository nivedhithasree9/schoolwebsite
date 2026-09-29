<?php

declare(strict_types=1);

require_once __DIR__ . '/helpers.php';

session_start();
$_SESSION = [];
session_destroy();

sendJson(['success' => true]);

