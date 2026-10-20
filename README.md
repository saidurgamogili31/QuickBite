# QuickBite

A beginner-friendly food ordering demo built with Flask, SQLite, HTML, CSS, and JavaScript.

## Features
- Registration and login with hashed passwords
- Restaurant search and menu pages
- Session-based cart
- Checkout with delivery address
- Cash on delivery or clearly marked simulated test payment
- Order history and order status page
- Admin dashboard for updating order status

## Run locally
1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Create and activate a virtual environment:
   - Windows: `py -m venv .venv` then `.venv\\Scripts\\activate`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
4. Install packages: `pip install -r requirements.txt`
5. Set a secret key for local use:
   - macOS/Linux: `export QUICKBITE_SECRET_KEY="replace-with-a-long-random-secret"`
   - PowerShell: `$env:QUICKBITE_SECRET_KEY="replace-with-a-long-random-secret"`
6. Run: `python app.py`
7. Open http://127.0.0.1:5000

The SQLite database is created automatically on first run.

## Demo admin
- Email: `admin@quickbite.local`
- Password: `Admin123!`

Change or remove this demo account before deploying anywhere public.

## Important production notes
- The `demo` payment option is simulated only. It does not charge a card or verify a payment.
- For real Razorpay payments, create an order on the server, send the returned order ID to the client, verify the signature server-side, and use verified webhooks for final payment status. Never store raw card data.
- Before public deployment: set a strong secret key, disable debug mode, add CSRF protection and rate limiting, validate all inputs, use HTTPS, configure secure cookies, add migrations/backups, and review authorization.
- Order progress is manually updated from the admin dashboard. GPS/live driver tracking is not implemented in this starter.
