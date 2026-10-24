# Fire Extractor (Render)

A basic Telegram bot for extracting ordinary URLs from user-provided `.txt`, `.html`, and `.htm` files. It does not process APKs, access private courses, or bypass DRM/access controls.

## Features
- Force-join check for `@BankingTitanss`
- Plans: 7 days ₹99, 28 days ₹299, lifetime ₹599
- UPI ID / optional QR URL shown to buyers
- User submits UTR; admin receives Approve/Reject buttons
- SQLite plan/payment records
- Admin ID defaults to `6871050893`

## Render setup
Create a **Background Worker** from this folder. Add environment variables:
- `BOT_TOKEN`: token for the new Fire Extractor bot from @BotFather
- `ADMIN_ID`: `6871050893`
- `FORCE_CHANNEL`: `@BankingTitanss`
- `FORCE_CHANNEL_URL`: `https://t.me/BankingTitanss`
- `UPI_ID`: your own UPI ID (leave placeholder only while testing)
- `UPI_QR_URL`: optional publicly reachable QR image URL
- `DB_PATH`: optional path to SQLite DB file

Add the bot to the channel and grant enough access to check membership. For persistent SQLite data on Render, attach a persistent disk and set `DB_PATH` to a path on that disk (for example `/var/data/fire_extractor.db`).

## Payment safety
UTR is only a claim, not proof of payment. Admin must independently verify the credit in their UPI/bank app before approving. Never approve based only on a screenshot or submitted UTR.

## Important
This is a starter implementation and has not been live-tested with your bot token or Render account. Test in a private test channel first. Lifetime means no expiry. The bot only extracts ordinary URLs from user-supplied text/HTML files.
