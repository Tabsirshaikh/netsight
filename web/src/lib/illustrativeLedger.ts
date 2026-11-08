import { illustrativeEvidence, partB } from '../content.partB';

export type IllustrationRecord = {
  index: number;
  previousHash: string;
  payload: { name: string; value: unknown };
  hash: string;
};

async function digest(value: string): Promise<string> {
  const buffer = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
  return Array.from(new Uint8Array(buffer), byte => byte.toString(16).padStart(2, '0')).join('');
}

function serialise(record: Pick<IllustrationRecord, 'index' | 'previousHash' | 'payload'>): string {
  return JSON.stringify({
    index: record.index,
    previousHash: record.previousHash,
    payload: record.payload
  });
}

export async function makeIllustrativeLedger(): Promise<IllustrationRecord[]> {
  if (!globalThis.crypto?.subtle) throw new Error('Web Crypto unavailable');

  const names = partB.ledger.payloadNames;
  const payloads: IllustrationRecord['payload'][] = [
    { name: names[0], value: 'procedural illustration; no survey geometry measured' },
    { name: names[1], value: illustrativeEvidence.detection },
    { name: names[2], value: illustrativeEvidence.applicability },
    { name: names[3], value: illustrativeEvidence }
  ];
  const records: IllustrationRecord[] = [];
  let previousHash = '0'.repeat(64);
  for (let index = 0; index < payloads.length; index += 1) {
    const record = {
      index,
      previousHash,
      payload: payloads[index]!
    };
    const hash = await digest(serialise(record));
    records.push({ ...record, hash });
    previousHash = hash;
  }
  return records;
}

/** Returns the first record whose payload or incoming link no longer verifies. */
export async function firstBrokenRecord(records: IllustrationRecord[]): Promise<number> {
  let previousHash = '0'.repeat(64);
  for (const record of records) {
    if (record.previousHash !== previousHash) return record.index;
    if (await digest(serialise(record)) !== record.hash) return record.index;
    previousHash = record.hash;
  }
  return -1;
}

export function alterIllustration(records: IllustrationRecord[]): IllustrationRecord[] {
  return records.map(record => record.index === 1
    ? {
        ...record,
        payload: { ...record.payload, value: partB.ledger.changedPayload }
      }
    : record
  );
}
