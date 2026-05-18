from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID
from app.models.invoice import InvoiceType, InvoiceSource


class OutwardInvoiceCreate(BaseModel):
    period: str
    invoice_number: str
    invoice_date: date
    customer_name: str
    customer_gstin: str | None = None
    place_of_supply: str
    invoice_type: InvoiceType = InvoiceType.B2B
    taxable_value: Decimal
    igst: Decimal = Decimal("0")
    cgst: Decimal = Decimal("0")
    sgst: Decimal = Decimal("0")
    cess: Decimal = Decimal("0")


class OutwardInvoiceUpdate(OutwardInvoiceCreate):
    pass


class OutwardInvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    period: str
    invoice_number: str
    invoice_date: date
    customer_name: str
    customer_gstin: str | None
    place_of_supply: str
    invoice_type: InvoiceType
    taxable_value: Decimal
    igst: Decimal
    cgst: Decimal
    sgst: Decimal
    cess: Decimal
    source: InvoiceSource
    created_at: datetime


class InwardInvoiceCreate(BaseModel):
    period: str
    supplier_name: str
    supplier_gstin: str | None = None
    invoice_number: str
    invoice_date: date
    taxable_value: Decimal
    igst: Decimal = Decimal("0")
    cgst: Decimal = Decimal("0")
    sgst: Decimal = Decimal("0")


class InwardInvoiceUpdate(InwardInvoiceCreate):
    pass


class InwardInvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    period: str
    supplier_name: str
    supplier_gstin: str | None
    invoice_number: str
    invoice_date: date
    taxable_value: Decimal
    igst: Decimal
    cgst: Decimal
    sgst: Decimal
    source: str
    created_at: datetime
