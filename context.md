# Project Context: Dumu Apparels (Instagram Bot)

## 1. Project Overview
**Dumu Apparels** is a specialized Instagram Automation project by Dumu Technologies. It is a retail bot designed for a Kenyan online fashion brand selling men's and women's shoes and clothing.

**Mission:** Transform Instagram Direct Messages (DMs) into an automated, high-conversion sales funnel. The bot handles inventory browsing, sizing queries, and payment processing (M-Pesa/Card) without human intervention, using a "Hybrid" architecture (Rule-based for sales, AI for support).

## 2. Technical Stack
* **Language:** Python 3.11+
* **Framework:** FastAPI (Asynchronous)
* **Database:** PostgreSQL (Hosted on Railway) via SQLAlchemy (Async) & Alembic for migrations.
* **AI Engine:** OpenAI API (GPT-4o-mini).
* **Platform:** Meta/Instagram Graph API (Messenger Platform).
* **Infrastructure:** Railway (utilizing `railway.toml` or Dockerfile).
* **Payments:**
    * **IntaSend** (Primary - for M-Pesa STK Push & Payment Links).
    * **PesaPal** (Secondary/Fallback).

## 3. Architecture & Logic Flow
The bot operates on a **Hybrid Architecture**:
1.  **Rule-Based Layer (The "Happy Path"):** Critical sales actions (Menus, Carousels, "Buy Now" buttons) are deterministic to ensure accurate pricing and inventory checks.
2.  **AI Layer (The "Safety Net"):** Used ONLY when user input does not match a predefined button. The AI acts as a polite sales assistant to answer unstructured queries (e.g., "Do you deliver to Roysambu?").

### Core Workflows
1.  **Webhook Ingestion:** Endpoint `/webhook` verifies Meta tokens and receives `messages`.
2.  **User Identity:** Check DB for `instagram_id`. If new, create `User` record.
3.  **Intent Classification:**
    * **Payload (Button Click):** Execute specific function (e.g., `show_mens_shoes`).
    * **Text:** Send to OpenAI with a system prompt defining "Dumu Apparels" persona.
4.  **Inventory Display:** Use Instagram **Generic Templates (Carousels)**.
    * Cards display: Image, Name, Price (KES), Size Availability.
5.  **Checkout:**
    * User selects item & size -> Bot generates IntaSend Payment Link.
    * Bot monitors Webhook for payment success.
    * Upon success: Bot sends confirmation + Order Number.

## 4. Database Schema (Draft)
* **Users:** `id`, `instagram_id` (Unique), `name`, `phone_number`, `location`, `created_at`.
* **Products:** `id`, `name`, `category` (Men/Women), `type` (Shoe/Cloth), `price` (Decimal), `image_url`, `stock_status`, `description`.
* **Orders:** `id`, `user_id`, `product_id`, `amount`, `status` (Pending/Paid/Failed), `payment_provider`, `transaction_ref`.
* **ConversationLogs:** `id`, `user_id`, `message_content`, `sender` (User/Bot), `timestamp`.

## 5. Environment Variables (.env)
```env
# Meta
VERIFY_TOKEN=...
PAGE_ACCESS_TOKEN=...
INSTAGRAM_ACCOUNT_ID=...

# OpenAI
OPENAI_API_KEY=...

# Database
DATABASE_URL=... (Railway Postgres URL)

# Payments
INTASEND_PUBLIC_KEY=...
INTASEND_SECRET_KEY=...
PESAPAL_CONSUMER_KEY=...
PESAPAL_CONSUMER_SECRET=...

6. Important Business Rules (Kenyan Context)
Currency: KES (Kenyan Shillings).

Payment Flow: Prioritize M-Pesa. The bot should explicitly mention M-Pesa when presenting payment options.

Tone: "Dumu Apparels" is trendy, professional, but accessible. Uses Kenyan English nuances where appropriate (polite and direct).

Timeouts: Payment links are valid for 15 minutes.

7. Development Constraints
Code Style: PEP 8.

Async/Await: All I/O operations (DB, API calls) MUST be asynchronous (async def).

Error Handling: Graceful degradation. If the AI fails, fallback to a "Main Menu" button. Never leave the user on "read".