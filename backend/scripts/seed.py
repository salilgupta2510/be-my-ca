"""
Seed sample data for all users.
Run: .venv/bin/python scripts/seed.py
"""
import asyncio
import uuid
from datetime import date
from decimal import Decimal

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.models.gst import GSTR2BRecord, ReconciliationResult, IMSAction
from app.models.business import Business, ReturnFrequency
from app.models.invoice import OutwardInvoice, InwardInvoice, InvoiceType, InvoiceSource
from app.models.user import User

PERIOD = "2025-01"

GSTR2B_DATA = [
    {
        "supplier_gstin": "27AABCS1429B1ZB",
        "supplier_name": "AB Corp Private Limited",
        "invoice_number": "INV-2025-001",
        "invoice_date": date(2025, 1, 5),
        "taxable_value": Decimal("100000.00"),
        "igst": Decimal("18000.00"),
        "cgst": Decimal("0.00"),
        "sgst": Decimal("0.00"),
    },
    {
        "supplier_gstin": "29AABCX5432B1ZA",
        "supplier_name": "XYZ Industries Ltd",
        "invoice_number": "XYZ/2025/112",
        "invoice_date": date(2025, 1, 8),
        "taxable_value": Decimal("50000.00"),
        "igst": Decimal("0.00"),
        "cgst": Decimal("4500.00"),
        "sgst": Decimal("4500.00"),
    },
    {
        "supplier_gstin": "06AABCS6543C1ZB",
        "supplier_name": "Sharma Traders",
        "invoice_number": "ST-001-25",
        "invoice_date": date(2025, 1, 12),
        "taxable_value": Decimal("35000.00"),
        "igst": Decimal("0.00"),
        "cgst": Decimal("3150.00"),
        "sgst": Decimal("3150.00"),
    },
    {
        "supplier_gstin": "07AAHCS7382H1ZS",
        "supplier_name": "Delhi Supplies Pvt Ltd",
        "invoice_number": "DS/JAN/2025/45",
        "invoice_date": date(2025, 1, 15),
        "taxable_value": Decimal("75000.00"),
        "igst": Decimal("13500.00"),
        "cgst": Decimal("0.00"),
        "sgst": Decimal("0.00"),
    },
    {
        "supplier_gstin": "33AABCT8765B1ZK",
        "supplier_name": "Tamil Nadu Tech Solutions",
        "invoice_number": "TNTS-2025-007",
        "invoice_date": date(2025, 1, 20),
        "taxable_value": Decimal("20000.00"),
        "igst": Decimal("0.00"),
        "cgst": Decimal("1800.00"),
        "sgst": Decimal("1800.00"),
    },
    # In GSTR-2B but NOT in inward invoices → MISSING_IN_BOOKS
    {
        "supplier_gstin": "19AABCM3421C1ZP",
        "supplier_name": "Mumbai Trading Co",
        "invoice_number": "MTC/2025/88",
        "invoice_date": date(2025, 1, 22),
        "taxable_value": Decimal("45000.00"),
        "igst": Decimal("8100.00"),
        "cgst": Decimal("0.00"),
        "sgst": Decimal("0.00"),
    },
]

OUTWARD_DATA = [
    {
        "invoice_number": "SALE-2025-001",
        "invoice_date": date(2025, 1, 3),
        "customer_name": "Reliance Industries Ltd",
        "customer_gstin": "27AAACR5055K1ZS",
        "place_of_supply": "27",
        "invoice_type": InvoiceType.B2B,
        "taxable_value": Decimal("200000.00"),
        "igst": Decimal("36000.00"),
        "cgst": Decimal("0.00"),
        "sgst": Decimal("0.00"),
        "cess": Decimal("0.00"),
        "source": InvoiceSource.MANUAL,
    },
    {
        "invoice_number": "SALE-2025-002",
        "invoice_date": date(2025, 1, 7),
        "customer_name": "Tata Consultancy Services",
        "customer_gstin": "07AAACT2727Q1ZS",
        "place_of_supply": "07",
        "invoice_type": InvoiceType.B2B,
        "taxable_value": Decimal("150000.00"),
        "igst": Decimal("27000.00"),
        "cgst": Decimal("0.00"),
        "sgst": Decimal("0.00"),
        "cess": Decimal("0.00"),
        "source": InvoiceSource.MANUAL,
    },
    {
        "invoice_number": "SALE-2025-003",
        "invoice_date": date(2025, 1, 10),
        "customer_name": "Local Retail Customer",
        "customer_gstin": None,
        "place_of_supply": "27",
        "invoice_type": InvoiceType.B2C_SMALL,
        "taxable_value": Decimal("15000.00"),
        "igst": Decimal("0.00"),
        "cgst": Decimal("1350.00"),
        "sgst": Decimal("1350.00"),
        "cess": Decimal("0.00"),
        "source": InvoiceSource.MANUAL,
    },
    {
        "invoice_number": "SALE-2025-004",
        "invoice_date": date(2025, 1, 14),
        "customer_name": "Infosys BPM Limited",
        "customer_gstin": "29AACCI1681G1ZT",
        "place_of_supply": "29",
        "invoice_type": InvoiceType.B2B,
        "taxable_value": Decimal("80000.00"),
        "igst": Decimal("14400.00"),
        "cgst": Decimal("0.00"),
        "sgst": Decimal("0.00"),
        "cess": Decimal("0.00"),
        "source": InvoiceSource.MANUAL,
    },
    {
        "invoice_number": "SALE-2025-005",
        "invoice_date": date(2025, 1, 18),
        "customer_name": "Export Customer USA",
        "customer_gstin": None,
        "place_of_supply": "96",
        "invoice_type": InvoiceType.EXPORT,
        "taxable_value": Decimal("300000.00"),
        "igst": Decimal("0.00"),
        "cgst": Decimal("0.00"),
        "sgst": Decimal("0.00"),
        "cess": Decimal("0.00"),
        "source": InvoiceSource.MANUAL,
    },
]

INWARD_DATA = [
    {
        "supplier_name": "AB Corp Pvt Ltd",
        "supplier_gstin": "27AABCS1429B1ZB",
        "invoice_number": "INV-2025-001",
        "invoice_date": date(2025, 1, 5),
        "taxable_value": Decimal("100000.00"),
        "igst": Decimal("18000.00"),
        "cgst": Decimal("0.00"),
        "sgst": Decimal("0.00"),
        "source": "manual",
    },
    {
        "supplier_name": "XYZ Industries",
        "supplier_gstin": "29AABCX5432B1ZA",
        "invoice_number": "XYZ/2025/112",
        "invoice_date": date(2025, 1, 8),
        "taxable_value": Decimal("62500.00"),  # intentional mismatch vs GSTR-2B
        "igst": Decimal("0.00"),
        "cgst": Decimal("5625.00"),
        "sgst": Decimal("5625.00"),
        "source": "manual",
    },
    {
        "supplier_name": "Sharma Traders",
        "supplier_gstin": "06AABCS6543C1ZB",
        "invoice_number": "ST-001-25",
        "invoice_date": date(2025, 1, 12),
        "taxable_value": Decimal("35000.00"),
        "igst": Decimal("0.00"),
        "cgst": Decimal("3150.00"),
        "sgst": Decimal("3150.00"),
        "source": "manual",
    },
    {
        "supplier_name": "Delhi Supplies Private Limited",
        "supplier_gstin": "07AAHCS7382H1ZS",
        "invoice_number": "DS/JAN/2025/45",
        "invoice_date": date(2025, 1, 15),
        "taxable_value": Decimal("75000.00"),
        "igst": Decimal("13500.00"),
        "cgst": Decimal("0.00"),
        "sgst": Decimal("0.00"),
        "source": "tally",
    },
    {
        "supplier_name": "Tamil Nadu Tech Solutions",
        "supplier_gstin": "33AABCT8765B1ZK",
        "invoice_number": "TNTS-2025-007",
        "invoice_date": date(2025, 1, 20),
        "taxable_value": Decimal("20000.00"),
        "igst": Decimal("0.00"),
        "cgst": Decimal("1800.00"),
        "sgst": Decimal("1800.00"),
        "source": "tally",
    },
    # Extra inward not in GSTR-2B → MISSING_IN_2B
    {
        "supplier_name": "Rajasthan Fabrics",
        "supplier_gstin": "08AABCR9876D1ZM",
        "invoice_number": "RF-2025-033",
        "invoice_date": date(2025, 1, 25),
        "taxable_value": Decimal("28000.00"),
        "igst": Decimal("0.00"),
        "cgst": Decimal("2520.00"),
        "sgst": Decimal("2520.00"),
        "source": "manual",
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        users = (await db.scalars(select(User))).all()
        if not users:
            print("No users found. Register first.")
            return

        DEMO_GSTINS = [
            ("27AAPFU0939F1ZV", "27", "AAPFU0939F"),
            ("29AABCS1429B1ZB", "29", "AABCS1429B"),
            ("07AAHCS7382H1ZS", "07", "AAHCS7382H"),
        ]

        for idx, user in enumerate(users):
            # Ensure business exists
            business = await db.scalar(select(Business).where(Business.user_id == user.id))
            if not business:
                gstin, state_code, pan = DEMO_GSTINS[idx % len(DEMO_GSTINS)]
                business = Business(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    legal_name=f"{user.full_name} Enterprises",
                    gstin=gstin,
                    state_code=state_code,
                    pan=pan,
                    return_frequency=ReturnFrequency.MONTHLY,
                )
                db.add(business)
                await db.flush()
                print(f"Created business for {user.email}")

            # Clear existing seed data — order matters for FK constraints
            await db.execute(
                delete(ReconciliationResult).where(
                    ReconciliationResult.user_id == user.id,
                    ReconciliationResult.period == PERIOD,
                )
            )
            await db.execute(
                delete(GSTR2BRecord).where(
                    GSTR2BRecord.user_id == user.id,
                    GSTR2BRecord.period == PERIOD,
                )
            )
            await db.execute(
                delete(OutwardInvoice).where(
                    OutwardInvoice.business_id == business.id,
                    OutwardInvoice.period == PERIOD,
                )
            )
            await db.execute(
                delete(InwardInvoice).where(
                    InwardInvoice.business_id == business.id,
                    InwardInvoice.period == PERIOD,
                )
            )

            for row in GSTR2B_DATA:
                db.add(GSTR2BRecord(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    period=PERIOD,
                    ims_action=IMSAction.PENDING,
                    **row,
                ))

            for row in OUTWARD_DATA:
                db.add(OutwardInvoice(
                    id=uuid.uuid4(),
                    business_id=business.id,
                    period=PERIOD,
                    **row,
                ))

            for row in INWARD_DATA:
                db.add(InwardInvoice(
                    id=uuid.uuid4(),
                    business_id=business.id,
                    period=PERIOD,
                    **row,
                ))

            await db.commit()
            print(
                f"Seeded {len(GSTR2B_DATA)} GSTR-2B + "
                f"{len(OUTWARD_DATA)} outward + "
                f"{len(INWARD_DATA)} inward invoices for {user.email}"
            )


if __name__ == "__main__":
    asyncio.run(seed())
