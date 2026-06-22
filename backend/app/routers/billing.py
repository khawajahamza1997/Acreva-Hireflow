import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from app.config import settings
from app.database import get_admin_client
from app.deps import get_current_user, require_role, CurrentUser

router = APIRouter(prefix="/billing", tags=["billing"])

stripe.api_key = settings.stripe_secret_key


@router.post("/checkout")
def create_checkout(user: CurrentUser = Depends(require_role("owner"))):
    if not settings.stripe_secret_key or not settings.stripe_price_id:
        raise HTTPException(status_code=503, detail="Stripe is not configured yet.")

    db = get_admin_client()
    org = (
        db.table("organizations")
        .select("*")
        .eq("id", user.organization_id)
        .maybe_single()
        .execute()
    )
    if not org.data:
        raise HTTPException(status_code=404, detail="Organization not found.")

    customer_id = org.data.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.org_name,
            metadata={"organization_id": user.organization_id},
        )
        customer_id = customer.id
        db.table("organizations").update({"stripe_customer_id": customer_id}).eq("id", user.organization_id).execute()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        subscription_data={"trial_period_days": settings.stripe_trial_days},
        success_url=f"{settings.frontend_url}/dashboard/billing?success=1",
        cancel_url=f"{settings.frontend_url}/dashboard/billing?canceled=1",
        metadata={"organization_id": user.organization_id},
    )
    return {"checkout_url": session.url}


@router.post("/portal")
def billing_portal(user: CurrentUser = Depends(require_role("owner"))):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")
    db = get_admin_client()
    org = db.table("organizations").select("stripe_customer_id").eq("id", user.organization_id).maybe_single().execute()
    if not org.data or not org.data.get("stripe_customer_id"):
        raise HTTPException(status_code=400, detail="No billing account yet. Start checkout first.")
    session = stripe.billing_portal.Session.create(
        customer=org.data["stripe_customer_id"],
        return_url=f"{settings.frontend_url}/dashboard/billing",
    )
    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured.")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db = get_admin_client()
    if event["type"] in ("checkout.session.completed", "customer.subscription.updated"):
        obj = event["data"]["object"]
        org_id = obj.get("metadata", {}).get("organization_id")
        sub_id = obj.get("subscription") or obj.get("id")
        status = obj.get("status") or "active"
        if org_id:
            db.table("organizations").update(
                {
                    "stripe_subscription_id": sub_id,
                    "subscription_status": "active" if status in ("complete", "active", "trialing") else status,
                }
            ).eq("id", org_id).execute()
    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer = sub.get("customer")
        org = db.table("organizations").select("id").eq("stripe_customer_id", customer).maybe_single().execute()
        if org.data:
            db.table("organizations").update({"subscription_status": "canceled"}).eq("id", org.data["id"]).execute()

    return {"received": True}
