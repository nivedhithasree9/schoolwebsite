CREATE DATABASE IF NOT EXISTS school_management;
USE school_management;

CREATE TABLE IF NOT EXISTS admin_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    gender VARCHAR(20) NOT NULL,
    aadhaar CHAR(12) NOT NULL,
    phone CHAR(10) NOT NULL,
    father VARCHAR(100) DEFAULT '',
    focc VARCHAR(100) DEFAULT '',
    faadhaar CHAR(12) DEFAULT '',
    mother VARCHAR(100) DEFAULT '',
    mocc VARCHAR(100) DEFAULT '',
    maadhaar CHAR(12) DEFAULT '',
    school VARCHAR(150) DEFAULT '',
    class_name VARCHAR(50) DEFAULT '',
    medium VARCHAR(50) DEFAULT '',
    nation VARCHAR(100) DEFAULT '',
    state_name VARCHAR(100) DEFAULT '',
    religion VARCHAR(100) DEFAULT '',
    caste VARCHAR(100) DEFAULT '',
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO admin_users (username, password)
SELECT 'admin', '1234'
WHERE NOT EXISTS (
    SELECT 1 FROM admin_users WHERE username = 'admin'
);
