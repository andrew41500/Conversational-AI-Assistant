# Teaching Git & GitHub

Hello! Setting up Git and GitHub is a great step. I've already prepared a `.gitignore` file in your directory to make sure we don't accidentally share secrets (like API keys in your `.env` file) or large, unnecessary folders (like your `venv/` folder).

Follow these steps in your terminal inside the `z:\Downloadss\MAISTORAGE 2` folder.

## Phase 1: Local Setup

### 1. Initialize Git
Run this command to tell your project it's a Git repository:
```bash
git init
```

### 2. Configure Your Identity (One-time)
If you haven't done this before, Git needs to know who you are for your "commits":
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 3. Stage Your Files
"Staging" is like putting files in a box before you seal it. This prepares all your project files for the first snapshot:
```bash
git add .
```

### 4. Create Your First Commit
This "seals the box" and gives it a label. It's a snapshot of your code at this moment:
```bash
git commit -m "Initial commit"
```

---

## Phase 2: GitHub Setup

1.  Go to [github.com](https://github.com/) and log in.
2.  Click the **+** icon in the top-right and select **New repository**.
3.  Give it a name (e.g., `maistorage-2`).
4.  **Important**: Do NOT check "Initialize this repository with a README" (since we already have one).
5.  Click **Create repository**.

---

## Phase 3: Pushing to GitHub

After you create the repository on GitHub, it will show you some commands. You only need these three:

### 1. Link Your Local Project to GitHub
Replace `YOUR_URL` with the URL GitHub gives you (it looks like `https://github.com/your-username/your-repo-name.git`):
```bash
git remote add origin YOUR_URL
```

### 2. Rename Your Branch
This ensures you're using the standard name `main`:
```bash
git branch -M main
```

### 3. Push Your Code
This uploads everything to GitHub!
```bash
git push -u origin main
```

---

> [!TIP]
> After your first push, you only need `git add .`, `git commit -m "Message"`, and `git push` to update your work in the future!
