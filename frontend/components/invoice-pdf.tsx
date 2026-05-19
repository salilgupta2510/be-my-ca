"use client";
import { Document, Page, Text, View, StyleSheet, pdf } from "@react-pdf/renderer";

const S = StyleSheet.create({
  page: { fontFamily: "Helvetica", fontSize: 9, color: "#1e293b", padding: 32, backgroundColor: "#ffffff" },
  header: { flexDirection: "row", justifyContent: "space-between", marginBottom: 20, paddingBottom: 12, borderBottom: "1 solid #e2e8f0" },
  companyName: { fontSize: 14, fontWeight: "bold", color: "#0f172a" },
  small: { fontSize: 8, color: "#64748b", marginTop: 2 },
  title: { fontSize: 18, fontWeight: "bold", color: "#1e40af", textAlign: "right" },
  invoiceMeta: { textAlign: "right", marginTop: 4 },
  section: { marginBottom: 12 },
  label: { fontSize: 8, color: "#64748b", marginBottom: 2 },
  value: { fontSize: 9, color: "#0f172a" },
  tableHeader: { flexDirection: "row", backgroundColor: "#f1f5f9", padding: "5 8", borderRadius: 2 },
  tableRow: { flexDirection: "row", padding: "5 8", borderBottom: "0.5 solid #e2e8f0" },
  col: { flex: 1 },
  colWide: { flex: 3 },
  colRight: { flex: 1, textAlign: "right" },
  bold: { fontWeight: "bold" },
  totals: { marginTop: 12, alignItems: "flex-end" },
  totalRow: { flexDirection: "row", justifyContent: "space-between", width: 220, marginBottom: 3 },
  grandTotal: { flexDirection: "row", justifyContent: "space-between", width: 220, marginTop: 6, paddingTop: 6, borderTop: "1 solid #1e40af" },
  badge: { backgroundColor: "#eff6ff", padding: "2 6", borderRadius: 3, color: "#1d4ed8", fontSize: 7 },
  footer: { marginTop: 24, paddingTop: 10, borderTop: "0.5 solid #e2e8f0", fontSize: 7.5, color: "#94a3b8", textAlign: "center" },
});

interface Business { legal_name: string; gstin: string; pan: string; state_code: string; }
interface Invoice {
  invoice_number: string; invoice_date: string; customer_name: string;
  customer_gstin: string | null; place_of_supply: string; invoice_type: string;
  taxable_value: string; igst: string; cgst: string; sgst: string; cess: string;
  hsn_code?: string | null;
}

const TYPE_LABELS: Record<string, string> = {
  b2b: "Tax Invoice", b2c_large: "Tax Invoice", b2c_small: "Tax Invoice",
  export: "Export Invoice", credit_note: "Credit Note",
};

function InvoicePDF({ business, invoice }: { business: Business; invoice: Invoice }) {
  const taxable = Number(invoice.taxable_value);
  const igst = Number(invoice.igst);
  const cgst = Number(invoice.cgst);
  const sgst = Number(invoice.sgst);
  const cess = Number(invoice.cess ?? 0);
  const total = taxable + igst + cgst + sgst + cess;
  const fmt = (n: number) => "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: 2 });

  return (
    <Document>
      <Page size="A4" style={S.page}>
        {/* Header */}
        <View style={S.header}>
          <View>
            <Text style={S.companyName}>{business.legal_name}</Text>
            <Text style={S.small}>GSTIN: {business.gstin}</Text>
            <Text style={S.small}>PAN: {business.pan}</Text>
            <Text style={S.small}>State: {business.state_code}</Text>
          </View>
          <View>
            <Text style={S.title}>{TYPE_LABELS[invoice.invoice_type] ?? "TAX INVOICE"}</Text>
            <View style={S.invoiceMeta}>
              <Text style={S.small}>Invoice No: {invoice.invoice_number}</Text>
              <Text style={S.small}>Date: {invoice.invoice_date}</Text>
              <Text style={[S.badge, { marginTop: 4 }]}>{invoice.invoice_type.toUpperCase().replace("_", " ")}</Text>
            </View>
          </View>
        </View>

        {/* Bill To */}
        <View style={[S.section, { flexDirection: "row", gap: 32 }]}>
          <View style={{ flex: 1 }}>
            <Text style={[S.label, { marginBottom: 4 }]}>BILL TO</Text>
            <Text style={[S.value, S.bold]}>{invoice.customer_name}</Text>
            {invoice.customer_gstin && <Text style={S.small}>GSTIN: {invoice.customer_gstin}</Text>}
            <Text style={S.small}>Place of Supply: {invoice.place_of_supply}</Text>
          </View>
          {invoice.hsn_code && (
            <View>
              <Text style={S.label}>HSN / SAC</Text>
              <Text style={[S.value, S.bold]}>{invoice.hsn_code}</Text>
            </View>
          )}
        </View>

        {/* Line items table */}
        <View style={S.tableHeader}>
          <Text style={[S.colWide, S.bold, { fontSize: 8 }]}>Description</Text>
          <Text style={[S.col, S.bold, { fontSize: 8 }]}>HSN</Text>
          <Text style={[S.colRight, S.bold, { fontSize: 8 }]}>Taxable Value</Text>
          {igst > 0 && <Text style={[S.colRight, S.bold, { fontSize: 8 }]}>IGST</Text>}
          {cgst > 0 && <Text style={[S.colRight, S.bold, { fontSize: 8 }]}>CGST</Text>}
          {sgst > 0 && <Text style={[S.colRight, S.bold, { fontSize: 8 }]}>SGST</Text>}
          {cess > 0 && <Text style={[S.colRight, S.bold, { fontSize: 8 }]}>CESS</Text>}
          <Text style={[S.colRight, S.bold, { fontSize: 8 }]}>Amount</Text>
        </View>
        <View style={S.tableRow}>
          <Text style={S.colWide}>Supply of Goods/Services</Text>
          <Text style={S.col}>{invoice.hsn_code ?? "—"}</Text>
          <Text style={S.colRight}>{fmt(taxable)}</Text>
          {igst > 0 && <Text style={S.colRight}>{fmt(igst)}</Text>}
          {cgst > 0 && <Text style={S.colRight}>{fmt(cgst)}</Text>}
          {sgst > 0 && <Text style={S.colRight}>{fmt(sgst)}</Text>}
          {cess > 0 && <Text style={S.colRight}>{fmt(cess)}</Text>}
          <Text style={S.colRight}>{fmt(taxable + igst + cgst + sgst + cess)}</Text>
        </View>

        {/* Totals */}
        <View style={S.totals}>
          <View style={S.totalRow}>
            <Text style={S.label}>Taxable Value</Text>
            <Text style={S.value}>{fmt(taxable)}</Text>
          </View>
          {igst > 0 && <View style={S.totalRow}><Text style={S.label}>IGST</Text><Text style={S.value}>{fmt(igst)}</Text></View>}
          {cgst > 0 && <View style={S.totalRow}><Text style={S.label}>CGST</Text><Text style={S.value}>{fmt(cgst)}</Text></View>}
          {sgst > 0 && <View style={S.totalRow}><Text style={S.label}>SGST</Text><Text style={S.value}>{fmt(sgst)}</Text></View>}
          {cess > 0 && <View style={S.totalRow}><Text style={S.label}>CESS</Text><Text style={S.value}>{fmt(cess)}</Text></View>}
          <View style={S.grandTotal}>
            <Text style={[S.value, S.bold, { color: "#1e40af" }]}>Total Amount</Text>
            <Text style={[S.value, S.bold, { color: "#1e40af" }]}>{fmt(total)}</Text>
          </View>
        </View>

        {/* Footer */}
        <Text style={S.footer}>
          This is a computer generated invoice. Generated by BeMyCa GST Management Platform.
        </Text>
      </Page>
    </Document>
  );
}

export async function downloadInvoicePdf(business: Business, invoice: Invoice) {
  const blob = await pdf(<InvoicePDF business={business} invoice={invoice} />).toBlob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `invoice-${invoice.invoice_number}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}
