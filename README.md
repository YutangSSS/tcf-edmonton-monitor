# TCF Edmonton GitHub Actions Monitor

This project checks the Edmonton Alliance Francaise TCF page every 30 minutes:

https://www.afedmonton.com/en/exams/tcf/

It downloads the page text and looks for signs that a new TCF slot may be available:

- a new exam month appears, such as September 2026 or October 2026;
- the number of `SOLD OUT` labels drops;
- the number of `Closed` labels drops;
- booking words such as `Register`, `Available`, `Purchase`, or `Book` appear near TCF exam rows.

When a possible slot is detected, the GitHub Actions job fails and prints:

```text
Possible new TCF Edmonton slot found. Check the website immediately.
```

## Files

- `check_tcf.py` - Python monitor script.
- `requirements.txt` - Python dependencies.
- `.github/workflows/tcf-monitor.yml` - GitHub Actions workflow.

## How It Runs

The workflow runs every 30 minutes with this cron schedule:

```yaml
*/30 * * * *
```

You can also run it manually from GitHub:

1. Open your repository on GitHub.
2. Go to **Actions**.
3. Select **TCF Edmonton monitor**.
4. Click **Run workflow**.

## Baseline Settings

The current baseline is set in `.github/workflows/tcf-monitor.yml`:

```yaml
EXPECTED_MONTHS: "June 2026,July 2026,August 2026"
MIN_SOLD_OUT_COUNT: "34"
MIN_CLOSED_COUNT: "28"
```

If the page changes and you want to accept the new page as normal, update these values.
For example, after you notice September 2026 is sold out and you still want monitoring to continue, add `September 2026` to `EXPECTED_MONTHS` and adjust the counts.

## Email Notifications

GitHub can email you when this workflow fails.

To enable failure emails:

1. Log in to GitHub.
2. Click your profile photo in the top-right corner.
3. Go to **Settings**.
4. Go to **Notifications**.
5. Under **System**, enable email notifications for **Actions** or workflow failures.
6. Make sure your repository is not muted or ignored in notification settings.

After this is enabled, a failed monitor run should send you a GitHub Actions failure email.

## Local Test

Run this locally:

```bash
pip install -r requirements.txt
python check_tcf.py
```

Exit code `0` means no possible slot was detected.
Exit code `1` means the script found a possible slot and printed the alert message.
