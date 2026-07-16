# TCF Edmonton GitHub Actions Monitor

This project checks the Edmonton Alliance Francaise TCF page every 30 minutes:

https://www.afedmonton.com/en/exams/tcf/

It inspects individual TCF Canada exam rows and alerts only when a row exposes
an explicit booking signal such as `Available`, `Register`, `Purchase`, `Book`,
or the site's available-status class. It intentionally does not use aggregate
`SOLD OUT` or `Closed` counts, because old sessions naturally disappear from
the page as their dates pass. Page fetches are retried with exponential backoff
before a connection failure is reported.

When a possible slot is detected, the GitHub Actions job creates a new GitHub
Issue containing the detector output, then fails so GitHub can send a workflow
failure notification.

## Files

- `check_tcf.py` - Python monitor script.
- `test_check_tcf.py` - Detector regression tests.
- `requirements.txt` - Python dependencies.
- `.github/workflows/tcf-monitor.yml` - GitHub Actions workflow.

## How It Runs

The workflow runs every 30 minutes with this cron schedule:

```yaml
*/30 * * * *
```

You can also run it manually from GitHub:

1. Open the repository on GitHub.
2. Go to **Actions**.
3. Select **TCF Edmonton monitor**.
4. Click **Run workflow**.

## Exit Codes

- `0` means no explicit availability was detected.
- `1` means a TCF exam row exposed a booking signal and an alert was created.
- `2` means the page could not be fetched after retries; the workflow fails without creating a misleading slot alert.

## Notifications

GitHub can email you when this workflow fails. Configure workflow failure
notifications under your GitHub account's **Settings → Notifications** and
make sure this repository is not muted.

The workflow also creates an issue for each confirmed availability alert. Watch
the repository with **All Activity** enabled if you want issue notifications.

## Local Test

Run the monitor and its regression tests locally:

```bash
pip install -r requirements.txt
python check_tcf.py
python -m unittest -v test_check_tcf.py
```
