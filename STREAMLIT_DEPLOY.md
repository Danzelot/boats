# Streamlit Community Cloud Deployment

This project is configured for automatic daily scraping via GitHub Actions and remote dashboard hosting via Streamlit Community Cloud.

## Setup Instructions

### Prerequisites
1. A **public** GitHub repository (required for free Streamlit hosting)
2. GitHub account with email notifications enabled

### Step 1: Make Repository Public

Streamlit Community Cloud requires a public repository for free hosting.

1. Go to your repository on GitHub
2. Settings → Manage access → Change visibility → Public

### Step 2: Enable GitHub Actions

The workflow is already configured in `.github/workflows/scrape.yml`:
- Runs daily at 08:00 UTC (10:00 Norway time)
- Scrapes 5 pages with detail scraping
- Random jitter on delays (3-6s for pages, 1-3s for details)
- Commits database updates back to the repo
- **Failing workflows automatically send email notifications** to repository admins

### Step 3: Add Database to Git

```bash
# Make sure finn_boats.db is tracked (not ignored)
git add finn_boats.db
git commit -m "Add database to repository"
git push
```

### Step 4: Deploy to Streamlit Community Cloud

1. Go to [Streamlit Community Cloud](https://share.streamlit.io/)
2. Click **"New app"**
3. Click **"From existing repo"**
4. Select your repository
5. Configure:
   - **Repository**: Your repo name
   - **Branch**: `main` (or your default branch)
   - **Main file path**: `dashboard.py`
6. Click **"Deploy"**

Your dashboard will be live at: `https://<your-app-name>.streamlit.app`

### Step 5: Configure Email Notifications

GitHub automatically sends emails to repository administrators when workflows fail. Ensure:

1. You are a repository **admin** or **collaborator** with write access
2. Your GitHub email notifications are enabled:
   - Settings → Notifications → Automatically watch repositories
   - Settings → Notifications → Participating and @mentions

### Step 6: Test the Workflow Manually

1. Go to your repository on GitHub
2. Actions → "Daily Finn.no Scraper" → "Run workflow" → "Run workflow"
3. Monitor the run - if it fails, you'll receive an email

## How It Works

### GitHub Actions Workflow
- **Trigger**: Daily at 08:00 UTC or manual
- **Steps**:
  1. Checkout repository with full history
  2. Set up Python 3.11
  3. Install dependencies (requests, beautifulsoup4)
  4. Run scraper with random jitter to avoid rate limiting
  5. Verify database was created and has data
  6. Commit and push database changes back to repository

### Random Jitter
The scraper uses random delays between requests:
- Page requests: Random delay between 3-6 seconds
- Detail requests: Random delay between 1-3 seconds

This prevents rate limiting from Finn.no while still completing within the 45-minute timeout.

### Failure Notifications
The workflow will fail and send email notifications if:
- The scraper exits with an error (non-zero exit code)
- The database file is missing after scraping
- The database file is too small (< 1000 bytes)
- Git operations fail (permission issues)

## Customization

### Change Scraping Parameters
Edit `.github/workflows/scrape.yml`:
```yaml
- name: Run scraper
  run: |
    python main.py \
      --max-pages 10 \      # Change number of pages
      --delay-min 2 \       # Change min delay
      --delay-max 8 \       # Change max delay
      --scrape-details       # Enable/disable detail scraping
```

### Change Schedule
Edit the cron expression in `.github/workflows/scrape.yml`:
```yaml
on:
  schedule:
    # Runs at 06:00 UTC (08:00 Norway time)
    - cron: '0 6 * * *'
```

Cron format: `minute hour day month weekday`
- `0 8 * * *` = 08:00 UTC daily
- `0 */6 * * *` = Every 6 hours
- `0 0 * * *` = Midnight UTC daily

### Add More Pages
To scrape more pages, increase `--max-pages` and adjust timeout:
```yaml
timeout-minutes: 60  # Increase from 45 if scraping many pages
```

## Troubleshooting

### Workflow Fails with Permission Denied
Ensure the workflow has write permissions:
```yaml
permissions:
  contents: write
```

### Database Not Being Updated
- Check that `finn_boats.db` is not in `.gitignore`
- Run the scraper manually to verify it works:
  ```bash
  python main.py --max-pages 1 --scrape-details --verbose
  ```

### No Email Notifications
- Verify you are a repository admin/collaborator
- Check GitHub notification settings
- Ensure your email is verified in GitHub account settings

### Database Growing Too Large
Consider:
- Limiting the number of pages scraped
- Adding a cleanup script to remove old entries
- Using Git LFS for large files

## Files Modified
- `.github/workflows/scrape.yml` - GitHub Actions workflow
- `main.py` - Added proper exit codes for error handling
- `requirements.txt` - Dependencies for Streamlit
- `.gitignore` - Removed `*.db` to allow tracking finn_boats.db
