# RSS Tech Feeds → Discord

A GitHub Action that fetches the latest post from 9 top tech engineering blogs and delivers each new article as a rich embed to your Discord channel — twice a day, automatically.

## Feeds Included

| Blog | RSS Feed |
|---|---|
| Netflix Tech Blog | https://netflixtechblog.medium.com/feed |
| Uber Engineering | https://www.uber.com/en-IN/blog/engineering/backend/rss/ |
| Meta Engineering | https://engineering.fb.com/feed/ |
| LinkedIn Engineering | https://www.linkedin.com/blog/engineering/feed |
| Cloudflare Blog | https://blog.cloudflare.com/rss/ |
| GitHub Engineering | https://github.blog/changelog/feed/ |
| Etsy Code as Craft | https://codeascraft.com/feed/ |
| Medium Engineering | https://medium.engineering/feed |
| Stripe Engineering | https://stripe.com/blog/feed.rss |

## Setup

### 1. Add the Discord Webhook Secret

1. In your Discord server, go to **Server Settings → Integrations → Webhooks** and create a new webhook for the channel you want posts sent to. Copy the webhook URL.
2. In this GitHub repo, go to **Settings → Secrets and variables → Actions → New repository secret**.
3. Name: `DISCORD_WEBHOOK_URL`  
   Value: _(paste your Discord webhook URL)_

### 2. Push to GitHub

Push this repository to GitHub. The workflow will automatically register with GitHub Actions.

### 3. (Optional) Adjust Schedule

Edit `.github/workflows/rss-to-discord.yml` and change the `cron` values under `schedule:`:

```yaml
- cron: "0 6 * * *"   # 06:00 UTC
- cron: "0 18 * * *"  # 18:00 UTC
```

Use [crontab.guru](https://crontab.guru) to build your preferred schedule.

## Running Manually

Go to **Actions → RSS Tech Feeds to Discord → Run workflow** and click the green **Run workflow** button.

## How It Works

- `feeds.json` — list of all RSS feed URLs
- `scripts/fetch_rss.py` — parses each feed, finds the latest entry, posts to Discord
- `state/seen_posts.json` — tracks which posts have already been sent (auto-committed by the workflow) to avoid duplicates

## Adding or Removing Feeds

Edit `feeds.json` — add or remove objects in the format:

```json
{ "name": "Blog Name", "url": "https://example.com/feed" }
```
