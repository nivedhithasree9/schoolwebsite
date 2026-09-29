## MySQL Setup

1. Make sure MySQL server is running on this computer.
2. Install Python packages with `pip install -r requirements.txt`.
3. If your MySQL username or password is different, set `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` as environment variables before running the app.
4. Open this folder with VS Code Live Server for the HTML pages.
5. In a terminal, run `python app.py` from this project folder.
6. Open the Live Server URL, usually `http://127.0.0.1:5500/index.html`.

## Default Admin Login

- Username: `admin`
- Password: `1234`

## Notes

- `app.py` creates the database and tables automatically when it starts.
- The admission form submits to `http://127.0.0.1:8000/api/create_student`.
- Admin login uses `http://127.0.0.1:8000/api/login`.
- Admin panel reads data from `http://127.0.0.1:8000/api/get_students`.
- Delete uses `http://127.0.0.1:8000/api/delete_student`.
