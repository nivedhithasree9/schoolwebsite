const API_BASE_URL = "http://127.0.0.1:8000/api";
const ADMIN_TOKEN_KEY = "adminToken";
const STUDENT_TOKEN_KEY = "studentToken";

function getAdminToken() {
    return localStorage.getItem(ADMIN_TOKEN_KEY) || "";
}

function setAdminToken(token) {
    localStorage.setItem(ADMIN_TOKEN_KEY, token);
}

function clearAdminToken() {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
}

function getStudentToken() {
    return localStorage.getItem(STUDENT_TOKEN_KEY) || "";
}

function setStudentToken(token) {
    localStorage.setItem(STUDENT_TOKEN_KEY, token);
}

function clearStudentToken() {
    localStorage.removeItem(STUDENT_TOKEN_KEY);
}

function hashText(value) {
    let hash = 0;
    const text = String(value || "");
    for (let index = 0; index < text.length; index += 1) {
        hash = text.charCodeAt(index) + ((hash << 5) - hash);
    }
    return Math.abs(hash);
}

function avatarColors(seed) {
    const palettes = [
        ["#0f4c5c", "#2f7f8d", "#f4efe7"],
        ["#7b2d26", "#c97f39", "#fff4e8"],
        ["#355070", "#6d597a", "#f7f1e8"],
        ["#2d6a4f", "#52b788", "#edf8f1"],
        ["#6a040f", "#e85d04", "#fff3e9"]
    ];
    return palettes[seed % palettes.length];
}

function buildAvatarSvg(student = {}) {
    const seedSource = `${student.name || ""}-${student.phone || ""}-${student.gender || ""}`;
    const seed = hashText(seedSource);
    const [primary, secondary, textBg] = avatarColors(seed);
    const initials = (student.name || "Student")
        .split(" ")
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0].toUpperCase())
        .join("") || "S";
    const icon = student.gender === "Girl" ? "G" : student.gender === "TG" ? "T" : "B";

    return `
        <svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160">
            <defs>
                <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="${primary}" />
                    <stop offset="100%" stop-color="${secondary}" />
                </linearGradient>
            </defs>
            <rect width="160" height="160" rx="36" fill="url(#g)" />
            <circle cx="124" cy="34" r="18" fill="rgba(255,255,255,0.18)" />
            <circle cx="34" cy="132" r="24" fill="rgba(255,255,255,0.12)" />
            <rect x="24" y="92" width="112" height="42" rx="21" fill="${textBg}" opacity="0.96" />
            <text x="80" y="66" text-anchor="middle" font-size="30" font-family="Georgia, serif" fill="white">${icon}</text>
            <text x="80" y="119" text-anchor="middle" font-size="26" font-weight="700" font-family="Arial, sans-serif" fill="${primary}">${initials}</text>
        </svg>
    `.trim();
}

function avatarUrl(student) {
    return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(buildAvatarSvg(student))}`;
}

function barcodePattern(value) {
    const seed = String(hashText(value || "STUDENT"));
    let bars = "";
    for (let index = 0; index < seed.length; index += 1) {
        const digit = Number(seed[index]);
        const width = 2 + (digit % 4);
        const gap = 1 + (digit % 2);
        bars += `<rect x="${index * 7}" y="0" width="${width}" height="54" fill="#111827" />`;
        bars += `<rect x="${index * 7 + width}" y="0" width="${gap}" height="54" fill="white" />`;
    }
    return bars;
}

function barcodeUrl(value) {
    const svg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="180" height="70" viewBox="0 0 180 70">
            <rect width="180" height="70" rx="10" fill="white" />
            <g transform="translate(18,8)">
                ${barcodePattern(value)}
            </g>
            <text x="90" y="64" text-anchor="middle" font-size="10" font-family="Arial, sans-serif" fill="#111827">${String(value || "STUDENT-ID")}</text>
        </svg>
    `.trim();
    return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function qrBlocks(value) {
    const seed = String(hashText(value || "PAYMENT"));
    let blocks = "";
    let cursor = 0;
    for (let row = 0; row < 13; row += 1) {
        for (let col = 0; col < 13; col += 1) {
            const digit = Number(seed[cursor % seed.length]);
            if ((digit + row + col) % 2 === 0) {
                blocks += `<rect x="${col * 10}" y="${row * 10}" width="8" height="8" rx="1" fill="#111827" />`;
            }
            cursor += 1;
        }
    }
    return blocks;
}

function paymentQrUrl(details = {}) {
    const studentId = details.studentId || "000000";
    const amount = details.amount || "0";
    const method = details.method || "PhonePe";
    const reference = `${studentId}-${amount}-${method}`;
    const svg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="240" height="300" viewBox="0 0 240 300">
            <rect width="240" height="300" rx="26" fill="#ffffff" />
            <rect x="14" y="14" width="212" height="54" rx="18" fill="#5f259f" />
            <text x="120" y="47" text-anchor="middle" font-size="22" font-weight="700" font-family="Arial, sans-serif" fill="white">PhonePe</text>
            <rect x="32" y="88" width="176" height="176" rx="20" fill="#f8f7ff" stroke="#e0d7f6" />
            <g transform="translate(55,111)">
                ${qrBlocks(reference)}
            </g>
            <text x="120" y="278" text-anchor="middle" font-size="12" font-family="Arial, sans-serif" fill="#111827">${reference}</text>
        </svg>
    `.trim();
    return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

async function apiRequest(path, options = {}) {
    let response;
    try {
        response = await fetch(`${API_BASE_URL}${path}`, options);
    } catch (error) {
        throw new Error("Unable to reach backend API. Start app.py and open this site from localhost (Live Server).");
    }
    const raw = await response.text();
    let data = {};

    if (raw) {
        try {
            data = JSON.parse(raw);
        } catch (error) {
            throw new Error(raw);
        }
    }

    if (!response.ok) {
        throw new Error(data.message || `Request failed with status ${response.status}`);
    }

    return data;
}
