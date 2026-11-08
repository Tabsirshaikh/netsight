/**
 * Part B editorial additions.
 * Measured results remain in content.ts.
 * Illustration coordinates, schematic chart bars and ledger records are not
 * additional research measurements or real survey detections.
 */
export const partB = {
  common: {
    illustration: 'Procedural illustration · not a survey',
    artwork: 'Illustrative sonar artwork · not validation imagery',
    metric: 'Research model / AP50',
    neverSeen: 'Never-seen surveys',
    previous: 'v0.1',
    current: 'v0.4',
    average: 'Average AP50',
    specialist: 'Ghost-gear specialist',
    arrow: '→'
  },
  detections: {
    footer: 'Different targets. Different limits.',
    box: 'Illustrated target',
    descriptions: [
      'An elongated wreck return with structural ribs and a trailing acoustic shadow.',
      'A small human-shaped return and its acoustic shadow.',
      'A mesh crab pot with bright edges and a dark acoustic shadow.',
      'A trap-like return illustrated under a different sensor texture.',
      'A compact mine-like object with a bright return and acoustic shadow.'
    ],
    files: [
      'sonar-wreck.webp',
      'sonar-person.webp',
      'sonar-pot.webp',
      'sonar-contact.webp',
      'sonar-mine.webp'
    ]
  },
  trust: {
    survey: 'Survey applicability',
    schematic: 'Illustrative gate transition · not a measured decision boundary',
    geometry: 'Pixel geometry',
    diagramTitle: 'A score should mean what it says.',
    diagramNote: 'Schematic reliability diagram · bars are explanatory, not validation bins',
    predicted: 'Predicted probability',
    observed: 'Observed frequency',
    raw: 'Raw score',
    calibrated: 'After calibration',
    fixed: 'Fixed in advance',
    counting: 'Label-free counting rule',
    held: 'Budget held',
    error: 'Measured calibration error',
    slash: '/',
    file: 'trust-water.webp'
  },
  geometry: {
    noRetraining: 'No retraining.',
    instruction: 'One recording. Corrected pixel geometry.',
    scanLabel: 'Illustrated sonar geometry correction',
    caption: 'The illustration changes shape; the reported improvement comes from the stretched-sensor recording.',
    file: 'geometry-seabed.webp'
  },
  curve: {
    metric: 'Crab-pot detection / AP50',
    recordings: 'Training recordings',
    mapLabel: 'Schematic recording tiles, not geographic survey locations',
    tiles: 'Recordings, not neighbouring images',
    sensorLabel: 'Beyond the training sensor',
    footer: 'The unit of experience is a survey.',
    ticks: ['0.0', '0.2', '0.4'],
    tickValues: [0, 0.2, 0.4]
  },
  ledger: {
    report: 'Evidence pack',
    reportType: 'Illustrative export / JSON + report',
    record: 'Record',
    fingerprint: 'SHA-256 · abbreviated',
    original: 'Inspect original',
    change: 'Alter illustration',
    download: 'Download illustrative JSON',
    working: 'Computing illustrative hashes…',
    unavailable: 'Hash verification needs Web Crypto on HTTPS or localhost.',
    linked: 'Hash links verified',
    illustration: 'Demonstration records · not a real detection',
    emptyProbability: 'No probability assigned to this illustration',
    file: 'ledger-depth.webp',
    payloadNames: ['Survey geometry', 'Detection + evidence', 'Applicability', 'Evidence export'],
    changedPayload: 'Illustrative record changed',
    exportName: 'netsight-illustrative-evidence.json'
  },
  video: {
    title: 'From echo to evidence.',
    stages: [
      { title: 'Send sound sideways.', body: 'A towfish pings the seabed. Objects return echoes and cast shadows.' },
      { title: 'Build an image, line by line.', body: 'Each return adds a line to the side-scan waterfall.' },
      { title: 'Find a target. Inspect its evidence.', body: 'The research model proposes detections; shadows, texture and lines add evidence.' },
      { title: 'Put conditions on confidence.', body: 'Calibrate the score. Check whether the survey resembles validated data.' },
      { title: 'Preserve the claim.', body: 'Export JSON and a report in a hash-chained, tamper-evident ledger.' }
    ],
    note: 'Illustrative workflow · not a real survey',
    end: 'See the find. Know its limits.'
  }
} as const;

export const illustrativeEvidence = {
  kind: 'illustrative-evidence-pack',
  project: 'NetSight',
  team: 'SIH26057',
  model: 'research model v0.4',
  detection: {
    source: 'procedural illustration, not a survey',
    target: 'illustrated crab pot',
    detectorScore: null,
    calibratedProbability: null
  },
  supportingEvidence: ['acoustic shadow', 'mesh texture', 'lines'],
  applicability: {
    level: null,
    reason: 'No claim is assigned to procedural artwork.'
  },
  exports: ['JSON', 'report'],
  ledger: 'SHA-256 hash-chained illustrative records'
} as const;
