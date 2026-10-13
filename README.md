
# Lost & Found Management System

## Local Setup

1. Clone the repository.

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project folder and add your Gemini API key:

   ```text
   GEMINI_API_KEY=your_key_here
   ```

4. Run the application locally:

   ```powershell
   python main.py
   ```

## Docker

Docker allows the application to run in a consistent Python 3.12 environment without manually installing Python dependencies on the host.

Make sure Docker Desktop is running before executing these commands.

### Build the Docker Image

From the project folder, run:

```powershell
docker build -t lost-and-found .
```

This creates a Docker image named `lost-and-found`.

### Run with Docker (Windows PowerShell)

```powershell
docker run --rm -it --env-file .env -v "${PWD}/data:/app/data" lost-and-found
```

### Run with Docker (Linux / macOS)

```bash
docker run --rm -it --env-file .env -v "$(pwd)/data:/app/data" lost-and-found
```

The commands:

- `--rm`: removes the container after it exits.
- `-it`: enables interactive terminal input.
- `--env-file .env`: passes the Gemini API key to the container.
- `-v`: mounts the local `data` folder to `/app/data`.
- `lost-and-found`: specifies the Docker image to run.

The Docker image uses the Asia/Singapore timezone.

## Automated Tests

`test_logic.py` tests the functions in `logic_manager.py` using hard-coded sample AI responses.

These tests do not require an API key or an internet connection.

### Run Tests Locally

```powershell
python test_logic.py
```

### Run Tests Inside Docker

```powershell
docker run --rm --network none lost-and-found python test_logic.py
```

The Docker test runs without network access.

The tests print PASS/FAIL results and exit with code 1 if any test fails.
