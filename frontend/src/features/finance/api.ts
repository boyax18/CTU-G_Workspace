import { getJSON, postJSON } from '../../api/client';

export interface Payment {
  id: number;
  reference: string;
  amount: string;
  status: 'pending' | 'verified';
  created_at: string;
}

export interface FinanceSummary {
  total: string | number;
  paid: string | number;
  balance: string | number;
  payments: Payment[];
}

export async function getFinanceSummary(): Promise<FinanceSummary> {
  const result = await getJSON('/api/v1/finance/summary/');
  if (!result || typeof result !== 'object') {
    throw new Error('The server returned an unexpected finance response.');
  }
  const body = result as Partial<FinanceSummary>;
  if (!Array.isArray(body.payments)) {
    throw new Error('The server returned an unexpected payment history.');
  }
  return body as FinanceSummary;
}

export async function submitPayment(amount: number): Promise<Payment> {
  return await postJSON('/api/v1/finance/payments/', { amount }) as Payment;
}
