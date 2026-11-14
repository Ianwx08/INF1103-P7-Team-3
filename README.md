
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


## Project Structure (OOP Part 2)

The project uses an object-oriented structure:

- `main.py` — LostAndFoundApp entry point
- `models/` — Item classes and related data models
- `managers/` — AI, IO, data and logic managers
- `tests/` — Automated offline unit tests
- `tests/helpers/` — SampleReplies and ScriptedIOManager
- `Dockerfile` — Docker image configuration
- `.github/workflows/ci.yml` — GitHub Actions workflow

## Automated Tests

The OOP tests are located in `tests/`.

They use sample AI responses and mock managers, so they do not require a Gemini API key or internet connection.

### Run Tests Locally

```powershell
python -m unittest discover tests -v
```

### Run Tests Inside Docker

First, build the image:

```powershell
docker build -t lost-and-found .
```

Then run the complete test suite:

```powershell
docker run --rm --network none lost-and-found python -m unittest discover tests -v
```

The `--network none` option disables networking inside the container during testing.

## Continuous Integration (CI)

GitHub Actions automatically runs the Docker build and offline tests whenever code is pushed or a pull request is created.

The workflow is located at `.github/workflows/ci.yml`.

The workflow:

1. Checks out the latest project code.
2. Builds the Docker image.
3. Runs the automated unit tests inside Docker with networking disabled.

No Gemini API key or GitHub secret is required for these tests.

### View CI Results

Open the GitHub repository and select the **Actions** tab.

- A green check means the Docker build and tests passed.
- A red cross means the workflow failed.

The workflow can also be started manually from the Actions tab.
